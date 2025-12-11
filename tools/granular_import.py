#!/usr/bin/env python3
"""
Granular UBL Release Importer with Per-File Tracking

This tool processes release packages file-by-file, classifying each file as:
- NEW: File doesn't exist in previous state
- RENAMED: File name changed due to version bump (detected via pattern matching)
- DELETED: File existed before but not in current release
- MODIFIED: File exists in both but content changed

Key features:
- Processes releases in correct order (1 to 34)
- Tracks each file change individually
- Validates repo state after processing each file
- Supports testing with local git repos (preserves existing repos)
- Multiple commit strategies (per-file, per-type, per-release)

Usage:
    # Production mode: run from within existing repo
    cd /path/to/repo && python3 /path/to/tools/granular_import.py --release 9

    # Test mode: creates/reuses test repo (preserves if .git exists)
    python -m tools.granular_import --release 1 --test-repo /tmp/test-repo
    python -m tools.granular_import --range 1 5 --commit-strategy per_type
"""

import argparse
import enum
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.release_data import RELEASES, Release, get_release_by_num
from tools.gdrive_downloader import download_release_from_gdrive


class ChangeType(enum.Enum):
    """Types of file changes between releases."""
    NEW = "new"           # File is new (didn't exist before)
    RENAMED = "renamed"   # File renamed (version bump pattern)
    DELETED = "deleted"   # File removed (existed before, not now)
    MODIFIED = "modified" # File content changed


@dataclass
class FileChange:
    """Represents a single file change between releases."""
    change_type: ChangeType
    new_path: Optional[Path] = None   # Path in new release (None for deletions)
    old_path: Optional[Path] = None   # Path in old state (None for additions)
    content_hash: Optional[str] = None  # Hash of new content (for validation)

    def __str__(self):
        if self.change_type == ChangeType.NEW:
            return f"ADD {self.new_path}"
        elif self.change_type == ChangeType.RENAMED:
            return f"RENAME {self.old_path} -> {self.new_path}"
        elif self.change_type == ChangeType.DELETED:
            return f"DELETE {self.old_path}"
        elif self.change_type == ChangeType.MODIFIED:
            return f"MODIFY {self.new_path}"
        return f"{self.change_type.value} {self.new_path or self.old_path}"


@dataclass
class ReleaseChangeset:
    """All changes needed to transition from one release state to another."""
    release: Release
    previous_release: Optional[Release]
    changes: List[FileChange] = field(default_factory=list)

    @property
    def renames(self) -> List[FileChange]:
        return [c for c in self.changes if c.change_type == ChangeType.RENAMED]

    @property
    def deletions(self) -> List[FileChange]:
        return [c for c in self.changes if c.change_type == ChangeType.DELETED]

    @property
    def additions(self) -> List[FileChange]:
        return [c for c in self.changes if c.change_type == ChangeType.NEW]

    @property
    def modifications(self) -> List[FileChange]:
        return [c for c in self.changes if c.change_type == ChangeType.MODIFIED]

    def summary(self) -> str:
        return (f"Release #{self.release.num} ({self.release.tag_name}): "
                f"{len(self.renames)} renames, {len(self.deletions)} deletions, "
                f"{len(self.additions)} additions, {len(self.modifications)} modifications")


# Infrastructure paths to preserve (never deleted/modified)
PRESERVED_PATHS = {'.git', '.gitignore', '.claude', 'tools', 'README.md'}


def file_hash(filepath: Path) -> str:
    """Calculate MD5 hash of a file for comparison."""
    if not filepath.exists():
        return ""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def is_preserved_path(path: Path) -> bool:
    """Check if a path should be preserved (infrastructure)."""
    parts = path.parts
    if not parts:
        return False
    return parts[0] in PRESERVED_PATHS


def get_repo_files(repo_root: Path) -> Dict[Path, str]:
    """
    Get all git-tracked UBL content files with their hashes.

    Returns:
        Dict mapping relative path to file hash
    """
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            check=True, capture_output=True, text=True, cwd=repo_root
        )
        files = {}
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            path = Path(line)
            if not is_preserved_path(path):
                abs_path = repo_root / path
                if abs_path.exists() and abs_path.is_file():
                    files[path] = file_hash(abs_path)
        return files
    except subprocess.CalledProcessError:
        return {}


