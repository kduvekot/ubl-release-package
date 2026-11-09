# UBL Release Import Tools

Automated tools for importing OASIS UBL (Universal Business Language) releases into this git repository, creating a commit-based history from UBL 2.0 through 2.5.

## Overview

This toolset provides:
- **Git-based state tracking** - No separate state files, git history is the source of truth
- **Sequential import validation** - Ensures releases are imported in correct chronological order
- **Patch handling** - Automatically applies errata/update packages as overlays
- **Safety guardrails** - Prevents out-of-order imports, duplicate imports, and broken dependencies
- **Dry-run mode** - Validate before making changes
- **Batch import** - Import all releases with a single command

## Quick Start

### Import a Single Release

```bash
# Import release #1 (first UBL 2.0 release)
python3 -m tools.import_release 1

# Dry-run to preview what would happen
python3 -m tools.import_release 1 --dry-run

# Force import out of order (not recommended)
python3 -m tools.import_release 10 --force
```

### Import All Releases (Catchup)

```bash
# Import all releases in chronological order
python3 -m tools.catchup

# Dry-run to validate all releases
python3 -m tools.catchup --dry-run

# Import a range of releases
python3 -m tools.catchup --start-from 1 --end-at 10

# Resume after failure
python3 -m tools.catchup --start-from 15
```

### Check Current State

```bash
# Show what releases have been imported
python3 -m tools.git_state

# Show release inventory
python3 -m tools.release_data
```

## Architecture

### Modules

- **`git_state.py`** - Queries git history to determine what releases have been imported
- **`release_data.py`** - Hardcoded inventory of all UBL releases with metadata
- **`oasis_downloader.py`** - Downloads release packages directly from OASIS (stdlib `urllib`)
- **`validators.py`** - Validation logic and safety checks
- **`import_release.py`** - Core import logic for a single release
- **`catchup.py`** - Batch import tool for importing multiple releases

### Safety Features

#### 1. Git-Based State Tracking
No separate state file needed - the tool queries git history to determine what's been imported:
```python
from tools.git_state import GitStateManager

# Get all imported releases
commits = GitStateManager.get_release_commits()

# Check if specific release was imported
imported = GitStateManager.has_release_been_imported('os', '2.0')
```

#### 2. Sequential Order Enforcement
By default, releases must be imported in order:
```bash
# This works (first import)
python3 -m tools.import_release 1

# This fails (skipping releases)
python3 -m tools.import_release 10
# ERROR: Expected release #2, got #10

# Override with --force (not recommended)
python3 -m tools.import_release 10 --force
```

#### 3. Patch Dependency Validation
Patch releases (errata/updates) require their base release:
```bash
# Release #7 (errata-UBL-2.0) requires #6 (os-UBL-2.0)
python3 -m tools.import_release 7
# ERROR: Base release #6 not imported yet
```

#### 4. Working Directory Clean Check
Prevents imports when there are uncommitted changes:
```bash
python3 -m tools.import_release 1
# ERROR: Working directory is not clean
# Run 'git status' to see what needs attention
```

## Release Types

### Full Releases (36 total)
Standard UBL releases - extract and replace all repository content:
- All `prd`, `cs`, `os`, etc. releases
- Content is completely replaced (except protected paths)

### Patch Releases (2 total)
Errata/update packages - overlay changed files on existing content:
- **Release #7**: `errata-UBL-2.0` (applies to #6: os-UBL-2.0)
- **Release #8**: `os-UBL-2.0-update` (applies to #7: errata-UBL-2.0)

## Commit Strategy

Each release creates a structured commit:

```
Release: UBL 2.0 (OASIS Standard)

Date: 2006-12-18
Stage: os
Source: https://docs.oasis-open.org/ubl/os-UBL-2.0.zip
```

## Tagging Strategy

### Descriptive Tags (All Releases)
Every release gets a descriptive tag:
- Format: `{stage}-UBL-{version}`
- Examples: `prd-UBL-2.0`, `cs01-UBL-2.2`, `os-UBL-2.4`

### Version Tags (OASIS Standards Only)
Official standards get additional version tags:
- Format: `v{version}`
- Examples: `v2.0`, `v2.1`, `v2.2`, `v2.3`, `v2.4`

## Protected Paths

These paths are never modified during import:
- `.git/` - Git repository data
- `.gitignore` - Git ignore rules
- `.claude/` - Project documentation
- `tools/` - Import tools (this directory)
- `README.md` - Meta-README

## Release Inventory

Total: **38 releases** from UBL 2.0 (2006) through UBL 2.5 (2026)

