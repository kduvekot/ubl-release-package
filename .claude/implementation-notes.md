# Implementation Notes

## Metadata Extraction from XML

### Success Rate
**29 of 34 releases** have `UBL-X.X.xml` files with complete metadata (90% coverage).

### Releases WITHOUT XML (Need Fallback)
- `prd-UBL-2.0` (20 Jan 2006)
- `prd2-UBL-2.0` (28 Jul 2006)
- `prd3-UBL-2.0` (21 Sep 2006)

All other releases from `prd3r1-UBL-2.0` onwards have XML files.

## XML Parsing Patterns

### Pattern 1: Entity Declarations (UBL 2.0 - early 2.3)

Found in DOCTYPE declaration at top of XML file:

```xml
<!ENTITY name "UBL">
<!ENTITY version "2.2">
<!ENTITY pubdate "21 February 2018">
<!ENTITY stage "csprd03">
<!ENTITY standard "Committee Specification Public Review Draft 03">
<!ENTITY previous-loc "http://docs.oasis-open.org/ubl/csprd02-UBL-2.2">
```

**How to Parse:**
1. Read file until DOCTYPE declaration
2. Extract ENTITY definitions using regex or XML parser
3. Look for: `version`, `pubdate`, `stage`, `standard`

### Pattern 2: ArticleInfo Elements (late 2.3 - 2.5)

Found in document body:

```xml
<article>
  <articleinfo>
    <productname>UBL</productname>
    <productnumber>2.4</productnumber>
    <pubdate>20 June 2024</pubdate>
  </articleinfo>
</article>

<article status="OASIS Standard">
```

**How to Parse:**
1. Parse as XML document
2. Find `<productnumber>` element for version
3. Find `<pubdate>` element for date
4. Find `<article status="...">` attribute for status
5. Derive stage from status or document structure

### Extractable Metadata

All releases with XML provide:
- ✅ **Version number** (e.g., "2.2")
- ✅ **Publication date** (various formats)
- ✅ **Stage code** (e.g., "os", "csprd03") - most releases
- ✅ **Status description** (e.g., "OASIS Standard", "Committee Specification Draft 01")
- ✅ **Previous version URL** (useful for validation)

## Date Format Handling

UBL specifications use multiple date formats:
- "12 December 2006"
- "2018-07-09"
- "21 February 2018"
- "04 November 2013"

**Solution:** Parse all formats and convert to ISO 8601 (YYYY-MM-DD) for commit messages.

**Python Implementation:**
```python
from dateutil import parser
iso_date = parser.parse("21 February 2018").strftime("%Y-%m-%d")
# Result: "2018-02-21"
```

## Stage Type Mapping

For fallback parsing or validation:

```python
STAGE_TYPES = {
    # UBL 2.0 series
    'prd': 'Public Review Draft',
    'prd2': 'Public Review Draft 2',
    'prd3': 'Public Review Draft 3',
    'prd3r1': 'Public Review Draft 3 Rev 1',
    'cs': 'Committee Specification',
    'os': 'OASIS Standard',

    # UBL 2.1 series
    'prd1': 'Public Review Draft 1',
    'prd4': 'Public Review Draft 4',
    'csd4': 'Committee Specification Draft 4',
    'cs1': 'Committee Specification 1',
    'cos1': 'Candidate OASIS Standard 1',

    # UBL 2.2 series onwards
    'csprd01': 'Committee Specification Public Review Draft 01',
    'csprd02': 'Committee Specification Public Review Draft 02',
    'csprd03': 'Committee Specification Public Review Draft 03',
    'cs01': 'Committee Specification 01',
    'cos01': 'Candidate OASIS Standard 01',

    # UBL 2.3 series
    'csprd01': 'Committee Specification Public Review Draft 01',
    'csprd02': 'Committee Specification Public Review Draft 02',
    'csd03': 'Committee Specification Draft 03',
    'csd04': 'Committee Specification Draft 04',
    'cs02': 'Committee Specification 02',

    # UBL 2.4 series
    'csd01': 'Committee Specification Draft 01',
    'csd02': 'Committee Specification Draft 02',
}
```

## Script Architecture

### import_release.py (Core Worker)

**Purpose:** Import a single UBL release from URL

**Usage:**
```bash
python import_release.py --url https://docs.oasis-open.org/ubl/os-UBL-2.0.zip
```

**Process:**
1. Download ZIP to temporary location
2. Extract to temporary directory
3. Find `UBL-X.X.xml` file in extracted content
4. Parse XML to extract metadata (version, date, stage, status)
5. Clear all existing UBL content (preserve `tools/`, `.claude/`, `.git/`, `README.md`)
6. Copy extracted contents to repository root
7. Update `README.md` with new release information
8. Stage all changes: `git add -A`
9. Create commit with structured message
10. Create git tag(s) based on stage
11. Clean up temporary files

**Key Features:**
- Idempotent: can re-run safely if commit fails
- Auto-detects metadata from XML
- Handles file deletions/additions automatically
- Returns success/failure status
- Logs all operations

