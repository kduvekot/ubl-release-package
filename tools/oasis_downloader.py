#!/usr/bin/env python3
"""
OASIS Downloader Module

Downloads UBL release packages directly from the OASIS document repository,
using the package URL recorded for each release in release_data.py.

Uses only the Python standard library (urllib).
"""

import shutil
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "ubl-release-package-importer"
CHUNK_SIZE = 1024 * 1024  # 1 MiB
DEFAULT_RETRIES = 4
TIMEOUT_SECONDS = 120


def download_file(url: str, dest_path: Path, retries: int = DEFAULT_RETRIES) -> Path:
    """
    Download a URL to dest_path, retrying with exponential backoff.

    Supports https:// and file:// URLs (file:// is used by the test suites).
    The download is written to a temporary '.part' file and only moved into
    place once complete, so a failed download never leaves a partial file
    at dest_path.

    Raises:
        RuntimeError: If the download fails after all retries.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = dest_path.with_name(dest_path.name + '.part')

    last_error = None
    for attempt in range(retries + 1):
        if attempt:
            delay = 2 ** attempt
            print(f"  Retrying in {delay}s (attempt {attempt + 1}/{retries + 1})...")
            time.sleep(delay)
        try:
            request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response, \
                    open(part_path, 'wb') as out:
                expected = response.headers.get('Content-Length')
                shutil.copyfileobj(response, out, CHUNK_SIZE)
            size = part_path.stat().st_size
            if expected is not None and size != int(expected):
                raise RuntimeError(f"incomplete download: got {size} of {expected} bytes")
            part_path.replace(dest_path)
            elapsed = max(time.monotonic() - start, 0.001)
            print(f"  Downloaded {size / 1024 / 1024:.1f} MB in {elapsed:.1f}s")
            return dest_path
        except (urllib.error.URLError, OSError, RuntimeError) as e:
            last_error = e
            print(f"  Download attempt {attempt + 1} failed: {e}")
            if part_path.exists():
                part_path.unlink()

    raise RuntimeError(f"Download of {url} failed after {retries + 1} attempts: {last_error}")


def download_release(release, dest_path: Path) -> Path:
    """
    Download the package ZIP for a release from OASIS and verify it.

    Args:
        release: Release object (uses release.url)
        dest_path: Where to store the ZIP. Keep this OUTSIDE the directory the
                   ZIP will be extracted into, otherwise packages without a
                   top-level folder would pick up the ZIP file itself as content.

    Returns:
        Path to the downloaded ZIP file

    Raises:
        RuntimeError: If the download fails or the file is not a valid ZIP.
    """
    print(f"  Downloading: {release.url}")
    path = download_file(release.url, dest_path)
    if not zipfile.is_zipfile(path):
        raise RuntimeError(f"Downloaded file is not a valid ZIP: {release.url}")
    return path