def get_zip_files(extract_dir: Path) -> Dict[Path, str]:
    """
    Get all files from extracted ZIP with their hashes.

    Returns:
        Dict mapping relative path to file hash
    """
    files = {}
    for file_path in extract_dir.rglob('*'):
        if not file_path.is_file():
            continue
        # Skip junk files
        if file_path.name.startswith('.') or file_path.name.startswith('__'):
            continue
        if '__MACOSX' in file_path.parts:
            continue

        rel_path = file_path.relative_to(extract_dir)
        files[rel_path] = file_hash(file_path)
    return files


def detect_version_rename(old_path: Path, old_version: str, new_version: str) -> Optional[Path]:
    """
    Detect if a file would be renamed due to version bump.

    E.g., UBL-Invoice-2.1.xsd -> UBL-Invoice-2.2.xsd
    """
    old_str = str(old_path)

    # Try various version patterns in the filename
    patterns = [
        (f'-{old_version}', f'-{new_version}'),  # UBL-Invoice-2.1.xsd
        (f'_{old_version}', f'_{new_version}'),  # CCTS_CCT-2.1.xsd
        (f'{old_version}.', f'{new_version}.'),  # UBL-2.1.xml
    ]

    for old_pattern, new_pattern in patterns:
        if old_pattern in old_str:
            new_str = old_str.replace(old_pattern, new_pattern, 1)
            return Path(new_str)

    return None


def compute_changeset(
    repo_files: Dict[Path, str],
    zip_files: Dict[Path, str],
    release: Release,
    previous_release: Optional[Release]
) -> ReleaseChangeset:
    """
    Compute all file changes needed to transition to this release.

    Args:
        repo_files: Current repo state {path: hash}
        zip_files: New release contents {path: hash}
        release: Target release
        previous_release: Previous release (for version detection)

    Returns:
        ReleaseChangeset with all classified changes
    """
    changeset = ReleaseChangeset(release=release, previous_release=previous_release)

    old_version = previous_release.version if previous_release else None
    new_version = release.version

    # Track which files have been matched
    matched_old: Set[Path] = set()
    matched_new: Set[Path] = set()

    # Step 1: Detect renames (version bumps)
    if old_version and old_version != new_version:
        for old_path in repo_files:
            potential_new = detect_version_rename(old_path, old_version, new_version)
            if potential_new and potential_new in zip_files:
                # Verify same parent directory (don't match across restructures)
                if old_path.parent == potential_new.parent:
                    changeset.changes.append(FileChange(
                        change_type=ChangeType.RENAMED,
                        old_path=old_path,
                        new_path=potential_new,
                        content_hash=zip_files[potential_new]
                    ))
                    matched_old.add(old_path)
                    matched_new.add(potential_new)

    # Step 2: Find exact path matches that need modification
    for path in set(repo_files.keys()) & set(zip_files.keys()):
        if path in matched_old or path in matched_new:
            continue
        if repo_files[path] != zip_files[path]:
            changeset.changes.append(FileChange(
                change_type=ChangeType.MODIFIED,
                new_path=path,
                old_path=path,
                content_hash=zip_files[path]
            ))
        matched_old.add(path)
        matched_new.add(path)

    # Step 3: Find deletions (in repo but not in new release)
    # IMPORTANT: For PATCH releases, only files in the patch are processed.
    # Files not in the patch are preserved (not deleted).
    if not release.is_patch:
        for old_path in repo_files:
            if old_path not in matched_old:
                changeset.changes.append(FileChange(
                    change_type=ChangeType.DELETED,
                    old_path=old_path
                ))

    # Step 4: Find additions (in new release but not matched)
    for new_path in zip_files:
        if new_path not in matched_new:
            changeset.changes.append(FileChange(
                change_type=ChangeType.NEW,
                new_path=new_path,
                content_hash=zip_files[new_path]
            ))

    return changeset


def apply_change(
    change: FileChange,
    repo_root: Path,
    extract_dir: Path,
    dry_run: bool = False
) -> bool:
    """
    Apply a single file change to the repository.

    Returns:
        True if successful
    """
    try:
        if dry_run:
            print(f"    [DRY RUN] {change}")
            return True

        if change.change_type == ChangeType.RENAMED:
            # Use git mv for rename tracking
            old_abs = repo_root / change.old_path
            new_abs = repo_root / change.new_path

            # Ensure parent directory exists
            new_abs.parent.mkdir(parents=True, exist_ok=True)

            # Git mv
            subprocess.run(
                ['git', 'mv', str(change.old_path), str(change.new_path)],
                check=True, cwd=repo_root, capture_output=True
            )

            # Update content from ZIP
            src = extract_dir / change.new_path
            if src.exists():
                shutil.copy2(src, new_abs)

        elif change.change_type == ChangeType.DELETED:
            subprocess.run(
                ['git', 'rm', '-f', '--quiet', str(change.old_path)],
                check=True, cwd=repo_root, capture_output=True
            )

        elif change.change_type == ChangeType.NEW:
            dest = repo_root / change.new_path
            src = extract_dir / change.new_path

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

        elif change.change_type == ChangeType.MODIFIED:
            dest = repo_root / change.new_path
            src = extract_dir / change.new_path
            shutil.copy2(src, dest)

        return True

    except Exception as e:
        print(f"    ERROR applying {change}: {e}")
        return False


