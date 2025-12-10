#!/usr/bin/env python3
"""
Test suite for granular_import.py

Tests the file classification and change detection logic using mock data.
No network access required - uses locally created test files.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.granular_import import (
    FileChange, ChangeType, ReleaseChangeset,
    compute_changeset, detect_version_rename,
    apply_change, validate_file, validate_repo_matches_release,
    get_repo_files, get_zip_files, file_hash
)
from tools.release_data import Release


class TestContext:
    """Context for creating temporary test repos and mock data."""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix='test-granular-'))
        self.repo_root = self.temp_dir / 'repo'
        self.extract_dir = self.temp_dir / 'extract'

    def setup_repo(self, files: dict):
        """
        Create a git repo with specified files.

        Args:
            files: Dict mapping path to content
        """
        self.repo_root.mkdir(parents=True, exist_ok=True)

        # Initialize git
        subprocess.run(['git', 'init'], cwd=self.repo_root, capture_output=True, check=True)
        subprocess.run(
            ['git', 'config', 'user.email', 'test@test.com'],
            cwd=self.repo_root, capture_output=True, check=True
        )
        subprocess.run(
            ['git', 'config', 'user.name', 'Test User'],
            cwd=self.repo_root, capture_output=True, check=True
        )
        # Disable GPG signing for tests
        subprocess.run(
            ['git', 'config', 'commit.gpgsign', 'false'],
            cwd=self.repo_root, capture_output=True, check=True
        )

        # Create files
        for path, content in files.items():
            file_path = self.repo_root / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        # Commit
        subprocess.run(['git', 'add', '-A'], cwd=self.repo_root, capture_output=True, check=True)
        subprocess.run(
            ['git', 'commit', '-m', 'Initial'],
            cwd=self.repo_root, capture_output=True, check=True
        )

    def setup_extract(self, files: dict):
        """
        Create extracted release directory with specified files.

        Args:
            files: Dict mapping path to content
        """
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        for path, content in files.items():
            file_path = self.extract_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    def cleanup(self):
        """Remove temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)


def create_mock_release(num: int, version: str, stage: str) -> Release:
    """Create a mock Release object for testing."""
    return Release(
        num=num,
        version=version,
        stage=stage,
        date="2024-01-01",
        url="http://test.com/test.zip"
    )


# ==============================================================================
# Test: Version Rename Detection
# ==============================================================================

def test_version_rename_detection():
    """Test detection of version-based file renames."""
    print("\n=== Test: Version Rename Detection ===")

    # Test case 1: Standard version bump
    old = Path("xsd/maindoc/UBL-Invoice-2.1.xsd")
    result = detect_version_rename(old, "2.1", "2.2")
    assert result == Path("xsd/maindoc/UBL-Invoice-2.2.xsd"), f"Expected version bump, got {result}"
    print("  ✓ Standard version bump: UBL-Invoice-2.1.xsd -> UBL-Invoice-2.2.xsd")

    # Test case 2: Underscore version pattern
    old = Path("xsd/common/CCTS_CCT-2.1.xsd")
    result = detect_version_rename(old, "2.1", "2.2")
    assert result == Path("xsd/common/CCTS_CCT-2.2.xsd"), f"Expected underscore bump, got {result}"
    print("  ✓ Underscore pattern: CCTS_CCT-2.1.xsd -> CCTS_CCT-2.2.xsd")

    # Test case 3: No version in filename
    old = Path("xsd/common/README.txt")
    result = detect_version_rename(old, "2.1", "2.2")
    assert result is None, f"Expected None for no-version file, got {result}"
    print("  ✓ No version in filename returns None")

    print("  All version rename detection tests passed!")


# ==============================================================================
# Test: Changeset Computation
# ==============================================================================

