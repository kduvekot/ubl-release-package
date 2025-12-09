#!/usr/bin/env python3
"""
File rename detection for UBL release imports.

Detects files renamed between versions by:
1. Version number patterns (UBL-Invoice-2.1.xsd → UBL-Invoice-2.2.xsd)
2. Content similarity for semantic renames (within-version only)

This module enables proper git rename tracking, so instead of:
  D  UBL-Invoice-2.1.xsd
  A  UBL-Invoice-2.2.xsd

Git shows:
  R  UBL-Invoice-2.1.xsd -> UBL-Invoice-2.2.xsd

Benefits:
- git blame shows true file origins
- git diff shows actual changes, not whole-file rewrites
- git log --follow tracks file history across renames
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, Optional, Set, List, Tuple
from difflib import SequenceMatcher


class RenameDetector:
    """Detects and applies renamed files between UBL versions."""

    VERSION_PATTERN = re.compile(r'(\d\.\d+)')

    def __init__(self, repo_root: Path, old_version: str, new_version: str, dry_run: bool = False):
        self.repo_root = repo_root
        self.old_version = old_version
        self.new_version = new_version
        self.dry_run = dry_run

    def detect_renames(self, old_files: Set[Path], new_files: Set[Path]) -> Dict[Path, Path]:
        """
        Detect file renames between versions.

        Args:
            old_files: Set of files in the current (old) state (relative paths)
            new_files: Set of files in the new extract (relative paths)

        Returns:
            Dictionary mapping {old_path: new_path} for detected renames
        """
        print(f"\n  Detecting renames from {self.old_version} → {self.new_version}...")

        # Filter to version-relevant files
        old_version_files = {f for f in old_files if self.old_version in str(f)}
        new_version_files = {f for f in new_files if self.new_version in str(f)}

        renames = {}

        # Phase 1: Version number pattern matching
        for old_file in old_version_files:
            # Try replacing old version with new version in filename
            old_str = str(old_file)

            # Handle different version patterns in filenames
            # e.g., UBL-Invoice-2.1.xsd → UBL-Invoice-2.2.xsd
            # e.g., CCTS_CCT-2.1.xsd → CCTS_CCT-2.2.xsd
            potential_new_str = old_str.replace(f'-{self.old_version}', f'-{self.new_version}')
            potential_new_str = potential_new_str.replace(f'_{self.old_version}', f'_{self.new_version}')
            potential_new = Path(potential_new_str)

            if potential_new in new_version_files:
                # Also verify same parent directory (don't match across directory restructures)
                if old_file.parent == potential_new.parent:
                    renames[old_file] = potential_new

        print(f"    Phase 1 (version bumps): {len(renames)} renames detected")

        # Phase 2: Fuzzy matching for semantic renames (only same-version transitions)
        # This is for patches/errata that might rename files within the same version
        if self.old_version == self.new_version:
            unmatched_old = old_version_files - set(renames.keys())
            unmatched_new = new_version_files - set(renames.values())

            if len(unmatched_old) < 100 and len(unmatched_new) < 100:
                semantic_renames = self._fuzzy_match(unmatched_old, unmatched_new)
                renames.update(semantic_renames)
                if semantic_renames:
                    print(f"    Phase 2 (semantic): {len(semantic_renames)} renames detected")

        if renames:
            print(f"    Total: {len(renames)} renames")
        else:
            print(f"    No renames detected (version transition or first import)")

        return renames

    def apply_renames(self, renames: Dict[Path, Path], extract_dir: Path) -> Set[Path]:
        """
        Apply renames using git mv, then update content from extract.

        Args:
            renames: Dictionary mapping old_path → new_path (relative paths)
            extract_dir: Directory containing extracted new release content

        Returns:
            Set of new_paths that were successfully renamed (for exclusion from copy)
        """
        if not renames:
            return set()

        if self.dry_run:
            print(f"\n  DRY RUN: Would execute {len(renames)} git mv operations")
            for old_path, new_path in list(renames.items())[:5]:
                print(f"    git mv {old_path} → {new_path}")
            if len(renames) > 5:
                print(f"    ... and {len(renames) - 5} more")
            return set(renames.values())

        print(f"\n  Applying {len(renames)} file renames...")

        successfully_renamed = set()  # Track successful new paths
        failed = []

        for old_path, new_path in renames.items():
            old_abs = self.repo_root / old_path
            new_abs = self.repo_root / new_path

            # Ensure parent directory exists for new path
            new_abs.parent.mkdir(parents=True, exist_ok=True)

            try:
                # Use git mv to preserve rename tracking
                result = subprocess.run(
                    ['git', 'mv', str(old_path), str(new_path)],
                    check=True,
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True
                )
                successfully_renamed.add(new_path)
            except subprocess.CalledProcessError as e:
                failed.append((old_path, new_path, str(e)))
                continue

        if failed:
            print(f"    Warning: {len(failed)} renames failed:")
            for old_p, new_p, err in failed[:3]:
                print(f"      {old_p} → {new_p}: {err}")
            if len(failed) > 3:
                print(f"      ... and {len(failed) - 3} more")

        print(f"    ✓ {len(successfully_renamed)} renames applied via git mv")
        return successfully_renamed

    def update_renamed_files_content(self, renames: Dict[Path, Path], extract_dir: Path) -> int:
        """
        Update the content of renamed files with new version content.

        After git mv, the files have old content but new names.
        This copies the actual new content over.

        Args:
            renames: Dictionary mapping old_path → new_path (relative paths)
            extract_dir: Directory containing extracted new release content

        Returns:
            Number of files updated
        """
        if self.dry_run:
            return len(renames)

        updated = 0
        for old_path, new_path in renames.items():
            # Find source file in extract directory
            source = extract_dir / new_path
            dest = self.repo_root / new_path

            if source.exists():
                try:
                    # Copy content (file already exists due to git mv)
                    import shutil
                    shutil.copy2(source, dest)
                    updated += 1
                except Exception as e:
                    print(f"    Warning: Failed to update content for {new_path}: {e}")

        return updated

    def _fuzzy_match(self, old_files: Set[Path], new_files: Set[Path]) -> Dict[Path, Path]:
        """
        Detect semantic renames using content similarity (85% threshold).

        Only used for same-version transitions (patches/errata).
        """
        renames = {}
        matched_new = set()

        for old_file in old_files:
            old_abs = self.repo_root / old_file
            old_content = self._read_file_safely(old_abs)
            if not old_content:
                continue

            best_match = None
            best_score = 0

            for new_file in new_files:
                if new_file in matched_new:
                    continue

                # For fuzzy matching, we'd need the new file content
                # This is tricky since new files are in extract_dir
                # For now, skip fuzzy matching - version bumps cover most cases
                pass

            if best_score > 0.85 and best_match:
                renames[old_file] = best_match
                matched_new.add(best_match)

        return renames

    def _read_file_safely(self, file_path: Path, max_size: int = 1000000) -> Optional[str]:
        """Read file content, skip binary and large files."""
        try:
            if not file_path.exists():
                return None
            if file_path.stat().st_size > max_size:
                return None
            if file_path.suffix.lower() in {'.jpg', '.png', '.pdf', '.zip', '.xls', '.xlsx', '.ods', '.bin', '.gif'}:
                return None
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None


def create_rename_detector(repo_root: Path, old_version: str, new_version: str,
                          dry_run: bool = False) -> RenameDetector:
    """Factory function to create a RenameDetector."""
    return RenameDetector(repo_root, old_version, new_version, dry_run)


def get_previous_version(releases: list, current_release) -> Optional[str]:
    """
    Get the previous UBL version from the release list.

    Returns the version of the most recent release with a different version number.
    """
    for i, rel in enumerate(releases):
        if rel.num == current_release.num:
            for j in range(i - 1, -1, -1):
                prev_rel = releases[j]
                if prev_rel.version != current_release.version:
                    return prev_rel.version
            break
    return None
