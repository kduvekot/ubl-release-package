#!/usr/bin/env python3
"""
Tests for tools/build_history.py, using small mock packages (no downloads).

Run from the repository root:
    python3 -m unittest tools.tests.test_build_history -v
"""

import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from tools import build_history
from tools.release_data import Release, TYPE_PATCH


def make_zip(path: Path, files: dict, top: str = '') -> None:
    with zipfile.ZipFile(path, 'w') as zf:
        for name, data in files.items():
            zf.writestr(top + name, data)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


class BuildHistoryTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / 'target'
        self.cache = base / 'cache'
        self.cache.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        self.releases = [
            Release(1, "9.0", "csd01", "2001-02-03", "https://example.invalid/1.zip"),
            Release(2, "9.0", "os", "2002-03-04", "https://example.invalid/2.zip"),
            Release(3, "9.0", "errata", "2003-04-05", "https://example.invalid/3.zip",
                    TYPE_PATCH, 2),
        ]
        # 1: nested in a top-level folder, with macOS junk
        make_zip(self.cache / '01.zip', {'xsd/a.xsd': 'A1', 'doc/x.txt': 'X',
                                         '.DS_Store': 'junk'}, top='csd01-UBL-9.0/')
        with zipfile.ZipFile(self.cache / '01.zip', 'a') as zf:
            zf.writestr('__MACOSX/._csd01-UBL-9.0', 'junk')
        # 2: flat ZIP (no top-level folder); doc/x.txt removed, a.xsd changed
        make_zip(self.cache / '02.zip', {'xsd/a.xsd': 'A2', 'lib/b.zip': 'B'})
        # 3: patch: changes a.xsd only
        make_zip(self.cache / '03.zip', {'xsd/a.xsd': 'A3'})

    def tearDown(self):
        self.tmp.cleanup()

    def run_build(self, *extra: str) -> int:
        argv = ['build_history', '--repo', str(self.repo), '--cache', str(self.cache), *extra]
        with mock.patch.object(build_history, 'RELEASES', self.releases), \
                mock.patch('sys.argv', argv):
            return build_history.main()

    def test_full_history(self):
        self.assertEqual(self.run_build(), 0)
        log = git(self.repo, 'log', '--reverse', '--format=%an|%ae|%cn|%ce|%ad|%cd|%s',
                  '--date=format:%Y-%m-%d %H:%M')
        lines = log.strip().split('\n')
        self.assertEqual(len(lines), 3)
        for line, date in zip(lines, ['2001-02-03', '2002-03-04', '2003-04-05']):
            an, ae, cn, ce, ad, cd, subject = line.split('|')
            self.assertEqual((an, cn), (build_history.AUTHOR_NAME,) * 2)
            self.assertEqual((ae, ce), (build_history.AUTHOR_EMAIL,) * 2)
            self.assertTrue(ad.startswith(date) and cd.startswith(date))
            self.assertTrue(subject.startswith('Release: UBL 9.0 ('))

        # junk skipped, top folder stripped, README added
        first = git(self.repo, 'ls-tree', '-r', '--name-only', 'HEAD~2').split()
        self.assertEqual(sorted(first), ['README.md', 'doc/x.txt', 'xsd/a.xsd'])
        # full release replaces the tree; lib/ and .zip content are kept
        second = git(self.repo, 'ls-tree', '-r', '--name-only', 'HEAD~1').split()
        self.assertEqual(sorted(second), ['README.md', 'lib/b.zip', 'xsd/a.xsd'])
        # patch overlays: lib/b.zip kept, a.xsd updated
        self.assertEqual(git(self.repo, 'show', 'HEAD:xsd/a.xsd'), 'A3')
        self.assertEqual(git(self.repo, 'show', 'HEAD:lib/b.zip'), 'B')
        # no signature
        self.assertNotIn('gpgsig', git(self.repo, 'cat-file', '-p', 'HEAD'))

    def test_resume_and_noop(self):
        self.assertEqual(self.run_build('--end', '1'), 0)
        self.assertEqual(git(self.repo, 'rev-list', '--count', 'HEAD').strip(), '1')
        self.assertEqual(self.run_build(), 0)
        self.assertEqual(git(self.repo, 'rev-list', '--count', 'HEAD').strip(), '3')
        self.assertEqual(self.run_build(), 0)  # nothing left to do
        self.assertEqual(git(self.repo, 'rev-list', '--count', 'HEAD').strip(), '3')

    def test_dirty_target_refused(self):
        (self.repo / 'stray.txt').write_text('x')
        self.assertEqual(self.run_build(), 1)

    def test_mismatched_history_refused(self):
        self.assertEqual(self.run_build('--end', '1'), 0)
        self.releases[0] = Release(1, "9.0", "csd02", "2001-02-03",
                                   "https://example.invalid/1.zip")
        self.assertEqual(self.run_build(), 1)


if __name__ == '__main__':
    unittest.main()
