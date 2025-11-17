#!/usr/bin/env python3
"""
Extract file information from Google Drive folder page.
"""

import urllib.request
import re
import json

def extract_gdrive_files(folder_url):
    """Extract file IDs and names from Google Drive folder page."""

    # Fetch the page
    req = urllib.request.Request(
        folder_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    )

    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')

    print(f"Fetched {len(html)} bytes of HTML\n")

    # Try multiple patterns to find file data
    files_found = []

    # Pattern 1: Look for file IDs in standard format
    file_id_pattern = r'["\']([-\w]{25,})["\']'
    potential_ids = re.findall(file_id_pattern, html)
    print(f"Found {len(potential_ids)} potential file IDs\n")

    # Pattern 2: Look for JSON data structures that might contain file info
    # Google Drive often embeds data in JavaScript variables
    json_patterns = [
        r'var _DRIVE_ivd\s*=\s*(\[.+?\]);',
        r'window\[\'_DRIVE_ivd\'\]\s*=\s*(\[.+?\]);',
        r'AF_initDataCallback\({[^}]*data:(\[.+?\])[,}]',
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, html, re.DOTALL)
        print(f"Pattern '{pattern[:30]}...' found {len(matches)} matches")

        for match in matches[:3]:  # Check first few matches
            try:
                # Try to parse as JSON
                if len(match) > 100 and len(match) < 1000000:  # Reasonable size
                    data = json.loads(match)
                    print(f"  Successfully parsed JSON structure with {len(str(data))} chars")

                    # Recursively search for file-like structures
                    def find_files(obj, depth=0):
                        if depth > 10:
                            return

                        if isinstance(obj, dict):
                            # Look for file-like structures
                            if 'id' in obj and 'name' in obj:
                                files_found.append({
                                    'id': obj['id'],
                                    'name': obj.get('name', 'unknown'),
                                    'mimeType': obj.get('mimeType', ''),
                                })
                            for v in obj.values():
                                find_files(v, depth + 1)
                        elif isinstance(obj, list):
                            for item in obj:
                                find_files(item, depth + 1)

                    find_files(data)

            except json.JSONDecodeError:
                continue

    # Pattern 3: Look for specific ZIP file references
    zip_pattern = r'(["\'])([^"\']*\.zip)\\1.*?["\']([a-zA-Z0-9_-]{25,})["\']'
    zip_matches = re.findall(zip_pattern, html, re.IGNORECASE)

    for match in zip_matches:
        files_found.append({
            'name': match[1],
            'id': match[2],
            'mimeType': 'application/zip'
        })

    print(f"\nTotal files found: {len(files_found)}\n")

    # Deduplicate and filter
    seen = set()
    unique_files = []
    for f in files_found:
        key = (f.get('id'), f.get('name'))
        if key not in seen and f.get('name', '').endswith('.zip'):
            seen.add(key)
            unique_files.append(f)

    return unique_files

if __name__ == '__main__':
    folder_url = 'https://drive.google.com/drive/folders/1yq-RWOhaFIYW5byso8lZqpPUahtmaNvm?usp=sharing'

    print("Attempting to extract Google Drive folder contents...\n")

    files = extract_gdrive_files(folder_url)

    if files:
        print(f"\n{'='*60}")
        print(f"Found {len(files)} ZIP files:")
        print(f"{'='*60}\n")

        for f in files:
            print(f"Name: {f['name']}")
            print(f"  ID: {f['id']}")
            print(f"  Download URL: https://drive.google.com/uc?export=download&id={f['id']}")
            print()
    else:
        print("\nNo files extracted. The page structure may require browser rendering.")
        print("Showing first 2000 chars of HTML for analysis:")
        print("-" * 60)

        # Re-fetch to show sample
        req = urllib.request.Request(
            folder_url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            print(html[:2000])