def test_changeset_new_files():
    """Test detection of new files (additions)."""
    print("\n=== Test: Changeset - New Files ===")
    ctx = TestContext()

    try:
        # Setup empty repo
        ctx.setup_repo({".gitignore": "*.pyc"})

        # Setup extract with new files
        ctx.setup_extract({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice/>",
            "xsd/common/UBL-Types-2.1.xsd": "<Types/>"
        })

        repo_files = get_repo_files(ctx.repo_root)
        zip_files = get_zip_files(ctx.extract_dir)

        release = create_mock_release(1, "2.1", "prd")
        changeset = compute_changeset(repo_files, zip_files, release, None)

        assert len(changeset.additions) == 2, f"Expected 2 additions, got {len(changeset.additions)}"
        assert len(changeset.deletions) == 0
        assert len(changeset.renames) == 0

        print(f"  ✓ Detected {len(changeset.additions)} new files")
        print("  All new files tests passed!")

    finally:
        ctx.cleanup()


def test_changeset_deletions():
    """Test detection of deleted files."""
    print("\n=== Test: Changeset - Deletions ===")
    ctx = TestContext()

    try:
        # Setup repo with some files
        ctx.setup_repo({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice/>",
            "xsd/common/UBL-Types-2.1.xsd": "<Types/>",
            "xsd/common/OLD-File.xsd": "<Old/>"  # This will be deleted
        })

        # Setup extract without the old file
        ctx.setup_extract({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice/>",
            "xsd/common/UBL-Types-2.1.xsd": "<Types/>"
        })

        repo_files = get_repo_files(ctx.repo_root)
        zip_files = get_zip_files(ctx.extract_dir)

        release = create_mock_release(2, "2.1", "prd2")
        prev_release = create_mock_release(1, "2.1", "prd")
        changeset = compute_changeset(repo_files, zip_files, release, prev_release)

        assert len(changeset.deletions) == 1, f"Expected 1 deletion, got {len(changeset.deletions)}"
        assert changeset.deletions[0].old_path == Path("xsd/common/OLD-File.xsd")

        print(f"  ✓ Detected {len(changeset.deletions)} deleted file(s)")
        print("  All deletion tests passed!")

    finally:
        ctx.cleanup()


def test_changeset_renames():
    """Test detection of renamed files (version bumps)."""
    print("\n=== Test: Changeset - Renames (Version Bumps) ===")
    ctx = TestContext()

    try:
        # Setup repo with 2.1 files
        ctx.setup_repo({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice v2.1/>",
            "xsd/common/UBL-Types-2.1.xsd": "<Types v2.1/>"
        })

        # Setup extract with 2.2 files (same names but version bumped)
        ctx.setup_extract({
            "xsd/maindoc/UBL-Invoice-2.2.xsd": "<Invoice v2.2/>",
            "xsd/common/UBL-Types-2.2.xsd": "<Types v2.2/>"
        })

        repo_files = get_repo_files(ctx.repo_root)
        zip_files = get_zip_files(ctx.extract_dir)

        release = create_mock_release(9, "2.2", "prd1")
        prev_release = create_mock_release(8, "2.1", "os")
        changeset = compute_changeset(repo_files, zip_files, release, prev_release)

        assert len(changeset.renames) == 2, f"Expected 2 renames, got {len(changeset.renames)}"
        assert len(changeset.additions) == 0
        assert len(changeset.deletions) == 0

        print(f"  ✓ Detected {len(changeset.renames)} version-bump renames")
        for r in changeset.renames:
            print(f"    {r.old_path} -> {r.new_path}")
        print("  All rename tests passed!")

    finally:
        ctx.cleanup()


def test_changeset_modifications():
    """Test detection of modified files (same path, different content)."""
    print("\n=== Test: Changeset - Modifications ===")
    ctx = TestContext()

    try:
        # Setup repo with initial content
        ctx.setup_repo({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice version='1'/>",
            "xsd/common/UBL-Types-2.1.xsd": "<Types/>"  # Unchanged
        })

        # Setup extract with modified content
        ctx.setup_extract({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice version='2'/>",  # Modified
            "xsd/common/UBL-Types-2.1.xsd": "<Types/>"  # Unchanged
        })

        repo_files = get_repo_files(ctx.repo_root)
        zip_files = get_zip_files(ctx.extract_dir)

        release = create_mock_release(2, "2.1", "prd2")
        prev_release = create_mock_release(1, "2.1", "prd")
        changeset = compute_changeset(repo_files, zip_files, release, prev_release)

        assert len(changeset.modifications) == 1, f"Expected 1 modification, got {len(changeset.modifications)}"
        assert changeset.modifications[0].new_path == Path("xsd/maindoc/UBL-Invoice-2.1.xsd")

        print(f"  ✓ Detected {len(changeset.modifications)} modification(s)")
        print("  All modification tests passed!")

    finally:
        ctx.cleanup()


