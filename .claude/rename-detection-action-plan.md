# Rename Detection: Action Plan

## Quick Summary

The UBL import system currently deletes and recreates files with new version numbers, losing rename history. We need to implement **rename detection** to properly track file renames in git, improving code history quality.

**Impact**: ~1,700+ file renames across all releases

---

## What Needs to Be Done

### 1. Create New Module: `tools/file_rename_detector.py`
**Purpose**: Detect and apply file renames between versions

**Key Responsibilities**:
- Compare old version files with new version files
- Detect version number pattern renames (`-2.1` → `-2.2`)
- Detect semantic renames using fuzzy content matching
- Execute `git mv` for detected renames
- Stage changes for commit

**Estimated LOC**: 300-400 lines

**Dependencies**: Standard library only (difflib, re, pathlib, subprocess)

### 2. Modify: `tools/import_release.py`
**Changes**:
- Import `RenameDetector` from new module
- Add `_get_previous_version()` method to find prior UBL version
- Modify `apply_full_release()` to call rename detection before clearing/copying files
- Enhance `create_commit()` to show rename statistics

**Estimated changes**: ~50 lines

### 3. Modify: `tools/release_data.py`
**Optional enhancement**:
- Add `get_previous_release()` helper method
- Makes it easier to find the previous version

**Estimated changes**: ~10 lines

### 4. Create Test File: `tools/tests/test_rename_detector.py`
**Purpose**: Unit tests for rename detection logic

**Test Cases**:
- Version extraction from filenames
- Simple version bump detection
- Junk file filtering
- Directory preservation
- Content similarity calculation

**Estimated LOC**: 150-200 lines

---

## Detailed Implementation Steps

### Step 1: Create `file_rename_detector.py`
- [x] Design class structure: `RenameDetector`
- [x] Implement Phase 1: Version pattern detection
  - Extract version numbers from filenames
  - Match files by replacing old version with new version
  - Verify same directory
- [x] Implement Phase 2: Fuzzy matching
  - Content similarity calculation
  - For semantic renames (Activity → Process)
  - Only for within-version transitions (2.1 → 2.1)
- [x] Implement Git integration
  - Execute `git mv` for each rename
  - Stage changes with `git add -A`
- [x] Add safety validation
  - Check for collision (multiple old files → same new file)
  - Verify directory structure
- [x] Add verbose logging
  - Show detection progress
  - Show which renames are being applied

### Step 2: Integrate into `import_release.py`
- [ ] Add import statement
- [ ] Add `_get_previous_version()` method
- [ ] Modify `apply_full_release()`:
  - Call rename detection before clearing repo
  - Log statistics
  - Handle dry-run mode correctly
- [ ] Enhance `create_commit()`:
  - Show rename count in statistics
  - Verify staged changes include renames

### Step 3: Test Implementation
- [ ] Unit tests for `file_rename_detector.py`
- [ ] Manual test with actual release import
- [ ] Verify git history shows renames (R status)
- [ ] Verify content is identical (not rewritten)
- [ ] Test dry-run mode

### Step 4: Document & Deploy
- [ ] Add docstrings to all methods
- [ ] Update CLAUDE.md project instructions
- [ ] Create user guide for new feature
- [ ] Test with production release import

---

## Execution Sequence

```
1. Write file_rename_detector.py
   ├── Version bump detection
   ├── Fuzzy matching
   ├── Git integration
   └── Validation

2. Write unit tests
   ├── Version extraction tests
   ├── Detection tests
   └── Integration tests (optional)

3. Modify import_release.py
   ├── Add imports
   ├── Add helper methods
   ├── Integrate detection into apply_full_release()
   └── Enhance create_commit()

4. Manual testing
   ├── Test with --dry-run first
   ├── Test with actual import
   ├── Verify git history
   └── Check for edge cases

5. Documentation
   ├── Update CLAUDE.md
   ├── Add code comments
   └── Create usage examples
```

---

## Validation Criteria

### Code Quality
- [ ] All methods have docstrings
- [ ] Type hints on all parameters
- [ ] No magic numbers (use constants)
- [ ] Proper error handling
- [ ] Clear logging messages

