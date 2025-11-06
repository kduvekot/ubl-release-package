#!/bin/bash
#
# Verbose test runner - shows exactly what each test does
#

set -e

echo "========================================================================"
echo "VERBOSE TEST RUN - Detailed Logging"
echo "========================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Setup:"
echo "  Repository root: $REPO_ROOT"
echo "  Test directory: $SCRIPT_DIR"
echo ""

# Create temporary test environment
TEST_DIR=$(mktemp -d -t ubl-verbose-test-XXXXXX)
echo "Created test directory: $TEST_DIR"
echo ""

# Cleanup function
cleanup() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        echo ""
        echo "Cleaning up: $TEST_DIR"
        rm -rf "$TEST_DIR"
    fi
}
trap cleanup EXIT

echo "========================================================================"
echo "Step 1: Initialize Test Repository"
echo "========================================================================"
cd "$TEST_DIR"
echo "→ Running: git init"
git init 2>&1 | head -3
echo "→ Running: git config user.email test@example.com"
git config user.email "test@example.com"
echo "→ Running: git config user.name 'Test User'"
git config user.name "Test User"
echo "→ Running: git config commit.gpgsign false"
git config commit.gpgsign false
echo ""

echo "Step 2: Create Initial Files"
echo "→ Creating .gitignore"
cat > .gitignore <<EOF
__pycache__/
*.pyc
EOF

echo "→ Creating README.md"
cat > README.md <<EOF
# Test Repository
EOF

echo "→ Creating .claude/CLAUDE.md"
mkdir -p .claude
echo "Test project" > .claude/CLAUDE.md
echo ""

echo "Step 3: Copy Tools Directory"
echo "→ Running: cp -r $REPO_ROOT/tools ."
cp -r "$REPO_ROOT/tools" .
echo "  Files copied: $(find tools -type f | wc -l) files"
echo ""

echo "Step 4: Create Initial Commit"
echo "→ Running: git add ."
git add .
echo "→ Running: git commit -m 'Initial commit'"
git commit -m "Initial commit: test infrastructure" --quiet
INITIAL_COMMIT=$(git rev-parse HEAD)
echo "  Commit created: $INITIAL_COMMIT"
echo ""

echo "========================================================================"
echo "TEST 1: Git State Management"
echo "========================================================================"
echo ""

echo "Test 1.1: Run git_state.py as module"
echo "→ Running: python3 -m tools.git_state"
echo "--- Output: ---"
python3 -m tools.git_state
echo "--- End Output ---"
echo ""

echo "Test 1.2: Count release commits (should be 0)"
echo "→ Running Python:"
echo "  from tools.git_state import GitStateManager"
echo "  print(GitStateManager.count_release_commits())"
RELEASE_COUNT=$(python3 -c "from tools.git_state import GitStateManager; print(GitStateManager.count_release_commits())")
echo "  Result: $RELEASE_COUNT"
if [ "$RELEASE_COUNT" = "0" ]; then
    echo "  ✓ PASS: Correctly reports 0 releases"
else
    echo "  ✗ FAIL: Expected 0, got $RELEASE_COUNT"
fi
echo ""

echo "Test 1.3: Get release commits list (should be empty)"
echo "→ Running Python:"
echo "  commits = GitStateManager.get_release_commits()"
echo "  print(f'Found {len(commits)} release commits')"
python3 <<EOF
from tools.git_state import GitStateManager
commits = GitStateManager.get_release_commits()
print(f"  Result: Found {len(commits)} release commits")
if len(commits) == 0:
    print("  ✓ PASS: Empty list as expected")
else:
    print(f"  ✗ FAIL: Expected empty list, got {len(commits)} commits")
EOF
echo ""

echo "========================================================================"
echo "TEST 2: Release Data Inventory"
echo "========================================================================"
echo ""

echo "Test 2.1: Count total releases"
echo "→ Running Python:"
echo "  from tools.release_data import get_total_count"
echo "  print(get_total_count())"
TOTAL=$(python3 -c "from tools.release_data import get_total_count; print(get_total_count())")
echo "  Result: $TOTAL releases"
if [ "$TOTAL" = "34" ]; then
    echo "  ✓ PASS: Correct count (34)"
else
    echo "  ✗ FAIL: Expected 34, got $TOTAL"
fi
echo ""

echo "Test 2.2: Count OASIS Standards"
echo "→ Running Python:"
echo "  from tools.release_data import get_oasis_standards"
echo "  standards = get_oasis_standards()"
echo "  print(len(standards))"
python3 <<EOF
from tools.release_data import get_oasis_standards
standards = get_oasis_standards()
print(f"  Result: {len(standards)} OASIS Standards")
for s in standards:
    print(f"    - UBL {s.version} ({s.stage}) - {s.date}")
if len(standards) == 5:
    print("  ✓ PASS: Correct count (5)")
else:
    print(f"  ✗ FAIL: Expected 5, got {len(standards)}")
EOF
echo ""

echo "Test 2.3: Count patch releases"
echo "→ Running Python:"
echo "  from tools.release_data import get_patch_releases"
echo "  patches = get_patch_releases()"
echo "  print(len(patches))"
python3 <<EOF
from tools.release_data import get_patch_releases
patches = get_patch_releases()
print(f"  Result: {len(patches)} patch releases")
for p in patches:
    print(f"    - #{p.num}: {p.tag_name} (applies to #{p.base_release_num})")
if len(patches) == 2:
    print("  ✓ PASS: Correct count (2)")
else:
    print(f"  ✗ FAIL: Expected 2, got {len(patches)}")
EOF
echo ""

