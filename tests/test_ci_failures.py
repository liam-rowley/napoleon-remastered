"""Unit tests for tools/ci_failures.py: the rendered table carries the flaky evidence (same commit passed elsewhere) and a class per row (J42 review)."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('ci_failures', ROOT / 'tools/ci_failures.py')
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)


def row(**kw):
    r = {'run': 40898971722, 'attempt': 1, 'event': 'push', 'branch': 'job/J9', 'sha': 'abcdef12', 'created': '2026-10-29T10:00:00Z',
         'run_conclusion': 'failure', 'job': 'harness-windows', 'step': 'harness host tests',
         'error': 'FAILED: auto-restore: lock expiry', 'passed_elsewhere': True}
    r.update(kw)
    return r


class Render(unittest.TestCase):
    def test_every_row_says_whether_the_same_commit_passed_elsewhere(self):
        text = cf.render([row(), row(run=40931548409, job='gates', step='x', error='jobs check: 1 problem', passed_elsewhere=False)],
                         '2026-10-29T00:00:00Z', '2026-10-29T22:20:00Z')
        head = next(ln for ln in text.splitlines() if ln.startswith('| run |'))
        cols = [c.strip() for c in head.strip('|').split('|')]
        self.assertIn('same commit passed elsewhere', cols)
        lines = [ln for ln in text.splitlines() if ln.startswith('| 40')]
        self.assertEqual(len(lines), 2)
        i = cols.index('same commit passed elsewhere')
        cells = [[c.strip() for c in ln.strip('|').split('|')][i] for ln in lines]
        self.assertEqual(cells, ['yes', 'no'])
        self.assertIn('| flaky |', lines[0])
        self.assertIn('| branch bug |', lines[1])

    def test_an_unclassed_row_is_reported(self):
        self.assertEqual(cf.classify(row(run=1))[0], 'unclassed')
        self.assertEqual(cf.classify(row())[0], cf.FLAKY)



class ListRuns(unittest.TestCase):
    def test_runs_come_from_the_dated_api_filter_paginated_not_the_newest_n(self):
        calls = []

        def gh(*args):
            calls.append(args)
            return ('[{"workflow_runs": [{"id": 1, "event": "push", "head_branch": "job/J9", "head_sha": "abc", "conclusion": "failure", '
                    '"created_at": "2026-10-29T10:00:00Z", "run_attempt": 2}]}, {"workflow_runs": []}]')
        runs = cf.list_runs('2026-10-29T00:00:00Z', '2026-10-29T22:20:00Z', gh=gh)
        self.assertEqual(runs, [{'databaseId': 1, 'event': 'push', 'headBranch': 'job/J9', 'headSha': 'abc', 'conclusion': 'failure',
                                 'createdAt': '2026-10-29T10:00:00Z', 'attempt': 2}])
        [(a, *rest)] = calls
        self.assertEqual(a, 'api')
        self.assertIn('--paginate', rest)
        self.assertIn('created=2026-10-29T00:00:00Z..2026-10-29T22:20:00Z', rest[-1])
        self.assertIn('per_page=100', rest[-1])


if __name__ == '__main__':
    unittest.main()
