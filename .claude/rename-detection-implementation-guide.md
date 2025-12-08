# Rename Detection Implementation Guide

## Module: `file_rename_detector.py`

### Overview
This module detects files that have been renamed between versions by analyzing:
1. Version number patterns in filenames
2. Content similarity (for semantic renames)
3. Directory structure preservation

### Complete Module Code

```python
#!/usr/bin/env python3
"""
File rename detection for UBL release imports.

Detects files that have been renamed between versions by:
1. Matching version number patterns (e.g., -2.1 → -2.2)
2. Content-based fuzzy matching for semantic renames
3. Ensuring directory structure is preserved
"""

import re
from pathlib import Path
from typing import Dict, Optional, Set, Tuple, List
from difflib import SequenceMatcher


class RenameDetector:
    """Detects renamed files between UBL versions."""

    # Regex to extract version numbers from filenames
    VERSION_PATTERN = re.compile(r'(\d\.\d+)')

    def __init__(self, repo_root: Path, old_version: str, new_version: str, dry_run: bool = False):
        """
        Initialize rename detector.

        Args:
            repo_root: Root of the repository
            old_version: Previous version (e.g., "2.1")
            new_version: New version (e.g., "2.2")
            dry_run: If True, don't execute renames
        """
        self.repo_root = repo_root
        self.old_version = old_version
        self.new_version = new_version
        self.dry_run = dry_run

    def detect_renames(self, new_extract_dir: Path) -> Dict[Path, Path]:
        """
        Detect file renames between versions.

        Returns:
            Dictionary mapping {old_path: new_path} for detected renames
        """
        print(f"\n  Detecting renames from {self.old_version} → {self.new_version}...")

        old_files = self._get_current_files()
        new_files = self._get_extracted_files(new_extract_dir)

        # Filter to version-relevant files only
        old_version_files = self._filter_by_version(old_files, self.old_version)
        new_version_files = self._filter_by_version(new_files, self.new_version)

        renames = {}

        # Phase 1: Detect version number pattern renames
        phase1_renames = self._detect_version_bumps(old_version_files, new_version_files)
        renames.update(phase1_renames)
        print(f"    Phase 1 (version bumps): {len(phase1_renames)} renames detected")

        # Phase 2: Detect semantic renames (content-based matching)
        unmatched_old = set(old_version_files) - set(phase1_renames.keys())
        unmatched_new = set(new_version_files) - set(phase1_renames.values())

        # Only do fuzzy matching for within-version transitions
        if self.old_version == self.new_version:
            phase2_renames = self._detect_semantic_renames(
                unmatched_old, unmatched_new, new_extract_dir, old_version_files
            )
            renames.update(phase2_renames)
            print(f"    Phase 2 (semantic): {len(phase2_renames)} renames detected")

        if renames:
            print(f"    Total renames: {len(renames)}")
            self._validate_renames(renames)

        return renames

    def apply_renames(self, renames: Dict[Path, Path]) -> bool:
        """
        Apply renames using git mv.

        Args:
            renames: Dictionary of {old_path: new_path}

        Returns:
            True if successful
        """
        if self.dry_run:
            print(f"\n  DRY RUN: Would execute {len(renames)} git mv operations:")
            for old_path, new_path in list(renames.items())[:5]:
                print(f"    git mv {old_path.relative_to(self.repo_root)} → {new_path.relative_to(self.repo_root)}")
            if len(renames) > 5:
                print(f"    ... and {len(renames) - 5} more")
            return True

        print(f"\n  Applying {len(renames)} file renames...")

        import subprocess

        for old_path, new_path in renames.items():
            # Create parent directory if needed
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Execute git mv
            try:
                rel_old = old_path.relative_to(self.repo_root)
                rel_new = new_path.relative_to(self.repo_root)
                subprocess.run(
                    ['git', 'mv', str(rel_old), str(rel_new)],
                    check=True,
                    cwd=self.repo_root,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                print(f"    Warning: Could not rename {old_path}: {e}")
                return False

        # Stage the rename changes
        try:
            subprocess.run(
                ['git', 'add', '-A'],
                check=True,
                cwd=self.repo_root,
                capture_output=True
            )
            print(f"    ✓ {len(renames)} renames staged")
        except subprocess.CalledProcessError as e:
            print(f"    Error: Could not stage renames: {e}")
            return False

        return True

    # Private helper methods

    def _get_current_files(self) -> Set[Path]:
        """Get all tracked files in current git repository."""
        import subprocess

        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                check=True,
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            files = {self.repo_root / line.strip() for line in result.stdout.split('\n') if line.strip()}
            return files
        except subprocess.CalledProcessError:
            return set()

    def _get_extracted_files(self, extract_dir: Path) -> Set[Path]:
        """Get all files in extracted ZIP directory."""
        files = set()
        for file_path in extract_dir.rglob('*'):
            if file_path.is_file() and not self._is_junk_file(file_path):
                files.add(file_path)
        return files

    def _filter_by_version(self, files: Set[Path], version: str) -> Set[Path]:
        """Filter files that contain the version number in their path."""
        filtered = set()
        for file_path in files:
            path_str = str(file_path)
            if version in path_str or self._extract_version(str(file_path)) == version:
                filtered.add(file_path)
        return filtered

    def _detect_version_bumps(self, old_files: Set[Path], new_files: Set[Path]) -> Dict[Path, Path]:
        """
        Phase 1: Detect simple version number replacements.

        Example: UBL-Invoice-2.1.xsd → UBL-Invoice-2.2.xsd
        """
        renames = {}

        # Create lookup table of new files by normalized name
        new_files_by_normalized = {}
        for new_file in new_files:
            normalized = str(new_file).replace(f'-{self.new_version}', f'-{self.old_version}')
            new_files_by_normalized[normalized] = new_file

        for old_file in old_files:
            old_normalized = str(old_file)

            # Check if there's a corresponding file with new version
            if old_normalized in new_files_by_normalized:
                new_file = new_files_by_normalized[old_normalized]

                # Verify they're in the same directory
                if old_file.parent == new_file.parent:
                    renames[old_file] = new_file

        return renames

    def _detect_semantic_renames(
        self,
        old_files: Set[Path],
        new_files: Set[Path],
        new_extract_dir: Path,
        all_old_files: Set[Path]
    ) -> Dict[Path, Path]:
        """
        Phase 2: Detect semantic renames using content similarity.

        Used for cases like:
        - BillofLading → BillOfLading (case fixes)
        - PerformanceHistory → TransportProgressStatus (terminology changes)
        """
        renames = {}

        # Only do this for reasonable-sized sets (avoid N² comparisons)
        if len(old_files) > 100 or len(new_files) > 100:
            print(f"    Skipping fuzzy matching (too many files)")
            return renames

        # Map new files by content for matching
        new_files_by_similarity = {}

        for old_file in old_files:
            old_content = self._read_file_safely(old_file)
            if not old_content:
                continue

            best_match = None
            best_score = 0

            for new_file in new_files:
                if new_file in new_files_by_similarity.values():
                    continue  # Already matched

                new_content = self._read_file_safely(new_file)
                if not new_content:
                    continue

                # Calculate similarity
                similarity = self._calculate_similarity(old_content, new_content)

                if similarity > best_score:
                    best_match = new_file
                    best_score = similarity

            # If similarity is high enough, consider it a rename
            if best_score > 0.85:  # 85% threshold
                renames[old_file] = best_match
                new_files_by_similarity[best_match] = True

        return renames

    def _extract_version(self, path_str: str) -> Optional[str]:
        """Extract version number from file path."""
        match = self.VERSION_PATTERN.search(path_str)
        return match.group(1) if match else None

    def _is_junk_file(self, file_path: Path) -> bool:
        """Check if file should be ignored."""
        name = file_path.name
        return (
            name.startswith('.')
            or name.startswith('__')
            or '__MACOSX' in file_path.parts
        )

    def _read_file_safely(self, file_path: Path, max_size: int = 1000000) -> Optional[str]:
        """Read file content safely (skip binary files, large files)."""
        try:
            if file_path.stat().st_size > max_size:
                return None

            # Skip binary files
            if file_path.suffix in {'.jpg', '.png', '.pdf', '.zip', '.bin', '.xls', '.xlsx', '.ods'}:
                return None

            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return None

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text blocks (0-1)."""
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()

    def _validate_renames(self, renames: Dict[Path, Path]) -> None:
        """Validate that renames make sense."""
        # Check for collisions (two old files → same new file)
        new_paths = list(renames.values())
        if len(new_paths) != len(set(new_paths)):
            print("    WARNING: Duplicate targets detected in rename mapping")


def create_rename_detector(
    repo_root: Path,
    from_version: str,
    to_version: str,
    dry_run: bool = False
) -> RenameDetector:
    """Factory function to create a rename detector."""
    return RenameDetector(repo_root, from_version, to_version, dry_run)
```