def validate_file(
    change: FileChange,
    repo_root: Path,
    extract_dir: Path
) -> Tuple[bool, str]:
    """
    Validate that a single file change was applied correctly.

    Returns:
        (is_valid, error_message)
    """
    if change.change_type == ChangeType.DELETED:
        # File should not exist
        path = repo_root / change.old_path
        if path.exists():
            return False, f"File should be deleted but exists: {change.old_path}"
        return True, ""

    elif change.change_type in (ChangeType.NEW, ChangeType.RENAMED, ChangeType.MODIFIED):
        # File should exist with correct content
        repo_path = repo_root / change.new_path
        zip_path = extract_dir / change.new_path

        if not repo_path.exists():
            return False, f"File missing: {change.new_path}"

        if not zip_path.exists():
            return False, f"Source file missing in ZIP: {change.new_path}"

        repo_hash = file_hash(repo_path)
        zip_hash = file_hash(zip_path)

        if repo_hash != zip_hash:
            return False, f"Content mismatch: {change.new_path}"

        return True, ""

    return True, ""


def validate_repo_matches_release(
    repo_root: Path,
    extract_dir: Path,
    release: Release
) -> Tuple[bool, List[str]]:
    """
    Validate that the repository matches the release package.

    For FULL releases: repo should match package exactly
    For PATCH releases: repo should contain all patch files (may have extras from base)

    Returns:
        (is_valid, list of error messages)
    """
    errors = []

    repo_files = get_repo_files(repo_root)
    zip_files = get_zip_files(extract_dir)

    # Check for missing files
    missing = set(zip_files.keys()) - set(repo_files.keys())
    for f in sorted(missing):
        errors.append(f"MISSING: {f}")

    # Check for extra files (only for FULL releases)
    # PATCH releases are overlays, so extra files are expected
    if not release.is_patch:
        extra = set(repo_files.keys()) - set(zip_files.keys())
        for f in sorted(extra):
            errors.append(f"EXTRA: {f}")

    # Check content mismatches
    common = set(repo_files.keys()) & set(zip_files.keys())
    for f in sorted(common):
        if repo_files[f] != zip_files[f]:
            errors.append(f"DIFFERS: {f}")

    return len(errors) == 0, errors


def download_and_extract(release: Release, temp_dir: Path) -> Path:
    """Download and extract a release, return the content directory."""
    print(f"  Downloading release #{release.num}...")

    zip_path = temp_dir / "release.zip"
    download_release_from_gdrive(
        release.num, release.stage, release.version, zip_path
    )

    print(f"  Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(temp_dir)

    # Find content directory (might be nested)
    subdirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name != '__MACOSX']
    if len(subdirs) == 1:
        subdir = subdirs[0]
        if any((subdir / name).exists() for name in ['xsd', 'xsdrt', 'doc', 'cl', 'mod']):
            return subdir

    return temp_dir


def create_commit(
    repo_root: Path,
    message: str,
    dry_run: bool = False
) -> bool:
    """Stage all changes and create a commit."""
    if dry_run:
        print(f"    [DRY RUN] Would commit: {message[:60]}...")
        return True

    try:
        # Stage all changes
        subprocess.run(['git', 'add', '-A'], check=True, cwd=repo_root, capture_output=True)

        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=repo_root, capture_output=True
        )

        if result.returncode == 0:
            # No changes staged
            return True

        # Create commit
        subprocess.run(
            ['git', 'commit', '-m', message],
            check=True, cwd=repo_root, capture_output=True
        )
        return True

    except subprocess.CalledProcessError as e:
        print(f"    ERROR creating commit: {e}")
        return False


