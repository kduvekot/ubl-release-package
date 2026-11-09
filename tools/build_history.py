#!/usr/bin/env python3
"""
Build the UBL release history in a separate target repository.

The target repository's branch contains ONLY release commits: each commit's
tree is exactly one OASIS UBL package (plus a short README.md), authored and
committed by the OASIS UBL TC on the package's official publication date.
The tools themselves live elsewhere (the 'tools' branch) and never end up in
the target history.

Usage:
    # Build (or continue) the history in a target repository
    python3 -m tools.build_history --repo /path/to/target

    # Only up to a given release, reusing downloaded ZIPs
    python3 -m tools.build_history --repo /path/to/target --end 10 --cache /tmp/ubl-cache

    # Show what would happen
    python3 -m tools.build_history --repo /path/to/target --dry-run

The tool continues after the last release already committed in the target
(detected from the 'Stage:' line of the commit messages), so adding a new OASIS
release is: add it to release_data.py, then run this command again.

Content rules:
- A single top-level package folder (name containing "UBL") is stripped, so
  content sits at the root.
- macOS metadata (__MACOSX/, .DS_Store) is not package content and is skipped.
- Files are stored as regular (non-executable) files; the executable bits in
  some ZIPs are packaging artefacts.
- FULL releases replace the whole tree; PATCH releases (#7, #8) overlay on the
  previous release.
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from .oasis_downloader import download_release
from .release_data import RELEASES, Release

AUTHOR_NAME = "OASIS UBL TC"
AUTHOR_EMAIL = "ubl@lists.oasis-open.org"
COMMIT_TIME = "12:00:00 +0000"  # noon UTC: same calendar date in every time zone

README_NAME = "README.md"
README_TEXT = """# UBL release packages

This repository contains the release packages of the OASIS Universal Business
Language (UBL) 2.x, as published by the OASIS UBL Technical Committee at
https://docs.oasis-open.org/ubl/.

Each commit is one release package (public review drafts, committee
specifications, OASIS Standards and errata), in chronological order. The commit
date is the publication date printed in that release's specification, and the
commit message gives the stage and the source URL of the package.

The files are the package contents as published; only this README is added, and
macOS metadata files (`__MACOSX/`, `.DS_Store`) are left out.