### Functionality
- [ ] Detects version bumps correctly
- [ ] Detects semantic renames (when enabled)
- [ ] No false positives (files that shouldn't be renames)
- [ ] Preserves directory structure
- [ ] Handles binary files correctly

### Git Integration
- [ ] `git mv` executed correctly
- [ ] Changes staged properly
- [ ] Commit includes rename information
- [ ] `git log --name-status` shows 'R' entries
- [ ] Content is identical (git show -R doesn't lose data)

### Testing
- [ ] Unit tests pass
- [ ] Manual import test succeeds
- [ ] Dry-run mode works
- [ ] Error cases handled gracefully

---

## Risk Assessment

### Low Risk
- ✅ Version pattern detection is straightforward
- ✅ Uses existing git commands (`git mv`, `git add`)
- ✅ Isolated module (easy to disable if needed)
- ✅ Doesn't break existing functionality

### Medium Risk
- ⚠️ Fuzzy matching could have false positives
  - **Mitigation**: High threshold (85%), only within same version
- ⚠️ Performance with large file sets
  - **Mitigation**: Skip fuzzy matching if >100 files

### High Risk
- ❌ None identified

### Rollback Plan
If issues occur:
1. Remove rename detection calls from `import_release.py`
2. Re-import release using old method (without renames)
3. Investigate issue in `file_rename_detector.py`

---

## Performance Expectations

### Phase 1: Version Pattern Detection
- **Time**: O(n) where n = number of files
- **Expected**: <100ms for 200 files
- **No content reading required**

### Phase 2: Fuzzy Matching
- **Time**: O(n²) worst case (but limited to 100 files max)
- **Expected**: <1s for 100 files
- **Only runs for within-version imports**

### Git Operations
- **`git mv`**: ~10ms per file
- **Expected**: ~3-5s for 300 renames
- **Total per import**: ~5-10 seconds overhead

---

## Files to Create/Modify

| File | Type | Lines | Complexity |
|------|------|-------|-----------|
| `tools/file_rename_detector.py` | CREATE | 350-400 | Medium |
| `tools/import_release.py` | MODIFY | +50 | Low |
| `tools/release_data.py` | MODIFY | +10 | Low |
| `tools/tests/test_rename_detector.py` | CREATE | 150-200 | Medium |

**Total New Code**: ~560 lines
**Total Modified Code**: ~60 lines

---

## Success Metrics

### Before Implementation
```bash
$ git log --oneline --name-status HEAD~1..HEAD
83a9d5a Release: UBL 2.5
  D  UBL-Invoice-2.4.xsd
  A  UBL-Invoice-2.5.xsd
  D  UBL-Order-2.4.xsd
  A  UBL-Order-2.5.xsd
```
**Metric**: 287 deletions + 287 additions = 574 changes

### After Implementation
```bash
$ git log --oneline --name-status HEAD~1..HEAD
83a9d5a Release: UBL 2.5
  R  UBL-Invoice-2.4.xsd -> UBL-Invoice-2.5.xsd
  R  UBL-Order-2.4.xsd -> UBL-Order-2.5.xsd
```
**Metric**: 287 renames = 287 changes (cleaner history)

### Benefits
✅ **Cleaner git history** - Renames properly tracked
✅ **Better blame tracking** - Source files clearly identified
✅ **Better diffing** - Actual changes visible, not whole-file rewrites
✅ **Better merge tools** - Proper rename detection in conflicts

---

## Questions to Resolve

1. **Semantic Rename Matching - How aggressive?**
   - Current: 85% threshold, only for same-version imports
   - Alternative: Manual config file for known renames
   - **Decision**: Keep 85% threshold, add config option later

2. **Separate Rename Commit or Same Commit?**
   - Option A: One commit with renames + new files
   - Option B: Two commits (renames, then new files)
   - **Decision**: Option A (one commit) is cleaner

3. **Fuzzy Matching - Performance Acceptable?**
   - Skip if >100 files?
   - Implement parallel processing?
   - **Decision**: Skip fuzzy matching if >100 files (safe default)

4. **Backward Compatibility?**
   - Re-import old releases with renames?
   - **Decision**: Optional - `--detect-renames` flag for now

---

## Timeline Estimate

| Phase | Time | Dependencies |
|-------|------|--------------|
| Create `file_rename_detector.py` | 2-3 hours | None |
| Unit tests | 1 hour | Module complete |
| Integrate into `import_release.py` | 1 hour | Module complete |
| Manual testing | 1-2 hours | Integration complete |
| Documentation | 30 minutes | All tests pass |
| **TOTAL** | **6-8 hours** | - |

---

## Next Steps

1. **Create branch for implementation**:
   ```bash
   git checkout -b feature/rename-detection
   ```

2. **Implement module**:
   ```bash
   # Start with file_rename_detector.py
   vim tools/file_rename_detector.py
   ```

3. **Test in isolation**:
   ```bash
   python -m tools.file_rename_detector
   ```

4. **Integrate into import system**:
   ```bash
   # Modify import_release.py
   vim tools/import_release.py
   ```

5. **Test full import**:
   ```bash
   python -m tools.import_release 17 --dry-run
   python -m tools.import_release 17
   ```

6. **Verify git history**:
   ```bash
   git log --oneline --name-status
   git show HEAD | grep "^R"
   ```

---

## References

- Current analysis: `.claude/rename-detection-analysis.md`
- Implementation code: `.claude/rename-detection-implementation-guide.md`
- Historical renames: 1,709 renamed files detected across 34 releases

