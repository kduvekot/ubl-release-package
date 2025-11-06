# UBL Release History Import - Project Rules

## Project Goal

Import all official UBL (Universal Business Language) releases from OASIS into this git repository in chronological order, creating a commit-based history that shows the evolution of UBL from version 2.0 through 2.5.

## Scope

### Included
- UBL 2.0 through UBL 2.5 releases (34 total)
- All intermediate releases: prd, csprd, csd, cs, cos, os stages
- Draft releases (e.g., csd01-UBL-2.5)

### Excluded
- UBL 1.0 series (too different from 2.x)
- NDR (Naming and Design Rules) specifications
- JSON/ASN.1 format transformations
- Supplementary documentation (governance, guidelines, etc.)

### Special Handling (Resolved)
- `errata-UBL-2.0` (#10): **SKIP** - draft corrections package (superseded by #11)
- `os-UBL-2.0-update-delta` (#11): **PATCH** - apply as overlay on os-UBL-2.0 (#9)
  - Contains 14 changed files (non-substantive corrections)
  - See `.claude/deferred-items.md` for complete analysis

## Core Principles

### Commit Separation (CRITICAL RULE)

**NEVER mix release commits with infrastructure commits.**

- ✅ Tooling/infrastructure changes: separate commits
- ✅ Each UBL release: separate commit
- ❌ Release content + tool changes: NEVER in same commit

### Repository Structure

```
ubl-release-package/
├── .claude/              # Project documentation
├── .git/                 # Git repository data
├── tools/                # Import automation scripts
├── README.md             # Meta-README about this repo
└── [UBL content]         # All UBL files at root level
    ├── xsd/
    ├── cl/
    ├── art/
    ├── mod/
    └── ...
```

**Key Principle:** UBL content lives at repository root; tooling is clearly separated in `tools/`.

## README.md Policy

### Type
Meta-README that explains what this repository is (not UBL documentation).

### Content
- Explains this repo contains historical UBL releases
- Shows latest release included
- Lists all releases with dates and commit hashes

### Update Strategy
- Updated as part of each release commit
- Shows the release being added
- Commit hash can be added in follow-up commit (after release import)

### Example Structure
```markdown
# UBL Release Package History

This repository contains the complete release history of OASIS Universal
Business Language (UBL) versions 2.0 through 2.5.

## Latest Release
UBL 2.4 (OASIS Standard) - 20 June 2024

## Release History
- v2.4 (os-UBL-2.4) - 2024-06-20 - commit abc123
- cs01-UBL-2.4 - 2023-10-17 - commit def456
...
```

## Git Tagging Strategy

### All Releases
Every release gets a descriptive tag:
- Format: `{stage}-UBL-{version}`
- Examples: `prd-UBL-2.0`, `cs01-UBL-2.2`, `csd03-UBL-2.3`

### OASIS Standards Only
Official standards (os-*) get additional major version tags:
- Format: `v{version}`
- Examples: `v2.0`, `v2.1`, `v2.2`, `v2.3`, `v2.4`

### Rationale
- Descriptive tags preserve full release context
- Major version tags provide easy access to official standards
- Both tag types can coexist on the same commit

## File Handling Per Release

### Process
1. **Remove all files** except: `tools/`, `.claude/`, `.git/`, `README.md`
2. **Extract ZIP** contents to repository root
3. **Update README.md** with release information
4. **Stage all changes**: `git add -A`
   - Captures new files (additions)
   - Captures deleted files (removals)
   - Captures modified files (changes)
   - Git auto-detects renames/moves

### Why Complete Replacement?
- Ensures perfect accuracy of each release
- Git automatically tracks what changed between releases
- Handles file deletions/renames correctly
- No risk of leftover files from previous releases

## Commit Message Format

```
Release: UBL {version} ({status})

Date: {iso_date}
Stage: {stage_code}
Source: {url}
```

### Example
```
Release: UBL 2.2 (OASIS Standard)

Date: 2018-07-09
Stage: os
Source: https://docs.oasis-open.org/ubl/os-UBL-2.2/UBL-2.2.zip
```

## Python Implementation Decisions

### CLI Library
**Decision:** Use `argparse` (Python stdlib)

**Rationale:**
- No external dependencies
- Part of standard library (always available)
- Sufficient for our needs
- Well-documented and stable

### No Manifest File
**Decision:** Hardcode release URLs in `catchup.py`

**Rationale:**
- Manifest only used once (initial catchup)
- No ongoing value after import complete
- Simpler architecture
- `.claude/ubl-releases-complete-inventory.md` already documents all releases

### Metadata Extraction
**Primary:** Auto-extract from `UBL-X.X.xml` inside each ZIP

**Fallback:** Parse URL + use file dates for releases without XML

## Commit Order

```
Commit 1: Add infrastructure (tools/, initial README, .claude/)
Commit 2: Release prd-UBL-2.0
Commit 3: Release prd2-UBL-2.0
Commit 4: Release prd3-UBL-2.0
...
Commit 35: Release csd01-UBL-2.5
```

Each release commit is completely independent and contains only that release's content plus updated README.md.
