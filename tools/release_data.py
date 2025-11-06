#!/usr/bin/env python3
"""
Complete UBL release inventory data.

This module contains hardcoded information about all 37 UBL releases to be imported,
based on the official OASIS documentation.
"""

from typing import List, Dict, Optional


# Release type constants
TYPE_FULL = "FULL"
TYPE_PATCH = "PATCH"

# Stage descriptions mapping
STAGE_DESCRIPTIONS = {
    'cd': 'Committee Draft',
    'prd': 'Public Review Draft',
    'prd2': 'Public Review Draft 2',
    'prd3': 'Public Review Draft 3',
    'prd3r1': 'Public Review Draft 3 Revision 1',
    'cs': 'Committee Specification',
    'os': 'OASIS Standard',
    'errata': 'Errata Draft',
    'os-update': 'OASIS Standard Update',
    'prd1': 'Public Review Draft 1',
    'csprd01': 'Committee Specification Public Review Draft 01',
    'csprd02': 'Committee Specification Public Review Draft 02',
    'csprd03': 'Committee Specification Public Review Draft 03',
    'csd03': 'Committee Specification Draft 03',
    'csd04': 'Committee Specification Draft 04',
    'csd4': 'Committee Specification Draft 4',
    'cs01': 'Committee Specification 01',
    'cs02': 'Committee Specification 02',
    'cs1': 'Committee Specification 1',
    'cos1': 'Committee OASIS Specification 1',
    'cos01': 'Committee OASIS Specification 01',
    'csd01': 'Committee Specification Draft 01',
    'csd02': 'Committee Specification Draft 02',
}


class Release:
    """Represents a single UBL release."""

    def __init__(self, num: int, version: str, stage: str, date: str,
                 url: str, release_type: str = TYPE_FULL,
                 base_release_num: Optional[int] = None):
        self.num = num
        self.version = version
        self.stage = stage
        self.date = date
        self.url = url
        self.release_type = release_type
        self.base_release_num = base_release_num

    @property
    def status(self) -> str:
        """Get human-readable status description."""
        return STAGE_DESCRIPTIONS.get(self.stage, self.stage.upper())

    @property
    def is_patch(self) -> bool:
        """Check if this is a patch/overlay release."""
        return self.release_type == TYPE_PATCH

    @property
    def is_oasis_standard(self) -> bool:
        """Check if this is an official OASIS Standard."""
        return self.stage == 'os'

    @property
    def tag_name(self) -> str:
        """Get the git tag name for this release."""
        # For patches, use descriptive names
        if 'errata' in self.stage:
            return f"errata-UBL-{self.version}"
        if 'update' in self.stage:
            return f"os-UBL-{self.version}-update"

        # Standard format: {stage}-UBL-{version}
        return f"{self.stage}-UBL-{self.version}"

    @property
    def version_tag(self) -> Optional[str]:
        """Get version tag if this is an OASIS Standard (e.g., 'v2.0')."""
        if self.is_oasis_standard:
            return f"v{self.version}"
        return None

    def __repr__(self):
        return f"Release({self.num}, {self.version}, {self.stage}, {self.date})"


