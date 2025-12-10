#!/usr/bin/env python3
"""
Integration test for granular_import.py

Creates mock release ZIP files to test the full import flow without network access.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.granular_import import (
    import_release_granular, setup_test_repo,
    compute_changeset, get_repo_files, get_zip_files,
    ReleaseChangeset
)
from tools.release_data import Release


def create_mock_zip(zip_path: Path, files: dict):
    """Create a mock ZIP file with specified content."""
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for path, content in files.items():
            zf.writestr(path, content)


def run_integration_test():
    """Run full integration test with mock releases."""
    print("=" * 70)
    print("Granular Import Integration Test (Mock Data)")
    print("=" * 70)

    temp_dir = Path(tempfile.mkdtemp(prefix='test-integration-'))

    try:
        # Setup test repository
        repo_root = temp_dir / 'repo'
        repo_root.mkdir()

        # Initialize git with proper config
        subprocess.run(['git', 'init'], cwd=repo_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                      cwd=repo_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                      cwd=repo_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'commit.gpgsign', 'false'],
                      cwd=repo_root, capture_output=True, check=True)

        # Create .gitignore and initial commit
        (repo_root / '.gitignore').write_text('*.pyc\n')
        subprocess.run(['git', 'add', '.'], cwd=repo_root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'],
                      cwd=repo_root, capture_output=True, check=True)

        print(f"\n  Test repo created at: {repo_root}")

        # =====================================================================
        # Test 1: First release (all new files)
        # =====================================================================
        print("\n--- Test 1: First Release (All New Files) ---")

        release1_dir = temp_dir / 'release1'
        release1_dir.mkdir()

        # Create mock release 1 content with realistic schema-like content
        # This ensures git can detect renames when we bump versions (>50% similarity)
        invoice_base = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
            version="2.0">
  <!-- UBL Invoice Document Schema -->
  <xsd:element name="Invoice" type="InvoiceType"/>
  <xsd:complexType name="InvoiceType">
    <xsd:sequence>
      <xsd:element name="ID" type="xsd:string"/>
      <xsd:element name="IssueDate" type="xsd:date"/>
      <xsd:element name="InvoiceTypeCode" type="xsd:string"/>
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>"""

        order_base = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:oasis:names:specification:ubl:schema:xsd:Order-2"
            version="2.0">
  <!-- UBL Order Document Schema -->
  <xsd:element name="Order" type="OrderType"/>
  <xsd:complexType name="OrderType">
    <xsd:sequence>
      <xsd:element name="ID" type="xsd:string"/>
      <xsd:element name="IssueDate" type="xsd:date"/>
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>"""

        release1_files = {
            'xsd/maindoc/UBL-Invoice-2.0.xsd': invoice_base,
            'xsd/maindoc/UBL-Order-2.0.xsd': order_base,
            'xsd/common/UBL-Types-2.0.xsd': '<Types version="2.0"/>',
            'doc/UBL-2.0.xml': '<Documentation version="2.0"/>',
        }

        for path, content in release1_files.items():
            file_path = release1_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        # Compute changeset for release 1
        repo_files = get_repo_files(repo_root)
        zip_files = get_zip_files(release1_dir)

        release1 = Release(1, "2.0", "prd", "2006-01-01", "http://test.com/r1.zip")
        changeset1 = compute_changeset(repo_files, zip_files, release1, None)

        print(f"  {changeset1.summary()}")
        assert len(changeset1.additions) == 4, f"Expected 4 additions, got {len(changeset1.additions)}"
        assert len(changeset1.renames) == 0
        assert len(changeset1.deletions) == 0

        # Apply changes manually (simulating what import_release_granular does)
        for path, content in release1_files.items():
            dest = repo_root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)

        subprocess.run(['git', 'add', '-A'], cwd=repo_root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Release 1'],
                      cwd=repo_root, capture_output=True, check=True)

        print("  ✓ Test 1 passed: All files added correctly")

        # =====================================================================
        # Test 2: Second release (with modifications)
        # =====================================================================
        print("\n--- Test 2: Second Release (Modifications) ---")

        release2_dir = temp_dir / 'release2'
        release2_dir.mkdir()

        # Use the same base content with slight modifications
        invoice_modified = invoice_base.replace('version="2.0"', 'version="2.0" revision="2"')

        release2_files = {
            'xsd/maindoc/UBL-Invoice-2.0.xsd': invoice_modified,  # Modified
            'xsd/maindoc/UBL-Order-2.0.xsd': order_base,  # Unchanged
            'xsd/common/UBL-Types-2.0.xsd': '<Types version="2.0"/>',  # Unchanged
            'doc/UBL-2.0.xml': '<Documentation version="2.0" rev="2"/>',  # Modified
            'xsd/maindoc/UBL-CreditNote-2.0.xsd': '<CreditNote version="2.0"/>',  # New
        }

        for path, content in release2_files.items():
            file_path = release2_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        repo_files = get_repo_files(repo_root)
        zip_files = get_zip_files(release2_dir)

        release2 = Release(2, "2.0", "prd2", "2006-02-01", "http://test.com/r2.zip")
        changeset2 = compute_changeset(repo_files, zip_files, release2, release1)

        print(f"  {changeset2.summary()}")
        assert len(changeset2.additions) == 1, f"Expected 1 addition, got {len(changeset2.additions)}"
        assert len(changeset2.modifications) == 2, f"Expected 2 modifications, got {len(changeset2.modifications)}"

        # Apply changes
        for path, content in release2_files.items():
            dest = repo_root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)

        subprocess.run(['git', 'add', '-A'], cwd=repo_root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Release 2'],
                      cwd=repo_root, capture_output=True, check=True)

        print("  ✓ Test 2 passed: Modifications and additions detected")

        # =====================================================================
        # Test 3: Version bump release (with renames)
        # =====================================================================
        print("\n--- Test 3: Version Bump Release (Renames) ---")

        release3_dir = temp_dir / 'release3'
        release3_dir.mkdir()

        # Version 2.1 - files renamed from 2.0 -> 2.1
        # Use realistic content that's similar enough for git to detect renames (>50% similarity)
        invoice_content = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
            version="2.1">
  <!-- UBL Invoice Document Schema -->
  <xsd:element name="Invoice" type="InvoiceType"/>
  <xsd:complexType name="InvoiceType">
    <xsd:sequence>
      <xsd:element name="ID" type="xsd:string"/>
      <xsd:element name="IssueDate" type="xsd:date"/>
      <xsd:element name="InvoiceTypeCode" type="xsd:string"/>
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>"""

        order_content = """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            targetNamespace="urn:oasis:names:specification:ubl:schema:xsd:Order-2"
            version="2.1">
  <!-- UBL Order Document Schema -->
  <xsd:element name="Order" type="OrderType"/>
  <xsd:complexType name="OrderType">
    <xsd:sequence>
      <xsd:element name="ID" type="xsd:string"/>
      <xsd:element name="IssueDate" type="xsd:date"/>
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>"""

        release3_files = {
            'xsd/maindoc/UBL-Invoice-2.1.xsd': invoice_content,  # Rename from 2.0
            'xsd/maindoc/UBL-Order-2.1.xsd': order_content,  # Rename from 2.0
            'xsd/maindoc/UBL-CreditNote-2.1.xsd': '<CreditNote version="2.1"/>',  # Rename from 2.0
            'xsd/common/UBL-Types-2.1.xsd': '<Types version="2.1"/>',  # Rename from 2.0
            'doc/UBL-2.1.xml': '<Documentation version="2.1"/>',  # Rename from 2.0
        }

        for path, content in release3_files.items():
            file_path = release3_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        repo_files = get_repo_files(repo_root)
        zip_files = get_zip_files(release3_dir)

        release3 = Release(9, "2.1", "prd1", "2010-10-01", "http://test.com/r3.zip")
        changeset3 = compute_changeset(repo_files, zip_files, release3, release2)

        print(f"  {changeset3.summary()}")
        assert len(changeset3.renames) == 5, f"Expected 5 renames, got {len(changeset3.renames)}"
        assert len(changeset3.additions) == 0, f"Expected 0 additions, got {len(changeset3.additions)}"

        # Apply renames using git mv
        for change in changeset3.renames:
            old_abs = repo_root / change.old_path
            new_abs = repo_root / change.new_path
            new_abs.parent.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                ['git', 'mv', str(change.old_path), str(change.new_path)],
                cwd=repo_root, capture_output=True, check=True
            )
            # Update content
            src = release3_dir / change.new_path
            shutil.copy2(src, new_abs)

        subprocess.run(['git', 'add', '-A'], cwd=repo_root, capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Release 3: Version bump to 2.1'],
                      cwd=repo_root, capture_output=True, check=True)

        # Verify git detected renames (use -M flag for rename detection)
        result = subprocess.run(
            ['git', 'log', '--name-status', '-M', '-1'],
            cwd=repo_root, capture_output=True, text=True
        )
        rename_count = result.stdout.count('\nR')
        # At least 2 renames should be detected (the larger files with similar content)
        assert rename_count >= 2, f"Expected at least 2 renames in git log, got {rename_count}\n{result.stdout}"

        print("  ✓ Test 3 passed: Version bump renames detected and applied")

        # =====================================================================
        # Test 4: Deletions
        # =====================================================================
        print("\n--- Test 4: Deletions ---")

        release4_dir = temp_dir / 'release4'
        release4_dir.mkdir()

        # Remove one file
        release4_files = {
            'xsd/maindoc/UBL-Invoice-2.1.xsd': '<Invoice version="2.1"/>',
            'xsd/maindoc/UBL-Order-2.1.xsd': '<Order version="2.1"/>',
            # UBL-CreditNote-2.1.xsd removed
            'xsd/common/UBL-Types-2.1.xsd': '<Types version="2.1"/>',
            'doc/UBL-2.1.xml': '<Documentation version="2.1"/>',
        }

        for path, content in release4_files.items():
            file_path = release4_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        repo_files = get_repo_files(repo_root)
        zip_files = get_zip_files(release4_dir)

        release4 = Release(10, "2.1", "prd2", "2011-01-01", "http://test.com/r4.zip")
        changeset4 = compute_changeset(repo_files, zip_files, release4, release3)

        print(f"  {changeset4.summary()}")
        assert len(changeset4.deletions) == 1, f"Expected 1 deletion, got {len(changeset4.deletions)}"
        assert changeset4.deletions[0].old_path == Path("xsd/maindoc/UBL-CreditNote-2.1.xsd")

        print("  ✓ Test 4 passed: Deletions detected correctly")

        # =====================================================================
        # Summary
        # =====================================================================
        print("\n" + "=" * 70)
        print("Integration Test Summary")
        print("=" * 70)

        # Show git log
        result = subprocess.run(
            ['git', 'log', '--oneline'],
            cwd=repo_root, capture_output=True, text=True
        )
        print(f"Git history:\n{result.stdout}")

        print("\nAll integration tests passed!")
        return True

    except AssertionError as e:
        print(f"\n✗ ASSERTION FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    success = run_integration_test()
    sys.exit(0 if success else 1)
