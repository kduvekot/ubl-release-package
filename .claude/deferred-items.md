# Deferred Items

Items that need attention in future sessions but are not critical for initial implementation.

**Note:** Resolved items are moved to `session-history.md`

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
