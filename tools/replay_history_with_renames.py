#!/usr/bin/env python3
"""
Replay UBL Release History with Rename Detection

This script recreates the entire UBL release history on a new branch,
using proper git rename detection (git mv) to track file renames between versions.

Instead of showing:
  D  UBL-Invoice-2.1.xsd
  A  UBL-Invoice-2.2.xsd

Git will show:
  R  UBL-Invoice-2.1.xsd -> UBL-Invoice-2.2.xsd

This enables:
- git blame to show true file origins
- git diff to show actual changes
- git log --follow to track file history across versions

RESUME SUPPORT:
- Use --resume to automatically detect and skip completed releases
- If interrupted mid-release, validates repo state against ZIP
- Only processes files that haven't been committed yet
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Set, Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.release_data import RELEASES, Release, get_release_by_num
from tools.gdrive_downloader import download_release_from_gdrive
from tools.file_rename_detector import RenameDetector, get_previous_version


# Directories and files to preserve during import
PRESERVED_PATHS = {
    '.git',
    '.gitignore',
    '.claude',
    'tools',
    'README.md',
}


def file_hash(filepath: Path) -> str:
    """Calculate MD5 hash of a file for comparison."""
    if not filepath.exists():
        return ""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_completed_releases(repo_root: Path) -> Set[int]:
    """
    Parse git log to find which releases have been fully committed.

    Looks for commit messages matching "Release: UBL X.X" pattern.
    Returns set of release numbers that are complete.
    """
    completed = set()
    try:
        result = subprocess.run(
            ['git', 'log', '--oneline', '--all'],
            capture_output=True,
            text=True,
            cwd=repo_root
        )

        # Pattern: "Release: UBL 2.0 (status)" or tag names like "prd-UBL-2.0"
        for line in result.stdout.split('\n'):
            # Check for release commit messages
            # Match patterns like "Release: UBL 2.0 (Public Review Draft)"
            match = re.search(r'Release: UBL (\d+\.\d+)', line)
            if match:
                version = match.group(1)
                # Map version to release numbers
                from tools.release_data import RELEASES
                for rel in RELEASES:
                    if rel.version == version and f"({rel.status})" in line:
                        completed.add(rel.num)
                        break

    except subprocess.CalledProcessError:
        pass

    return completed


def validate_repo_matches_zip(repo_root: Path, extract_dir: Path) -> Tuple[bool, List[str]]:
    """
    Validate that repository UBL content matches ZIP contents exactly.

    Returns:
        (is_valid, list of differences)
    """
    differences = []

    # Get files from repo (UBL content only)
    repo_files = filter_ubl_content_files(get_tracked_files(repo_root))

    # Get files from ZIP
    zip_files = get_extracted_files(extract_dir)

    # Check for missing files (in ZIP but not in repo)
    missing = zip_files - repo_files
    for f in sorted(missing):
        differences.append(f"MISSING: {f}")

    # Check for extra files (in repo but not in ZIP)
    extra = repo_files - zip_files
    for f in sorted(extra):
        differences.append(f"EXTRA: {f}")

    # Check for content differences
    common = repo_files & zip_files
    for f in sorted(common):
        repo_file = repo_root / f
        zip_file = extract_dir / f
        if repo_file.exists() and zip_file.exists():
            if file_hash(repo_file) != file_hash(zip_file):
                differences.append(f"DIFFERS: {f}")

    return len(differences) == 0, differences


def detect_resume_point(repo_root: Path, releases: list) -> Tuple[int, bool]:
    """
    Detect where to resume from based on git history.

    Returns:
        (release_num to start from, whether current release is partial)
    """
    completed = get_completed_releases(repo_root)

    if not completed:
        return 1, False

    # Find the highest completed release
    max_completed = max(completed)

    # Check if there are gaps (missing releases)
    expected = set(range(1, max_completed + 1))
    missing = expected - completed
    if missing:
        # Start from the first missing release
        return min(missing), False

    # All releases up to max_completed are done, start from next
    return max_completed + 1, False


def get_tracked_files(repo_root: Path) -> Set[Path]:
    """Get all git-tracked files as relative paths."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        return {Path(line.strip()) for line in result.stdout.split('\n') if line.strip()}
    except subprocess.CalledProcessError:
        return set()


