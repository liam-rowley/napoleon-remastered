"""Unit tests for tools/ci_notify.py: the failed jobs it names, the class hints and one comment per run attempt (J42)."""
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('ci_notify', ROOT / 'tools/ci_notify.py')
cn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cn)

JOBS = {'jobs': [
    {'name': 'changes', 'conclusion': 'success', 'steps': []},
    {'name': 'gates', 'conclusion': 'success', 'steps': []},
    {'name': 'proxy', 'conclusion': 'failure', 'steps': [{'name': 'Run proxy/tools/build.sh all', 'conclusion': 'success'},
                                                          {'name': 'smoke test the DLL under wine', 'conclusion': 'failure'}]},
    {'name': 'harness-windows', 'conclusion': 'skipped', 'steps': []}]}


class FakeGh:
    def __init__(self, prs=({'number': 5},), seen=''):
        self.prs, self.seen, self.calls = list(prs), seen, []

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        a = argv[1:]
        if a[:2] == ['pr', 'list']:
            out = json.dumps(self.prs)
        elif a[0] == 'api' and a[1].endswith('/jobs'):
            out = json.dumps(JOBS)
        elif a[0] == 'api' and '/comments' in a[-3]:
            out = self.seen
        elif a[0] == 'api':
            out = json.dumps({'u': 'https://github.com/o/r/actions/runs/42'})
        else:
            out = ''
        return subprocess.CompletedProcess(argv, 0, out, '')

    def comments(self):
        return [c for c in self.calls if c[1:3] == ['pr', 'comment']]


class Notify(unittest.TestCase):
    ARGS = ['--run-id', '42', '--attempt', '1', '--branch', 'job/J9', '--repo', 'o/r']

    def test_failed_names_each_failed_job_and_its_first_failed_step(self):
        self.assertEqual(cn.failed(JOBS['jobs']), [('proxy', 'smoke test the DLL under wine')])

    def test_comment_names_job_step_url_and_class(self):
        gh = FakeGh()
        self.assertEqual(cn.main(self.ARGS, run=gh), 0)
        [c] = gh.comments()
        body = c[c.index('--body') + 1]
        for s in ('`proxy`', 'smoke test the DLL under wine', 'https://github.com/o/r/actions/runs/42', 'CI-only test',
                  '--docker smoke', '<!-- ci_notify run 42 attempt 1 -->', 'docs/CI_FAILURES.md'):
            self.assertIn(s, body)
        self.assertEqual(c[c.index('comment') + 1], '5')

    def test_once_per_run_attempt(self):
        gh = FakeGh(seen='earlier\n<!-- ci_notify run 42 attempt 1 -->\n')
        self.assertEqual(cn.main(self.ARGS, run=gh), 0)
        self.assertEqual(gh.comments(), [])

    def test_no_open_pull_request_no_comment(self):
        gh = FakeGh(prs=[])
        self.assertEqual(cn.main(self.ARGS, run=gh), 0)
        self.assertEqual(len(gh.calls), 1)

    def test_class_hints(self):
        self.assertIn('wsc.py gates', cn.class_hint('gates', ''))
        self.assertIn('pr_policy.py', cn.class_hint('policy', ''))
        self.assertIn('--docker all', cn.class_hint('proxy', 'Run proxy/tools/build.sh all'))
        self.assertIn('repeat=20', cn.class_hint('harness-windows', 'harness host tests'))
        self.assertIn('branch', cn.message([('policy', 'x')], 1, 1, 'u', 'brief/J4'))
        self.assertIn('brief/J4 --base', cn.message([('policy', 'x')], 1, 1, 'u', 'brief/J4'))


if __name__ == '__main__':
    unittest.main()
