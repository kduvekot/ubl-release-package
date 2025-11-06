#!/usr/bin/env python3
"""
Validation logic for UBL release imports.

This module contains all the safety checks and guardrails to ensure releases
are imported correctly and in the right order.
"""

import sys
from typing import Optional, List
from .git_state import GitStateManager
from .release_data import Release, get_release_by_num


class ValidationError(Exception):
    """Raised when a validation check fails."""
    pass


class Validators:
    """Collection of validation checks for safe release imports."""

    @staticmethod
    def check_git_repo():
        """Ensure we're in a git repository."""
        if not GitStateManager.is_git_repo():
            raise ValidationError(
                "ERROR: Not in a git repository.\n"
                "This tool must be run from within the UBL release package repository."
            )

    @staticmethod
    def check_git_clean():
        """Ensure working directory has no uncommitted changes."""
        if not GitStateManager.is_working_directory_clean():
            raise ValidationError(
                "ERROR: Working directory is not clean.\n"
                "You have uncommitted changes. Please commit or stash them first.\n"
                "Run 'git status' to see what needs attention."
            )

    @staticmethod
    def check_branch(force: bool = False):
        """Ensure we're on the correct development branch."""
        import sys

        branch = GitStateManager.get_current_branch()
        if not branch:
            raise ValidationError("ERROR: Could not determine current branch.")

        if not branch.startswith('claude/'):
            print(f"WARNING: You are on branch '{branch}'")
            print("         Recommended to work on a branch starting with 'claude/'")

            # Skip interactive prompt if:
            # 1. Force flag is set
            # 2. stdin is not a TTY (non-interactive mode like pipes, tests)
            if force:
                print("         Continuing anyway (force mode)")
                return

            if not sys.stdin.isatty():
                print("         Continuing anyway (non-interactive mode)")
                return

            response = input("Continue anyway? [y/N]: ")
            if response.lower() != 'y':
                raise ValidationError("Aborted by user.")

    @staticmethod
    def check_sequential_order(release_num: int, force: bool = False) -> None:
        """
        Ensure release is being imported in sequential order.

        Args:
            release_num: The release number to import (1-34)
            force: If True, skip sequential check

        Raises:
            ValidationError: If release is out of order and force=False
        """
        commits = GitStateManager.get_release_commits()

        if not commits:
            # No releases imported yet
            if release_num != 1:
                if force:
                    print(f"WARNING: Starting with release #{release_num} (forced)")
                    print("         This may create an incomplete history.")
                else:
                    raise ValidationError(
                        f"ERROR: Cannot start with release #{release_num}.\n"
                        f"       No releases have been imported yet.\n"
                        f"       Expected release #1, or use --force to override."
                    )
        else:
            # Find the highest release number already imported
            imported_nums = []
            for commit in commits:
                stage = commit['stage']
                version = commit['version']
                # Try to find this release in our data
                from .release_data import RELEASES
                for rel in RELEASES:
                    if rel.stage == stage and rel.version == version:
                        imported_nums.append(rel.num)
                        break

            if imported_nums:
                max_imported = max(imported_nums)
                expected = max_imported + 1

                if release_num != expected:
                    if force:
                        print(f"WARNING: Importing release #{release_num} out of order (forced)")
                        print(f"         Last imported: #{max_imported}")
                        print(f"         Expected: #{expected}")
                    else:
                        raise ValidationError(
                            f"ERROR: Release out of order.\n"
                            f"       Last imported: #{max_imported}\n"
                            f"       Expected next: #{expected}\n"
                            f"       You requested: #{release_num}\n"
                            f"       Use --force to override (not recommended)."
                        )

    @staticmethod
    def check_patch_dependencies(release: Release) -> None:
        """
        For patch releases, ensure the base release has been imported.

        Args:
            release: The patch release to validate

        Raises:
            ValidationError: If base release is missing
        """
        if not release.is_patch:
            return  # Not a patch, no dependencies to check

        if release.base_release_num is None:
            raise ValidationError(
                f"ERROR: Patch release {release.tag_name} has no base_release_num defined.\n"
                f"       This is a bug in release_data.py"
            )

        # Get the base release
        base_release = get_release_by_num(release.base_release_num)
        if not base_release:
            raise ValidationError(
                f"ERROR: Cannot find base release #{release.base_release_num}\n"
                f"       This is a bug in release_data.py"
            )

        # Check if base release has been imported
        if not GitStateManager.has_release_been_imported(base_release.stage, base_release.version):
            raise ValidationError(
                f"ERROR: Cannot apply patch {release.tag_name}\n"
                f"       Base release {base_release.tag_name} (#{base_release.num}) has not been imported yet.\n"
                f"       Import release #{base_release.num} first."
            )

    @staticmethod
    def check_duplicate_import(release: Release, force: bool = False) -> None:
        """
        Check if this release has already been imported.

        Args:
            release: The release to check
            force: If True, allow re-import with warning

        Raises:
            ValidationError: If release already imported and force=False
        """
        if GitStateManager.has_release_been_imported(release.stage, release.version):
            if force:
                print(f"WARNING: Release {release.tag_name} already imported (re-importing anyway)")
            else:
                raise ValidationError(
                    f"ERROR: Release {release.tag_name} has already been imported.\n"
                    f"       Use --force to re-import (this will create a duplicate commit)."
                )

    @staticmethod
    def validate_all(release: Release, force: bool = False) -> None:
        """
        Run all validation checks for a release import.

        Args:
            release: The release to validate
            force: If True, some checks become warnings instead of errors

        Raises:
            ValidationError: If any critical validation fails
        """
        print(f"Validating import of release #{release.num}: {release.tag_name}...")

        # Critical checks (always enforced)
        Validators.check_git_repo()
        Validators.check_git_clean()

        # Important checks (can be overridden with --force)
        Validators.check_branch(force)
        Validators.check_sequential_order(release.num, force)
        Validators.check_duplicate_import(release, force)

        # Patch-specific checks
        if release.is_patch:
            Validators.check_patch_dependencies(release)

        print("✓ All validation checks passed")


if __name__ == '__main__':
    # Quick test when run directly
    from .release_data import get_release_by_num

    print("Testing validators...")
    print()

    # Test git repo check
    try:
        Validators.check_git_repo()
        print("✓ Git repository check passed")
    except ValidationError as e:
        print(f"✗ {e}")

    # Test git clean check
    try:
        Validators.check_git_clean()
        print("✓ Git clean check passed")
    except ValidationError as e:
        print(f"✗ {e}")

    # Test branch check
    try:
        Validators.check_branch()
        print("✓ Branch check passed")
    except ValidationError as e:
        print(f"✗ {e}")

    print()
    print("Current state:")
    print(GitStateManager.get_release_summary())
