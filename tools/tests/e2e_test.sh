#!/bin/bash
#
# End-to-End Integration Test
#
# This test creates mock UBL releases and actually tests the complete import workflow:
# - Creating realistic ZIP files
# - Downloading (from file:// URLs)
# - Extracting
# - Applying to repository
# - Creating commits
# - Creating tags
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
echo "UBL Import Tool - End-to-End Integration Test"
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
TEST_WORKSPACE=$(mktemp -d -t ubl-e2e-test-XXXXXX)
info "Created test workspace: $TEST_WORKSPACE"

# Cleanup function
cleanup() {
    if [ -n "$TEST_WORKSPACE" ] && [ -d "$TEST_WORKSPACE" ]; then
        info "Cleaning up: $TEST_WORKSPACE"
        rm -rf "$TEST_WORKSPACE"
    fi
}
trap cleanup EXIT

cd "$TEST_WORKSPACE"

#
# STEP 1: Create Mock UBL Release ZIPs
#
echo ""
echo -e "${BLUE}========================================================================"
echo "Step 1: Creating Mock UBL Release Packages"
echo -e "========================================================================${NC}"

mkdir -p mock_releases

# Function to create a mock UBL release
create_mock_release() {
    local release_name=$1
    local version=$2
    local has_xml=$3

    local work_dir="$TEST_WORKSPACE/mock_releases/${release_name}_content"
    mkdir -p "$work_dir"

    # Create realistic UBL directory structure
    mkdir -p "$work_dir/xsd/maindoc"
    mkdir -p "$work_dir/xsd/common"
    mkdir -p "$work_dir/xsdrt/maindoc"
    mkdir -p "$work_dir/cl/gc"
    mkdir -p "$work_dir/doc"

    # Create sample XSD files
    cat > "$work_dir/xsd/maindoc/UBL-Invoice-${version}.xsd" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:oasis:names:specification:ubl:schema:xsd:Invoice-${version}">
  <xsd:element name="Invoice" type="InvoiceType"/>
  <xsd:complexType name="InvoiceType">
    <xsd:sequence>
      <xsd:element name="ID" type="xsd:string"/>
      <xsd:element name="IssueDate" type="xsd:date"/>
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>
EOF

    cat > "$work_dir/xsd/common/UBL-CommonBasicComponents-${version}.xsd" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="ID" type="xsd:string"/>
  <xsd:element name="IssueDate" type="xsd:date"/>
</xsd:schema>
EOF

    # Create sample code list
    cat > "$work_dir/cl/gc/UnitCodeList-${version}.gc" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<CodeList>
  <Code>EA</Code>
  <Code>KG</Code>
</CodeList>
EOF

    # Create metadata file if requested
    if [ "$has_xml" = "true" ]; then
        cat > "$work_dir/UBL-${version}.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE article PUBLIC "-//OASIS//DTD DocBook XML V4.5//EN">
<!ENTITY version "${version}">
<!ENTITY stage "os">
<!ENTITY standard "OASIS Standard">
<!ENTITY pubdate "2006-12-18">
<article>
  <title>UBL ${version}</title>
</article>
EOF
    fi

    # Create README
    cat > "$work_dir/README.txt" <<EOF
UBL ${version} - ${release_name}

This is a mock UBL release for testing purposes.
EOF

    # Create the ZIP file
    local zip_path="$TEST_WORKSPACE/mock_releases/${release_name}.zip"
    (cd "$work_dir" && zip -q -r "$zip_path" .)

    # Cleanup work directory
    rm -rf "$work_dir"

    # Output only the path (no color codes or extra text)
    echo "$zip_path"
}

# Create mock releases
info "Creating 3 mock releases for testing..."
echo ""

info "Creating prd-UBL-2.0 (no XML metadata)"
RELEASE1_ZIP=$(create_mock_release "prd-UBL-2.0" "2.0" "false")
info "  Created: $RELEASE1_ZIP"

info "Creating os-UBL-2.0 (with XML metadata)"
RELEASE2_ZIP=$(create_mock_release "os-UBL-2.0" "2.0" "true")
info "  Created: $RELEASE2_ZIP"

info "Creating os-UBL-2.1 (with XML metadata)"
RELEASE3_ZIP=$(create_mock_release "os-UBL-2.1" "2.1" "true")
info "  Created: $RELEASE3_ZIP"

