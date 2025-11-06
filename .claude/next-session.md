# Next Session Tasks

## What Has NOT Been Done Yet

This document lists all remaining work to complete the UBL release history import project.

---

## Phase 2: Create Import Tooling (NOT STARTED)

### Task 2.1: Create `tools/` Directory Structure
- [ ] Create `tools/` directory
- [ ] Add `.gitignore` if needed (for temp files, __pycache__, etc.)
- [ ] Create `requirements.txt` (may be empty if using only stdlib)

### Task 2.2: Write `import_release.py`
- [ ] Create file skeleton with argparse setup
- [ ] Implement XML metadata extraction
  - [ ] Entity declaration parser (Pattern 1)
  - [ ] ArticleInfo element parser (Pattern 2)
  - [ ] Date format converter (multiple formats → ISO 8601)
- [ ] Implement ZIP download and extraction
- [ ] Implement UBL content clearing logic (preserve tools/, .claude/, .git/, README.md)
- [ ] Implement file copying to repository root
- [ ] Implement README.md update logic
- [ ] Implement git operations (add, commit, tag)
- [ ] Implement cleanup (remove temp files)
- [ ] Add error handling and logging
- [ ] Add fallback for releases without XML
- [ ] Test on single release

### Task 2.3: Write `catchup.py`
- [ ] Create file skeleton with argparse setup
- [ ] Hardcode list of 34 release URLs in chronological order
- [ ] Implement loop to call import_release.py logic for each
- [ ] Add progress reporting
- [ ] Add `--dry-run` flag
- [ ] Add `--start-from` flag for resuming
- [ ] Handle special cases (3 releases without XML)
- [ ] Add summary report at end

### Task 2.4: Create Initial README.md
- [ ] Write meta-README explaining the repository
- [ ] Add project description
- [ ] Add structure showing it will be updated per release
- [ ] Commit as infrastructure (separate from releases)

---

## Phase 3: Testing (NOT STARTED)

### Task 3.1: Unit Testing
- [ ] Test XML metadata extraction on sample files
- [ ] Test date parsing with various formats
- [ ] Test URL parsing for fallback cases
- [ ] Test file clearing logic (verify preserve list works)

### Task 3.2: Integration Testing
- [ ] Test import_release.py on single release (e.g., os-UBL-2.4)
  - [ ] Verify download works
  - [ ] Verify extraction works
  - [ ] Verify metadata extracted correctly
  - [ ] Verify commit created with correct message
  - [ ] Verify tags created correctly
  - [ ] Verify README.md updated
- [ ] Test on release without XML (e.g., prd2-UBL-2.0)
  - [ ] Verify fallback works
  - [ ] Verify reasonable defaults used
- [ ] Test on first 3 releases as batch
  - [ ] Verify commits in correct order
  - [ ] Verify file deletions work properly between releases
  - [ ] Verify git history looks clean

### Task 3.3: Dry-Run Full Catchup
- [ ] Run catchup.py with --dry-run
- [ ] Review planned operations
- [ ] Verify URL list is correct
- [ ] Verify chronological order

---

## Phase 4: Full Import (NOT STARTED)

### Task 4.1: Commit Infrastructure
- [ ] Commit tools/ directory
- [ ] Commit initial README.md
- [ ] Push to branch
- [ ] Verify no release content in this commit

### Task 4.2: Run Full Catchup
- [ ] Run catchup.py to import all 34 releases
- [ ] Monitor for errors
- [ ] Verify each commit created successfully
- [ ] Verify tags created correctly
- [ ] Handle any failures (resume with --start-from)

### Task 4.3: Post-Import Validation
- [ ] Verify 34 release commits created
- [ ] Verify commit messages formatted correctly
- [ ] Verify all tags exist
  - [ ] 34 descriptive tags (one per release)
  - [ ] 5 major version tags (v2.0 through v2.4)
- [ ] Review git log for consistency
- [ ] Check final repository structure
- [ ] Verify README.md completeness

### Task 4.4: Add Commit Hashes to README
- [ ] Run script to update README.md with commit hashes
- [ ] Or manually update
- [ ] Create single commit with hash updates
- [ ] Push to branch

---

## Phase 5: Review and Merge (NOT STARTED)

### Task 5.1: Self-Review
- [ ] Review full git history
- [ ] Check representative commits
- [ ] Verify tags are correct
- [ ] Review README.md
- [ ] Check .claude/ documentation is complete

