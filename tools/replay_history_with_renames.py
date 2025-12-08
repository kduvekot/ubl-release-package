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
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Set, Dict

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

    # Find the earliest commit (before any UBL content)
    # We want to start from infrastructure-only state
    result = subprocess.run(
        ['git', 'rev-list', '--max-parents=0', 'HEAD'],
        capture_output=True,
        text=True,
        cwd=repo_root
    )
    root_commits = result.stdout.strip().split('\n')

    if not root_commits or not root_commits[0]:
        print("  Error: Could not find root commit")
        return False

    # Find the commit just before UBL imports started
    # Look for commits that have tools/ but no UBL content
    result = subprocess.run(
        ['git', 'log', '--oneline', '--all'],
        capture_output=True,
        text=True,
        cwd=repo_root
    )
    commits = result.stdout.strip().split('\n')

    # Find infrastructure commit (one that has tools but no Release: commits before it)
    infra_commit = None
    for commit in reversed(commits):
        if 'Release:' not in commit and commit.strip():
            parts = commit.split(' ', 1)
            if len(parts) >= 1:
                infra_commit = parts[0]
                break

    if not infra_commit:
        # Fall back to root commit
        infra_commit = root_commits[0]

    print(f"  Starting from commit: {infra_commit}")

    # Create orphan branch
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

        # Create new branch from infrastructure commit
        subprocess.run(
            ['git', 'checkout', '-b', branch_name, infra_commit],
            check=True,
            cwd=repo_root,
            capture_output=True
        )
        print(f"  ✓ Created branch {branch_name}")

        # Clear any UBL content that might be there
        for item in repo_root.iterdir():
            if item.name not in PRESERVED_PATHS:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Commit clean state if there are changes
        subprocess.run(['git', 'add', '-A'], check=True, cwd=repo_root)
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=repo_root
        )
        if result.returncode != 0:
            subprocess.run(
                ['git', 'commit', '-m', 'Clean state before UBL imports'],
                check=True,
                cwd=repo_root,
                capture_output=True
            )

        return True

    except subprocess.CalledProcessError as e:
        print(f"  Error setting up branch: {e}")
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
        '--skip-branch-setup', action='store_true',
        help='Skip branch setup (use current branch)'
    )

    args = parser.parse_args()

    repo_root = Path.cwd()

    # Validate we're in a git repository
    if not (repo_root / '.git').exists():
        print("Error: Not in a git repository")
        sys.exit(1)

    # Setup branch
    if not args.skip_branch_setup and not args.dry_run:
        if not setup_branch(repo_root, args.branch):
            print("Failed to setup branch")
            sys.exit(1)

    # Import releases
    print(f"\nReplaying releases {args.start} through {args.end}...")

    success_count = 0
    fail_count = 0

    for num in range(args.start, args.end + 1):
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
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")

    if success_count > 0 and not args.dry_run:
        print(f"\nHistory replayed to branch: {args.branch}")
        print(f"Use 'git log --name-status' to verify rename detection")


if __name__ == '__main__':
    main()
