# Rename Detection Analysis for UBL Release Importer

## Executive Summary

The current import system does not detect or perform file renames between versions. Files are simply deleted and recreated with new names, losing the rename history in git. We need to:

1. **Detect renames** by comparing old and new version files
2. **Execute git mv** operations for detected renames
3. **Stage the renames** before applying new files
4. **Commit renames** separately from new file additions

---

## Current Flow

```
import_release.py (ReleaseImporter.run())
├── Download & Extract
├── apply_full_release() OR apply_patch()
│   ├── Remove old content
│   └── Copy new content (no rename detection)
├── update_readme()
├── create_commit() (git add -A)
└── create_tags()
```

**Problem**: All file changes appear as deletions + additions, losing rename history.

---

## What Needs to Change

### 1. **New Module: `file_rename_detector.py`**

This module should:
- Compare files from previous version with new version
- Detect files that are renamed (same content, different name)
- Match files based on:
  - Content similarity (fuzzy matching)
  - Version number patterns (e.g., `-2.1` → `-2.2`)
  - Directory structure
- Output a mapping of: `{old_path: new_path}`

### 2. **Modified: `import_release.py`**

Add a new method before `apply_full_release()`:
- `detect_and_apply_renames()` - should:
  1. Get the previous version's file list
  2. Get the new version's file list
  3. Run rename detection
  4. Execute `git mv old_path new_path` for each detected rename
  5. Stage changes with `git add -A`

Call this method **before** applying new content:
```python
# Step 2: Detect and apply renames
self.detect_and_apply_renames()

# Step 3: Apply full release (now with renames done)
self.apply_full_release(extract_dir)
```

### 3. **Detection Strategy**

Detect renames using **two patterns**:

#### Pattern A: Simple Version Number Updates
```
OLD: UBL-Invoice-2.1.xsd
NEW: UBL-Invoice-2.2.xsd
```
- Extract version numbers from filenames
- If `filename_prefix-OLD_VERSION.ext` exists in repo and `filename_prefix-NEW_VERSION.ext` exists in new files
- And they're in the same directory → likely a rename

#### Pattern B: Content-Based Matching (Fallback)
For cases where names change more dramatically:
```
OLD: UBL-PerformanceHistory-2.1.xsd
NEW: UBL-TransportProgressStatus-2.1.xsd  (in 2.1→2.1 transition, semantic rename)
```
- For files in old version that don't match pattern A
- Calculate similarity score with files in new version
- If similarity > threshold (e.g., 90%) → likely a rename
- Verify they're NOT both deleted+added in same commit

---

## Implementation Details

### File Structure

```
tools/
├── import_release.py (MODIFIED)
├── file_rename_detector.py (NEW)
├── git_state.py (unchanged)
├── release_data.py (unchanged)
├── validators.py (unchanged)
└── ...
```

### Pseudo-code for `file_rename_detector.py`

```python
class RenameDetector:
    def __init__(self, repo_root: Path, old_version: str, new_version: str):
        self.repo_root = repo_root
        self.old_version = old_version
        self.new_version = new_version

    def detect_renames(self, new_extract_dir: Path) -> Dict[Path, Path]:
        """
        Returns: {old_path: new_path} for detected renames
        """
        old_files = self.get_current_repo_files()  # What's in git now
        new_files = self.get_extracted_files(new_extract_dir)  # What's in ZIP

        renames = {}
        renames.update(self.detect_version_bumps(old_files, new_files))
        renames.update(self.detect_semantic_renames(old_files, new_files, renames))

        return renames

    def detect_version_bumps(self, old_files, new_files):
        """Pattern A: filename-OLD.ext → filename-NEW.ext"""
        renames = {}
        for old_file in old_files:
            # Extract version from old_file
            old_ver = extract_version(old_file)
            if not old_ver:
                continue

            # Try to find new_file with replaced version
            potential_new = old_file.replace(f'-{old_ver}', f'-{new_version}')

            if potential_new in new_files:
                # Verify they're in same directory
                if old_file.parent == potential_new.parent:
                    renames[old_file] = potential_new

        return renames

    def detect_semantic_renames(self, old_files, new_files, already_matched):
        """Pattern B: Content-based matching for remaining unmatched files"""
        # ... implement fuzzy matching ...
```

### Changes to `import_release.py`

In the `apply_full_release()` method, add rename detection:

```python
def apply_full_release(self, extract_dir: Path):
    """Apply a full release with rename detection."""
    print(f"Applying full release import...")

    if self.dry_run:
        print("  (DRY RUN: would detect renames and copy new content)")
        return

    # Step 1: Detect renames from previous version
    print("  Detecting file renames...")
    renames = self._detect_renames(extract_dir)
    if renames:
        print(f"    Found {len(renames)} renamed files")
        self._apply_renames(renames)
    else:
        print("    No renames detected")

    # Step 2: Remove old content (except renamed files)
    print("  Clearing repository...")
    # ... existing code ...

    # Step 3: Copy new content
    print("  Copying new content...")
    # ... existing code ...
```