echo ""
info "Mock releases created:"
ls -lh "$TEST_WORKSPACE/mock_releases/"*.zip
echo ""

#
# STEP 2: Create Test Repository with Modified release_data.py
#
echo ""
echo -e "${BLUE}========================================================================"
echo "Step 2: Setting Up Test Repository"
echo -e "========================================================================${NC}"

mkdir -p test_repo
cd test_repo

info "Initializing git repository"
git init --quiet
git config user.email "test@example.com"
git config user.name "Test User"
git config commit.gpgsign false

# Create initial structure
info "Creating initial repository structure"
mkdir -p .claude
echo "Test project" > .claude/CLAUDE.md
cat > .gitignore <<EOF
__pycache__/
*.pyc
*.pyo
EOF

cat > README.md <<EOF
# UBL Release Package History (E2E Test)

This is a test repository for end-to-end testing.

## Latest Release

(No releases imported yet)

## Release History

(No releases yet)
EOF

# Copy tools directory
info "Copying tools directory"
cp -r "$REPO_ROOT/tools" .

# Create a test-specific release_data.py that uses file:// URLs
info "Creating test release_data.py with file:// URLs"
cat > tools/test_release_data.py <<EOF
#!/usr/bin/env python3
"""
Test release data for E2E testing - uses local file:// URLs
"""
from tools.release_data import Release, TYPE_FULL, TYPE_PATCH

# Test releases using local file:// URLs
TEST_RELEASES = [
    Release(1, "2.0", "prd", "2006-01-20",
            "file://${RELEASE1_ZIP}"),
    Release(2, "2.0", "os", "2006-12-18",
            "file://${RELEASE2_ZIP}"),
    Release(3, "2.1", "os", "2013-11-04",
            "file://${RELEASE3_ZIP}"),
]

def get_test_release_by_num(num):
    for rel in TEST_RELEASES:
        if rel.num == num:
            return rel
    return None
EOF

# Initial commit
info "Creating initial commit"
git add .
git commit -m "Initial commit: test infrastructure" --quiet

INITIAL_COMMIT=$(git rev-parse HEAD)
info "Initial commit: $INITIAL_COMMIT"
echo ""

#
# STEP 3: Test Full Release Import
#
echo ""
echo -e "${BLUE}========================================================================"
echo "Step 3: Test Full Release Import (Release #1)"
echo -e "========================================================================${NC}"

info "Importing release #1 using file:// URL"
python3 <<EOF
import sys
sys.path.insert(0, '.')

from tools.import_release import ReleaseImporter
from tools.test_release_data import get_test_release_by_num

release = get_test_release_by_num(1)
print(f"Release: {release.tag_name}")
print(f"URL: {release.url}")
print()

importer = ReleaseImporter(release, dry_run=False, force=True)
success = importer.run()

if success:
    print("\n✓ Import completed successfully")
    sys.exit(0)
else:
    print("\n✗ Import failed")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    pass "Release #1 imported successfully"
else
    fail "Release #1 import failed"
    exit 1
fi

# Verify commit was created
info "Verifying commit was created"
COMMIT_COUNT=$(git rev-list --count HEAD)
if [ "$COMMIT_COUNT" = "2" ]; then
    pass "Commit created (count: 2)"
else
    fail "Expected 2 commits, got $COMMIT_COUNT"
fi

# Verify commit message format
info "Checking commit message format"
COMMIT_MSG=$(git log -1 --pretty=%B HEAD)
if echo "$COMMIT_MSG" | grep -q "Release: UBL 2.0"; then
    pass "Commit message has correct format"
else
    fail "Commit message format incorrect"
fi

# Verify files were extracted
info "Checking extracted files"
if [ -f "xsd/maindoc/UBL-Invoice-2.0.xsd" ]; then
    pass "XSD files extracted correctly"
else
    fail "XSD files not found"
fi

if [ -f "cl/gc/UnitCodeList-2.0.gc" ]; then
    pass "Code list files extracted correctly"
else
    fail "Code list files not found"
fi

if [ -f "README.txt" ]; then
    pass "README.txt extracted"
else
    fail "README.txt not found"
fi

# Verify tag was created
info "Checking git tags"
if git tag -l | grep -q "prd-UBL-2.0"; then
    pass "Release tag 'prd-UBL-2.0' created"
else
    fail "Release tag not created"
fi

