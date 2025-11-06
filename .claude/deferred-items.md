# Deferred Items

Items that need attention in future sessions but are not critical for initial implementation.

---

## High Priority - Must Address Before Final Release

### Errata and Update Packages ✓ RESOLVED

**Issue:** How to handle `errata-UBL-2.0` (23 Apr 2008) and `os-UBL-2.0-update` (29 May 2008)

**Analysis Complete (2025-11-06):**
Downloaded and analyzed both packages from `/tmp/errata-analysis/`. Full findings documented below.

**Key Findings:**

1. **Package Type:** These are **PATCH/OVERLAY packages**, NOT full replacements
   - Designed to be extracted directly into `os-UBL-2.0/` directory
   - Official installation instructions: "Unzip the Update Package using the appropriate flag or parameter to overwrite files without prompting"

2. **Package Differences:**
   - `errata-UBL-2.0.zip`: Draft version (prd - Public Review Draft, Apr 23 2008)
   - `os-UBL-2.0-update-delta.zip`: Final approved version (os - OASIS Standard, May 29 2008)
   - Both contain identical structure (289 files each)
   - Only 14 files differ between them (mostly just PDF filenames: prd vs os)

3. **What Changed (from os-UBL-2.0-update.pdf):**
   - Fixed typos and editorial errors in schemas/models
   - Fixed broken BOSNIA AND HERZEGOVINA entry in CountryIdentificationCode
   - Upgraded code lists from genericode 0.4 to 1.0 format
   - Restructured PortCode files (added columns, broke into smaller files)
   - Updated validation XSL stylesheet
   - **Important:** "None of these changes is considered substantive in the sense that any of them would require modifications to existing software"

4. **Files Changed (14 files total):**
   - 9 PortCode files in `cl/gc/special-purpose/`
   - 2 Model spreadsheets (`mod/common/UBL-CommonLibrary-2.0.ods` and `.xls`)
   - 1 Schema file (`xsd/common/UBL-CommonAggregateComponents-2.0.xsd`)
   - 2 PDF documentation files

**DECISION - Use Option B (Apply as Patch):**

**Rationale:**
- These are explicitly designed as overlay/patch packages
- Historically accurate representation
- Maintains integrity of the correction as part of UBL 2.0 release line
- Only 14 changed files need to be committed

**Implementation Requirements for Import Tool:**

1. **Special handling rules:**
   ```
   IF package_name matches "errata-*" OR "*-update-delta":
       - Mark as PATCH_TYPE package
       - Apply on top of previous OASIS Standard release
       - Only commit changed files (not all 289 files)
       - Use special commit message format
   ```

2. **Import sequence:**
   ```
   Step 1: Import os-UBL-2.0 (Dec 18, 2006) - tag as 'v2.0' or 'os-UBL-2.0'
   Step 2: Apply os-UBL-2.0-update-delta as patch commit (May 29, 2008)
           - Tag as 'os-UBL-2.0-errata01' or 'v2.0-errata01'
           - Commit message should indicate patch/correction nature
   ```

3. **Which package to use:**
   - Use `os-UBL-2.0-update-delta.zip` (final approved version)
   - Skip `errata-UBL-2.0.zip` (draft version)

4. **Commit message format:**
   ```
   Apply UBL 2.0 Errata 01 corrections

   Non-substantive corrections to os-UBL-2.0 (December 2006):
   - Fix typos and editorial errors in schemas/models
   - Fix BOSNIA AND HERZEGOVINA entry in CountryIdentificationCode
   - Upgrade code lists from genericode 0.4 to 1.0
   - Restructure PortCode files (add columns, split into smaller files)
   - Update validation XSL stylesheet

   Source: os-UBL-2.0-update-delta.zip
   Date: 29 May 2008
   Type: Errata/Correction Package
   Files changed: 14
   ```