echo "Test 2.4: Verify release #1 details"
echo "→ Running Python:"
echo "  from tools.release_data import get_release_by_num"
echo "  rel = get_release_by_num(1)"
python3 <<EOF
from tools.release_data import get_release_by_num
rel = get_release_by_num(1)
print(f"  Result:")
print(f"    Number: {rel.num}")
print(f"    Version: {rel.version}")
print(f"    Stage: {rel.stage}")
print(f"    Date: {rel.date}")
print(f"    Type: {rel.release_type}")
print(f"    URL: {rel.url}")
print(f"  ✓ PASS: Release #1 data accessible")
EOF
echo ""

echo "========================================================================"
echo "TEST 3: Validation Logic"
echo "========================================================================"
echo ""

echo "Test 3.1: Check if in git repository"
echo "→ Running Python:"
echo "  from tools.validators import Validators"
echo "  Validators.check_git_repo()"
if python3 -c "from tools.validators import Validators; Validators.check_git_repo()"; then
    echo "  ✓ PASS: Git repository check works"
else
    echo "  ✗ FAIL: Git repository check failed"
fi
echo ""

echo "Test 3.2: Check if working directory is clean"
echo "→ Running: git status --porcelain"
git status --porcelain
echo "→ Running Python:"
echo "  from tools.validators import Validators"
echo "  Validators.check_git_clean()"
if python3 -c "from tools.validators import Validators; Validators.check_git_clean()"; then
    echo "  ✓ PASS: Git clean check works"
else
    echo "  ✗ FAIL: Git clean check failed"
fi
echo ""

echo "Test 3.3: Test sequential order validation (should fail for #10)"
echo "→ Running Python:"
echo "  from tools.validators import Validators"
echo "  try:"
echo "      Validators.check_sequential_order(10, force=False)"
echo "  except ValidationError as e:"
echo "      print('Correctly raised error')"
python3 <<EOF
from tools.validators import Validators, ValidationError
try:
    Validators.check_sequential_order(10, force=False)
    print("  ✗ FAIL: Should have raised ValidationError")
except ValidationError as e:
    print(f"  Result: ValidationError raised")
    print(f"  Message preview: {str(e)[:80]}...")
    print("  ✓ PASS: Correctly prevents out-of-order import")
EOF
echo ""

echo "Test 3.4: Test sequential order with force=True (should succeed)"
echo "→ Running Python:"
echo "  Validators.check_sequential_order(10, force=True)"
python3 <<EOF
from tools.validators import Validators
try:
    Validators.check_sequential_order(10, force=True)
    print("  ✓ PASS: Force flag allows out-of-order import")
except Exception as e:
    print(f"  ✗ FAIL: {e}")
EOF
echo ""

echo "Test 3.5: Test patch dependency validation"
echo "→ Running Python:"
echo "  from tools.release_data import get_release_by_num"
echo "  patch = get_release_by_num(7)  # errata-UBL-2.0"
echo "  Validators.check_patch_dependencies(patch)"
python3 <<EOF
from tools.validators import Validators, ValidationError
from tools.release_data import get_release_by_num

patch = get_release_by_num(7)  # errata-UBL-2.0
print(f"  Testing patch: {patch.tag_name}")
print(f"  Requires base: #{patch.base_release_num}")

try:
    Validators.check_patch_dependencies(patch)
    print("  ✗ FAIL: Should have raised ValidationError (base not imported)")
except ValidationError as e:
    print(f"  Result: ValidationError raised")
    print(f"  Message preview: {str(e)[:80]}...")
    print("  ✓ PASS: Correctly prevents patch without base release")
EOF
echo ""

echo "========================================================================"
echo "TEST 4: Dry-Run Import"
echo "========================================================================"
echo ""

echo "Test 4.1: Run import_release in dry-run mode"
echo "→ Running: python3 -m tools.import_release 1 --dry-run"
echo "--- Output (first 30 lines): ---"
python3 -m tools.import_release 1 --dry-run 2>&1 | head -30
echo "--- End Output ---"
echo ""

if python3 -m tools.import_release 1 --dry-run 2>&1 | grep -q "Validating"; then
    echo "  ✓ PASS: Dry-run mode initiates and validates"
else
    echo "  ✗ FAIL: Dry-run did not show validation"
fi
echo ""

echo "========================================================================"
echo "TEST 5: Catchup Tool"
echo "========================================================================"
echo ""

echo "Test 5.1: Run catchup with small range in dry-run"
echo "→ Running: python3 -m tools.catchup --start-from 1 --end-at 2 --dry-run --force"
echo "--- Output: ---"
python3 -m tools.catchup --start-from 1 --end-at 2 --dry-run --force 2>&1 | head -40
echo "--- End Output ---"
echo ""

if python3 -m tools.catchup --start-from 1 --end-at 2 --dry-run --force 2>&1 | grep -q "Progress:"; then
    echo "  ✓ PASS: Catchup tool runs in dry-run mode"
else
    echo "  ✗ FAIL: Catchup tool did not show progress"
fi
echo ""

echo "========================================================================"
echo "TEST SUMMARY"
echo "========================================================================"
echo ""
echo "All tests examine the tool's behavior WITHOUT actually downloading or"
echo "importing real UBL releases. They validate:"
echo ""
echo "  1. Git state tracking queries git history correctly"
echo "  2. Release inventory has correct counts and metadata"
echo "  3. Validation logic enforces safety rules"
echo "  4. Dry-run mode validates without making changes"
echo "  5. Catchup tool can process multiple releases"
echo ""
echo "Key validation checks tested:"
echo "  ✓ Sequential import order enforcement"
echo "  ✓ Patch dependency validation"
echo "  ✓ Git working directory cleanliness"
echo "  ✓ Release data accuracy (34 releases, 5 standards, 2 patches)"
echo "  ✓ Dry-run preview mode"
echo ""
echo "All tests run in isolated temporary repository."
echo "No real UBL packages are downloaded during testing."
echo ""
