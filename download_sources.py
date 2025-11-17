#!/usr/bin/env python3
"""
Download all 34 UBL release ZIP files to sources/ directory.
"""

import urllib.request
import urllib.error
import os
import sys
from tools.release_data import RELEASES

def download_file(url, dest_path):
    """Download a file with progress indication."""
    try:
        print(f"  Downloading from {url}")

        # Download with progress
        with urllib.request.urlopen(url, timeout=60) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(dest_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"    Progress: {pct:.1f}% ({downloaded}/{total_size} bytes)", end='\r')

            print(f"    ✓ Downloaded {downloaded} bytes")
            return True

    except urllib.error.HTTPError as e:
        print(f"    ✗ HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"    ✗ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def get_filename_from_url(url, release):
    """Extract or generate appropriate filename for the ZIP."""
    # Extract the last part of the URL path
    parts = url.rstrip('/').split('/')

    # For URLs that end with directory/UBL-2.X.zip, use the directory name
    if len(parts) >= 2 and parts[-1] in ['UBL-2.1.zip', 'UBL-2.2.zip', 'UBL-2.3.zip', 'UBL-2.4.zip', 'UBL-2.5.zip']:
        # Use the directory name which is more descriptive
        return f"{parts[-2]}.zip"

    # Otherwise just use the filename from URL
    return parts[-1]

def main():
    """Download all release ZIP files."""
    sources_dir = "sources"

    if not os.path.exists(sources_dir):
        print(f"Error: {sources_dir} directory not found")
        return 1

    print(f"Downloading {len(RELEASES)} UBL release ZIP files to {sources_dir}/\n")

    success_count = 0
    fail_count = 0

    for release in RELEASES:
        filename = get_filename_from_url(release.url, release)
        dest_path = os.path.join(sources_dir, filename)

        print(f"[{release.num}/34] {filename}")

        # Skip if already exists
        if os.path.exists(dest_path):
            file_size = os.path.getsize(dest_path)
            print(f"  ⊙ Already exists ({file_size} bytes)")
            success_count += 1
            continue

        if download_file(release.url, dest_path):
            success_count += 1
        else:
            fail_count += 1

        print()

    print("\n" + "="*60)
    print(f"Complete: {success_count} successful, {fail_count} failed")

    if fail_count > 0:
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
