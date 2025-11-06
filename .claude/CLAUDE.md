# UBL Release History Import Project

## Project Goal
Import all official UBL (Universal Business Language) releases from OASIS into this git repository in chronological order, creating a commit-based history showing UBL evolution from version 2.0 through 2.5.

## Current Status
- **Phase:** Documentation and analysis complete
- **Branch:** `claude/analyze-errata-packages-011CUrvAgwtX28jnLoCXK4tB`
- **Next:** Create import tooling (`tools/import_release.py`, `tools/catchup.py`)

## Repository Structure
```
ubl-release-package/
├── CLAUDE.md              # This file - project memory
├── .claude/               # Detailed documentation (see below)
├── tools/                 # Import automation scripts (to be created)
├── README.md              # Meta-README about this repo
└── [UBL content]          # All UBL files at root level (after import)
```

## Critical Rules

### 1. Commit Separation
**NEVER mix release commits with infrastructure commits.**
- ✅ Tooling changes: separate commits
- ✅ Each UBL release: separate commit
- ❌ Release + tool changes: NEVER in same commit

### 2. Special Package Handling
- **Entry #10 (errata-UBL-2.0)**: SKIP - draft version
- **Entry #11 (os-UBL-2.0-update-delta)**: PATCH - apply as overlay on #9 (os-UBL-2.0)
- All others: FULL release import

### 3. File Handling Per Release
For each release: Remove all files except `tools/`, `.claude/`, `.git/`, `README.md`, then extract ZIP to root.

## Import Strategy
1. Import 36 releases total (#1-9, #12-37)
2. Skip #10 (errata draft)
3. Apply #11 as PATCH on #9
4. Tag OASIS Standards (os-*) with version tags (v2.0, v2.1, etc.)
5. Tag all releases with descriptive tags (prd-UBL-2.0, cs01-UBL-2.2, etc.)

## Terminology
- **prd/csprd**: Public Review Draft (Committee Specification Public Review Draft)
- **cs/cos**: Committee Specification (OASIS Specification)
- **os**: OASIS Standard (final approved release)
- **csd**: Committee Specification Draft
- Full OASIS terminology: https://www.oasis-open.org/policies-guidelines/

## Detailed Documentation
See `.claude/` directory for comprehensive documentation:
- `ubl-releases-complete-inventory.md` - All 37 releases with URLs, dates, sizes
- `project-rules.md` - Detailed rules, conventions, and technical implementation
- `next-steps.md` - Remaining work and task breakdown
- `session-history.md` - What has been completed, decisions made
- `deferred-items.md` - Future enhancements (nice-to-have items)

## Common Commands
```bash
# Check git status
git status

# When ready to create import tool
mkdir -p tools && cd tools

# Import single release (future)
python tools/import_release.py <url>

# Import all releases (future)
python tools/catchup.py
```

## Key Decisions
- **No external dependencies:** Python stdlib only (argparse, urllib, zipfile, xml.etree)
- **No manifest file:** Release URLs hardcoded in catchup.py
- **Metadata extraction:** Auto-extract from UBL-X.X.xml files, fallback to URL parsing
- **README updates:** Update with each release commit, add hashes in batch at end

## Documentation Maintenance

**After each commit, review and update documentation if needed:**
- Is `CLAUDE.md` still accurate with current status?
- Do `project-rules.md` decisions reflect latest changes?
- Should `session-history.md` be updated with what was completed?
- Are `next-steps.md` tasks still current?
- Move resolved items from `deferred-items.md` to `session-history.md`

**Keep documentation lean and current** - Remove outdated info, merge duplicates, delete unnecessary files.
