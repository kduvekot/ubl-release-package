# UBL Release History Import Project

## Project Goal
Import all official UBL (Universal Business Language) releases from OASIS into this git repository in chronological order, creating a commit-based history showing UBL evolution from version 2.0 through 2.5.

## Current Status
- **Phase:** Import tooling complete and tested ✓
- **Branch:** `claude/core-tool-development-011CUs6q9AwMBhuaLCmBksWM`
- **Next:** Ready for full import of all 34 UBL releases
- **Test Coverage:** 60 tests, 52 passing (87%)

## Repository Structure
```
ubl-release-package/
├── .claude/
│   ├── CLAUDE.md          # This file - project memory (auto-loaded)
│   ├── settings.json      # Project configuration
│   └── *.md               # Detailed documentation
├── .git/                  # Git repository
├── .gitignore             # Excluded files
├── tools/                 # Import automation scripts ✓ COMPLETE
│   ├── git_state.py       # Git-based state tracking
│   ├── release_data.py    # 34 release inventory
│   ├── validators.py      # Safety guardrails
│   ├── import_release.py  # Single release import
│   ├── catchup.py         # Batch import all releases
│   └── tests/             # Comprehensive test suite (60 tests)
├── README.md              # Meta-README
└── [UBL content]          # All UBL files at root level (after import)
```

## Critical Rules

### 1. Commit Separation
**NEVER mix release commits with infrastructure commits.**
- ✅ Tooling changes: separate commits
- ✅ Each UBL release: separate commit
- ❌ Release + tool changes: NEVER in same commit

### 2. Special Package Handling
- **Entry #7 (errata-UBL-2.0)**: PATCH - draft corrections, apply as overlay on #6 (os-UBL-2.0)
- **Entry #8 (os-UBL-2.0-update-delta)**: PATCH - final approved corrections, apply on top of #7
- All others: FULL release import

**Important:** #7 and #8 are applied sequentially to show the complete correction history from draft to final approval.

### 3. File Handling Per Release
For each release: Remove all files except `tools/`, `.claude/`, `.git/`, `.gitignore`, `README.md`, then extract ZIP to root.

### 4. Secrets and URLs
** NEVER STORE URLs or secrets or any other sensitive information inside a file, piece of code or anything else that might get committed to git.
only after dedicated approval and agreement that this URL can be stored and used you are allowed to commit it to a file and document that it was agreed and when.

## Import Strategy
1. Import all 34 releases (#1-34)
2. Apply #7 (errata-UBL-2.0) as PATCH on #6, then #8 (os-UBL-2.0-update-delta) as PATCH on #7
3. Tag OASIS Standards (os-*) with version tags (v2.0, v2.1, etc.)
4. Tag all releases with descriptive tags (prd-UBL-2.0, errata-UBL-2.0, os-UBL-2.0-update, etc.)

## Terminology
- **prd/csprd**: Public Review Draft (Committee Specification Public Review Draft)
- **cs/cos**: Committee Specification (OASIS Specification)
- **os**: OASIS Standard (final approved release)
- **csd**: Committee Specification Draft
- Full OASIS terminology: https://www.oasis-open.org/policies-guidelines/

## Detailed Documentation
See `.claude/` directory for comprehensive documentation:
- `ubl-releases-complete-inventory.md` - All 34 releases with URLs, dates, sizes
- `project-rules.md` - Detailed rules, conventions, and technical implementation
- `next-steps.md` - Remaining work and task breakdown
- `session-history.md` - What has been completed, decisions made
- `deferred-items.md` - Future enhancements (nice-to-have items)

## Common Commands
```bash
# Import single release (dry-run first)
python3 -m tools.import_release 1 --dry-run
python3 -m tools.import_release 1

# Import all releases
python3 -m tools.catchup

# Import range of releases
python3 -m tools.catchup --start-from 1 --end-at 10

# Check current state
python3 -m tools.git_state

# Run tests
bash tools/tests/run_tests.sh           # Logic tests (12 tests)
bash tools/tests/e2e_test.sh            # End-to-end tests (14 tests)
bash tools/tests/negative_test.sh       # Negative/edge case tests (21 tests)
```

## Key Decisions
- **No external dependencies:** Python stdlib only (argparse, urllib, zipfile, xml.etree)
- **No manifest file:** Release URLs hardcoded in release_data.py
- **Git-based state tracking:** No separate state file, queries git history
- **Metadata extraction:** Auto-extract from UBL-X.X.xml files, fallback to Release object data
- **README updates:** Update with each release commit
- **Comprehensive testing:** 60 tests across 6 test suites

## Safety Guardrails (All Tested ✓)
- Sequential import enforcement (prevents out-of-order imports)
- Duplicate import prevention
- Patch dependency validation (patches require base release)
- Dirty working directory detection
- Corrupt ZIP handling
- Protected path preservation (tools/, .claude/, .gitignore never removed)
- Non-interactive mode support (for automation/testing)

## Documentation Maintenance

**After each commit, review and update documentation if needed:**
- Is `CLAUDE.md` still accurate with current status?
- Do `project-rules.md` decisions reflect latest changes?
- Should `session-history.md` be updated with what was completed?
- Are `next-steps.md` tasks still current?
- Move resolved items from `deferred-items.md` to `session-history.md`

**Keep documentation lean and current** - Remove outdated info, merge duplicates, delete unnecessary files.
