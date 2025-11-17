#!/usr/bin/env python3
"""
Advanced extraction from Google Drive folder page - look for all embedded data.
"""

import urllib.request
import re
import json

def extract_all_json_structures(html):
    """Extract all possible JSON arrays/objects from the HTML."""

    # Find all potential JSON structures (arrays and objects)
    # Look for patterns that start with [ or { and try to parse them

    results = []

    # Pattern: Look for large array structures that might contain file data
    # Google Drive often has nested arrays like [[[...]]]
    array_pattern = r'\[\[\[.*?\]\]\]'

    matches = re.finditer(array_pattern, html, re.DOTALL)

    for i, match in enumerate(matches):
        chunk = match.group()
        if len(chunk) > 1000 and len(chunk) < 5000000:  # Reasonable size
            try:
                data = json.loads(chunk)
                results.append(('array', i, data))
                print(f"Found JSON array #{i}, length: {len(chunk)}")
            except:
                pass

    return results

def search_for_files_recursive(obj, path="", depth=0, max_depth=15):
    """Recursively search through nested structures for file data."""

    if depth > max_depth:
        return []

    files = []

    if isinstance(obj, dict):
        # Check if this looks like a file object
        if isinstance(obj.get('id'), str) and len(obj.get('id', '')) > 20:
            if 'title' in obj or 'name' in obj:
                filename = obj.get('title') or obj.get('name', '')
                if filename and filename.endswith('.zip'):
                    files.append({
                        'id': obj['id'],
                        'name': filename,
                        'path': path
                    })

        # Recurse into dict values
        for k, v in obj.items():
            files.extend(search_for_files_recursive(v, f"{path}.{k}", depth + 1))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            # Look for list items that have file-like structure
            if isinstance(item, list) and len(item) > 5:
                # Google Drive often uses array format like:
                # [file_id, file_name, mime_type, ...]
                if isinstance(item[0], str) and len(item[0]) > 20:
                    if len(item) > 1 and isinstance(item[1], str):
                        if item[1].endswith('.zip'):
                            files.append({
                                'id': item[0],
                                'name': item[1],
                                'path': f"{path}[{i}]"
                            })

            files.extend(search_for_files_recursive(item, f"{path}[{i}]", depth + 1))

    return files

def main():
    folder_url = 'https://drive.google.com/drive/folders/1yq-RWOhaFIYW5byso8lZqpPUahtmaNvm?usp=sharing'

    print("Fetching Google Drive folder page...\n")

    req = urllib.request.Request(
        folder_url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    )

    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')

    print(f"Fetched {len(html):,} bytes\n")

    # Try to find the main data initialization
    # Google Drive uses various patterns, let's try them all

    patterns = [
        (r'AF_initDataCallback\({[^}]*key:\s*["\']ds:(\d+)["\'][^}]*data:(.*?), sideChannel:', 'AF_initDataCallback'),
        (r'\[\["wrb.fr","[^"]*","\[\[.*?\]\]"', 'wrb.fr'),
        (r'window\[.+?\]\s*=\s*(\[\[.+?\]\]);', 'window assignment'),
    ]

    all_files = []

    for pattern, name in patterns:
        print(f"Trying pattern: {name}")
        matches = re.findall(pattern, html, re.DOTALL)
        print(f"  Found {len(matches)} matches")

        for j, match in enumerate(matches[:5]):  # Check first 5 matches
            try:
                # Extract the data part
                if isinstance(match, tuple):
                    data_str = match[-1]  # Last capture group
                else:
                    data_str = match

                # Try to parse
                if data_str.strip().startswith('['):
                    data = json.loads(data_str)
                    print(f"    Match #{j}: Parsed JSON, searching for files...")

                    files = search_for_files_recursive(data)
                    if files:
                        print(f"    Found {len(files)} files!")
                        all_files.extend(files)
            except Exception as e:
                print(f"    Match #{j}: Error - {str(e)[:50]}")

    # Deduplicate
    seen = set()
    unique_files = []
    for f in all_files:
        if f['id'] not in seen:
            seen.add(f['id'])
            unique_files.append(f)

    if unique_files:
        print(f"\n{'='*70}")
        print(f"SUCCESS! Found {len(unique_files)} ZIP files:")
        print(f"{'='*70}\n")

        for f in unique_files:
            print(f"Name: {f['name']}")
            print(f"  ID: {f['id']}")
            print(f"  Download: https://drive.google.com/uc?export=download&id={f['id']}")
            print()
    else:
        print("\n" + "="*70)
        print("Could not extract files automatically.")
        print("="*70)
        print("\nGoogle Drive requires browser rendering for this folder.")
        print("Please provide individual file share links or use the OASIS download.")

if __name__ == '__main__':
    main()