# Complete inventory of all 37 UBL releases
# Note: We're importing from UBL 2.0 onwards (skipping 1.0 series per project scope)
RELEASES: List[Release] = [
    # UBL 2.0 Series (2006-2008)
    Release(1, "2.0", "prd", "2006-01-20",
            "https://docs.oasis-open.org/ubl/prd-UBL-2.0.zip"),
    Release(2, "2.0", "prd2", "2006-07-28",
            "https://docs.oasis-open.org/ubl/prd2-UBL-2.0.zip"),
    Release(3, "2.0", "prd3", "2006-09-21",
            "https://docs.oasis-open.org/ubl/prd3-UBL-2.0.zip"),
    Release(4, "2.0", "prd3r1", "2006-10-05",
            "https://docs.oasis-open.org/ubl/prd3r1-UBL-2.0.zip"),
    Release(5, "2.0", "cs", "2006-10-12",
            "https://docs.oasis-open.org/ubl/cs-UBL-2.0.zip"),
    Release(6, "2.0", "os", "2006-12-18",
            "https://docs.oasis-open.org/ubl/os-UBL-2.0.zip"),
    Release(7, "2.0", "errata", "2008-04-23",
            "https://docs.oasis-open.org/ubl/errata-UBL-2.0.zip",
            TYPE_PATCH, 6),  # Patch on #6 (os-UBL-2.0)
    Release(8, "2.0", "os-update", "2008-05-29",
            "https://docs.oasis-open.org/ubl/os-UBL-2.0-update-delta.zip",
            TYPE_PATCH, 7),  # Patch on #7 (errata-UBL-2.0)

    # UBL 2.1 Series (2010-2013)
    Release(9, "2.1", "prd1", "2010-10-26",
            "https://docs.oasis-open.org/ubl/prd1-UBL-2.1/UBL-2.1-PRD1-20100925.zip"),
    Release(10, "2.1", "prd2", "2011-08-25",
            "https://docs.oasis-open.org/ubl/prd2-UBL-2.1/UBL-2.1-PRD2-2011-05-30.zip"),
    Release(11, "2.1", "prd3", "2013-02-23",
            "https://docs.oasis-open.org/ubl/prd3-UBL-2.1/UBL-2.1-PRD3-2013-02-23.zip"),
    Release(12, "2.1", "prd4", "2013-05-14",
            "https://docs.oasis-open.org/ubl/prd4-UBL-2.1/prd4-UBL-2.1.zip"),
    Release(13, "2.1", "csd4", "2013-05-14",
            "https://docs.oasis-open.org/ubl/csd4-UBL-2.1/csd4-UBL-2.1.zip"),
    Release(14, "2.1", "cs1", "2013-06-29",
            "https://docs.oasis-open.org/ubl/cs1-UBL-2.1/cs1-UBL-2.1.zip"),
    Release(15, "2.1", "cos1", "2013-07-15",
            "https://docs.oasis-open.org/ubl/cos1-UBL-2.1/cos1-UBL-2.1.zip"),
    Release(16, "2.1", "os", "2013-11-04",
            "https://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.zip"),

    # UBL 2.2 Series (2016-2018)
    Release(17, "2.2", "csprd01", "2016-12-21",
            "https://docs.oasis-open.org/ubl/csprd01-UBL-2.2/UBL-2.2.zip"),
    Release(18, "2.2", "csprd02", "2017-11-01",
            "https://docs.oasis-open.org/ubl/csprd02-UBL-2.2/UBL-2.2.zip"),
    Release(19, "2.2", "csprd03", "2018-02-21",
            "https://docs.oasis-open.org/ubl/csprd03-UBL-2.2/UBL-2.2.zip"),
    Release(20, "2.2", "cs01", "2018-03-22",
            "https://docs.oasis-open.org/ubl/cs01-UBL-2.2/UBL-2.2.zip"),
    Release(21, "2.2", "cos01", "2018-04-22",
            "https://docs.oasis-open.org/ubl/cos01-UBL-2.2/UBL-2.2.zip"),
    Release(22, "2.2", "os", "2018-07-09",
            "https://docs.oasis-open.org/ubl/os-UBL-2.2/UBL-2.2.zip"),

    # UBL 2.3 Series (2020-2021)
    Release(23, "2.3", "csprd02", "2020-01-29",
            "https://docs.oasis-open.org/ubl/csprd02-UBL-2.3/UBL-2.3.zip"),
    Release(24, "2.3", "csprd01", "2020-01-30",
            "https://docs.oasis-open.org/ubl/csprd01-UBL-2.3/UBL-2.3.zip"),
    Release(25, "2.3", "csd03", "2020-07-29",
            "https://docs.oasis-open.org/ubl/csd03-UBL-2.3/UBL-2.3.zip"),
    Release(26, "2.3", "csd04", "2020-11-25",
            "https://docs.oasis-open.org/ubl/csd04-UBL-2.3/UBL-2.3.zip"),
    Release(27, "2.3", "cs01", "2021-01-19",
            "https://docs.oasis-open.org/ubl/cs01-UBL-2.3/UBL-2.3.zip"),
    Release(28, "2.3", "cs02", "2021-05-25",
            "https://docs.oasis-open.org/ubl/cs02-UBL-2.3/UBL-2.3.zip"),
    Release(29, "2.3", "os", "2021-06-15",
            "https://docs.oasis-open.org/ubl/os-UBL-2.3/UBL-2.3.zip"),

    # UBL 2.4 Series (2023-2024)
    Release(30, "2.4", "csd01", "2023-02-08",
            "https://docs.oasis-open.org/ubl/csd01-UBL-2.4/UBL-2.4.zip"),
    Release(31, "2.4", "csd02", "2023-07-26",
            "https://docs.oasis-open.org/ubl/csd02-UBL-2.4/UBL-2.4.zip"),
    Release(32, "2.4", "cs01", "2023-10-17",
            "https://docs.oasis-open.org/ubl/cs01-UBL-2.4/UBL-2.4.zip"),
    Release(33, "2.4", "os", "2024-06-20",
            "https://docs.oasis-open.org/ubl/os-UBL-2.4/UBL-2.4.zip"),

    # UBL 2.5 Series (Draft - 2025)
    Release(34, "2.5", "csd01", "2025-08-28",
            "https://docs.oasis-open.org/ubl/csd01-UBL-2.5/UBL-2.5.zip"),
]


def get_release_by_num(num: int) -> Optional[Release]:
    """Get release by its sequence number (1-34)."""
    for release in RELEASES:
        if release.num == num:
            return release
    return None


def get_release_by_stage_version(stage: str, version: str) -> Optional[Release]:
    """Get release by stage and version."""
    for release in RELEASES:
        if release.stage == stage and release.version == version:
            return release
    return None


def get_releases_for_version(version: str) -> List[Release]:
    """Get all releases for a specific UBL version."""
    return [r for r in RELEASES if r.version == version]


def get_oasis_standards() -> List[Release]:
    """Get only the official OASIS Standard releases."""
    return [r for r in RELEASES if r.is_oasis_standard]


def get_patch_releases() -> List[Release]:
    """Get only patch/overlay releases."""
    return [r for r in RELEASES if r.is_patch]


def get_total_count() -> int:
    """Get total number of releases to import."""
    return len(RELEASES)


if __name__ == '__main__':
    # Quick test/demo when run directly
    print(f"Total releases: {get_total_count()}")
    print(f"OASIS Standards: {len(get_oasis_standards())}")
    print(f"Patch releases: {len(get_patch_releases())}")
    print()

    print("OASIS Standards:")
    for rel in get_oasis_standards():
        print(f"  - UBL {rel.version} ({rel.date}) - {rel.tag_name}")

    print()
    print("Patch releases:")
    for rel in get_patch_releases():
        print(f"  - {rel.tag_name} (applies to #{rel.base_release_num})")
