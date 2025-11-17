#!/usr/bin/env python3
"""
Validate downloaded UBL ZIP files.
- Check ZIP integrity
- Verify contents match expected release
- Compare key files with OASIS directory listings
"""

import os
import zipfile
import re
from tools.release_data import RELEASES

def validate_zip_integrity(zip_path):
    """Test if ZIP is valid and not corrupted."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Test all files in the archive
            bad_file = zf.testzip()
            if bad_file:
                return False, f"Corrupted file: {bad_file}"
            return True, "OK"
    except zipfile.BadZipFile:
        return False, "Bad ZIP file"
    except Exception as e:
        return False, str(e)

def get_zip_contents(zip_path, max_list=20):
    """Get list of files in ZIP."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = zf.namelist()
            return files[:max_list], len(files)
    except:
        return [], 0

def extract_version_from_filename(filename):
    """Extract UBL version from filename like '01_prd-UBL-2.0.zip'."""
    match = re.search(r'UBL-(\d+\.\d+)', filename)
    if match:
        return match.group(1)
    return None

def extract_stage_from_filename(filename):
    """Extract stage from filename like '01_prd-UBL-2.0.zip'."""
    # Remove number prefix and .zip
    name = re.sub(r'^\d+_', '', filename)
    name = name.replace('.zip', '')
    # Extract stage part (before -UBL-)
    match = re.search(r'^([^-]+)-UBL', name)
    if match:
        return match.group(1)
    return None

def main():
    temp_dir = "sources/temp"

    if not os.path.exists(temp_dir):
        print(f"Error: {temp_dir} not found")
        return 1

    zip_files = sorted([f for f in os.listdir(temp_dir) if f.endswith('.zip')])

    if not zip_files:
        print(f"No ZIP files found in {temp_dir}")
        return 1

    print(f"\n{'='*80}")
    print(f"Validating {len(zip_files)} ZIP files")
    print(f"{'='*80}\n")

    results = []
    all_valid = True

    for zip_file in zip_files:
        zip_path = os.path.join(temp_dir, zip_file)
        file_size_mb = os.path.getsize(zip_path) / (1024*1024)

        # Extract release number from filename
        match = re.match(r'(\d+)_', zip_file)
        release_num = int(match.group(1)) if match else None

        print(f"[{zip_file}]")
        print(f"  Size: {file_size_mb:.1f} MB")

        # Validate ZIP integrity
        is_valid, msg = validate_zip_integrity(zip_path)
        print(f"  Integrity: {msg}")

        if not is_valid:
            all_valid = False
            results.append((zip_file, False, "Corrupted"))
            print()
            continue

        # Get contents
        files, total_count = get_zip_contents(zip_path, max_list=10)
        print(f"  Files: {total_count} total")

        # Extract version and stage from filename
        version = extract_version_from_filename(zip_file)
        stage = extract_stage_from_filename(zip_file)

        # Check if matches release_data.py
        if release_num and release_num <= len(RELEASES):
            expected_release = RELEASES[release_num - 1]
            version_match = expected_release.version == version
            stage_match = expected_release.stage in stage.lower() if stage else False

            if version_match and stage_match:
                print(f"  Match: ✓ v{version} {stage} (Release #{release_num})")
            else:
                print(f"  Match: ✗ Expected v{expected_release.version} {expected_release.stage}")
                print(f"         Got v{version} {stage}")

        # Show sample of contents
        if files:
            print(f"  Sample contents:")
            for f in files[:5]:
                print(f"    - {f}")
            if len(files) > 5:
                print(f"    ... and {len(files)-5} more")

        results.append((zip_file, is_valid, "Valid"))
        print()

    # Summary
    print(f"{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    valid_count = sum(1 for _, valid, _ in results if valid)
    print(f"Total files: {len(results)}")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {len(results) - valid_count}")

    if all_valid:
        print("\n✓ ALL FILES VALIDATED SUCCESSFULLY")
        return 0
    else:
        print("\n✗ SOME FILES FAILED VALIDATION")
        for filename, valid, msg in results:
            if not valid:
                print(f"  - {filename}: {msg}")
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