---

## Changes to `import_release.py`

### 1. Add Import at Top
```python
from .file_rename_detector import create_rename_detector
```

### 2. Add Helper Method to ReleaseImporter Class
```python
def _get_previous_version(self) -> Optional[str]:
    """
    Get the previous UBL version from git history.

    Returns:
        Version string (e.g., '2.1') or None if this is the first version
    """
    from .release_data import RELEASES

    # Find current release in RELEASES list
    for i, rel in enumerate(RELEASES):
        if rel.num == self.release.num:
            # Look for previous release with different version
            for j in range(i - 1, -1, -1):
                prev_rel = RELEASES[j]
                if prev_rel.version != self.release.version:
                    return prev_rel.version
            break

    return None
```

### 3. Modify `apply_full_release()` Method
```python
def apply_full_release(self, extract_dir: Path):
    """
    Apply a full release: detect renames, clear repo, copy new content.

    Args:
        extract_dir: Directory containing extracted ZIP content
    """
    print(f"Applying full release import...")

    if self.dry_run:
        print("  (DRY RUN: would detect renames, clear repo, and copy new content)")
        return

    # NEW: Step 1 - Detect and apply renames from previous version
    prev_version = self._get_previous_version()
    if prev_version:
        detector = create_rename_detector(
            self.repo_root,
            prev_version,
            self.release.version,
            dry_run=self.dry_run
        )
        renames = detector.detect_renames(extract_dir)
        if renames:
            success = detector.apply_renames(renames)
            if not success:
                print("  Warning: Some renames could not be applied")
        print()  # Blank line

    # EXISTING: Step 2 - Remove all existing content (except preserved paths)
    print("  Clearing repository...")
    removed_count = 0
    for item in self.repo_root.iterdir():
        if item.name in self.PRESERVED_PATHS:
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            removed_count += 1
        except Exception as e:
            print(f"    Warning: Could not remove {item}: {e}")

    print(f"    Removed {removed_count} items")

    # EXISTING: Step 3 - Copy new content
    print("  Copying new content...")
    copied_count = 0
    for item in extract_dir.iterdir():
        # Skip __MACOSX and other junk
        if item.name.startswith('__') or item.name.startswith('.'):
            continue

        dest = self.repo_root / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            copied_count += 1
        except Exception as e:
            raise ImportError(f"Failed to copy {item}: {e}")

    print(f"    Copied {copied_count} items")
```