This is not an official OASIS repository. For the authoritative packages see
https://docs.oasis-open.org/ubl/.
"""


def log(msg: str = "") -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------
# git helpers (always run against the target repository)
# --------------------------------------------------------------------------

def git(repo: Path, *args: str, env: Optional[Dict[str, str]] = None,
        capture: bool = True) -> str:
    result = subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True, text=True, env=env,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout if capture else ''


def blob_hash(data: bytes) -> str:
    """Git blob SHA-1 of file contents."""
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def committed_stages(repo: Path) -> List[str]:
    """Return the release tag names already committed in the target, oldest first."""
    try:
        out = git(repo, 'log', '--reverse', '--format=%B%x00')
    except subprocess.CalledProcessError:
        return []  # no commits yet
    tags = []
    for body in filter(str.strip, out.split('\x00')):
        m_v = re.search(r'^Release: UBL (\S+) ', body, re.M)
        m_s = re.search(r'^Stage: (\S+)', body, re.M)
        if m_v and m_s:
            release = next((r for r in RELEASES
                            if r.version == m_v.group(1) and r.stage == m_s.group(1)), None)
            tags.append(release.tag_name if release else f"{m_s.group(1)}-UBL-{m_v.group(1)}")
    return tags


# --------------------------------------------------------------------------
# package handling
# --------------------------------------------------------------------------

def is_junk(path: str) -> bool:
    parts = [p for p in path.split('/') if p]
    return any(p == '__MACOSX' or p == '.DS_Store' for p in parts)


def package_files(zip_path: Path) -> Dict[str, bytes]:
    """Read a package ZIP into {relative path: contents}, with the rules above."""
    with zipfile.ZipFile(zip_path) as zf:
        entries = [i for i in zf.infolist() if not i.is_dir() and not is_junk(i.filename)]
        names = [i.filename for i in entries]
        tops = {n.split('/', 1)[0] for n in names}
        # Strip a single top-level package folder (e.g. 'os-UBL-2.5/',
        # 'UBL-2.1-PRD1-20100925/'), but never a content folder like 'xsd/'.
        strip = ''
        if len(tops) == 1 and all('/' in n for n in names) and 'UBL' in next(iter(tops)):
            strip = next(iter(tops)) + '/'
        files = {}
        for info in entries:
            rel = info.filename[len(strip):]
            if rel in files:
                raise RuntimeError(f"Duplicate path in package: {rel}")
            files[rel] = zf.read(info)
    if README_NAME in files:
        raise RuntimeError(f"Package contains its own {README_NAME}; refusing to overwrite it")
    return files


def get_zip(release: Release, cache: Optional[Path], tmp: Path) -> Path:
    if cache:
        cached = cache / f"{release.num:02d}.zip"
        if cached.exists() and zipfile.is_zipfile(cached):
            log(f"  Using cached package: {cached}")
            return cached
        cache.mkdir(parents=True, exist_ok=True)
        return download_release(release, cached)
    return download_release(release, tmp / 'release.zip')


def clear_worktree(repo: Path) -> None:
    for item in repo.iterdir():
        if item.name == '.git':
            continue
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()


def write_files(repo: Path, files: Dict[str, bytes]) -> None:
    for rel, data in files.items():
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            dest.unlink()
        dest.write_bytes(data)
        os.chmod(dest, 0o644)


def head_tree(repo: Path) -> Dict[str, str]:
    """{path: blob hash} of the HEAD commit (empty if no commits)."""
    try:
        out = git(repo, 'ls-tree', '-r', '-z', 'HEAD')
    except subprocess.CalledProcessError:
        return {}
    tree = {}
    for entry in filter(None, out.split('\0')):
        meta, path = entry.split('\t', 1)
        mode, _type, sha = meta.split()
        tree[path] = sha
    return tree


def commit_message(release: Release) -> str:
    return (f"Release: UBL {release.version} ({release.status})\n\n"
            f"Date: {release.date}\n"
            f"Stage: {release.stage}\n"
            f"Source: {release.url}\n")


def commit_env(release: Release) -> Dict[str, str]:
    env = dict(os.environ)
    stamp = f"{release.date} {COMMIT_TIME}"
    env.update({
        'GIT_AUTHOR_NAME': AUTHOR_NAME, 'GIT_AUTHOR_EMAIL': AUTHOR_EMAIL,
        'GIT_AUTHOR_DATE': stamp,
        'GIT_COMMITTER_NAME': AUTHOR_NAME, 'GIT_COMMITTER_EMAIL': AUTHOR_EMAIL,
        'GIT_COMMITTER_DATE': stamp,
    })
    return env


def import_one(repo: Path, release: Release, cache: Optional[Path], dry_run: bool) -> None:
    log(f"\n#{release.num} {release.tag_name}  ({release.date}, {release.release_type})")
    with tempfile.TemporaryDirectory(prefix='ubl-build-') as tmp:
        zip_path = get_zip(release, cache, Path(tmp))
        files = package_files(zip_path)
    log(f"  Package files: {len(files)}")

    previous = head_tree(repo)
    if release.is_patch:
        expected = {p: s for p, s in previous.items()}
    else:
        expected = {}
    expected.update({p: blob_hash(d) for p, d in files.items()})
    expected[README_NAME] = blob_hash(README_TEXT.encode())

    if dry_run:
        added = len(set(expected) - set(previous))
        removed = len(set(previous) - set(expected))
        changed = sum(1 for p in set(expected) & set(previous) if expected[p] != previous[p])
        log(f"  [DRY RUN] would commit: +{added} -{removed} ~{changed}")
        return

    if not release.is_patch:
        clear_worktree(repo)
    write_files(repo, files)
    (repo / README_NAME).write_text(README_TEXT)
    os.chmod(repo / README_NAME, 0o644)

    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify',
        '--allow-empty', '-m', commit_message(release), env=commit_env(release))

    actual = head_tree(repo)
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    differ = sorted(p for p in set(expected) & set(actual) if expected[p] != actual[p])
    if missing or extra or differ:
        raise RuntimeError(
            f"Verification failed for {release.tag_name}: "
            f"missing={missing[:5]} extra={extra[:5]} differ={differ[:5]}")
    log(f"  ✓ Committed {git(repo, 'rev-parse', '--short', 'HEAD').strip()}, "
        f"verified {len(actual)} files against the package")


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Build the UBL release-only history in a target repository')
    parser.add_argument('--repo', required=True, type=Path,
                        help='Target git repository (its current branch receives the commits)')
    parser.add_argument('--end', type=int, default=len(RELEASES),
                        help=f'Last release number to import (default: {len(RELEASES)})')
    parser.add_argument('--cache', type=Path,
                        help='Directory to keep downloaded ZIPs (NN.zip) for reuse')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be committed without changing anything')
    args = parser.parse_args()

    repo = args.repo.resolve()
    if not (repo / '.git').exists():
        log(f"ERROR: {repo} is not a git repository (expected {repo}/.git)")
        return 1
    if git(repo, 'status', '--porcelain').strip():
        log(f"ERROR: target working tree {repo} is not clean")
        return 1

    done = committed_stages(repo)
    expected_prefix = [r.tag_name for r in RELEASES[:len(done)]]
    if done != expected_prefix:
        log("ERROR: target history does not match the release inventory:")
        log(f"  target:    {done}")
        log(f"  inventory: {expected_prefix}")
        return 1

    todo = [r for r in RELEASES[len(done):] if r.num <= args.end]
    log(f"Target: {repo}")
    log(f"Already committed: {len(done)} release(s); to import: {len(todo)}")
    for release in todo:
        try:
            import_one(repo, release, args.cache, args.dry_run)
        except Exception as e:  # stop at the first problem
            log(f"\n✗ {release.tag_name}: {e}")
            return 1
    log("\n✓ Done")
    return 0


if __name__ == '__main__':
    sys.exit(main())