---

## Key Considerations

### 1. **What Counts as a Rename?**
- ✅ `UBL-Invoice-2.1.xsd` → `UBL-Invoice-2.2.xsd` (clear rename)
- ✅ `UBL-PerformanceHistory-2.1.xsd` → `UBL-TransportProgressStatus-2.1.xsd` (semantic rename, same version)
- ❌ Files moving to `endorsed/` directory (these are new file structures, not renames)
- ❌ Files that are content-identical but serve different purposes

### 2. **Version Matching Logic**
Need to know:
- Previous version (from git history)
- New version (from Release object)

```python
def get_previous_version(current_version: str) -> Optional[str]:
    """Get the previous UBL version"""
    # 2.5 → 2.4
    # 2.4 → 2.3
    # etc.
```

### 3. **Within-Version Renames**
When importing `2.1 → 2.1` (same version, different stage), still detect renames:
- Case corrections: `BillofLading` → `BillOfLading`
- Terminology updates: `Activity` → `Process`

Need to detect these by fuzzy matching, not version patterns.

### 4. **Patch Releases**
For patches (errata, updates):
- Only files that are modified/renamed should be handled
- Most files remain unchanged
- Use overlay strategy (current implementation is fine)
- Renames in patches are rare but possible

---

## Testing Strategy

### Test Cases

1. **Simple Version Bump (2.1 → 2.2)**
   - Detect ~210 renames
   - Verify git history shows proper renames
   - Check that content is identical (not rewritten)

2. **Within-Version Semantic Renames (2.1 → 2.1)**
   - Detect case corrections
   - Detect terminology changes
   - Should find ~17 renames (from historical data)

3. **No False Positives**
   - Files that genuinely change content should NOT be marked as renames
   - Files that move to different directory structures should NOT be marked as renames

4. **Dry-Run Mode**
   - Should preview detected renames
   - Should NOT execute git mv commands

---

## Implementation Phases

### Phase 1: Rename Detection (Standalone)
```bash
python -m tools.file_rename_detector <old_version> <new_version> <extract_dir>
```
- Develop and test rename detection in isolation
- Verify accuracy with historical data
- Generate reports of detected renames

### Phase 2: Integration into Import
```bash
python -m tools.import_release 17 --detect-renames
```
- Add `--detect-renames` flag to import_release.py
- Integrate RenameDetector into ReleaseImporter
- Test with actual imports (start with #17: 2.1→2.2)

### Phase 3: Refinement
- Add fuzzy matching for semantic renames
- Handle edge cases
- Performance optimization for large file sets

---

## Expected Improvements

### Before (Current)
```
git log --oneline --name-status
83a9d5a Release: UBL 2.5
  D  UBL-Invoice-2.4.xsd
  A  UBL-Invoice-2.5.xsd
  D  UBL-Order-2.4.xsd
  A  UBL-Order-2.5.xsd
  ... (287 deletions, 287 additions = 574 changes)
```

### After (With Rename Detection)
```
git log --oneline --name-status
83a9d5a Release: UBL 2.5
  R  UBL-Invoice-2.4.xsd → UBL-Invoice-2.5.xsd
  R  UBL-Order-2.4.xsd → UBL-Order-2.5.xsd
  ... (287 renames = 287 changes, cleaner history)
```

### Benefits
1. **Cleaner git history** - renames are properly tracked
2. **Better blame tracking** - `git blame` shows true file origins
3. **Better diffing** - `git diff` shows actual changes, not wholesale replacement
4. **Better merge conflict resolution** - tool-assisted rename detection

---

## Files to Modify/Create

| File | Type | Changes |
|------|------|---------|
| `tools/file_rename_detector.py` | CREATE | New rename detection module |
| `tools/import_release.py` | MODIFY | Add rename detection in `apply_full_release()` |
| `tools/release_data.py` | MODIFY | Add method to get previous version |
| `.claude/rename-detection-analysis.md` | CREATE | This document |

---

## Open Questions

1. **How aggressive should fuzzy matching be?**
   - 90% similarity threshold?
   - Should we require manual confirmation for fuzzy matches?

2. **Should renames be committed separately?**
   - Option A: Commit renames first, then new files (two commits)
   - Option B: Stage renames and new files together (one commit)
   - Recommendation: One commit is cleaner

3. **What about renames within same version?**
   - Current: Only detected by fuzzy matching
   - Should we have a config file mapping these manually?

4. **Performance concerns?**
   - 287 files need to be compared
   - Fuzzy matching could be slow
   - Should we cache results? Use parallel processing?

---

## References

- [1937 renamed files](../rename-detection-analysis.md) - Historical data showing rename patterns
- `git mv` documentation - How git tracks renames
- Similarity detection algorithms - For fuzzy matching