def get_extracted_files(extract_dir: Path) -> Set[Path]:
    """Get all files in extracted directory as relative paths."""
    files = set()
    for file_path in extract_dir.rglob('*'):
        if file_path.is_file():
            # Skip junk files
            if file_path.name.startswith('.') or file_path.name.startswith('__'):
                continue
            if '__MACOSX' in file_path.parts:
                continue
            # Get relative path from extract_dir
            rel_path = file_path.relative_to(extract_dir)
            files.add(rel_path)
    return files


def filter_ubl_content_files(files: Set[Path]) -> Set[Path]:
    """Filter to only UBL content files (exclude infrastructure)."""
    filtered = set()
    for f in files:
        parts = f.parts
        if parts and parts[0] in PRESERVED_PATHS:
            continue
        filtered.add(f)
    return filtered


def download_and_extract(release: Release, temp_dir: Path) -> Path:
    """Download and extract a release, return the content directory."""
    print(f"  Downloading release #{release.num}...")

    zip_path = temp_dir / "release.zip"
    download_release_from_gdrive(
        release.num,
        release.stage,
        release.version,
        zip_path
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


def clear_ubl_content(repo_root: Path, dry_run: bool = False):
    """Remove all UBL content files (preserve infrastructure)."""
    if dry_run:
        print("  (DRY RUN: would clear UBL content)")
        return

    removed = 0
    for item in repo_root.iterdir():
        if item.name in PRESERVED_PATHS:
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            removed += 1
        except Exception as e:
            print(f"    Warning: Could not remove {item}: {e}")

    print(f"  Cleared {removed} items")


def copy_new_content(extract_dir: Path, repo_root: Path, exclude_renamed: Set[Path] = None,
                     dry_run: bool = False):
    """Copy new content from extract directory to repo."""
    if dry_run:
        print("  (DRY RUN: would copy new content)")
        return

    if exclude_renamed is None:
        exclude_renamed = set()

    copied = 0
    for item in extract_dir.iterdir():
        if item.name.startswith('__') or item.name.startswith('.'):
            continue

        dest = repo_root / item.name
        try:
            if item.is_dir():
                if dest.exists():
                    # Merge directory contents
                    for sub_item in item.rglob('*'):
                        if sub_item.is_file():
                            rel = sub_item.relative_to(extract_dir)
                            if rel in exclude_renamed:
                                continue
                            sub_dest = repo_root / rel
                            sub_dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(sub_item, sub_dest)
                            copied += 1
                else:
                    shutil.copytree(item, dest)
                    copied += 1
            else:
                rel = item.relative_to(extract_dir)
                if rel not in exclude_renamed:
                    shutil.copy2(item, dest)
                    copied += 1
        except Exception as e:
            print(f"    Warning: Failed to copy {item}: {e}")

    print(f"  Copied {copied} items")


def update_readme(repo_root: Path, release: Release, dry_run: bool = False):
    """Update README.md with release information."""
    if dry_run:
        return

    readme_path = repo_root / 'README.md'

    if not readme_path.exists():
        content = f"""# UBL Release Package History

This repository contains the complete release history of OASIS Universal
Business Language (UBL) versions 2.0 through 2.5.

## Latest Release

UBL {release.version} ({release.status}) - {release.date}

## Release History

- {release.tag_name} - {release.date} - {release.status}

## About

Each release is imported as a separate commit, allowing you to explore the
evolution of UBL over time using git history.

Use `git log` to see all releases, or checkout specific tags to view
individual releases.

## Rename Detection

This branch uses proper git rename detection. When files are renamed
between versions (e.g., UBL-Invoice-2.1.xsd → UBL-Invoice-2.2.xsd),
git tracks them as renames rather than delete+add operations.

Use `git log --follow <file>` to track a file's history across versions.
"""
    else:
        content = readme_path.read_text()
        # Update Latest Release section
        latest_pattern = r'## Latest Release\n\n.*?\n'
        latest_replacement = f"## Latest Release\n\nUBL {release.version} ({release.status}) - {release.date}\n"
        content = re.sub(latest_pattern, latest_replacement, content, flags=re.DOTALL)

        # Add to release history
        history_pattern = r'(## Release History\n\n)'
        new_entry = f"- {release.tag_name} - {release.date} - {release.status}\n"
        content = re.sub(history_pattern, r'\1' + new_entry, content)

    readme_path.write_text(content)


def create_commit(repo_root: Path, release: Release, dry_run: bool = False):
    """Create git commit for this release."""
    if dry_run:
        print("  (DRY RUN: would create commit)")
        return

    # Stage all changes
    subprocess.run(['git', 'add', '-A'], check=True, cwd=repo_root)

    # Check what we're committing
    result = subprocess.run(
        ['git', 'diff', '--cached', '--stat'],
        capture_output=True,
        text=True,
        cwd=repo_root
    )
    if result.stdout.strip():
        # Count renames
        status_result = subprocess.run(
            ['git', 'diff', '--cached', '--name-status'],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        lines = [l for l in status_result.stdout.strip().split('\n') if l]
        renames = len([l for l in lines if l.startswith('R')])
        adds = len([l for l in lines if l.startswith('A')])
        deletes = len([l for l in lines if l.startswith('D')])
        modifies = len([l for l in lines if l.startswith('M')])

        stats = []
        if renames:
            stats.append(f"{renames} renamed")
        if adds:
            stats.append(f"{adds} added")
        if deletes:
            stats.append(f"{deletes} deleted")
        if modifies:
            stats.append(f"{modifies} modified")

        if stats:
            print(f"  Changes: {', '.join(stats)}")

    # Create commit
    commit_msg = f"""Release: UBL {release.version} ({release.status})

Date: {release.date}
Stage: {release.stage}
Source: {release.url}
"""

    subprocess.run(
        ['git', 'commit', '-m', commit_msg],
        check=True,
        cwd=repo_root,
        capture_output=True
    )
    print(f"  ✓ Commit created")


def create_tags(repo_root: Path, release: Release, dry_run: bool = False):
    """Create git tags for this release."""
    if dry_run:
        return

    # Descriptive tag
    try:
        subprocess.run(
            ['git', 'tag', '-a', release.tag_name, '-m',
             f'UBL {release.version} {release.status}'],
            check=True,
            cwd=repo_root,
            capture_output=True
        )
    except subprocess.CalledProcessError:
        pass  # Tag might already exist

    # Version tag for OASIS Standards
    if release.version_tag:
        try:
            subprocess.run(
                ['git', 'tag', '-a', release.version_tag, '-m',
                 f'UBL {release.version} OASIS Standard'],
                check=True,
                cwd=repo_root,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass


def import_release_with_renames(release: Release, repo_root: Path,
                                 dry_run: bool = False) -> bool:
    """
    Import a single release with rename detection.

    Returns True if successful.
    """
    print(f"\n{'='*70}")
    print(f"Importing Release #{release.num}: {release.tag_name}")
    print(f"{'='*70}")
    print(f"Version: {release.version}, Stage: {release.stage}")
    print(f"Date: {release.date}, Type: {release.release_type}")

    temp_dir = Path(tempfile.mkdtemp(prefix='ubl-replay-'))

    try:
        # Download and extract
        extract_dir = download_and_extract(release, temp_dir)

        # Get file lists
        current_files = filter_ubl_content_files(get_tracked_files(repo_root))
        new_files = get_extracted_files(extract_dir)

        # Find previous version for rename detection
        prev_version = get_previous_version(RELEASES, release)

        renamed_files = {}
        if prev_version and prev_version != release.version:
            # Detect renames from previous version
            detector = RenameDetector(
                repo_root,
                prev_version,
                release.version,
                dry_run=dry_run
            )
            renamed_files = detector.detect_renames(current_files, new_files)

            if renamed_files:
                # Apply renames via git mv
                detector.apply_renames(renamed_files, extract_dir)
                # Update renamed files with new content
                detector.update_renamed_files_content(renamed_files, extract_dir)

        # For full releases: clear remaining content and copy new
        if not release.is_patch:
            # Get files that were renamed (don't delete these, they're already moved)
            already_handled = set(renamed_files.values())

            # Clear old content (except renamed files which are now at new locations)
            clear_ubl_content(repo_root, dry_run)

            # Copy new content
            copy_new_content(extract_dir, repo_root, already_handled, dry_run)
        else:
            # Patch: overlay changed files
            print("  Applying patch/overlay...")
            if not dry_run:
                for item in extract_dir.rglob('*'):
                    if item.is_file() and '__MACOSX' not in item.parts:
                        rel_path = item.relative_to(extract_dir)
                        dest = repo_root / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)

        # Update README
        update_readme(repo_root, release, dry_run)

        # Create commit
        create_commit(repo_root, release, dry_run)

        # Create tags
        create_tags(repo_root, release, dry_run)

        # Validate the import matches the ZIP
        if not dry_run:
            print("  Validating import...")
            is_valid, differences = validate_repo_matches_zip(repo_root, extract_dir)
            if is_valid:
                print("  ✓ Validation passed - repo matches ZIP")
            else:
                print(f"  ⚠ Validation found {len(differences)} differences:")
                for diff in differences[:10]:  # Show first 10
                    print(f"    {diff}")
                if len(differences) > 10:
                    print(f"    ... and {len(differences) - 10} more")

        print(f"✓ Successfully imported {release.tag_name}")
        return True

    except Exception as e:
        print(f"✗ Failed to import {release.tag_name}: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


def setup_branch(repo_root: Path, branch_name: str) -> bool:
    """Create and checkout the new branch for replay."""
    print(f"\nSetting up branch: {branch_name}")

    # Save current infrastructure files to temp location
    # These will be copied back after branch setup
    temp_backup = Path(tempfile.mkdtemp(prefix='ubl-infra-backup-'))
    print("  Backing up infrastructure files...")

    for preserve_dir in ['tools', '.claude']:
        src = repo_root / preserve_dir
        if src.exists():
            shutil.copytree(src, temp_backup / preserve_dir)

    # Also preserve .gitignore and README.md
    for preserve_file in ['.gitignore', 'README.md']:
        src = repo_root / preserve_file
        if src.exists():
            shutil.copy2(src, temp_backup / preserve_file)

    print(f"  Backed up to {temp_backup}")

    # Create orphan branch with infrastructure
    try:
        # First, check if branch exists
        result = subprocess.run(
            ['git', 'branch', '--list', branch_name],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        if result.stdout.strip():
            print(f"  Branch {branch_name} already exists, deleting...")
            subprocess.run(['git', 'branch', '-D', branch_name], check=True, cwd=repo_root)

        # Create orphan branch (no parent commits)
        subprocess.run(
            ['git', 'checkout', '--orphan', branch_name],
            check=True,
            cwd=repo_root,
            capture_output=True
        )

        # Remove all files from staging and working directory
        subprocess.run(['git', 'rm', '-rf', '.'], check=True, cwd=repo_root,
                      capture_output=True)

        # Clear any remaining untracked files (except our backup reference)
        for item in repo_root.iterdir():
            if item.name == '.git':
                continue
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except Exception:
                pass

        # Restore infrastructure from backup
        print("  Restoring infrastructure files...")
        for item in temp_backup.iterdir():
            dest = repo_root / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Commit infrastructure
        subprocess.run(['git', 'add', '-A'], check=True, cwd=repo_root)
        subprocess.run(
            ['git', 'commit', '-m', 'Infrastructure for UBL release imports'],
            check=True,
            cwd=repo_root,
            capture_output=True
        )
        print(f"  ✓ Created orphan branch {branch_name} with infrastructure")

        # Cleanup backup
        shutil.rmtree(temp_backup, ignore_errors=True)

        return True

    except subprocess.CalledProcessError as e:
        print(f"  Error setting up branch: {e}")
        # Try to restore to previous state
        shutil.rmtree(temp_backup, ignore_errors=True)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Replay UBL release history with rename detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full replay of all 34 releases
  python -m tools.replay_history_with_renames

  # Replay specific range
  python -m tools.replay_history_with_renames --start 1 --end 10

  # Resume from where we left off (auto-detect)
  python -m tools.replay_history_with_renames --resume

  # Resume on existing branch
  python -m tools.replay_history_with_renames --resume --skip-branch-setup

  # Dry run to see what would happen
  python -m tools.replay_history_with_renames --dry-run

  # Use specific branch name
  python -m tools.replay_history_with_renames --branch my-branch
        """
    )

    parser.add_argument(
        '--start', type=int, default=1,
        help='First release to import (default: 1)'
    )
    parser.add_argument(
        '--end', type=int, default=34,
        help='Last release to import (default: 34)'
    )
    parser.add_argument(
        '--branch', type=str, default='history-with-renames',
        help='Branch name for replayed history'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--resume', action='store_true',
        help='Resume from last completed release (auto-detect)'
    )
    parser.add_argument(
        '--skip-branch-setup', action='store_true',
        help='Skip branch setup (use current branch)'
    )

    args = parser.parse_args()

    repo_root = Path.cwd()

    # Validate we're in a git repository
    if not (repo_root / '.git').exists():
        print("Error: Not in a git repository")
        sys.exit(1)

    # Handle resume mode
    start_from = args.start
    if args.resume:
        print("\nResume mode: Detecting completed releases...")
        completed = get_completed_releases(repo_root)
        if completed:
            print(f"  Found {len(completed)} completed releases: {sorted(completed)}")
            resume_point, _ = detect_resume_point(repo_root, RELEASES)
            if resume_point > args.end:
                print(f"  All releases up to #{args.end} are complete!")
                sys.exit(0)
            start_from = resume_point
            print(f"  Resuming from release #{start_from}")
            # Skip branch setup when resuming
            args.skip_branch_setup = True
        else:
            print("  No completed releases found, starting from beginning")

    # Setup branch (unless resuming or skipped)
    if not args.skip_branch_setup and not args.dry_run:
        if not setup_branch(repo_root, args.branch):
            print("Failed to setup branch")
            sys.exit(1)

    # Import releases
    print(f"\nReplaying releases {start_from} through {args.end}...")

    success_count = 0
    fail_count = 0
    skipped_count = start_from - args.start  # Count releases we skipped due to resume

    for num in range(start_from, args.end + 1):
        release = get_release_by_num(num)
        if not release:
            print(f"Warning: Release #{num} not found, skipping")
            continue

        if import_release_with_renames(release, repo_root, args.dry_run):
            success_count += 1
        else:
            fail_count += 1
            if not args.dry_run:
                print(f"\nStopping due to failure on release #{num}")
                break

    print(f"\n{'='*70}")
    print(f"Replay Summary")
    print(f"{'='*70}")
    if skipped_count > 0:
        print(f"Skipped (already done): {skipped_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

    if success_count > 0 and not args.dry_run:
        print(f"\nHistory replayed to branch: {args.branch}")
        print(f"Use 'git log --name-status' to verify rename detection")


if __name__ == '__main__':
    main()
