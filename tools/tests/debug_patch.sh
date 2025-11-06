#!/bin/bash
#
# Debug patch overlay
#

set -e

REPO_ROOT="/home/user/ubl-release-package"
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"

echo "Test directory: $TEST_DIR"
echo ""

# Setup
git init --quiet
git config user.email "t@t.com"
git config user.name "T"
git config commit.gpgsign false

cat > .gitignore <<'EOF'
*.zip
__pycache__/
*.pyc
EOF

mkdir -p .claude
echo "test" > .claude/CLAUDE.md

cat > README.md <<'EOF'
# Test

## Latest Release

(None)

## Release History

(None)
EOF

cp -r "$REPO_ROOT/tools" .
git add .
git commit -m "init" --quiet

# Create base ZIP
echo "Creating base ZIP..."
BASE_WORK="$TEST_DIR/base_work"
mkdir -p "$BASE_WORK/xsd/maindoc"
mkdir -p "$BASE_WORK/cl/gc"
echo "BASE XSD" > "$BASE_WORK/xsd/maindoc/Invoice.xsd"
echo "BASE CL" > "$BASE_WORK/cl/gc/Units.gc"
echo "BASE README" > "$BASE_WORK/README.txt"

BASE_ZIP="$TEST_DIR/base.zip"
(cd "$BASE_WORK" && zip -q -r "$BASE_ZIP" .)
rm -rf "$BASE_WORK"

echo "Base ZIP created: $BASE_ZIP"
unzip -l "$BASE_ZIP"
echo ""

# Create patch ZIP with extra files
echo "Creating patch ZIP..."
PATCH_WORK="$TEST_DIR/patch_work"
mkdir -p "$PATCH_WORK/xsd/maindoc"
mkdir -p "$PATCH_WORK/cl/gc"
echo "PATCHED XSD" > "$PATCH_WORK/xsd/maindoc/Invoice.xsd"
echo "BASE CL" > "$PATCH_WORK/cl/gc/Units.gc"
echo "PATCH README" > "$PATCH_WORK/README.txt"
echo "ERRATA NOTES" > "$PATCH_WORK/errata.txt"
echo "CHANGELOG" > "$PATCH_WORK/changelog.txt"

PATCH_ZIP="$TEST_DIR/patch.zip"
(cd "$PATCH_WORK" && zip -q -r "$PATCH_ZIP" .)
rm -rf "$PATCH_WORK"

echo "Patch ZIP created: $PATCH_ZIP"
unzip -l "$PATCH_ZIP"
echo ""

# Create test releases
cat > tools/test.py <<EOF
from tools.release_data import Release, TYPE_FULL, TYPE_PATCH
RELEASES = [
    Release(1, '2.0', 'os', '2006-12-18', 'file://$BASE_ZIP'),
    Release(2, '2.0', 'errata', '2008-04-23', 'file://$PATCH_ZIP', TYPE_PATCH, 1),
]
def get_rel(num):
    for r in RELEASES:
        if r.num == num:
            return r
EOF

git add tools/test.py
git commit -m "test" --quiet

echo "=== Importing BASE ==="
python3 <<'PYEOF'
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test import get_rel
importer = ReleaseImporter(get_rel(1), False, True)
success = importer.run()
print(f"\nBase import success: {success}")
PYEOF

echo ""
echo "Repository after base:"
ls -la
echo ""
echo "Files in repo:"
find . -type f -not -path './.git/*' -not -path './tools/*' | sort
echo ""

echo "=== Importing PATCH ==="
python3 <<'PYEOF'
import sys
sys.path.insert(0, '.')
from tools.import_release import ReleaseImporter
from tools.test import get_rel
importer = ReleaseImporter(get_rel(2), False, True)
success = importer.run()
print(f"\nPatch import success: {success}")
PYEOF

echo ""
echo "Repository after patch:"
ls -la
echo ""
echo "Files in repo:"
find . -type f -not -path './.git/*' -not -path './tools/*' | sort
echo ""

# Check for patch files
if [ -f "errata.txt" ]; then
    echo "✓ errata.txt exists"
    cat errata.txt
else
    echo "✗ errata.txt NOT FOUND"
fi

if [ -f "changelog.txt" ]; then
    echo "✓ changelog.txt exists"
    cat changelog.txt
else
    echo "✗ changelog.txt NOT FOUND"
fi

echo ""
echo "Git log:"
git log --oneline --all

# Cleanup
cd /
rm -rf "$TEST_DIR"
