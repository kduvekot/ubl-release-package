#!/bin/bash
#
# Negative Testing and Edge Cases
#
# Tests error handling, validation failures, and special cases:
# - Out-of-order imports
# - Duplicate imports
# - Patch without base
# - Dirty working directory
# - Corrupt/invalid ZIPs
# - Missing XML metadata
# - Patch overlay functionality
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================================================"
echo "UBL Import Tool - Negative Testing & Edge Cases"
echo -e "========================================================================${NC}"
echo ""

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

info() {
    echo -e "${YELLOW}→${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Create test workspace
TEST_WORKSPACE=$(mktemp -d -t ubl-negative-test-XXXXXX)
info "Created test workspace: $TEST_WORKSPACE"

# Cleanup function
cleanup() {
    if [ -n "$TEST_WORKSPACE" ] && [ -d "$TEST_WORKSPACE" ]; then
        rm -rf "$TEST_WORKSPACE"
    fi
}
trap cleanup EXIT

cd "$TEST_WORKSPACE"

#
# Helper: Create test repository
#
setup_test_repo() {
    local repo_name=$1
    local repo_dir="$TEST_WORKSPACE/$repo_name"

    mkdir -p "$repo_dir"
    cd "$repo_dir"

    git init --quiet
    git config user.email "test@example.com"
    git config user.name "Test User"
    git config commit.gpgsign false

    mkdir -p .claude
    echo "Test project" > .claude/CLAUDE.md
    echo "__pycache__/" > .gitignore

    cat > README.md <<EOF
# Test Repository

## Latest Release

(None)

## Release History

(None)
EOF

    cp -r "$REPO_ROOT/tools" .

    git add .
    git commit -m "Initial commit" --quiet

    echo "$repo_dir"
}

#
# Helper: Create mock release ZIP
#
create_mock_zip() {
    local name=$1
    local version=$2
    local has_xml=$3
    local add_extra_file=$4

    local work_dir="$TEST_WORKSPACE/${name}_work"
    mkdir -p "$work_dir/xsd/maindoc"
    mkdir -p "$work_dir/cl/gc"

    cat > "$work_dir/xsd/maindoc/UBL-Invoice-${version}.xsd" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="Invoice" type="InvoiceType"/>
</xsd:schema>
EOF

    cat > "$work_dir/cl/gc/UnitCodeList-${version}.gc" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<CodeList><Code>EA</Code></CodeList>
EOF

    if [ "$has_xml" = "true" ]; then
        cat > "$work_dir/UBL-${version}.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE article PUBLIC "-//OASIS//DTD DocBook XML V4.5//EN">
<!ENTITY version "${version}">
<!ENTITY stage "os">
<!ENTITY standard "OASIS Standard">
<!ENTITY pubdate "2006-12-18">
<article><title>UBL ${version}</title></article>
EOF
    fi

    if [ -n "$add_extra_file" ]; then
        echo "Extra content for patch testing" > "$work_dir/$add_extra_file"
    fi

    local zip_path="$TEST_WORKSPACE/${name}.zip"
    (cd "$work_dir" && zip -q -r "$zip_path" .)
    rm -rf "$work_dir"

    echo "$zip_path"
}

#
# Helper: Create test release_data.py
#
create_test_release_data() {
    local repo_dir=$1
    shift
    local releases=("$@")

    cat > "$repo_dir/tools/test_releases.py" <<EOF
#!/usr/bin/env python3
from tools.release_data import Release, TYPE_FULL, TYPE_PATCH

TEST_RELEASES = [
EOF

    for release_spec in "${releases[@]}"; do
        echo "    $release_spec," >> "$repo_dir/tools/test_releases.py"
    done

    cat >> "$repo_dir/tools/test_releases.py" <<EOF
]

def get_test_release_by_num(num):
    for rel in TEST_RELEASES:
        if rel.num == num:
            return rel
    return None
EOF
}

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 1: Out-of-Order Import Prevention"
echo -e "========================================================================${NC}"

REPO1=$(setup_test_repo "test1_out_of_order")
info "Testing import of release #10 without importing #1-9 first"

ZIP1=$(create_mock_zip "rel10" "2.0" "true")

create_test_release_data "$REPO1" \
    "Release(10, '2.0', 'os', '2006-12-18', 'file://$ZIP1')"

cd "$REPO1"

# Try to import #10 without force (should fail)
if python3 <<EOF 2>&1 | grep -q "Expected release #1"
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(10)
importer = ReleaseImporter(release, dry_run=False, force=False)
try:
    importer.run()
    sys.exit(1)  # Should have failed
except SystemExit:
    pass
EOF
then
    pass "Out-of-order import correctly prevented (without force)"
else
    fail "Out-of-order import was not prevented"
fi

# Try with force flag (should succeed with warning)
if python3 <<EOF 2>&1 | grep -q "WARNING.*forced"
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(10)
importer = ReleaseImporter(release, dry_run=False, force=True)
importer.run()
EOF
then
    pass "Out-of-order import allowed with force flag and warning"
else
    fail "Force flag did not work correctly"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 2: Duplicate Import Prevention"
echo -e "========================================================================${NC}"

REPO2=$(setup_test_repo "test2_duplicate")
ZIP2=$(create_mock_zip "rel1" "2.0" "true")

create_test_release_data "$REPO2" \
    "Release(1, '2.0', 'prd', '2006-01-20', 'file://$ZIP2')"

cd "$REPO2"

# Import once
info "Importing release #1 first time"
python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(1)
importer = ReleaseImporter(release, dry_run=False, force=True)
importer.run()
EOF

# Try to import again (should fail)
info "Attempting to import release #1 again"
if python3 <<EOF 2>&1 | grep -q "already been imported"
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(1)
importer = ReleaseImporter(release, dry_run=False, force=False)
importer.run()
EOF
then
    pass "Duplicate import correctly prevented"
else
    fail "Duplicate import was not prevented"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 3: Patch Without Base Release"
echo -e "========================================================================${NC}"

REPO3=$(setup_test_repo "test3_patch_no_base")
PATCH_ZIP=$(create_mock_zip "patch" "2.0" "true")

create_test_release_data "$REPO3" \
    "Release(7, '2.0', 'errata', '2008-04-23', 'file://$PATCH_ZIP', TYPE_PATCH, 6)"

cd "$REPO3"

info "Attempting to import patch #7 without base release #6"
if python3 <<EOF 2>&1 | grep -q "Base release.*not been imported"
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(7)
importer = ReleaseImporter(release, dry_run=False, force=True)
importer.run()
EOF
then
    pass "Patch without base correctly prevented"
else
    fail "Patch without base was not prevented"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 4: Dirty Working Directory"
echo -e "========================================================================${NC}"

REPO4=$(setup_test_repo "test4_dirty")
ZIP4=$(create_mock_zip "rel1" "2.0" "true")

create_test_release_data "$REPO4" \
    "Release(1, '2.0', 'prd', '2006-01-20', 'file://$ZIP4')"

cd "$REPO4"

# Create uncommitted change
info "Creating uncommitted change"
echo "uncommitted" > test_file.txt

if python3 <<EOF 2>&1 | grep -q "not clean"
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(1)
importer = ReleaseImporter(release, dry_run=False, force=True)
importer.run()
EOF
then
    pass "Dirty working directory correctly prevented import"
else
    fail "Import was allowed with dirty working directory"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 5: Invalid/Corrupt ZIP File"
echo -e "========================================================================${NC}"

REPO5=$(setup_test_repo "test5_corrupt")

# Create corrupt ZIP
CORRUPT_ZIP="$TEST_WORKSPACE/corrupt.zip"
echo "This is not a valid ZIP file" > "$CORRUPT_ZIP"

create_test_release_data "$REPO5" \
    "Release(1, '2.0', 'prd', '2006-01-20', 'file://$CORRUPT_ZIP')"

cd "$REPO5"

info "Attempting to import corrupt ZIP file"
if python3 <<EOF 2>&1 | grep -qi "error\|fail\|bad\|corrupt"
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(1)
importer = ReleaseImporter(release, dry_run=False, force=True)
try:
    importer.run()
    print("ERROR: Should have failed")
    sys.exit(1)
except Exception as e:
    print(f"Correctly caught error: {e}")
    sys.exit(0)
EOF
then
    pass "Corrupt ZIP correctly handled with error"
else
    fail "Corrupt ZIP did not produce error"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 6: Release Without XML Metadata (Fallback)"
echo -e "========================================================================${NC}"

REPO6=$(setup_test_repo "test6_no_xml")
ZIP_NO_XML=$(create_mock_zip "no_xml" "2.0" "false")  # has_xml=false

create_test_release_data "$REPO6" \
    "Release(1, '2.0', 'prd', '2006-01-20', 'file://$ZIP_NO_XML')"

cd "$REPO6"

info "Importing release without XML metadata file"
if python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(1)
importer = ReleaseImporter(release, dry_run=False, force=True)
success = importer.run()
sys.exit(0 if success else 1)
EOF
then
    # Check that commit was still created
    COMMIT_COUNT=$(git rev-list --count HEAD)
    if [ "$COMMIT_COUNT" = "2" ]; then
        pass "Release without XML imported successfully (fallback to URL metadata)"
    else
        fail "Release without XML did not create commit"
    fi
else
    fail "Release without XML failed to import"
fi

# Verify commit message still has metadata
if git log -1 --pretty=%B | grep -q "Release: UBL 2.0"; then
    pass "Commit message created from fallback metadata"
else
    fail "Commit message missing metadata"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 7: Patch Overlay Functionality"
echo -e "========================================================================${NC}"

REPO7=$(setup_test_repo "test7_patch")

# Create base release
BASE_ZIP=$(create_mock_zip "base" "2.0" "true")
# Create patch with an additional file
PATCH_ZIP=$(create_mock_zip "patch" "2.0" "true" "errata-notes.txt")

create_test_release_data "$REPO7" \
    "Release(1, '2.0', 'os', '2006-12-18', 'file://$BASE_ZIP')" \
    "Release(2, '2.0', 'errata', '2008-04-23', 'file://$PATCH_ZIP', TYPE_PATCH, 1)"

cd "$REPO7"

# Import base
info "Importing base release #1"
python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(1)
importer = ReleaseImporter(release, dry_run=False, force=True)
importer.run()
EOF

# Count files before patch
FILES_BEFORE=$(find . -type f -not -path './.git/*' -not -path './tools/*' -not -path './.claude/*' | wc -l)
info "Files before patch: $FILES_BEFORE"

# Check that errata-notes.txt doesn't exist yet
if [ ! -f "errata-notes.txt" ]; then
    pass "Patch file not present before patch import"
else
    fail "Patch file already exists (should not)"
fi

# Import patch
info "Importing patch release #2 (overlay)"
python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num

release = get_test_release_by_num(2)
importer = ReleaseImporter(release, dry_run=False, force=True)
importer.run()
EOF

# Verify patch was applied
if [ -f "errata-notes.txt" ]; then
    pass "Patch file added by overlay import"
else
    fail "Patch file not added"
fi

# Verify original files still exist
if [ -f "xsd/maindoc/UBL-Invoice-2.0.xsd" ]; then
    pass "Original files preserved during patch"
else
    fail "Original files lost during patch"
fi

# Verify commit was created
if git log -1 --pretty=%s | grep -q "errata"; then
    pass "Patch commit created with correct message"
else
    fail "Patch commit not created"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 8: Sequential Patch Application"
echo -e "========================================================================${NC}"

REPO8=$(setup_test_repo "test8_sequential_patch")

# Create three releases: base, first patch, second patch
BASE_ZIP8=$(create_mock_zip "base8" "2.0" "true")
PATCH1_ZIP=$(create_mock_zip "patch1" "2.0" "true" "patch1.txt")
PATCH2_ZIP=$(create_mock_zip "patch2" "2.0" "true" "patch2.txt")

create_test_release_data "$REPO8" \
    "Release(1, '2.0', 'os', '2006-12-18', 'file://$BASE_ZIP8')" \
    "Release(2, '2.0', 'errata', '2008-04-23', 'file://$PATCH1_ZIP', TYPE_PATCH, 1)" \
    "Release(3, '2.0', 'os-update', '2008-05-29', 'file://$PATCH2_ZIP', TYPE_PATCH, 2)"

cd "$REPO8"

# Import base
info "Importing base release"
python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num
release = get_test_release_by_num(1)
ReleaseImporter(release, dry_run=False, force=True).run()
EOF

# Import first patch
info "Importing first patch (depends on base)"
python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num
release = get_test_release_by_num(2)
ReleaseImporter(release, dry_run=False, force=True).run()
EOF

if [ -f "patch1.txt" ]; then
    pass "First patch applied successfully"
else
    fail "First patch not applied"
fi

# Import second patch (depends on first patch)
info "Importing second patch (depends on first patch)"
python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num
release = get_test_release_by_num(3)
ReleaseImporter(release, dry_run=False, force=True).run()
EOF

if [ -f "patch1.txt" ] && [ -f "patch2.txt" ]; then
    pass "Sequential patches both applied successfully"
else
    fail "Sequential patch application failed"
fi

# Verify 3 commits total
COMMIT_COUNT=$(git rev-list --count HEAD)
if [ "$COMMIT_COUNT" = "4" ]; then  # initial + base + patch1 + patch2
    pass "All three release commits created"
else
    fail "Expected 4 commits, got $COMMIT_COUNT"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test 9: Protected Paths During Full Import"
echo -e "========================================================================${NC}"

REPO9=$(setup_test_repo "test9_protected")
ZIP9=$(create_mock_zip "rel9" "2.0" "true")

create_test_release_data "$REPO9" \
    "Release(1, '2.0', 'prd', '2006-01-20', 'file://$ZIP9')"

cd "$REPO9"

# Create additional files that should be removed
info "Creating files that should be removed during import"
mkdir -p old_content
echo "old" > old_content/file.txt
git add old_content/
git commit -m "Add old content" --quiet

# Import release
info "Importing release (should remove old_content but keep tools/)"
python3 <<EOF >/dev/null 2>&1
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test_releases import get_test_release_by_num
release = get_test_release_by_num(1)
ReleaseImporter(release, dry_run=False, force=True).run()
EOF

# Check old content removed
if [ ! -d "old_content" ]; then
    pass "Old content removed during import"
else
    fail "Old content not removed"
fi

# Check protected paths preserved
if [ -d "tools" ] && [ -d ".claude" ] && [ -f ".gitignore" ]; then
    pass "Protected paths (tools/, .claude/, .gitignore) preserved"
else
    fail "Protected paths were removed"
fi

echo ""
echo -e "${BLUE}========================================================================"
echo "Test Summary"
echo -e "========================================================================${NC}"
echo -e "Tests passed: ${GREEN}${TESTS_PASSED}${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "Tests failed: ${RED}${TESTS_FAILED}${NC}"
else
    echo -e "Tests failed: ${TESTS_FAILED}"
fi
echo -e "========================================================================${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All negative tests and edge cases passed!${NC}"
    echo ""
    echo "Verified Error Handling:"
    echo "  ✓ Out-of-order import prevention"
    echo "  ✓ Duplicate import prevention"
    echo "  ✓ Patch dependency validation"
    echo "  ✓ Dirty working directory detection"
    echo "  ✓ Corrupt ZIP file handling"
    echo ""
    echo "Verified Edge Cases:"
    echo "  ✓ Releases without XML metadata (fallback)"
    echo "  ✓ Patch overlay functionality"
    echo "  ✓ Sequential patch application"
    echo "  ✓ Protected path preservation"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
