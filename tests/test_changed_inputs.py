"""tools/changed_inputs.py tree hashes (J54): the per-set hash CI keys its pass markers by (rule 79 for CI).

A throwaway git repo holds one file per input set, a `core` gitlink and the files that are not inputs (a report, a review, run
evidence); each test commits one change and compares the three hashes of the new commit with its parent's.
"""
import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('changed_inputs', ROOT / 'tools/changed_inputs.py')
ci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci)

FILES = {
    '.github/workflows/gates.yml': 'name: gates\n',
    'proxy/napoleon/adapter.cpp': 'int a;\n',
    'proxy/runs/2026-10-31_x/console.log': 'log\n',
    'harness/napoleon/watch.ps1': 'Write-Host 1\n',
    'viewer/core/main.cpp': 'int v;\n',
    'viewer/runs/r1.txt': 'run\n',
    'registries/engine_sites.jsonl': '{}\n',
    'jobs/J54/report.md': '# J54\n',
    'jobs/J54/review.md': '# review\n',
}
GITLINK = '1111111111111111111111111111111111111111'


def git(cwd, *args):
    env = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@t', 'GIT_COMMITTER_NAME': 't', 'GIT_COMMITTER_EMAIL': 't@t'}
    return subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', *args],
                          cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


class TreeHash(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        git(self.repo, 'init', '-q')
        for rel, text in FILES.items():
            self.write(rel, text)
        git(self.repo, 'add', '-A')
        git(self.repo, 'update-index', '--add', '--cacheinfo', f'160000,{GITLINK},core')
        git(self.repo, 'commit', '-q', '-m', 'base')

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode())

    def hashes(self, ref='HEAD', salt=ci.SALT):
        return ci.tree_hashes(ci.tree_entries(self.repo, ref), salt)

    def commit_change(self, rel, text):
        """The hashes of HEAD before and after a commit that writes rel."""
        before = self.hashes()
        self.write(rel, text)
        git(self.repo, 'add', '--', rel)   # never -A: the `core` gitlink has no checkout here and -A would stage its removal
        git(self.repo, 'commit', '-q', '-m', rel)
        return before, self.hashes()

    def test_hashes_are_full_sha256_and_differ_per_set(self):
        h = self.hashes()
        self.assertEqual(set(h), {'proxy', 'harness', 'viewer'})
        self.assertTrue(all(len(v) == 64 for v in h.values()))
        self.assertEqual(len(set(h.values())), 3)   # the set's name is hashed: equal file lists still give distinct keys

    def test_review_only_commit_keeps_every_hash(self):
        before, after = self.commit_change('jobs/J54/review.md', '# review\n\nround 2\n')
        self.assertEqual(before, after)

    def test_report_only_commit_keeps_every_hash(self):
        before, after = self.commit_change('jobs/J54/report.md', '# J54\n\nmore\n')
        self.assertEqual(before, after)

    def test_run_evidence_commit_keeps_every_hash(self):
        for rel in ('proxy/runs/2026-11-01_y/console.log', 'viewer/runs/r2.txt'):
            before, after = self.commit_change(rel, 'new run\n')
            self.assertEqual(before, after, rel)

    def test_proxy_input_changes_only_the_proxy_hash(self):
        for rel in ('proxy/napoleon/adapter.cpp', 'registries/engine_sites.jsonl'):
            before, after = self.commit_change(rel, f'changed {rel}\n')
            self.assertNotEqual(before['proxy'], after['proxy'], rel)
            self.assertEqual(before['harness'], after['harness'], rel)
            self.assertEqual(before['viewer'], after['viewer'], rel)

    def test_harness_and_viewer_inputs_change_only_their_hash(self):
        for rel, which in (('harness/napoleon/watch.ps1', 'harness'), ('viewer/core/main.cpp', 'viewer')):
            before, after = self.commit_change(rel, f'changed {rel}\n')
            self.assertEqual({k for k in before if before[k] != after[k]}, {which}, rel)

    def test_workflow_change_changes_all_three(self):
        before, after = self.commit_change('.github/workflows/gates.yml', 'name: gates\non: push\n')
        self.assertTrue(all(before[k] != after[k] for k in before))

    def test_core_pin_changes_proxy_and_harness(self):
        before = self.hashes()
        git(self.repo, 'update-index', '--cacheinfo', f'160000,{"2" * 40},core')
        git(self.repo, 'commit', '-q', '-m', 'bump core')
        after = self.hashes()
        self.assertEqual({k for k in before if before[k] != after[k]}, {'proxy', 'harness'})

    def test_mode_change_changes_the_hash(self):
        before = self.hashes()
        git(self.repo, 'update-index', '--chmod=+x', 'proxy/napoleon/adapter.cpp')
        git(self.repo, 'commit', '-q', '-m', 'chmod')
        self.assertNotEqual(before['proxy'], self.hashes()['proxy'])

    def test_salt_changes_every_hash(self):
        a, b = self.hashes(salt='1'), self.hashes(salt='2')
        self.assertTrue(all(a[k] != b[k] for k in a))

    def test_unreadable_tree_gives_empty_hashes(self):
        self.assertIsNone(ci.tree_entries(self.repo, 'no-such-ref'))
        self.assertEqual(ci.tree_hashes(None), {'proxy': '', 'harness': '', 'viewer': ''})
        self.assertIsNone(ci.tree_entries(self.repo, 'HEAD', git=lambda *a: (127, [])))   # git cannot start

    def test_main_prints_the_tree_lines(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            ci.main(['--base', ''])
        keys = [line.split('=', 1)[0] for line in out.getvalue().splitlines()]
        self.assertEqual(keys, ['proxy', 'harness', 'viewer', 'proxy_tree', 'harness_tree', 'viewer_tree', 'tree_salt'])


if __name__ == '__main__':
    unittest.main()
