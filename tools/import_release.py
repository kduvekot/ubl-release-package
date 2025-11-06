#!/usr/bin/env python3
"""
UBL Release Import Tool

This script imports a single UBL release into the repository, handling:
- Full releases (replace all content)
- Patch releases (overlay on existing content)
- Git commits with structured messages
- Git tags for releases
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional, Dict

# Import our modules
from .git_state import GitStateManager
from .release_data import Release, get_release_by_num
from .validators import Validators, ValidationError


class ImportError(Exception):
    """Raised when import fails."""
    pass


class ReleaseImporter:
    """Handles the import of a single UBL release."""

    # Directories and files to preserve during import
    PRESERVED_PATHS = [
        '.git',
        '.gitignore',
        '.claude',
        'tools',
        'README.md',
    ]

    def __init__(self, release: Release, dry_run: bool = False, force: bool = False):
        self.release = release
        self.dry_run = dry_run
        self.force = force
        self.repo_root = Path.cwd()
        self.temp_dir: Optional[Path] = None

    def run(self) -> bool:
        """
        Execute the full import process.

        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\n{'='*70}")
            print(f"Importing Release #{self.release.num}: {self.release.tag_name}")
            print(f"{'='*70}")
            print(f"Version: {self.release.version}")
            print(f"Stage: {self.release.stage} ({self.release.status})")
            print(f"Date: {self.release.date}")
            print(f"Type: {self.release.release_type}")
            print(f"URL: {self.release.url}")
            print()

            # Validate before proceeding
            Validators.validate_all(self.release, self.force)
            print()

            # Download and extract
            extract_dir = self.download_and_extract()
            print()

            # Apply to repository
            if self.release.is_patch:
                self.apply_patch(extract_dir)
            else:
                self.apply_full_release(extract_dir)
            print()

            # Update README
            self.update_readme()
            print()

            # Create commit
            self.create_commit()
            print()

            # Create tags
            self.create_tags()
            print()

            print(f"✓ Successfully imported {self.release.tag_name}")
            return True

        except (ValidationError, ImportError) as e:
            print(f"\n✗ Import failed: {e}", file=sys.stderr)
            return False

        finally:
            self.cleanup()

    def download_and_extract(self) -> Path:
        """Download ZIP and extract to temp directory."""
        print(f"Downloading {self.release.url}...")

        if self.dry_run:
            print("  (DRY RUN: skipping download)")
            return Path("/tmp/dry-run")

        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix='ubl-import-'))

        # Download
        zip_path = self.temp_dir / "release.zip"
        try:
            urllib.request.urlretrieve(self.release.url, zip_path)
            print(f"  Downloaded {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
        except Exception as e:
            raise ImportError(f"Download failed: {e}")

        # Extract
        print(f"Extracting to {self.temp_dir}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            print(f"  Extracted {len(list(self.temp_dir.rglob('*')))} files")
        except Exception as e:
            raise ImportError(f"Extraction failed: {e}")

        # Find the content directory (might be nested in a subdirectory)
        extract_dir = self.find_content_directory(self.temp_dir)
        return extract_dir

    def find_content_directory(self, temp_dir: Path) -> Path:
        """
        Find the actual content directory within the extracted ZIP.

        Some ZIPs extract to a subdirectory, others extract files directly.
        """
        # Check if there's a single subdirectory with all the content
        subdirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name != '__MACOSX']

        if len(subdirs) == 1:
            # Single subdirectory - likely the content is there
            subdir = subdirs[0]
            # Check if this looks like UBL content (has xsd/ or similar)
            if any((subdir / name).exists() for name in ['xsd', 'xsdrt', 'doc', 'cl']):
                print(f"  Content found in subdirectory: {subdir.name}")
                return subdir

        # Otherwise, assume content is at temp_dir level
        return temp_dir

    def apply_full_release(self, extract_dir: Path):
        """
        Apply a full release: clear repo and copy all content.

        Args:
            extract_dir: Directory containing extracted ZIP content
        """
        print(f"Applying full release import...")

        if self.dry_run:
            print("  (DRY RUN: would clear repo and copy new content)")
            return

        # Step 1: Remove all existing content (except preserved paths)
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

        # Step 2: Copy new content
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

    def apply_patch(self, extract_dir: Path):
        """
        Apply a patch release: overlay changed files on existing content.

        Args:
            extract_dir: Directory containing extracted ZIP content
        """
        print(f"Applying patch/overlay import...")

        if self.dry_run:
            print("  (DRY RUN: would overlay changed files)")
            return

        print("  Overlaying changed files...")
        copied_count = 0

        # Recursively copy all files, overwriting existing ones
        for item in extract_dir.rglob('*'):
            if item.is_file():
                # Skip __MACOSX and other junk
                if '__MACOSX' in item.parts or item.name.startswith('.'):
                    continue

                # Calculate relative path
                rel_path = item.relative_to(extract_dir)
                dest = self.repo_root / rel_path

                # Create parent directory if needed
                dest.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                try:
                    shutil.copy2(item, dest)
                    copied_count += 1
                except Exception as e:
                    raise ImportError(f"Failed to copy {item}: {e}")

        print(f"    Overlaid {copied_count} files")

    def update_readme(self):
        """Update README.md with release information."""
        print("Updating README.md...")

        if self.dry_run:
            print("  (DRY RUN: would update README)")
            return

        readme_path = self.repo_root / 'README.md'

        # For now, create a simple README if it doesn't exist
        # In production, this should be more sophisticated
        if not readme_path.exists():
            content = self.generate_initial_readme()
        else:
            content = self.update_existing_readme(readme_path)

        readme_path.write_text(content)
        print("  ✓ README.md updated")

    def generate_initial_readme(self) -> str:
        """Generate initial README.md content."""
        return f"""# UBL Release Package History

This repository contains the complete release history of OASIS Universal
Business Language (UBL) versions 2.0 through 2.5.

## Latest Release

UBL {self.release.version} ({self.release.status}) - {self.release.date}

## Release History

- {self.release.tag_name} - {self.release.date} - {self.release.status}

## About

Each release is imported as a separate commit, allowing you to explore the
evolution of UBL over time using git history.

Use `git log` to see all releases, or checkout specific tags to view
individual releases.
"""

    def update_existing_readme(self, readme_path: Path) -> str:
        """Update existing README.md with new release."""
        content = readme_path.read_text()

        # Update "Latest Release" section
        latest_pattern = r'## Latest Release\n\n.*?\n'
        latest_replacement = f"## Latest Release\n\nUBL {self.release.version} ({self.release.status}) - {self.release.date}\n"
        content = re.sub(latest_pattern, latest_replacement, content, flags=re.DOTALL)

        # Add to release history (after "## Release History" line)
        history_pattern = r'(## Release History\n\n)'
        new_entry = f"- {self.release.tag_name} - {self.release.date} - {self.release.status}\n"
        content = re.sub(history_pattern, r'\1' + new_entry, content)

        return content

    def create_commit(self):
        """Create git commit for this release."""
        print("Creating git commit...")

        if self.dry_run:
            print("  (DRY RUN: would create commit)")
            self.show_commit_preview()
            return

        # Stage all changes
        try:
            subprocess.run(['git', 'add', '-A'], check=True, cwd=self.repo_root)
        except subprocess.CalledProcessError as e:
            raise ImportError(f"Failed to stage changes: {e}")

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

    def generate_commit_message(self) -> str:
        """Generate structured commit message."""
        return f"""Release: UBL {self.release.version} ({self.release.status})

Date: {self.release.date}
Stage: {self.release.stage}
Source: {self.release.url}
"""

    def show_commit_preview(self):
        """Show what the commit would look like (dry run)."""
        print("\n--- Commit Message Preview ---")
        print(self.generate_commit_message())
        print("--- End Preview ---\n")

    def create_tags(self):
        """Create git tags for this release."""
        print("Creating git tags...")

        if self.dry_run:
            print(f"  (DRY RUN: would create tag {self.release.tag_name})")
            if self.release.version_tag:
                print(f"  (DRY RUN: would create tag {self.release.version_tag})")
            return

        # Create descriptive tag
        try:
            subprocess.run(
                ['git', 'tag', '-a', self.release.tag_name, '-m', f'UBL {self.release.version} {self.release.status}'],
                check=True,
                cwd=self.repo_root
            )
            print(f"  ✓ Created tag: {self.release.tag_name}")
        except subprocess.CalledProcessError as e:
            print(f"  Warning: Failed to create tag {self.release.tag_name}: {e}")

        # Create version tag if this is an OASIS Standard
        if self.release.version_tag:
            try:
                subprocess.run(
                    ['git', 'tag', '-a', self.release.version_tag, '-m', f'UBL {self.release.version} OASIS Standard'],
                    check=True,
                    cwd=self.repo_root
                )
                print(f"  ✓ Created tag: {self.release.version_tag}")
            except subprocess.CalledProcessError as e:
                print(f"  Warning: Failed to create tag {self.release.version_tag}: {e}")

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"Warning: Could not clean up temp directory: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Import a UBL release into the repository',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import release #1 (first release)
  python -m tools.import_release 1

  # Import release #33 (UBL 2.4 OASIS Standard)
  python -m tools.import_release 33

  # Dry run (validate and preview without making changes)
  python -m tools.import_release 1 --dry-run

  # Force import out of order (not recommended)
  python -m tools.import_release 10 --force
        """
    )

    parser.add_argument(
        'release_num',
        type=int,
        help='Release number to import (1-34)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate and preview without making changes'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force import even if out of order or already imported'
    )

    args = parser.parse_args()

    # Get release data
    release = get_release_by_num(args.release_num)
    if not release:
        print(f"ERROR: Invalid release number: {args.release_num}", file=sys.stderr)
        print(f"       Valid range: 1-34", file=sys.stderr)
        sys.exit(1)

    # Run import
    importer = ReleaseImporter(release, dry_run=args.dry_run, force=args.force)
    success = importer.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