# ==============================================================================
# Test: Apply Changes
# ==============================================================================

def test_apply_rename():
    """Test applying a rename change."""
    print("\n=== Test: Apply Rename Change ===")
    ctx = TestContext()

    try:
        # Setup repo
        ctx.setup_repo({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice v2.1/>"
        })

        # Setup extract with new version
        ctx.setup_extract({
            "xsd/maindoc/UBL-Invoice-2.2.xsd": "<Invoice v2.2/>"
        })

        change = FileChange(
            change_type=ChangeType.RENAMED,
            old_path=Path("xsd/maindoc/UBL-Invoice-2.1.xsd"),
            new_path=Path("xsd/maindoc/UBL-Invoice-2.2.xsd")
        )

        result = apply_change(change, ctx.repo_root, ctx.extract_dir)
        assert result, "apply_change should return True"

        # Verify old file is gone
        assert not (ctx.repo_root / "xsd/maindoc/UBL-Invoice-2.1.xsd").exists()
        # Verify new file exists with new content
        assert (ctx.repo_root / "xsd/maindoc/UBL-Invoice-2.2.xsd").exists()
        content = (ctx.repo_root / "xsd/maindoc/UBL-Invoice-2.2.xsd").read_text()
        assert "v2.2" in content

        # Verify git knows it's a rename
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-status'],
            capture_output=True, text=True, cwd=ctx.repo_root
        )
        assert 'R' in result.stdout, "Git should detect rename"

        print("  ✓ Rename applied successfully")
        print("  ✓ Git detected rename operation")
        print("  All rename application tests passed!")

    finally:
        ctx.cleanup()


def test_apply_addition():
    """Test applying an addition change."""
    print("\n=== Test: Apply Addition Change ===")
    ctx = TestContext()

    try:
        # Setup empty repo
        ctx.setup_repo({".gitignore": "*.pyc"})

        # Setup extract with new file
        ctx.setup_extract({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice/>"
        })

        change = FileChange(
            change_type=ChangeType.NEW,
            new_path=Path("xsd/maindoc/UBL-Invoice-2.1.xsd")
        )

        result = apply_change(change, ctx.repo_root, ctx.extract_dir)
        assert result, "apply_change should return True"

        # Verify file exists
        new_file = ctx.repo_root / "xsd/maindoc/UBL-Invoice-2.1.xsd"
        assert new_file.exists(), "New file should exist"
        assert new_file.read_text() == "<Invoice/>"

        print("  ✓ Addition applied successfully")
        print("  All addition application tests passed!")

    finally:
        ctx.cleanup()


def test_apply_deletion():
    """Test applying a deletion change."""
    print("\n=== Test: Apply Deletion Change ===")
    ctx = TestContext()

    try:
        # Setup repo with file to delete
        ctx.setup_repo({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice/>",
            "xsd/maindoc/OLD-File.xsd": "<Old/>"
        })

        # No extract needed for deletion
        ctx.extract_dir.mkdir(parents=True, exist_ok=True)

        change = FileChange(
            change_type=ChangeType.DELETED,
            old_path=Path("xsd/maindoc/OLD-File.xsd")
        )

        result = apply_change(change, ctx.repo_root, ctx.extract_dir)
        assert result, "apply_change should return True"

        # Verify file is gone
        assert not (ctx.repo_root / "xsd/maindoc/OLD-File.xsd").exists()

        print("  ✓ Deletion applied successfully")
        print("  All deletion application tests passed!")

    finally:
        ctx.cleanup()


# ==============================================================================
# Test: Validation
# ==============================================================================