**Reference Documentation:**
- Analysis files: `/tmp/errata-analysis/` (local)
- Official doc: `os-UBL-2.0-update.pdf` in package
- Complete change list: Pages 7-22 of PDF

---

## Medium Priority - Nice to Have

### README.md Commit Hash Updates

**Issue:** When to add commit hashes to README.md

**Current Plan:** README.md updated with each release but without commit hash

**Options:**
1. **Immediate follow-up commits**
   - Each release gets 2 commits: release + hash update
   - Pros: Immediate, automated
   - Cons: Doubles commit count, clutters history

2. **Batch update at end**
   - Single commit after all releases imported
   - Pros: Clean history, one update
   - Cons: Manual step at end

3. **Manual update**
   - Update README.md manually after import complete
   - Pros: Simple, flexible
   - Cons: Easy to forget

**Recommendation:** Batch update at end (Option 2)

**Implementation:**
```bash
# After all releases imported:
python tools/update_readme_hashes.py
git commit -m "Add commit hashes to README.md release history"
```

---

### Testing and Validation

**Current Status:** No automated testing planned for initial implementation

**Future Enhancements:**
1. **Schema validation**
   - Validate XSD files are well-formed XML
   - Check schema consistency
   - Detect breaking changes between versions

2. **Metadata validation**
   - Verify extracted metadata matches official OASIS records
   - Check date formats consistent
   - Validate URL accessibility

3. **Import verification**
   - Confirm all files extracted correctly
   - Verify no data loss during import
   - Check git history integrity

4. **Unit tests**
   - Test XML parsing functions
   - Test metadata extraction
   - Test URL parsing fallback

**Decision:** Start without tests, add if needed during development

---

### Python External Dependencies

**Current Decision:** Use only Python stdlib

**Potential External Packages:**
- `requests` - Better HTTP downloads (more robust than urllib)
- `python-dateutil` - Better date parsing (handles multiple formats)
- `lxml` - Faster/better XML parsing
- `click` - Better CLI framework (more features than argparse)

**Consideration:**
- External deps require `requirements.txt`
- Need pip install before running
- Adds complexity for simple one-time script

**Decision:** Start with stdlib, only add external deps if stdlib proves insufficient

---

## Low Priority - Future Enhancements

### Automatic New Release Detection

**Idea:** Monitor OASIS website for new UBL releases

**Implementation:**
- Scheduled script (cron/GitHub Actions)
- Scrape https://docs.oasis-open.org/ubl/
- Detect new directories/ZIPs
- Trigger import automatically
- Create PR with new release

**Value:** Keeps repo up-to-date automatically

**Timeline:** After initial import proven successful

---

### Diff Reports Between Releases

**Idea:** Generate human-readable reports of changes between UBL versions

**Features:**
- Schema changes (new elements, removed elements, type changes)
- New document types added
- Deprecated features
- Code list changes

**Implementation:**
- Compare XSD files between releases
- Parse and diff XML structures
- Generate markdown reports
- Add to each release commit

**Value:** Makes changes visible without reading schemas

**Timeline:** Future enhancement

---

### CI/CD Integration

**Idea:** Automate import process with GitHub Actions

**Features:**
- Run tests on import
- Validate schemas
- Auto-generate diff reports
- Create PRs automatically
- Notify on failures

**Timeline:** After manual process proven

---

### Documentation Generation

**Idea:** Auto-generate documentation from schemas

**Features:**
- HTML documentation for each release
- API reference from XSD
- Change logs between versions
- Migration guides

**Value:** Makes UBL more accessible

**Timeline:** Long-term enhancement

---

## Questions for Future Sessions

1. Should we include any pre-UBL-2.0 releases for historical completeness?
2. What's the best way to handle the errata packages?
3. Should we add schema validation to import process?
4. Is there value in generating diff reports?
5. Should README.md include more metadata (file counts, size, etc.)?

---

## Notes

- This file should be updated as items are addressed or new items identified
- When an item is completed, move it to session-history.md
- Keep this file focused on actionable future work
