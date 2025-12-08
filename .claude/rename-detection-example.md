# Rename Detection: Concrete Example

## Scenario: Importing UBL 2.2 (after 2.1)

This example walks through what happens when importing release #17 (UBL 2.2 CSPRD01) which comes after #16 (UBL 2.1 OS).

### Current Behavior (Without Rename Detection)

```bash
$ python -m tools.import_release 17 --dry-run

======================================================================
Importing Release #17: csprd01-UBL-2.2
======================================================================
Version: 2.2
Stage: csprd01 (Committee Specification Public Review Draft 01)
Date: 2016-12-21
Type: FULL
URL: https://docs.oasis-open.org/ubl/csprd01-UBL-2.2/UBL-2.2.zip

Validating import of release #17: csprd01-UBL-2.2...
✓ All validation checks passed

Downloading release #17 from Google Drive...
  (DRY RUN: skipping download)

Applying full release import...
  (DRY RUN: would clear repo and copy new content)

Updating README.md...
  (DRY RUN: would update README)

Creating git commit...
  (DRY RUN: would create commit)

--- Commit Message Preview ---
Release: UBL 2.2 (Committee Specification Public Review Draft 01)

Date: 2016-12-21
Stage: csprd01
Source: https://docs.oasis-open.org/ubl/csprd01-UBL-2.2/UBL-2.2.zip
--- End Preview ---

Creating git tags...
  (DRY RUN: would create tag csprd01-UBL-2.2)

✓ Successfully imported csprd01-UBL-2.2
```

**Git history would show:**
```
$ git log --oneline --name-status HEAD~1..HEAD
a1b2c3d Release: UBL 2.2
  D  UBL-Invoice-2.1.xsd
  D  UBL-Order-2.1.xsd
  D  UBL-CreditNote-2.1.xsd
  ...
  A  UBL-Invoice-2.2.xsd
  A  UBL-Order-2.2.xsd
  A  UBL-CreditNote-2.2.xsd
  ...
```
**Problem**: 210 deletions + 210 additions = 420 changes reported, but they're actually renames!

---

### New Behavior (With Rename Detection)

```bash
$ python -m tools.import_release 17 --dry-run

======================================================================
Importing Release #17: csprd01-UBL-2.2
======================================================================
Version: 2.2
Stage: csprd01 (Committee Specification Public Review Draft 01)
Date: 2016-12-21
Type: FULL
URL: https://docs.oasis-open.org/ubl/csprd01-UBL-2.2/UBL-2.2.zip

Validating import of release #17: csprd01-UBL-2.2...
✓ All validation checks passed

Downloading release #17 from Google Drive...
  (DRY RUN: skipping download)

Applying full release import...
  Detecting file renames from 2.1 → 2.2...
    Phase 1 (version bumps): 210 renames detected
    Phase 2 (semantic): 0 renames detected
    Total renames: 210
    DRY RUN: Would execute 210 git mv operations:
      git mv xsd/maindoc/UBL-Invoice-2.1.xsd → xsd/maindoc/UBL-Invoice-2.2.xsd
      git mv xsd/maindoc/UBL-Order-2.1.xsd → xsd/maindoc/UBL-Order-2.2.xsd
      git mv xsd/maindoc/UBL-CreditNote-2.1.xsd → xsd/maindoc/UBL-CreditNote-2.2.xsd
      ...
      ... and 207 more

  (DRY RUN: would clear repo and copy new content)

Updating README.md...
  (DRY RUN: would update README)

Creating git commit...
  (DRY RUN: would create commit)
  File changes: 210 renamed, 15 added, 0 modified, 0 deleted

  --- Commit Message Preview ---
  Release: UBL 2.2 (Committee Specification Public Review Draft 01)

  Date: 2016-12-21
  Stage: csprd01
  Source: https://docs.oasis-open.org/ubl/csprd01-UBL-2.2/UBL-2.2.zip
  --- End Preview ---

Creating git tags...
  (DRY RUN: would create tag csprd01-UBL-2.2)

✓ Successfully imported csprd01-UBL-2.2
```

**Git history would show:**
```
$ git log --oneline --name-status HEAD~1..HEAD
a1b2c3d Release: UBL 2.2
  R  xsd/maindoc/UBL-Invoice-2.1.xsd -> xsd/maindoc/UBL-Invoice-2.2.xsd
  R  xsd/maindoc/UBL-Order-2.1.xsd -> xsd/maindoc/UBL-Order-2.2.xsd
  R  xsd/maindoc/UBL-CreditNote-2.1.xsd -> xsd/maindoc/UBL-CreditNote-2.2.xsd
  ...
  A  mod/summary/reports/All-UBL-2.2-Documents.html
  A  xsd/common/UBL-SignatureExtensionComponents-2.2.xsd
  ...
```
**Benefit**: 210 renames + 15 new additions = 225 changes (much clearer!)

