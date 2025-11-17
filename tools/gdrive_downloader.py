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

from .gdrive_file_ids import get_file_id


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

    def download_release(self, release_num: int, stage: str, version: str,
                        dest_path: Optional[Path] = None) -> Path:
        """
        Download a release from Google Drive by file ID.

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

        # Get file ID for this release
        try:
            file_id = get_file_id(release_num)
        except KeyError as e:
            raise RuntimeError(f"No file ID mapping for release #{release_num}: {e}")

        # Generate expected filename for verification
        filename = self.get_file_naming_pattern(release_num, stage, version)

        # Create destination directory
        if dest_path is None:
            temp_dir = Path(tempfile.mkdtemp(prefix='ubl-gdrive-'))
            dest_path = temp_dir / "release.zip"
        else:
            dest_path = Path(dest_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  Downloading: {filename}")
        print(f"  File ID: {file_id}")

        try:
            # Download individual file by ID
            file_url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(file_url, str(dest_path), quiet=False, fuzzy=True)

            if not dest_path.exists():
                raise RuntimeError(f"Download completed but file not found at {dest_path}")

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