### By Version
- **UBL 2.0**: 8 releases (including 2 patches)
- **UBL 2.1**: 8 releases
- **UBL 2.2**: 6 releases
- **UBL 2.3**: 7 releases
- **UBL 2.4**: 4 releases
- **UBL 2.5**: 5 releases

### OASIS Standards (6 total)
Official approved standards:
1. UBL 2.0 (2006-12-18) - #6
2. UBL 2.1 (2013-11-04) - #16
3. UBL 2.2 (2018-07-09) - #22
4. UBL 2.3 (2021-06-15) - #29
5. UBL 2.4 (2024-06-20) - #33
6. UBL 2.5 (2026-08-12) - #38

## Testing

```bash
# Run all integration tests
bash tools/tests/run_tests.sh
```

Tests validate:
- Git state management
- Release data accuracy
- Validation logic
- Dry-run mode
- Sequential ordering
- Patch dependencies

See `tools/tests/README.md` for details.

## Python Dependencies

**None!** This toolset uses only Python standard library:
- `argparse` - CLI argument parsing
- `urllib.request` - Download ZIPs
- `zipfile` - Extract ZIPs
- `subprocess` - Git commands
- `pathlib` - Path handling
- `re` - Regular expressions

## Troubleshooting

### Import fails with "Working directory not clean"
```bash
# Check what's uncommitted
git status

# Commit or stash changes
git stash
```

### Import fails with "Expected release #X, got #Y"
```bash
# Import releases in order
python3 -m tools.import_release X

# Or use --force (not recommended)
python3 -m tools.import_release Y --force
```

### Want to see what would happen without making changes?
```bash
# Use dry-run mode
python3 -m tools.import_release 1 --dry-run
python3 -m tools.catchup --dry-run
```

### Download fails or times out
```bash
# Downloads are from docs.oasis-open.org
# Check network connectivity
curl -I https://docs.oasis-open.org/ubl/os-UBL-2.4/UBL-2.4.zip

# Try again - downloads can be large (up to 100MB)
python3 -m tools.import_release X
```

## Examples

### Import First 5 Releases
```bash
python3 -m tools.catchup --start-from 1 --end-at 5
```

### Resume After Failure at Release #20
```bash
python3 -m tools.catchup --start-from 20
```

### Preview All Imports Without Changes
```bash
python3 -m tools.catchup --dry-run
```

### Check What's Been Imported
```bash
python3 -m tools.git_state
```

Output:
```
Total releases imported: 5

UBL 2.0: 5 release(s)
  - prd             Public Review Draft              (2006-01-20)
  - prd2            Public Review Draft 2            (2006-07-28)
  - prd3            Public Review Draft 3            (2006-09-21)
  - prd3r1          Public Review Draft 3 Revision 1 (2006-10-05)
  - cs              Committee Specification          (2006-10-12)
```

## Development

### Adding a New Release

When OASIS publishes a new UBL package (check https://docs.oasis-open.org/ubl/):

1. **Find the package details** in the new release directory on OASIS:
   - the package ZIP URL (e.g. `https://docs.oasis-open.org/ubl/csd01-UBL-2.6/UBL-2.6.zip`)
   - the publication date: the `<pubdate>` in the release's `UBL-X.Y.xml`
     (`unzip -p UBL-2.6.zip '*UBL-2.6.xml' | grep -o '<pubdate>[^<]*'`)

2. **Add the release to `release_data.py`** with the next sequence number, in
   chronological order:
   ```python
   Release(39, "2.6", "csd01", "2027-01-15",
           "https://docs.oasis-open.org/ubl/csd01-UBL-2.6/UBL-2.6.zip"),
   ```
   If the stage is new (not yet in `STAGE_DESCRIPTIONS`), add its description too.

3. **Test the tooling and commit it** (tooling commit, separate from the release):
   ```bash
   python3 -m tools.release_data             # Should show new release
   python3 -m tools.import_release 39 --dry-run
   bash tools/tests/run_tests.sh             # Should pass
   ```

4. **Import the release** (creates the release commit and tags):
   ```bash
   python3 -m tools.import_release 39
   ```

5. **Push the commit and the new tags**:
   ```bash
   git push -u origin <branch>
   git push origin csd01-UBL-2.6             # plus vX.Y for an OASIS Standard
   ```

6. **Update the docs** (separate commit): `.claude/CLAUDE.md`,
   `.claude/ubl-releases-complete-inventory.md`, `.claude/session-history.md`
   and the inventory section of this README.

### Running Tests During Development
```bash
# Quick validation
python3 -m tools.git_state
python3 -m tools.release_data
python3 -m tools.validators

# Full test suite
bash tools/tests/run_tests.sh
```

## License

This tooling is part of the UBL Release Package History project.
The UBL specifications themselves are governed by OASIS IPR policies.