---

## Step-by-Step Execution

### Step 1: Validation
```python
# validators.py checks
✓ Git repository valid
✓ Working directory clean
✓ On proper branch (claude/...)
✓ Sequential order (importing #17 after #16)
✓ Not already imported
```

### Step 2: Download & Extract
```python
# Download from Google Drive
# Extract to /tmp/ubl-import-xxxxx/

# Directory structure:
/tmp/ubl-import-xxxxx/
├── xsd/
│   ├── maindoc/
│   │   ├── UBL-Invoice-2.2.xsd
│   │   ├── UBL-Order-2.2.xsd
│   │   └── ...
│   └── common/
│       └── ...
├── cl/
├── doc/
└── ...
```

### Step 3: Rename Detection (NEW)
```python
# Get previous version from git
previous_version = "2.1"

# Create detector
detector = RenameDetector(repo_root, "2.1", "2.2")

# Phase 1: Version pattern matching
old_files = [
    "xsd/maindoc/UBL-Invoice-2.1.xsd",
    "xsd/maindoc/UBL-Order-2.1.xsd",
    "cl/gc/UnitOfMeasureCode-2.1.gc",
    ...
]

new_files = [
    "xsd/maindoc/UBL-Invoice-2.2.xsd",
    "xsd/maindoc/UBL-Order-2.2.xsd",
    "cl/gc/UnitOfMeasureCode-2.2.gc",
    ...
]

# Match by version replacement
renames = {
    Path("xsd/maindoc/UBL-Invoice-2.1.xsd"): Path("xsd/maindoc/UBL-Invoice-2.2.xsd"),
    Path("xsd/maindoc/UBL-Order-2.1.xsd"): Path("xsd/maindoc/UBL-Order-2.2.xsd"),
    ...
}  # 210 total

# Phase 2: Fuzzy matching
# (Skipped - this is version-to-version change, not within-version)

# Apply the renames
for old_path, new_path in renames.items():
    subprocess.run(['git', 'mv', old_path, new_path])

# Stage the changes
subprocess.run(['git', 'add', '-A'])
```

**Output:**
```
Detecting file renames from 2.1 → 2.2...
  Phase 1 (version bumps): 210 renames detected
  Phase 2 (semantic): 0 renames detected
  Total renames: 210
  ✓ 210 renames staged
```

### Step 4: Clear Repository
```python
# Remove all files except:
#  - .git/
#  - .gitignore
#  - .claude/
#  - tools/
#  - README.md

# Already removed by renames (staged but not yet committed):
#  - xsd/maindoc/UBL-Invoice-2.1.xsd (renamed, not deleted)
#  - xsd/maindoc/UBL-Order-2.1.xsd (renamed, not deleted)

# Still need to remove:
#  - doc/old-release-notes.txt
#  - spec/old-schema.xsd
#  - ... (files that don't have 2.1 in name or are truly old)

removed_count = 50  # After excluding renamed files
```

### Step 5: Copy New Content
```python
# Copy extracted files from /tmp/ubl-import-xxxxx/ to repo
# Files already staged as renames are skipped (already in place)

for file in extract_dir.rglob('*'):
    if not file.is_file():
        continue

    # This skips files already handled by renames
    rel_path = file.relative_to(extract_dir)
    if (repo_root / rel_path).exists():
        continue  # Already staged as rename

    dest = repo_root / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file, dest)

copied_count = 15  # New files not in 2.1
```

### Step 6: Update README
```python
# Update latest release section
# Add new entry to release history
```

### Step 7: Create Commit
```python
# Git status before commit
git add -A  # Adds any remaining unstaged changes

# Git status after staging
$ git status --short
R  xsd/maindoc/UBL-Invoice-2.1.xsd -> xsd/maindoc/UBL-Invoice-2.2.xsd
R  xsd/maindoc/UBL-Order-2.1.xsd -> xsd/maindoc/UBL-Order-2.2.xsd
...
A  mod/summary/reports/All-UBL-2.2-Documents.html
A  xsd/common/UBL-SignatureExtensionComponents-2.2.xsd
M  README.md

# Create commit
commit_msg = """Release: UBL 2.2 (Committee Specification Public Review Draft 01)

Date: 2016-12-21
Stage: csprd01
Source: https://docs.oasis-open.org/ubl/csprd01-UBL-2.2/UBL-2.2.zip"""

git commit -m commit_msg

# Result
[claude/import-releases a1b2c3d] Release: UBL 2.2...
 210 files changed, 123 insertions(+), 87 deletions(-)
 rename xsd/maindoc/UBL-Invoice-2.1.xsd => xsd/maindoc/UBL-Invoice-2.2.xsd (93%)
 rename xsd/maindoc/UBL-Order-2.1.xsd => xsd/maindoc/UBL-Order-2.2.xsd (94%)
 ...
 create mode 100644 mod/summary/reports/All-UBL-2.2-Documents.html
 ...
```