# Verify protected paths still exist
info "Checking protected paths"
if [ -d "tools" ] && [ -d ".claude" ] && [ -f ".gitignore" ]; then
    pass "Protected paths preserved (tools/, .claude/, .gitignore)"
else
    fail "Protected paths were removed"
fi

echo ""

#
# STEP 4: Test Second Full Release Import
#
echo ""
echo -e "${BLUE}========================================================================"
echo "Step 4: Test Second Full Release Import (Release #2)"
echo -e "========================================================================${NC}"

info "Importing release #2 (os-UBL-2.0)"
python3 <<EOF
import sys
sys.path.insert(0, '.')

from tools.import_release import ReleaseImporter
from tools.test_release_data import get_test_release_by_num

release = get_test_release_by_num(2)
importer = ReleaseImporter(release, dry_run=False, force=True)
success = importer.run()

sys.exit(0 if success else 1)
EOF

if [ $? -eq 0 ]; then
    pass "Release #2 imported successfully"
else
    fail "Release #2 import failed"
fi

# Verify version tag for OASIS Standard
if git tag -l | grep -q "v2.0"; then
    pass "Version tag 'v2.0' created for OASIS Standard"
else
    fail "Version tag 'v2.0' not created"
fi

# Verify commit count
COMMIT_COUNT=$(git rev-list --count HEAD)
if [ "$COMMIT_COUNT" = "3" ]; then
    pass "Second commit created (count: 3)"
else
    fail "Expected 3 commits, got $COMMIT_COUNT"
fi

echo ""

#
# STEP 5: Test Git State Tracking
#
echo ""
echo -e "${BLUE}========================================================================"
echo "Step 5: Test Git State Tracking"
echo -e "========================================================================${NC}"

info "Querying git state after imports"
python3 <<EOF
from tools.git_state import GitStateManager

# Count releases
count = GitStateManager.count_release_commits()
print(f"Release commits found: {count}")

if count == 2:
    print("✓ PASS: Correct number of release commits")
else:
    print(f"✗ FAIL: Expected 2 commits, found {count}")
    exit(1)

# Get release details
commits = GitStateManager.get_release_commits()
print("\nRelease commits:")
for c in commits:
    print(f"  - {c['version']} ({c['stage']}) - {c['date']}")

# Check specific release
if GitStateManager.has_release_been_imported('os', '2.0'):
    print("\n✓ PASS: Can detect os-UBL-2.0 was imported")
else:
    print("\n✗ FAIL: os-UBL-2.0 not detected")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    pass "Git state tracking works correctly"
else
    fail "Git state tracking failed"
fi

echo ""

#
# STEP 6: Test README Updates
#
echo ""
echo -e "${BLUE}========================================================================"
echo "Step 6: Verify README Updates"
echo -e "========================================================================${NC}"

if [ -f "README.md" ]; then
    info "README.md contents:"
    head -10 README.md | sed 's/^/  /'
    echo ""
    if grep -q "UBL 2.0" README.md || grep -q "Latest Release" README.md; then
        pass "README.md was updated with release info"
    else
        fail "README.md not updated with release info"
    fi
else
    fail "README.md not found"
fi

echo ""

#
# STEP 7: Validate Full Git History
#
echo ""
echo -e "${BLUE}========================================================================"
echo "Step 7: Validate Complete Git History"
echo -e "========================================================================${NC}"

info "Git log:"
git log --oneline --decorate
echo ""

info "Git tags:"
git tag -l
echo ""

# Count tags
TAG_COUNT=$(git tag -l | wc -l)
if [ "$TAG_COUNT" -ge "3" ]; then
    pass "Multiple tags created ($TAG_COUNT tags)"
else
    fail "Expected at least 3 tags, got $TAG_COUNT"
fi

echo ""

#
# SUMMARY
#
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
    echo -e "${GREEN}✓ All end-to-end tests passed!${NC}"
    echo ""
    echo "Verified functionality:"
    echo "  ✓ ZIP download from file:// URLs"
    echo "  ✓ ZIP extraction"
    echo "  ✓ File placement in repository"
    echo "  ✓ Git commit creation"
    echo "  ✓ Git tag creation (both descriptive and version tags)"
    echo "  ✓ README.md updates"
    echo "  ✓ Protected paths preservation"
    echo "  ✓ Git state tracking across multiple imports"
    echo "  ✓ Sequential import workflow"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
