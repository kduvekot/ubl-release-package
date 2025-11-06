#!/bin/bash
#
# Simple diagnostic test to see what's actually happening
#

set -e

echo "Simple Negative Test - Diagnostic"
echo "=================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"

# Setup
git init --quiet
git config user.email "test@test.com"
git config user.name "Test"
git config commit.gpgsign false

mkdir .claude tools
echo "test" > .claude/CLAUDE.md
echo "# README" > README.md
cat > .gitignore <<'IGN'
*.zip
__pycache__/
*.pyc
*.pyo
IGN
cp -r "$REPO_ROOT/tools"/* tools/

git add .
git commit -m "init" --quiet

# Create a mock ZIP
mkdir mock_content
echo "<?xml version='1.0'?><xsd:schema/>" > mock_content/test.xsd
zip -q mock.zip -r mock_content/
rm -rf mock_content

# Get ZIP path before creating Python file
ZIP_PATH="$TEST_DIR/mock.zip"

# Create test releases
cat > tools/test_rel.py <<EOF
from tools.release_data import Release, TYPE_FULL, TYPE_PATCH

RELEASES = [
    Release(1, "2.0", "prd", "2006-01-20", "file://$ZIP_PATH"),
    Release(10, "2.1", "os", "2013-11-04", "file://$ZIP_PATH"),
]

def get_rel(num):
    for r in RELEASES:
        if r.num == num:
            return r
    return None
EOF

# Commit the test file so working directory is clean
git add tools/test_rel.py
git commit -m "Add test releases" --quiet

echo "Git status after commit:"
git status
echo ""

echo "TEST 1: Out-of-order import"
echo "----------------------------"
echo "Attempting to import release #10 without #1-9..."
echo ""

python3 <<'PYEOF' 2>&1 | head -50
import sys
sys.path.insert(0, '.')

from tools.import_release import ReleaseImporter
from tools.test_rel import get_rel

release = get_rel(10)
print(f"Release: #{release.num} - {release.tag_name}")
print(f"Force: False")
print("")

importer = ReleaseImporter(release, dry_run=False, force=False)
success = importer.run()

print("")
print(f"Result: success={success}")
if not success:
    print("✓ CORRECTLY FAILED")
else:
    print("✗ INCORRECTLY SUCCEEDED")
PYEOF

echo ""
echo "========================"
echo ""

cd /
rm -rf "$TEST_DIR"