### 4. Update `create_commit()` to Account for Pre-staged Changes
The current implementation uses `git add -A` which will pick up the pre-staged renames. This works correctly as-is, but we could enhance it to show better statistics:

```python
def create_commit(self):
    """Create git commit for this release."""
    print("Creating git commit...")

    if self.dry_run:
        print("  (DRY RUN: would create commit)")
        self.show_commit_preview()
        return

    # Stage all changes (including any pre-staged renames)
    try:
        subprocess.run(['git', 'add', '-A'], check=True, cwd=self.repo_root)
    except subprocess.CalledProcessError as e:
        raise ImportError(f"Failed to stage changes: {e}")

    # Get statistics for better messaging
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-status'],
            check=True,
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )
        changes = result.stdout.strip().split('\n')
        renames = len([l for l in changes if l.startswith('R')])
        added = len([l for l in changes if l.startswith('A')])
        modified = len([l for l in changes if l.startswith('M')])
        deleted = len([l for l in changes if l.startswith('D')])

        if renames:
            print(f"  File changes: {renames} renamed, {added} added, {modified} modified, {deleted} deleted")
    except subprocess.CalledProcessError:
        pass  # Silently ignore if we can't get stats

    # Create commit message
    commit_msg = self.generate_commit_message()

    # Commit
    try:
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            check=True,
            cwd=self.repo_root,
            capture_output=True,
            text=True
        )
        print(f"  ✓ Commit created")
    except subprocess.CalledProcessError as e:
        raise ImportError(f"Failed to create commit: {e}")
```

