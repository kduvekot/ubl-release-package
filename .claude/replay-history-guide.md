# UBL History Replay Guide

## Overview

This guide documents how to recreate the entire UBL release history (34 releases from UBL 2.0 to 2.5) on a clean git branch with proper rename detection.

## Current Status

- **Branch with tools**: `claude/rename-detection-implementation-01SHHSrmLe6T6zSHpwC6etku`
- **Tools tested**: Releases 1-10 validated successfully
- **Ready for**: Full 34-release replay

## Prerequisites

1. **Python 3.x** with `gdown` package:
   ```bash
   pip install gdown
   ```

2. **Git repository** with the tools checked out:
   ```bash
   git checkout claude/rename-detection-implementation-01SHHSrmLe6T6zSHpwC6etku
   ```

## Tools Location

All tools are in `/tools/`:
- `replay_history_with_renames.py` - Main replay script
- `file_rename_detector.py` - Rename detection logic
- `release_data.py` - Release inventory (34 releases)
- `gdrive_downloader.py` - Google Drive download helper

## Running the Full Replay

### Option 1: Fresh Start (Recommended)

Creates a new orphan branch and imports all 34 releases:

```bash
python3 -m tools.replay_history_with_renames \
  --branch history-with-renames \
  --start 1 --end 34
```

### Option 2: Resume After Interruption

If the process was interrupted, use `--resume` to continue:

```bash
python3 -m tools.replay_history_with_renames \
  --branch history-with-renames \
  --resume --skip-branch-setup
```

### Option 3: Test Run First

Test with a small range before full run:

```bash
python3 -m tools.replay_history_with_renames \
  --branch test-branch \
  --start 1 --end 10
```

## Command Options

| Option | Description |
|--------|-------------|
| `--branch NAME` | Branch name for the replay (default: `history-with-renames`) |
| `--start N` | First release number (default: 1) |
| `--end N` | Last release number (default: 34) |
| `--resume` | Auto-detect and resume from last completed release |
| `--skip-branch-setup` | Use current branch (don't create orphan) |
| `--dry-run` | Show what would happen without making changes |

## What the Script Does

For each release:
1. Downloads ZIP from Google Drive
2. Extracts content
3. Detects file renames (e.g., `UBL-Invoice-2.1.xsd` → `UBL-Invoice-2.2.xsd`)
4. Applies renames via `git mv` for proper tracking
5. Clears old content, copies new content
6. Validates repo matches ZIP exactly (100% match required)
7. Creates commit with release metadata
8. Tags the release

## Validation

Every release is validated after import:
- **FULL releases**: Repo must exactly match ZIP (no missing/extra files)
- **PATCH releases**: Patch files must be correctly applied

If validation fails, the script stops immediately.

## Expected Output

```
======================================================================
Importing Release #9: prd1-UBL-2.1
======================================================================
  Downloading release #9...
  Extracting...
  Detecting renames from 2.0 → 2.1...
    Phase 1 (version bumps): 152 renames detected
  Applying 152 file renames...
    ✓ 152 renames applied via git mv
  Cleared 621 items
  Copied 517 files
  ✓ Commit created
  Validating import...
  ✓ Validation passed - repo matches ZIP exactly
✓ Successfully imported prd1-UBL-2.1
```

## Troubleshooting

### Google Drive Rate Limiting
If download fails with "Cannot retrieve the public link", wait 1-2 minutes and retry with `--resume`.

### Validation Failures
If validation fails, the script stops. Check the differences listed and investigate. Common issues:
- `.gitignore` blocking UBL content (fixed in current version)
- Renamed files being deleted (fixed in current version)

## Key Fixes Applied

1. **apply_renames() returns Set[Path]** - Tracks which renames succeeded
2. **clear_ubl_content() preserves renamed files** - Uses file-level git rm
3. **validate_patch_applied()** - Separate validation for patches
4. **Validation stops on failure** - No silent failures

## After Completion

The replay creates a clean history branch with:
- 34 commits (one per release)
- Proper git rename tracking (`git log --follow` works)
- Tags for each release
- README updated with each release

To verify rename detection worked:
```bash
git log --name-status | grep "^R"  # Shows renames
git log --follow xsd/maindoc/UBL-Invoice-2.5.xsd  # Track file across versions
```
