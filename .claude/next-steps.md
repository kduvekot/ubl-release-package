# Next Steps

## Current Status
- **Phase 1:** Documentation and analysis ✓ COMPLETE
- **Phase 2:** Create import tooling - NOT STARTED
- **Phase 3:** Full import - NOT STARTED

---

## Phase 2: Create Import Tooling

### 2.1 Create Tools Directory
- Create `tools/` directory
- Add `tools/__init__.py` if needed
- Create `tools/.gitignore` (exclude `__pycache__`, `*.pyc`)

### 2.2 Write `tools/import_release.py`
Single release import script with:
- Download ZIP from URL
- Extract and parse `UBL-X.X.xml` for metadata
- Clear UBL content (preserve `tools/`, `.claude/`, `.git/`, `README.md`, `.gitignore`)
- Extract ZIP to root
- Update `README.md`
- Create git commit with structured message
- Create git tag(s)
- Handle special cases:
  - Releases without XML (fallback to URL parsing)
  - PATCH type packages (#11: os-UBL-2.0-update-delta)
  - SKIP packages (#10: errata-UBL-2.0)

### 2.3 Write `tools/catchup.py`
Batch import script with:
- Hardcoded list of 37 release URLs (in chronological order)
- Loop through releases calling import_release logic
- Handle package type detection (FULL, PATCH, SKIP)
- Progress reporting
- Support `--dry-run` flag
- Support `--start-from N` flag for resuming

### 2.4 Testing
- Test on single release (e.g., `os-UBL-2.4`)
- Test on release without XML (e.g., `prd2-UBL-2.0`)
- Test on first 3 releases as batch
- Dry-run full catchup to validate

---

## Phase 3: Full Import

### 3.1 Commit Infrastructure
- Commit `tools/` directory (separate commit)
- Commit initial `README.md`
- Push to branch
- Verify no release content in this commit

### 3.2 Run Full Catchup
- Run `catchup.py` to import all releases
- Monitor for errors
- Handle failures (resume with `--start-from`)
- Import sequence:
  - Releases #1-9 (UBL 2.0 series, skip #10, apply #11 as PATCH)
  - Releases #12-37 (UBL 2.1-2.5)

### 3.3 Post-Import Validation
- Verify 36 release commits created (skipped #10)
- Verify commit messages formatted correctly
- Verify all tags exist (36 descriptive + 5 version tags)
- Review git log for consistency
- Check final repository structure

### 3.4 Add Commit Hashes to README
- Update `README.md` with commit hashes
- Single commit at end (batch update)

### 3.5 Create Pull Request
- Push all commits to branch
- Create PR with summary
- Merge to main

---

## Known Issues to Address

### Issue 1: Three Releases Without XML
- `prd-UBL-2.0`, `prd2-UBL-2.0`, `prd3-UBL-2.0`
- **Solution:** URL parsing + hardcoded dates from inventory

### Issue 2: Date Format Variations
- Multiple formats: "DD Month YYYY", "YYYY-MM-DD", etc.
- **Solution:** Robust date parser or manual conversion to ISO 8601

### Issue 3: Package Type Detection
- Need to detect FULL vs PATCH vs SKIP
- **Solution:** Check package name/URL patterns (see project-rules.md)

---

## Quick Reference

**Documentation:**
- `CLAUDE.md` - Project overview (auto-loaded)
- `project-rules.md` - Detailed rules and implementation
- `ubl-releases-complete-inventory.md` - All 37 releases
- `deferred-items.md` - Future enhancements
- `session-history.md` - What's been completed

**To Create:**
- `tools/import_release.py` - Single release import
- `tools/catchup.py` - Batch historical import
- `README.md` - Meta-README (updated per release)
