# UBL Import Tool Tests

This directory contains integration tests for the UBL release import tools.

## Running Tests

```bash
# Run all tests
./tools/tests/run_tests.sh

# Or from repository root
bash tools/tests/run_tests.sh
```

## What Gets Tested

The test suite validates:

1. **Git State Management** - Querying git history for imported releases
2. **Release Data Inventory** - Correct count and categorization of releases
3. **Validation Logic** - Git checks, sequential order, patch dependencies
4. **Dry-Run Mode** - Import tool runs without making changes
5. **Sequential Validation** - Prevents out-of-order imports
6. **Patch Dependencies** - Ensures patch releases have base releases
7. **Catchup Tool** - Batch import functionality

## Test Environment

Tests run in an isolated temporary directory with:
- Fresh git repository
- Clean initial state
- No network access (dry-run mode only)
- Automatic cleanup on exit

## Mock Test Releases

The `test_releases/` directory would contain mock ZIP files for testing actual
imports, but since we test in dry-run mode, we validate the logic without
requiring actual download of UBL packages.

## Expected Output

```
UBL Import Tool - Integration Tests
====================================

Test 1: Git state management
✓ PASS: git_state.py runs successfully
✓ PASS: Correctly reports 0 releases in fresh repo

Test 2: Release data inventory
✓ PASS: Release inventory has correct count (34)
✓ PASS: Correctly identifies 5 OASIS Standards
✓ PASS: Correctly identifies 2 patch releases

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Test Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests run: 7
Passed: 7
Failed: 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All tests passed!
```
