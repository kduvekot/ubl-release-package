#!/usr/bin/env python3
"""
Try to access Google Drive API for public folder.
"""

import urllib.request
import json

def try_drive_api():
    folder_id = "1yq-RWOhaFIYW5byso8lZqpPUahtmaNvm"

    # Try different API endpoints
    endpoints = [
        # Drive API v3 - files list
        f"https://www.googleapis.com/drive/v3/files?q='{folder_id}'+in+parents&key=AIzaSyA",
        # Drive API v2
        f"https://www.googleapis.com/drive/v2/files?q='{folder_id}'+in+parents",
        # Direct folder metadata
        f"https://www.googleapis.com/drive/v3/files/{folder_id}?fields=*",
    ]

    print(f"Trying Google Drive API endpoints for folder: {folder_id}\n")

    for endpoint in endpoints:
        print(f"Trying: {endpoint[:80]}...")
        try:
            req = urllib.request.Request(endpoint)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                print("  SUCCESS! Got response:")
                print(json.dumps(data, indent=2)[:500])
                return data
        except urllib.error.HTTPError as e:
            print(f"  HTTP {e.code}: {e.reason}")
        except Exception as e:
            print(f"  Error: {str(e)[:50]}")

    print("\nAPI endpoints require authentication.")
    print("\nAlternative: Download using gdown library")
    print("  pip install gdown")
    print(f"  gdown --folder https://drive.google.com/drive/folders/{folder_id}")

    return None

if __name__ == '__main__':
    try_drive_api()