**Error Handling:**
- If XML not found: fall back to URL parsing + manual date
- If metadata incomplete: use fallback strategy
- If commit fails: preserve state for manual intervention

### catchup.py (One-Time Historical Import)

**Purpose:** Import all 34 historical releases in chronological order

**Usage:**
```bash
python catchup.py              # Import all releases
python catchup.py --dry-run    # Preview without committing
python catchup.py --start-from 10  # Resume from release #10
```

**Implementation:**
- Hardcoded list of 34 release URLs (in chronological order)
- Each URL maps to release number
- Loops through list calling `import_release.py` logic
- Handles special cases (3 releases without XML)
- Creates tags for all releases
- Progress reporting

**Hardcoded URL List:**
```python
RELEASES = [
    "https://docs.oasis-open.org/ubl/prd-UBL-2.0.zip",
    "https://docs.oasis-open.org/ubl/prd2-UBL-2.0.zip",
    # ... 32 more URLs
]
```

**Why Hardcoded?**
- One-time use only
- No value in external manifest file
- Simpler to maintain and understand
- Self-contained script

### Fallback Strategy for Releases Without XML

For `prd-UBL-2.0`, `prd2-UBL-2.0`, `prd3-UBL-2.0`:

1. **Parse URL** to extract:
   - Stage: `prd`, `prd2`, `prd3`
   - Version: `2.0`

2. **Look up stage type** from mapping table

3. **Get date from**:
   - Option A: ZIP file modification date
   - Option B: File timestamps inside ZIP
   - Option C: Hardcoded dates (we have them from OASIS directory listing)

4. **Create commit** with best-effort metadata

## Python Dependencies

### Standard Library Only
- `argparse` - CLI argument parsing
- `urllib.request` - Download ZIPs
- `zipfile` - Extract ZIPs
- `xml.etree.ElementTree` - Parse XML
- `re` - Parse entity declarations
- `tempfile` - Temporary file handling
- `shutil` - File operations
- `subprocess` - Git commands
- `pathlib` - Path handling
- `json` - If needed for data structures

### Optional External (Nice to Have)
- `dateutil` - Better date parsing (handles multiple formats)
- `requests` - More robust HTTP downloads (vs urllib)

**Decision:** Start with stdlib only, add external deps only if needed.

## Testing Strategy

### Manual Testing During Development
1. Test on single release first (e.g., `os-UBL-2.4`)
2. Verify metadata extraction
3. Check commit message format
4. Verify tags created correctly
5. Test on release without XML (e.g., `prd2-UBL-2.0`)

### Before Full Catchup
1. Test on first 3 releases (prd, prd2, prd3)
2. Verify commit history looks correct
3. Check that file deletions work properly
4. Validate README.md updates correctly

### Post-Import Validation
1. Verify all 34 commits created
2. Check all tags exist
3. Verify major version tags on correct commits
4. Review git log for consistency
5. Check final README.md completeness

## README.md Update Logic

### Per-Release Update
Each release commit updates README.md to add:
```markdown
## Latest Release
UBL {version} ({status}) - {date}

## Release History
- {stage}-UBL-{version} - {date} - [to be filled with commit hash]
```

### Post-Commit Hash Update
After each commit, optionally run:
```bash
# Get commit hash
HASH=$(git rev-parse HEAD)
# Update README.md to add hash
# Create follow-up commit
```

**Note:** Hash update could be done as:
- Immediate follow-up commits (doubles commit count)
- Single batch update at end (one commit to add all hashes)
- Manual update after full import

**Recommendation:** Batch update at end to keep commit count clean.

## Git Operations

### Clearing UBL Content
```python
# Keep these:
PRESERVE = ['.git', '.claude', 'tools', 'README.md', '.gitignore']

# Remove everything else
for item in os.listdir('.'):
    if item not in PRESERVE:
        if os.path.isdir(item):
            shutil.rmtree(item)
        else:
            os.remove(item)
```

### Staging Changes
```bash
git add -A
# Stages: new files, modifications, deletions
```

### Creating Commit
```bash
git commit -m "Release: UBL 2.0 (OASIS Standard)

Date: 2006-12-18
Stage: os
Source: https://docs.oasis-open.org/ubl/os-UBL-2.0.zip"
```

### Creating Tags
```bash
# Always create descriptive tag
git tag prd-UBL-2.0

# For OASIS Standards, also create major version tag
git tag v2.0
```

## Future Enhancement Ideas

### Automatic New Release Detection
- Check OASIS website periodically
- Detect new UBL releases
- Trigger import automatically

### Schema Validation
- Validate extracted XSD schemas are well-formed
- Check that XML instances validate against schemas

### Diff Reports
- Generate human-readable diffs between releases
- Highlight schema changes, new document types, etc.

### GitHub Actions Integration
- Automate import on new release detection
- Run validation checks on import
- Auto-create pull requests

These are out of scope for initial implementation but worth considering for future work.