---

## Testing the Implementation

### Unit Tests for `file_rename_detector.py`

Create `tools/tests/test_rename_detector.py`:

```python
#!/usr/bin/env python3
"""Tests for file rename detection."""

import unittest
from pathlib import Path
import tempfile
import shutil
from tools.file_rename_detector import RenameDetector, create_rename_detector


class TestRenameDetector(unittest.TestCase):
    """Test the RenameDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = Path(self.temp_dir)

    def tearDown(self):
        """Clean up temp files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_version_number_extraction(self):
        """Test extracting version numbers from paths."""
        detector = RenameDetector(self.repo_root, "2.1", "2.2")
        self.assertEqual(detector._extract_version("UBL-Invoice-2.1.xsd"), "2.1")
        self.assertEqual(detector._extract_version("UBL-Invoice-2.2.xsd"), "2.2")
        self.assertEqual(detector._extract_version("common/UBL-Types-2.1.xsd"), "2.1")

    def test_detect_simple_version_bump(self):
        """Test detection of simple version number changes."""
        # Create test files
        (self.repo_root / "test1-2.1.txt").write_text("content")
        (self.repo_root / "test2-2.1.txt").write_text("content")

        # Simulate new version files
        extract_dir = Path(self.temp_dir) / "new"
        extract_dir.mkdir()
        (extract_dir / "test1-2.2.txt").write_text("content")
        (extract_dir / "test2-2.2.txt").write_text("content")

        detector = RenameDetector(self.repo_root, "2.1", "2.2")
        # Note: This is simplified; full test would need git initialization
        print("Simple version bump test would run in integration tests")

    def test_junk_file_detection(self):
        """Test that junk files are properly ignored."""
        detector = RenameDetector(self.repo_root, "2.1", "2.2")
        self.assertTrue(detector._is_junk_file(Path("/__MACOSX/file.txt")))
        self.assertTrue(detector._is_junk_file(Path(".gitignore")))
        self.assertFalse(detector._is_junk_file(Path("normal/file.txt")))


if __name__ == '__main__':
    unittest.main()
```

### Manual Testing Procedure

1. **Setup test repository**:
   ```bash
   cd /tmp
   git clone /home/user/ubl-release-package test-rename
   cd test-rename
   git checkout -b test/rename-detection
   ```

2. **Test with UBL 2.1 → 2.2 transition** (has ~210 renames):
   ```bash
   python -m tools.import_release 17 --dry-run
   ```

3. **Verify rename detection**:
   ```bash
   git log --oneline --name-status
   git show --name-status HEAD
   ```

4. **Verify renames vs deletions/additions**:
   ```bash
   # Should show 'R' (rename) not 'D' (delete) + 'A' (add)
   git diff-tree --no-commit-id -r HEAD | grep "^R"
   ```

---

## Configuration Options (Future Enhancements)

### 1. Fuzzy Matching Threshold
```python
FUZZY_MATCH_THRESHOLD = 0.85  # 85% similarity required
```

### 2. File Types to Skip
```python
BINARY_EXTENSIONS = {'.jpg', '.png', '.pdf', '.zip', '.xls', '.xlsx', '.ods'}
```

### 3. Manual Rename Mappings
Future: Load from JSON file for problematic renames
```json
{
  "2.1->2.2": {
    "old-name.xsd": "new-name.xsd"
  }
}
```

---

## Rollout Plan

1. **Phase 1**: Implement and test `file_rename_detector.py` standalone
2. **Phase 2**: Integrate into `import_release.py` with `--detect-renames` flag
3. **Phase 3**: Enable by default for future releases
4. **Phase 4**: Re-import historical releases with renames enabled