### Step 8: Create Tags
```bash
git tag -a csprd01-UBL-2.2 -m "UBL 2.2 Committee Specification Public Review Draft 01"
```

---

## Key Differences

### Code Inspection (git show)
```bash
# Before: Shows whole file content changes
$ git show HEAD | grep "^+UBL-Invoice-2.2.xsd" | head -1
+<?xml version="1.0" encoding="UTF-8"?>
+<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
...  (entire file)

# After: Shows it's a rename with minor changes
$ git show -M --name-only HEAD
Release: UBL 2.2 (...)
 xsd/maindoc/UBL-Invoice-2.1.xsd => xsd/maindoc/UBL-Invoice-2.2.xsd
 xsd/maindoc/UBL-Order-2.1.xsd => xsd/maindoc/UBL-Order-2.2.xsd
```

### Blame Tracking (git blame)
```bash
# Before: All content shows as new (introduced in this commit)
$ git blame xsd/maindoc/UBL-Invoice-2.2.xsd | head -5
a1b2c3d (Claude 2016-12-21 10:00:00) <?xml version="1.0"?>
a1b2c3d (Claude 2016-12-21 10:00:00) <xs:schema ...>

# After: Shows original commit from 2.1, with rename information
$ git blame xsd/maindoc/UBL-Invoice-2.2.xsd | head -5
8f1e2d3 (Claude 2013-11-04 10:00:00) <?xml version="1.0"?>
8f1e2d3 (Claude 2013-11-04 10:00:00) <xs:schema ...>
^ (Claude 2016-12-21 10:00:00) (renamed from xsd/maindoc/UBL-Invoice-2.1.xsd)
```

### Diffing (git diff)
```bash
# Before: Shows entire file deleted and added
$ git diff HEAD~1..HEAD xsd/maindoc/UBL-Invoice-2.2.xsd | wc -l
1200  (entire file shown as additions)

# After: Shows only actual schema changes
$ git diff HEAD~1..HEAD xsd/maindoc/UBL-Invoice-2.2.xsd | wc -l
45    (only the real differences)
```

---

## Special Case: Within-Version Semantic Renames

When importing UBL 2.1 → 2.1 (different stage, same version), semantic renames are detected:

```
OLD: UBL-PerformanceHistory-2.1.xsd
NEW: UBL-TransportProgressStatus-2.1.xsd

Phase 2: Fuzzy matching
  Comparing content of UBL-PerformanceHistory-2.1.xsd with all new files
  Similarity with UBL-TransportProgressStatus-2.1.xsd: 92%
  → Match! (above 85% threshold)
```

This handles cases where document types are renamed or replaced.

---

## Performance Impact

### Time Breakdown (estimated for release #17)

| Phase | Files | Time |
|-------|-------|------|
| Validation | - | 100ms |
| Download & Extract | 500 | 2-3s |
| Rename Detection | 210 old + 500 new | 150ms |
| Git mv operations | 210 | 2-3s |
| Clear & Copy | 500 | 1-2s |
| Update README | 1 | 50ms |
| Create Commit | - | 200ms |
| Create Tags | 2 | 100ms |
| **TOTAL** | | **6-9s** |

**Overhead from rename detection**: ~150ms detection + ~2-3s git operations = ~2.5s (25% slower)

This is acceptable given the improved git history quality.

---

## Testing Checklist

After implementing rename detection:

- [ ] Dry-run shows correct rename count
- [ ] Actual import completes successfully
- [ ] Git log shows 'R' entries for renames
- [ ] Git blame shows original commits, not new commit
- [ ] Git diff shows only real changes, not whole-file rewrites
- [ ] No false positives (files that shouldn't be renames)
- [ ] Binary files handled correctly
- [ ] Large file sets don't cause performance issues
- [ ] Error messages are clear and helpful

---

## Summary

By implementing rename detection:
1. **Git history becomes clearer** - Renames properly tracked
2. **Code investigation easier** - Blame and diff work better
3. **Team collaboration improves** - Tools can properly merge changes
4. **Slight performance cost** (~2.5 seconds per import) is worth it

