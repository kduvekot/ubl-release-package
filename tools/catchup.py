#!/usr/bin/env python3
"""
UBL Release Catchup Tool

This script imports all UBL releases in chronological order, creating a complete
git history from UBL 2.0 through 2.5.
"""

import argparse
import sys
from typing import List

from .release_data import RELEASES, get_total_count
from .import_release import ReleaseImporter
from .git_state import GitStateManager


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Import all UBL releases in chronological order',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool will import all 34 UBL releases from version 2.0 through 2.5,
creating a complete git history.

Examples:
  # Import all releases
  python -m tools.catchup

  # Dry run (validate all releases without importing)
  python -m tools.catchup --dry-run

  # Start from release #10 (resume after failure)
  python -m tools.catchup --start-from 10

  # Import only up to release #5
  python -m tools.catchup --end-at 5

  # Import a range
  python -m tools.catchup --start-from 1 --end-at 10
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate all releases without making changes'
    )
    parser.add_argument(
        '--start-from',
        type=int,
        metavar='N',
        help='Start from release number N (useful for resuming)'
    )
    parser.add_argument(
        '--end-at',
        type=int,
        metavar='N',
        help='Stop after importing release number N'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force import even if out of order (use with caution)'
    )

    args = parser.parse_args()

    # Determine range
    start = args.start_from if args.start_from else 1
    end = args.end_at if args.end_at else get_total_count()

    if start < 1 or start > get_total_count():
        print(f"ERROR: --start-from must be between 1 and {get_total_count()}", file=sys.stderr)
        sys.exit(1)

    if end < 1 or end > get_total_count():
        print(f"ERROR: --end-at must be between 1 and {get_total_count()}", file=sys.stderr)
        sys.exit(1)

    if start > end:
        print(f"ERROR: --start-from ({start}) must be <= --end-at ({end})", file=sys.stderr)
        sys.exit(1)

    # Show what we're about to do
    print(f"UBL Release Catchup Tool")
    print(f"{'='*70}")
    print(f"Total releases: {get_total_count()}")
    print(f"Import range: #{start} to #{end} ({end - start + 1} releases)")
    if args.dry_run:
        print(f"Mode: DRY RUN (no changes will be made)")
    else:
        print(f"Mode: LIVE (will create commits and tags)")
    print(f"{'='*70}")
    print()

    # Show current state
    if not args.dry_run:
        print("Current repository state:")
        print(GitStateManager.get_release_summary())
        print()

    # Confirm if not dry run
    if not args.dry_run and not args.force:
        response = input("Proceed with import? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted by user.")
            sys.exit(0)
        print()

    # Import releases
    releases_to_import = [r for r in RELEASES if start <= r.num <= end]
    success_count = 0
    failure_count = 0

    for i, release in enumerate(releases_to_import, 1):
        print(f"\n{'='*70}")
        print(f"Progress: {i}/{len(releases_to_import)}")
        print(f"{'='*70}")

        importer = ReleaseImporter(release, dry_run=args.dry_run, force=args.force)
        success = importer.run()

        if success:
            success_count += 1
        else:
            failure_count += 1
            print(f"\n✗ Failed to import release #{release.num}")

            if not args.force:
                print(f"\nStopping after failure. To resume:")
                print(f"  python -m tools.catchup --start-from {release.num}")
                break

    # Summary
    print(f"\n{'='*70}")
    print(f"Import Complete")
    print(f"{'='*70}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"{'='*70}")

    if not args.dry_run and success_count > 0:
        print()
        print("Updated repository state:")
        print(GitStateManager.get_release_summary())

    sys.exit(0 if failure_count == 0 else 1)


if __name__ == '__main__':
    main()
