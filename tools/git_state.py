#!/usr/bin/env python3
"""
Git-based state management for UBL release imports.

This module queries git history to determine which releases have been imported,
avoiding the need for a separate state file.
"""

import re
import subprocess
from typing import Optional, List, Dict, Tuple


class GitStateManager:
    """Query git history to track imported UBL releases."""

    # Pattern to match release commit messages
    # Example: "Release: UBL 2.0 (OASIS Standard)"
    RELEASE_PATTERN = re.compile(r'^Release: UBL ([\d.]+) \((.*?)\)$', re.MULTILINE)

    # Pattern to extract metadata from commit body
    # Example: "Stage: os" or "Date: 2006-12-18"
    STAGE_PATTERN = re.compile(r'^Stage: (.+)$', re.MULTILINE)
    DATE_PATTERN = re.compile(r'^Date: (.+)$', re.MULTILINE)
    SOURCE_PATTERN = re.compile(r'^Source: (.+)$', re.MULTILINE)

    @staticmethod
    def is_git_repo() -> bool:
        """Check if current directory is a git repository."""
        try:
            subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def get_current_branch() -> Optional[str]:
        """Get the current git branch name."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def is_working_directory_clean() -> bool:
        """Check if git working directory is clean (no uncommitted changes)."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                check=True,
                capture_output=True,
                text=True
            )
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def get_release_commits() -> List[Dict[str, str]]:
        """
        Get all release commits from git history.

        Returns:
            List of dicts with keys: hash, version, status, stage, date, source
        """
        try:
            # Get all commits with subject and body
            result = subprocess.run(
                ['git', 'log', '--all', '--format=%H%n%s%n%b%n---COMMIT-END---'],
                check=True,
                capture_output=True,
                text=True
            )

            commits = []
            commit_blocks = result.stdout.split('---COMMIT-END---')

            for block in commit_blocks:
                block = block.strip()
                if not block:
                    continue

                lines = block.split('\n', 2)
                if len(lines) < 2:
                    continue

                commit_hash = lines[0].strip()
                subject = lines[1].strip()
                body = lines[2] if len(lines) > 2 else ""

                # Check if this is a release commit
                match = GitStateManager.RELEASE_PATTERN.match(subject)
                if match:
                    version = match.group(1)
                    status = match.group(2)

                    # Extract metadata from body
                    stage_match = GitStateManager.STAGE_PATTERN.search(body)
                    date_match = GitStateManager.DATE_PATTERN.search(body)
                    source_match = GitStateManager.SOURCE_PATTERN.search(body)

                    commits.append({
                        'hash': commit_hash,
                        'version': version,
                        'status': status,
                        'stage': stage_match.group(1) if stage_match else '',
                        'date': date_match.group(1) if date_match else '',
                        'source': source_match.group(1) if source_match else ''
                    })

            return commits

        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def get_last_imported_release() -> Optional[Dict[str, str]]:
        """
        Get the most recent release commit.

        Returns:
            Dict with release info, or None if no releases imported yet
        """
        commits = GitStateManager.get_release_commits()
        if commits:
            return commits[0]  # First commit in log is most recent
        return None

    @staticmethod
    def get_imported_versions() -> List[str]:
        """Get list of all imported UBL versions (e.g., ['2.0', '2.1', '2.2'])."""
        commits = GitStateManager.get_release_commits()
        versions = []
        for commit in commits:
            version = commit['version']
            if version not in versions:
                versions.append(version)
        return sorted(versions, key=lambda v: [int(x) for x in v.split('.')])

    @staticmethod
    def has_release_been_imported(stage: str, version: str) -> bool:
        """
        Check if a specific release has been imported.

        Args:
            stage: Release stage (e.g., 'os', 'prd', 'cs01')
            version: UBL version (e.g., '2.0', '2.1')

        Returns:
            True if this release exists in git history
        """
        commits = GitStateManager.get_release_commits()
        for commit in commits:
            if commit['version'] == version and commit['stage'] == stage:
                return True
        return False

    @staticmethod
    def get_all_tags() -> List[str]:
        """Get all git tags in the repository."""
        try:
            result = subprocess.run(
                ['git', 'tag', '-l'],
                check=True,
                capture_output=True,
                text=True
            )
            tags = [t.strip() for t in result.stdout.split('\n') if t.strip()]
            return tags
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def count_release_commits() -> int:
        """Count how many release commits exist in git history."""
        return len(GitStateManager.get_release_commits())

    @staticmethod
    def get_release_summary() -> str:
        """Get a human-readable summary of imported releases."""
        commits = GitStateManager.get_release_commits()
        if not commits:
            return "No releases imported yet."

        # Group by version
        by_version = {}
        for commit in commits:
            version = commit['version']
            if version not in by_version:
                by_version[version] = []
            by_version[version].append(commit)

        lines = [f"Total releases imported: {len(commits)}"]
        lines.append("")

        for version in sorted(by_version.keys(), key=lambda v: [int(x) for x in v.split('.')]):
            releases = by_version[version]
            lines.append(f"UBL {version}: {len(releases)} release(s)")
            for rel in reversed(releases):  # Show chronologically
                lines.append(f"  - {rel['stage']:15} {rel['status']:30} ({rel['date']})")

        return '\n'.join(lines)


if __name__ == '__main__':
    # Quick test/demo when run directly
    if not GitStateManager.is_git_repo():
        print("ERROR: Not in a git repository")
        exit(1)

    print("Current branch:", GitStateManager.get_current_branch())
    print("Working directory clean:", GitStateManager.is_working_directory_clean())
    print()
    print(GitStateManager.get_release_summary())
    print()
    print("Tags:", ', '.join(GitStateManager.get_all_tags()) or 'None')
