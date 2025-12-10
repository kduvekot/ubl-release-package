# UBL History Replay Guide

## Overview

This guide documents how to recreate the entire UBL release history (34 releases from UBL 2.0 to 2.5) on a clean git branch with proper rename detection and granular file tracking.

## Current Status

- **Branch with tools**: merged into main
- **Tools tested**: Unit tests (10) + Integration tests (4) passing
- **Ready for**: Full 34-release replay

## Release Processing Order

34 releases total, processed in order:

| # | Version | Name | Type |
|---|---------|------|------|
| 1 | 2.0 | Public Review Draft | FULL |
| 2 | 2.0 | Public Review Draft 2 | FULL |
| 3 | 2.0 | Public Review Draft 3 | FULL |
| 4 | 2.0 | Public Review Draft 3 Revision 1 | FULL |
| 5 | 2.0 | Committee Specification | FULL |
| 6 | 2.0 | OASIS Standard | FULL |
| 7 | 2.0 | Errata Draft | PATCH (on #6) |
| 8 | 2.0 | OASIS Standard Update | PATCH (on #7) |
| 9 | 2.1 | Public Review Draft 1 | FULL |
| 10-16 | 2.1 | (various stages) | FULL |
| 17-22 | 2.2 | (various stages) | FULL |
| 23-29 | 2.3 | (various stages) | FULL |
| 30-33 | 2.4 | (various stages) | FULL |
| 34 | 2.5 | Committee Specification Draft 01 | FULL |

Run `python3 -c "from tools.release_data import RELEASES; [print(f'#{r.num} {r.version} {r.status}') for r in RELEASES]"` for full list.

## Prerequisites

1. **Python 3.x** with `gdown` package:
   ```bash
   pip install gdown
   ```

2. **Git repository** with the tools checked out

## Tools Location

All tools are in `/tools/`:

| Tool | Purpose |
|------|---------|
| `granular_import.py` | **NEW** - Granular file-level import with change classification |
| `replay_history_with_renames.py` | Original replay script (one commit per release) |
| `file_rename_detector.py` | Rename detection logic |
| `release_data.py` | Release inventory (34 releases) |
| `gdrive_downloader.py` | Google Drive download helper |

## File Classification Logic

For each release, files are classified by comparing current repo state with release package:

| Status | Condition | Git Operation |
|--------|-----------|---------------|
| **UNCHANGED** | Same path, same content hash | None (skip) |
| **MODIFIED** | Same path, different content hash | Update content |
| **RENAMED** | Version pattern match (e.g., `-2.1` → `-2.2`) | `git mv` + update |
| **NEW** | Path only in release package | Add file |
| **DELETED** | Path only in repo (not renamed) | `git rm` |

### How Comparison Works

```python
repo_files = {path: content_hash}   # Current git-tracked files
zip_files = {path: content_hash}    # Files in release package

# Hash is MD5 of file CONTENTS, not filename
# This detects content changes even when path is unchanged
```

### Rename Detection

Renames are detected for ALL version transitions:

| Transition | Example |
|------------|---------|
| 2.0 → 2.1 | `UBL-Invoice-2.0.xsd` → `UBL-Invoice-2.1.xsd` |
| 2.1 → 2.2 | `UBL-Invoice-2.1.xsd` → `UBL-Invoice-2.2.xsd` |
| 2.2 → 2.3 | `UBL-Invoice-2.2.xsd` → `UBL-Invoice-2.3.xsd` |
| etc. | Pattern: `-{old_version}` → `-{new_version}` |

## Granular Import (Recommended)

The new `granular_import.py` provides fine-grained control:

### Commit Strategies

| Strategy | Description |
|----------|-------------|
| `per_file` | One commit per file change (most granular) |
| `per_type` | Batch by change type: renames → deletes → adds → modifications |
| `per_release` | Single commit per release (like original tool) |

### Usage

```bash
# Import single release
python3 -m tools.granular_import --release 1

# Import range with per-type commits (recommended)
python3 -m tools.granular_import --range 1 34 --commit-strategy per_type

# Test with local repo (creates fresh repo)
python3 -m tools.granular_import --release 1 --test-repo /tmp/ubl-test

# Dry run to see what would happen
python3 -m tools.granular_import --range 1 5 --dry-run

# Validate after each file (slower but thorough)
python3 -m tools.granular_import --release 1 --validate-each-file
```

### Command Options

| Option | Description |
|--------|-------------|
| `--release N` | Single release number to import |
| `--range START END` | Range of releases to import |
| `--commit-strategy` | `per_file`, `per_type`, or `per_release` |
| `--test-repo PATH` | Create fresh test repo at path |
| `--validate-each-file` | Validate after each file change |
| `--dry-run` | Show what would happen without changes |

### Processing Flow

```
For each release:
1. Download ZIP from Google Drive
2. Extract contents
3. Compare repo state with package: {path: content_hash}
4. Classify each file: UNCHANGED, MODIFIED, RENAMED, NEW, DELETED
5. Apply changes in order:
   a. Renames (git mv + update content)
   b. Deletions (git rm)
   c. Additions (copy new files)
   d. Modifications (update content)
6. Create commit(s) based on strategy
7. Validate: repo must match package exactly
```

### Expected Output

```
======================================================================
Importing Release #9: prd1-UBL-2.1
======================================================================
  Version: 2.1, Stage: prd1
  Type: FULL, Date: 2010-10-26
  Commit strategy: per_type
  Downloading release #9...
  Extracting...
  Current repo files: 621
  New release files: 517

  Release #9 (prd1-UBL-2.1): 152 renames, 104 deletions, 0 additions, 0 modifications

  Applying 152 renames...
  Applying 104 deletions...

  Validating final state...
  ✓ Validation passed - repo matches release exactly

✓ Successfully imported prd1-UBL-2.1
```

## Original Replay Script

The original `replay_history_with_renames.py` is still available for one-commit-per-release imports:

```bash
python3 -m tools.replay_history_with_renames \
  --branch history-with-renames \
  --start 1 --end 34
```

## Validation

Every release is validated after import:
- **FULL releases**: Repo must exactly match ZIP (no missing/extra files)
- **PATCH releases**: Patch files must be correctly applied

If validation fails, the script stops immediately.

## Testing

Run the test suites:

```bash
# Unit tests (10 tests) - file classification logic
python3 tools/tests/test_granular_import.py

# Integration tests (4 tests) - full workflow with mock data
python3 tools/tests/test_granular_integration.py
```

## Troubleshooting

### Google Drive Rate Limiting
If download fails with "Cannot retrieve the public link", wait 1-2 minutes and retry.

### Validation Failures
If validation fails, check the differences listed. Common issues:
- `.gitignore` blocking UBL content
- File permissions issues

### Git Rename Detection
Git uses content similarity (default 50%) to detect renames. Use `-M` flag to see renames:
```bash
git log --name-status -M | grep "^R"
```

## After Completion

The replay creates a clean history branch with:
- Commits based on chosen strategy
- Proper git rename tracking (`git log --follow` works)
- Tags for each release
- Validation ensuring repo matches each release exactly

To verify rename detection worked:
```bash
git log --name-status -M | grep "^R"  # Shows renames
git log --follow xsd/maindoc/UBL-Invoice-2.5.xsd  # Track file across versions
```