### Task 5.2: Create Pull Request
- [ ] Push all commits to branch
- [ ] Create PR with description
- [ ] Link to relevant issues (if any)
- [ ] Add summary of what was done

### Task 5.3: Address Review Feedback
- [ ] Respond to comments
- [ ] Make requested changes
- [ ] Update documentation if needed

### Task 5.4: Merge
- [ ] Merge PR to main branch
- [ ] Verify main branch looks correct
- [ ] Tag merge commit if appropriate

---

## Optional Enhancements (NOT REQUIRED)

### Enhancement 1: README Commit Hash Automation
- [ ] Write script to auto-update README.md with commit hashes
- [ ] Make it reusable for future releases

### Enhancement 2: Schema Validation
- [ ] Add XSD schema validation
- [ ] Verify schemas are well-formed
- [ ] Check for broken references

### Enhancement 3: Diff Reports
- [ ] Generate diff reports between releases
- [ ] Highlight schema changes
- [ ] Add to commit messages or separate files

### Enhancement 4: CI/CD Setup
- [ ] Create GitHub Actions workflow
- [ ] Add automated testing
- [ ] Add validation checks

---

## Known Issues to Address

### Issue 1: Three Releases Without XML
**Releases:** prd-UBL-2.0, prd2-UBL-2.0, prd3-UBL-2.0

**Solution Needed:**
- Implement URL parsing fallback
- Use dates from inventory file or OASIS directory listing
- Test thoroughly

### Issue 2: Date Format Variations
**Issue:** Multiple date formats in XML files

**Solution Needed:**
- Robust date parser (dateutil or custom)
- Handle: "DD Month YYYY", "YYYY-MM-DD", etc.
- Test with all 29 XML files

### Issue 3: Errata/Update Packages
**Status:** DEFERRED (see deferred-items.md)

**Next Steps:**
- Investigate after main 32 releases done
- Determine if patches or replacements
- Design import strategy

---

## Decision Points for Next Session

These questions need answers before proceeding:

1. **External dependencies:** Should we use `requests` and `dateutil`, or stick with stdlib?
   - Current: stdlib only
   - Consider: external deps if stdlib proves insufficient

2. **Error handling:** How to handle download failures?
   - Retry with backoff?
   - Fail immediately?
   - Log and continue?

3. **Commit hash updates:** When to add them to README.md?
   - After each commit (doubles commits)?
   - Batch at end (single commit)?
   - Manual update?

4. **Testing approach:** Unit tests or just integration testing?
   - Current: integration testing only
   - Consider: unit tests if issues arise

5. **Logging:** What level of detail?
   - INFO: high-level progress
   - DEBUG: detailed operations
   - File logging or just console?

---

## Session Start Checklist

When starting the next session:

1. [ ] Review this file
2. [ ] Review session-history.md for context
3. [ ] Review project-rules.md for constraints
4. [ ] Check deferred-items.md for issues
5. [ ] Verify branch is up to date
6. [ ] Confirm working directory clean
7. [ ] Begin with Phase 2, Task 2.1

---

## Quick Reference: File Locations

### Created in Session 1:
- `.claude/ubl-releases-complete-inventory.md` ✓
- `.claude/project-rules.md` ✓
- `.claude/implementation-notes.md` ✓
- `.claude/session-history.md` ✓
- `.claude/deferred-items.md` ✓
- `.claude/glossary.md` ✓
- `.claude/next-session.md` ✓ (this file)

### To Create in Session 2:
- `tools/import_release.py`
- `tools/catchup.py`
- `tools/requirements.txt`
- `README.md` (initial version)

### To Create in Future Sessions:
- `tools/update_readme_hashes.py` (optional)
- Test files (if needed)

---

## Estimated Time Requirements

**Phase 2 (Tooling):** 2-3 hours
- import_release.py: 1.5 hours
- catchup.py: 0.5 hours
- README.md: 0.5 hours

**Phase 3 (Testing):** 1-2 hours
- Unit tests: 0.5 hours
- Integration tests: 1 hour

**Phase 4 (Import):** 1-2 hours
- Infrastructure commit: 0.25 hours
- Full catchup run: 0.5 hours (automated, but monitor)
- Validation: 0.5 hours
- Hash updates: 0.25 hours

**Phase 5 (Review/Merge):** 0.5-1 hour

**Total Estimated:** 5-8 hours of work

---

*This file should be updated as tasks are completed. Move completed items to session-history.md.*
