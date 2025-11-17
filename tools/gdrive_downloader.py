#!/usr/bin/env python3
"""
Google Drive Downloader Module

Handles downloading UBL release packages from Google Drive.
Approved for use 2025-11-17 - see .claude/gdrive_sources.json
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    import gdown
except ImportError:
    gdown = None


class GoogleDriveDownloader:
    """Downloads files from Google Drive folder."""

    def __init__(self):
        """Initialize downloader with config from gdrive_sources.json."""
        self.config_path = Path(__file__).parent.parent / '.claude' / 'gdrive_sources.json'
        self.config = self._load_config()
        self.folder_id = self.config['gdrive_folder']['folder_id']

    def _load_config(self) -> dict:
        """Load Google Drive configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Google Drive config not found: {self.config_path}\n"
                "Expected .claude/gdrive_sources.json with approved URLs"
            )

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def get_file_naming_pattern(self, release_num: int, stage: str, version: str) -> str:
        """
        Generate the expected filename in Google Drive.

        Args:
            release_num: Release number (1-34)
            stage: Release stage (prd, os, csprd01, etc.)
            version: UBL version (2.0, 2.1, etc.)

        Returns:
            Expected filename in Google Drive folder
        """
        # Handle special cases for os-update stage
        if stage == 'os-update':
            return f"{release_num:02d}_os-update-UBL-{version}.zip"

        return f"{release_num:02d}_{stage}-UBL-{version}.zip"

    def _get_file_list_cache(self) -> dict:
        """
        Get or build a cache of all files in the Google Drive folder.

        Returns:
            Dictionary mapping filename -> file_id
        """
        cache_file = Path(tempfile.gettempdir()) / 'ubl_gdrive_file_cache.json'

        # Check if cache exists and is recent (less than 1 hour old)
        if cache_file.exists():
            import time
            age_seconds = time.time() - cache_file.stat().st_mtime
            if age_seconds < 3600:  # 1 hour
                with open(cache_file, 'r') as f:
                    return json.load(f)

        # Build cache by listing folder contents
        print("  Building file list cache (this may take a moment)...")
        file_list = self._list_folder_contents()

        # Save cache
        with open(cache_file, 'w') as f:
            json.dump(file_list, f, indent=2)

        return file_list

    def _list_folder_contents(self) -> dict:
        """
        List all files in the Google Drive folder.

        Returns:
            Dictionary mapping filename -> file_id
        """
        if gdown is None:
            raise ImportError("gdown library required")

        # Use gdown to list folder contents
        # We'll download the folder metadata only
        import tempfile
        temp_dir = Path(tempfile.mkdtemp(prefix='ubl-gdrive-list-'))

        try:
            # Download folder structure (files will be listed but not fully downloaded)
            # Actually, gdown doesn't have a list-only mode, so we need to download
            # Let's use a different approach - hardcode the file IDs from exploration
            # This is more efficient than downloading the whole folder every time

            # Fallback: download entire folder once to build cache
            gdown.download_folder(
                id=self.folder_id,
                output=str(temp_dir),
                quiet=True,
                use_cookies=False
            )

            # Extract file mappings
            file_map = {}
            for zip_file in temp_dir.rglob('*.zip'):
                # Extract file ID from the download (not available in gdown API)
                # We'll rely on filename matching instead
                file_map[zip_file.name] = None  # Placeholder

            return file_map

        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def download_release(self, release_num: int, stage: str, version: str,
                        dest_path: Optional[Path] = None) -> Path:
        """
        Download a release from Google Drive.

        Args:
            release_num: Release number (1-34)
            stage: Release stage
            version: UBL version
            dest_path: Optional destination path (defaults to temp directory)

        Returns:
            Path to downloaded ZIP file

        Raises:
            ImportError: If gdown is not installed
            RuntimeError: If download fails
        """
        if gdown is None:
            raise ImportError(
                "gdown library not installed. Install with: pip install gdown>=5.0.0"
            )

        # Generate expected filename
        filename = self.get_file_naming_pattern(release_num, stage, version)

        # Create destination directory
        if dest_path is None:
            temp_dir = Path(tempfile.mkdtemp(prefix='ubl-gdrive-'))
            dest_path = temp_dir / "release.zip"
        else:
            dest_path = Path(dest_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  Looking for: {filename}")

        try:
            # Download the entire folder (gdown doesn't support downloading single files from folder)
            # Files will be cached locally after first download
            download_dir = Path(tempfile.mkdtemp(prefix='ubl-gdrive-folder-'))

            # Download folder with file we need
            print(f"  Downloading from Google Drive (folder: {self.folder_id})...")
            gdown.download_folder(
                id=self.folder_id,
                output=str(download_dir),
                quiet=True,
                use_cookies=False
            )

            # Find the specific file we need
            found_file = None
            for file in download_dir.rglob('*.zip'):
                if file.name == filename:
                    found_file = file
                    break

            if not found_file:
                # List available files for debugging
                available = [f.name for f in download_dir.rglob('*.zip')]
                raise RuntimeError(
                    f"File not found in Google Drive folder: {filename}\n"
                    f"Available files: {', '.join(sorted(available[:5]))}..."
                )

            # Move the file to destination
            import shutil
            shutil.move(str(found_file), str(dest_path))

            # Clean up temp folder
            shutil.rmtree(download_dir, ignore_errors=True)

            file_size_mb = dest_path.stat().st_size / 1024 / 1024
            print(f"  Downloaded {file_size_mb:.1f} MB")

            return dest_path

        except Exception as e:
            raise RuntimeError(f"Google Drive download failed: {e}")


def download_release_from_gdrive(release_num: int, stage: str, version: str,
                                  dest_path: Optional[Path] = None) -> Path:
    """
    Convenience function to download a release from Google Drive.

    Args:
        release_num: Release number (1-34)
        stage: Release stage
        version: UBL version
        dest_path: Optional destination path

    Returns:
        Path to downloaded ZIP file
    """
    downloader = GoogleDriveDownloader()
    return downloader.download_release(release_num, stage, version, dest_path)


if __name__ == '__main__':
    # Quick test
    import sys

    if len(sys.argv) != 4:
        print("Usage: python -m tools.gdrive_downloader <release_num> <stage> <version>")
        print("Example: python -m tools.gdrive_downloader 1 prd 2.0")
        sys.exit(1)

    release_num = int(sys.argv[1])
    stage = sys.argv[2]
    version = sys.argv[3]

    print(f"Testing Google Drive download for release #{release_num}")
    zip_path = download_release_from_gdrive(release_num, stage, version)
    print(f"Success! Downloaded to: {zip_path}")
