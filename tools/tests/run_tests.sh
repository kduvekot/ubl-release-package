#!/bin/bash
#
# Integration tests for UBL import tools
#
# This script creates a temporary git repository and tests the import tools
# with mock releases to ensure they work correctly before running on real data.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test results
pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Test $TESTS_RUN: $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "UBL Import Tool - Integration Tests"
echo "===================================="
echo ""
echo "Repository root: $REPO_ROOT"
echo "Test directory: $SCRIPT_DIR"
echo ""

# Create temporary test environment
TEST_DIR=$(mktemp -d -t ubl-test-XXXXXX)
info "Created test directory: $TEST_DIR"

# Cleanup function
cleanup() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        info "Cleaning up test directory: $TEST_DIR"
        rm -rf "$TEST_DIR"
    fi
}

# Register cleanup on exit
trap cleanup EXIT

# Initialize test repository
cd "$TEST_DIR"
git init
git config user.email "test@example.com"
git config user.name "Test User"
git config commit.gpgsign false  # Disable commit signing for tests

# Create initial .gitignore
cat > .gitignore <<EOF
__pycache__/
*.pyc
*.pyo
.DS_Store
EOF

# Create initial README
cat > README.md <<EOF
# UBL Release Package History (Test)

This is a test repository.
EOF

# Create .claude directory
mkdir -p .claude
echo "Test project" > .claude/CLAUDE.md

# Copy tools directory to test repo
info "Copying tools directory to test repository..."
cp -r "$REPO_ROOT/tools" .

# Initial commit
git add .
git commit -m "Initial commit: test infrastructure"

info "Test repository initialized"
info "Repository structure:"
ls -la

#
# TEST 1: Validate git_state.py
#
run_test "Git state management"

# Test that we can query git state
if python3 -m tools.git_state; then
    pass "git_state.py runs successfully"
else
    fail "git_state.py failed to run"
fi

# Check that no releases are detected yet
RELEASE_COUNT=$(python3 -c "from tools.git_state import GitStateManager; print(GitStateManager.count_release_commits())")
if [ "$RELEASE_COUNT" = "0" ]; then
    pass "Correctly reports 0 releases in fresh repo"
else
    fail "Expected 0 releases, got $RELEASE_COUNT"
fi

#
# TEST 2: Validate release_data.py
#
run_test "Release data inventory"

# Check that we have 34 releases
TOTAL_RELEASES=$(python3 -c "from tools.release_data import get_total_count; print(get_total_count())")
if [ "$TOTAL_RELEASES" = "34" ]; then
    pass "Release inventory has correct count (34)"
else
    fail "Expected 34 releases, got $TOTAL_RELEASES"
fi

# Check OASIS Standards count
OS_COUNT=$(python3 -c "from tools.release_data import get_oasis_standards; print(len(get_oasis_standards()))")
if [ "$OS_COUNT" = "5" ]; then
    pass "Correctly identifies 5 OASIS Standards"
else
    fail "Expected 5 OASIS Standards, got $OS_COUNT"
fi

# Check patch releases count
PATCH_COUNT=$(python3 -c "from tools.release_data import get_patch_releases; print(len(get_patch_releases()))")
if [ "$PATCH_COUNT" = "2" ]; then
    pass "Correctly identifies 2 patch releases"
else
    fail "Expected 2 patch releases, got $PATCH_COUNT"
fi

#
# TEST 3: Validate validators.py
#
run_test "Validation logic"

# Test git repo check
if python3 -c "from tools.validators import Validators; Validators.check_git_repo()"; then
    pass "Git repository check works"
else
    fail "Git repository check failed"
fi

# Test git clean check
if python3 -c "from tools.validators import Validators; Validators.check_git_clean()"; then
    pass "Git clean check works"
else
    fail "Git clean check failed"
fi

#
# TEST 4: Test dry-run import
#
run_test "Dry-run import of release #1"

# We can't actually download from OASIS in tests, but we can test the validation
# and command-line parsing
if python3 -m tools.import_release 1 --dry-run 2>&1 | grep -q "Validating"; then
    pass "Dry-run mode initiates correctly"
else
    fail "Dry-run mode failed"
fi

#
# TEST 5: Test sequential validation
#
run_test "Sequential import validation"

# Try to import release #10 without importing #1-9 first
if python3 -c "from tools.validators import Validators; from tools.release_data import get_release_by_num; Validators.check_sequential_order(10, force=False)" 2>&1 | grep -q "ERROR"; then
    pass "Correctly prevents out-of-order import"
else
    fail "Should have prevented importing #10 before #1-9"
fi

# Allow with force flag
if python3 -c "from tools.validators import Validators; Validators.check_sequential_order(10, force=True)"; then
    pass "Force flag allows out-of-order import"
else
    fail "Force flag should allow out-of-order import"
fi

#
# TEST 6: Test patch dependency validation
#
run_test "Patch dependency validation"

# Test that patch release #7 (errata-UBL-2.0) requires base release #6 (os-UBL-2.0)
PATCH_VALIDATION=$(python3 <<EOF
from tools.validators import Validators, ValidationError
from tools.release_data import get_release_by_num

try:
    release = get_release_by_num(7)  # errata-UBL-2.0
    Validators.check_patch_dependencies(release)
    print("NO_ERROR")
except ValidationError as e:
    if "not been imported" in str(e):
        print("CORRECTLY_BLOCKED")
    else:
        print("WRONG_ERROR")
EOF
)

if [ "$PATCH_VALIDATION" = "CORRECTLY_BLOCKED" ]; then
    pass "Correctly prevents patch without base release"
else
    fail "Patch dependency validation failed: $PATCH_VALIDATION"
fi

#
# TEST 7: Test catchup tool
#
run_test "Catchup tool dry-run"

# Test catchup with range
if python3 -m tools.catchup --start-from 1 --end-at 3 --dry-run --force 2>&1 | grep -q "Progress:"; then
    pass "Catchup tool runs in dry-run mode"
else
    fail "Catchup tool failed"
fi

#
# Print summary
#
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tests run: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
else
    echo "Failed: $TESTS_FAILED"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