def test_validation():
    """Test repo validation against release."""
    print("\n=== Test: Validation ===")
    ctx = TestContext()

    try:
        # Setup repo matching extract exactly
        files = {
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice/>",
            "xsd/common/UBL-Types-2.1.xsd": "<Types/>"
        }

        ctx.setup_repo(files)
        ctx.setup_extract(files)

        is_valid, errors = validate_repo_matches_release(ctx.repo_root, ctx.extract_dir)
        assert is_valid, f"Should be valid, but got errors: {errors}"

        print("  ✓ Matching repo/extract validates successfully")

        # Now test with mismatch
        (ctx.repo_root / "xsd/extra.xsd").write_text("<Extra/>")
        subprocess.run(['git', 'add', '.'], cwd=ctx.repo_root, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add extra'], cwd=ctx.repo_root, capture_output=True)

        is_valid, errors = validate_repo_matches_release(ctx.repo_root, ctx.extract_dir)
        assert not is_valid, "Should detect extra file"
        assert any("EXTRA" in e for e in errors)

        print("  ✓ Extra file detected as validation error")
        print("  All validation tests passed!")

    finally:
        ctx.cleanup()


# ==============================================================================
# Test: Mixed Changeset
# ==============================================================================

def test_mixed_changeset():
    """Test a complex changeset with all types of changes."""
    print("\n=== Test: Mixed Changeset (All Change Types) ===")
    ctx = TestContext()

    try:
        # Setup repo with v2.1 files
        ctx.setup_repo({
            "xsd/maindoc/UBL-Invoice-2.1.xsd": "<Invoice v2.1/>",     # Will be renamed
            "xsd/common/UBL-Types-2.1.xsd": "<Types v2.1/>",          # Will be renamed
            "xsd/deprecated/OLD-File.xsd": "<Old/>",                   # Will be deleted
            "xsd/unchanged/Static.xsd": "<Static/>"                    # Will remain but diff content
        })

        # Setup extract with v2.2 files + changes
        ctx.setup_extract({
            "xsd/maindoc/UBL-Invoice-2.2.xsd": "<Invoice v2.2/>",      # Renamed from 2.1
            "xsd/common/UBL-Types-2.2.xsd": "<Types v2.2/>",           # Renamed from 2.1
            "xsd/newdir/NewFile.xsd": "<New/>",                        # New file
            "xsd/unchanged/Static.xsd": "<Static Modified/>"           # Modified
        })

        repo_files = get_repo_files(ctx.repo_root)
        zip_files = get_zip_files(ctx.extract_dir)

        release = create_mock_release(17, "2.2", "csprd01")
        prev_release = create_mock_release(16, "2.1", "os")
        changeset = compute_changeset(repo_files, zip_files, release, prev_release)

        print(f"  Changeset summary: {changeset.summary()}")
        print(f"  - Renames: {len(changeset.renames)}")
        print(f"  - Deletions: {len(changeset.deletions)}")
        print(f"  - Additions: {len(changeset.additions)}")
        print(f"  - Modifications: {len(changeset.modifications)}")

        # Verify counts
        assert len(changeset.renames) == 2, f"Expected 2 renames, got {len(changeset.renames)}"
        assert len(changeset.deletions) == 1, f"Expected 1 deletion, got {len(changeset.deletions)}"
        assert len(changeset.additions) == 1, f"Expected 1 addition, got {len(changeset.additions)}"
        assert len(changeset.modifications) == 1, f"Expected 1 modification, got {len(changeset.modifications)}"

        print("  ✓ All change types detected correctly")
        print("  All mixed changeset tests passed!")

    finally:
        ctx.cleanup()


# ==============================================================================
# Main
# ==============================================================================

def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("Granular Import Test Suite")
    print("=" * 70)

    tests = [
        test_version_rename_detection,
        test_changeset_new_files,
        test_changeset_deletions,
        test_changeset_renames,
        test_changeset_modifications,
        test_apply_rename,
        test_apply_addition,
        test_apply_deletion,
        test_validation,
        test_mixed_changeset,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n  ✗ FAILED: {test.__name__}")
            print(f"    {e}")
            failed += 1
        except Exception as e:
            print(f"\n  ✗ ERROR: {test.__name__}")
            print(f"    {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