def import_release_granular(
    release: Release,
    repo_root: Path,
    previous_release: Optional[Release] = None,
    commit_strategy: str = "per_type",  # per_file, per_type, per_release
    validate_each_file: bool = False,
    dry_run: bool = False
) -> bool:
    """
    Import a single release with granular file tracking.

    Args:
        release: The release to import
        repo_root: Path to git repository
        previous_release: The previous release (for rename detection)
        commit_strategy: How to batch commits
        validate_each_file: Validate after each file change
        dry_run: Don't make actual changes

    Returns:
        True if successful
    """
    print(f"\n{'='*70}")
    print(f"Importing Release #{release.num}: {release.tag_name}")
    print(f"{'='*70}")
    print(f"  Version: {release.version}, Stage: {release.stage}")
    print(f"  Type: {release.release_type}, Date: {release.date}")
    print(f"  Commit strategy: {commit_strategy}")

    temp_dir = Path(tempfile.mkdtemp(prefix='ubl-granular-'))

    try:
        # Download and extract
        extract_dir = download_and_extract(release, temp_dir)

        # Get current repo state
        repo_files = get_repo_files(repo_root)
        zip_files = get_zip_files(extract_dir)

        print(f"  Current repo files: {len(repo_files)}")
        print(f"  New release files: {len(zip_files)}")

        # Compute changeset
        changeset = compute_changeset(repo_files, zip_files, release, previous_release)
        print(f"\n  {changeset.summary()}")

        # Process changes based on strategy
        if commit_strategy == "per_file":
            # Each file gets its own commit
            for change in changeset.changes:
                if apply_change(change, repo_root, extract_dir, dry_run):
                    if validate_each_file:
                        valid, err = validate_file(change, repo_root, extract_dir)
                        if not valid:
                            print(f"    VALIDATION FAILED: {err}")
                            return False

                    create_commit(repo_root, str(change), dry_run)

        elif commit_strategy == "per_type":
            # Batch by change type in order: renames, deletions, additions, modifications

            # 1. Renames first (must happen before deletions)
            if changeset.renames:
                print(f"\n  Applying {len(changeset.renames)} renames...")
                for change in changeset.renames:
                    apply_change(change, repo_root, extract_dir, dry_run)
                create_commit(
                    repo_root,
                    f"Release #{release.num}: Rename {len(changeset.renames)} files ({release.version})",
                    dry_run
                )

            # 2. Deletions
            if changeset.deletions:
                print(f"  Applying {len(changeset.deletions)} deletions...")
                for change in changeset.deletions:
                    apply_change(change, repo_root, extract_dir, dry_run)
                create_commit(
                    repo_root,
                    f"Release #{release.num}: Delete {len(changeset.deletions)} files",
                    dry_run
                )

            # 3. Additions
            if changeset.additions:
                print(f"  Applying {len(changeset.additions)} additions...")
                for change in changeset.additions:
                    apply_change(change, repo_root, extract_dir, dry_run)
                create_commit(
                    repo_root,
                    f"Release #{release.num}: Add {len(changeset.additions)} new files",
                    dry_run
                )

            # 4. Modifications
            if changeset.modifications:
                print(f"  Applying {len(changeset.modifications)} modifications...")
                for change in changeset.modifications:
                    apply_change(change, repo_root, extract_dir, dry_run)
                create_commit(
                    repo_root,
                    f"Release #{release.num}: Modify {len(changeset.modifications)} files",
                    dry_run
                )

        else:  # per_release
            # Single commit for entire release
            print(f"\n  Applying all {len(changeset.changes)} changes...")
            for change in changeset.changes:
                apply_change(change, repo_root, extract_dir, dry_run)

            create_commit(
                repo_root,
                f"Release: UBL {release.version} ({release.status})\n\n"
                f"Date: {release.date}\n"
                f"Stage: {release.stage}\n"
                f"Renames: {len(changeset.renames)}, Deletes: {len(changeset.deletions)}, "
                f"Adds: {len(changeset.additions)}, Modifies: {len(changeset.modifications)}",
                dry_run
            )

        # Final validation
        if not dry_run:
            print("\n  Validating final state...")
            valid, errors = validate_repo_matches_release(repo_root, extract_dir, release)

            if valid:
                print(f"  ✓ Validation passed - repo matches release exactly")
            else:
                print(f"  ✗ Validation FAILED - {len(errors)} differences:")
                for err in errors[:10]:
                    print(f"    {err}")
                if len(errors) > 10:
                    print(f"    ... and {len(errors) - 10} more")
                return False

        print(f"\n✓ Successfully imported {release.tag_name}")
        return True

    except Exception as e:
        print(f"\n✗ Failed to import {release.tag_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def setup_test_repo(test_repo_path: Path) -> bool:
    """
    Create a fresh test repository for local testing, or use existing one.

    If a valid git repository already exists at test_repo_path, it will be
    preserved and reused. This enables incremental testing where releases
    are imported one at a time for validation.

    Only invalid/partial repos (no .git directory) are removed.
    """
    print(f"Setting up test repository at: {test_repo_path}")

    # Check if repo already exists and is valid
    if test_repo_path.exists() and (test_repo_path / '.git').exists():
        print(f"  ✓ Using existing test repo")
        return True

    # Remove any partial/invalid repo
    if test_repo_path.exists():
        print(f"  ⚠ Removing incomplete repo (no .git directory)")
        shutil.rmtree(test_repo_path)

    test_repo_path.mkdir(parents=True)

    try:
        # Initialize git repo
        subprocess.run(['git', 'init'], check=True, cwd=test_repo_path, capture_output=True)

        # Configure git for testing
        subprocess.run(
            ['git', 'config', 'user.email', 'test@test.com'],
            check=True, cwd=test_repo_path, capture_output=True
        )
        subprocess.run(
            ['git', 'config', 'user.name', 'Test User'],
            check=True, cwd=test_repo_path, capture_output=True
        )
        # Disable GPG signing for test repos
        subprocess.run(
            ['git', 'config', 'commit.gpgsign', 'false'],
            check=True, cwd=test_repo_path, capture_output=True
        )

        # Create .gitignore
        gitignore = test_repo_path / '.gitignore'
        gitignore.write_text("*.pyc\n__pycache__/\n")

        # Create initial commit
        subprocess.run(['git', 'add', '.'], check=True, cwd=test_repo_path, capture_output=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Initial commit'],
            check=True, cwd=test_repo_path, capture_output=True
        )

        print(f"  ✓ Test repo initialized")
        return True

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to setup test repo: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Granular UBL Release Importer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import release 1 to current repo
  python -m tools.granular_import --release 1

  # Import releases 1-5 with per-type commits
  python -m tools.granular_import --range 1 5 --commit-strategy per_type

  # Test with local repo (creates fresh repo)
  python -m tools.granular_import --release 1 --test-repo /tmp/ubl-test

  # Dry run to see what would happen
  python -m tools.granular_import --release 1 --dry-run

  # Validate each file after applying
  python -m tools.granular_import --release 1 --validate-each-file
        """
    )

    parser.add_argument(
        '--release', type=int,
        help='Single release number to import'
    )
    parser.add_argument(
        '--range', type=int, nargs=2, metavar=('START', 'END'),
        help='Range of releases to import'
    )
    parser.add_argument(
        '--commit-strategy', choices=['per_file', 'per_type', 'per_release'],
        default='per_type',
        help='How to batch commits (default: per_type)'
    )
    parser.add_argument(
        '--validate-each-file', action='store_true',
        help='Validate after each file change (slower)'
    )
    parser.add_argument(
        '--test-repo', type=Path,
        help='Path for test repository (will be created fresh)'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    # Determine release range
    if args.release:
        start_num, end_num = args.release, args.release
    elif args.range:
        start_num, end_num = args.range
    else:
        print("Error: Must specify --release or --range")
        sys.exit(1)

    # Determine repository path
    if args.test_repo:
        repo_root = args.test_repo
        if not setup_test_repo(repo_root):
            sys.exit(1)
    else:
        repo_root = Path.cwd()
        if not (repo_root / '.git').exists():
            print("Error: Not in a git repository. Use --test-repo for testing.")
            sys.exit(1)

    # Import releases
    print(f"\nImporting releases {start_num} to {end_num}")
    print(f"Repository: {repo_root}")
    print(f"Commit strategy: {args.commit_strategy}")

    previous_release = None
    success_count = 0
    fail_count = 0

    for num in range(start_num, end_num + 1):
        release = get_release_by_num(num)
        if not release:
            print(f"Warning: Release #{num} not found, skipping")
            continue

        # For first import, get the previous release
        if num > 1 and previous_release is None:
            previous_release = get_release_by_num(num - 1)

        if import_release_granular(
            release, repo_root, previous_release,
            args.commit_strategy, args.validate_each_file, args.dry_run
        ):
            success_count += 1
            previous_release = release
        else:
            fail_count += 1
            print(f"\nStopping due to failure on release #{num}")
            break

    print(f"\n{'='*70}")
    print(f"Import Summary")
    print(f"{'='*70}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

    if success_count > 0 and not args.dry_run:
        print(f"\nReleases imported to: {repo_root}")
        print(f"Use 'git log --oneline' to see commits")


if __name__ == '__main__':
    main()
