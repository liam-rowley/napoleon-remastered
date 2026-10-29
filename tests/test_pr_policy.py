"""Host tests for tools/pr_policy.py (pure logic: no git)."""
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location('pr_policy', Path(__file__).resolve().parent.parent / 'tools' / 'pr_policy.py')
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)

ROW = {'id': 'J1', 'status': 'queued', 'brief': 'jobs/J1/brief.md'}
OTHER = {'id': 'J2', 'status': 'needs_brief'}


def files(**kw):
    return lambda p: kw.get(p)


class Policy(unittest.TestCase):
    def run_check(self, branch, changed, base_rows=None, head_rows=None, base=None, head=None):
        return pp.check(branch, changed, base_rows or {'J1': ROW, 'J2': OTHER}, head_rows or {'J1': ROW, 'J2': OTHER},
                        base or files(), head or files())

    def test_verdict_parsing(self):
        self.assertEqual(pp.verdict('# R\n\n**Verdict: merge after fixes.** The skeleton is fine.'), 'merge after fixes')
        self.assertEqual(pp.verdict('**Verdict: merge.** Looks good.'), 'merge')
        self.assertEqual(pp.verdict('Verdict: merge'), 'merge')
        self.assertEqual(pp.verdict('**Verdict: merge.**'), 'merge')
        self.assertIsNone(pp.verdict('no verdict here'))

    def test_unknown_branch_refused(self):
        errs = self.run_check('proxy/skeleton', ['proxy/a.cpp'])
        self.assertTrue(errs and 'not job/J<n>' in errs[0])

    def test_job_branch_complete(self):
        done = dict(ROW, status='done', report='jobs/J1/report.md', review='jobs/J1/review.md')
        errs = self.run_check('job/J1', ['proxy/a.cpp', 'registries/jobs.jsonl'], head_rows={'J1': done, 'J2': OTHER},
                              base=files(**{'jobs/J1/brief.md': 'b'}),
                              head=files(**{'jobs/J1/report.md': 'r', 'jobs/J1/review.md': '**Verdict: merge.**'}))
        self.assertEqual(errs, [])

    def test_job_branch_unreviewed_or_unfinished(self):
        errs = self.run_check('job/J1', ['proxy/a.cpp'], base=files(**{'jobs/J1/brief.md': 'b'}),
                              head=files(**{'jobs/J1/review.md': 'Verdict: merge after fixes'}))
        text = '\n'.join(errs)
        self.assertIn('report.md is missing', text)
        self.assertIn('"merge after fixes", not "merge"', text)
        self.assertIn('must be `done`', text)

    def test_job_branch_without_brief_on_base_and_touching_other_rows(self):
        done = dict(ROW, status='done', report='jobs/J1/report.md', review='jobs/J1/review.md')
        errs = self.run_check('job/J1', ['x'], head_rows={'J1': done, 'J2': dict(OTHER, status='queued')},
                              head=files(**{'jobs/J1/report.md': 'r', 'jobs/J1/review.md': 'Verdict: merge'}))
        text = '\n'.join(errs)
        self.assertIn('no brief on the base', text)
        self.assertIn('only its own row', text)

    def test_brief_branch(self):
        q = {'id': 'J2', 'status': 'queued', 'brief': 'jobs/J2/brief.md'}
        self.assertEqual(self.run_check('brief/J2', ['jobs/J2/brief.md', 'registries/jobs.jsonl', 'registries/jobs.md'],
                                        head_rows={'J1': ROW, 'J2': q}), [])
        errs = self.run_check('brief/J2', ['jobs/J2/brief.md', 'proxy/x.cpp'], head_rows={'J1': ROW, 'J2': q})
        self.assertTrue(any('may only add' in e for e in errs))
        errs = self.run_check('brief/J2', ['jobs/J2/brief.md'])
        self.assertTrue(any('must be `queued`' in e for e in errs))

    def test_plan_and_meta_scopes(self):
        self.assertEqual(self.run_check('plan/x', ['docs/plans/PLAN.md', 'jobs/J9/brief.md', 'CLAUDE.md']), [])
        self.assertTrue(self.run_check('plan/x', ['tools/a.py']))
        self.assertEqual(self.run_check('meta/x', ['.github/workflows/gates.yml', 'tools/pr_policy.py', 'tests/t.py', 'core',
                                                   'registries/tools.jsonl', 'docs/DECISIONS.md']), [])
        errs = self.run_check('meta/x', ['proxy/core/guard.cpp'])
        self.assertTrue(errs and 'game code goes through a job' in errs[0])


    def test_review_by_the_builder_is_refused(self):
        done = {'id': 'J1', 'status': 'done', 'brief': 'jobs/J1/brief.md', 'report': 'jobs/J1/report.md', 'review': 'jobs/J1/review.md'}
        head = files(**{'jobs/J1/report.md': 'r', 'jobs/J1/review.md': '**Verdict: merge.**'})
        base = files(**{'jobs/J1/brief.md': 'b'})
        same = lambda p: {'S1'} if p.endswith('report.md') else {'S1', 'S2'}
        e = pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base, head, same)
        self.assertTrue(any('session that also wrote the report' in x for x in e), e)
        other = lambda p: {'S1'} if p.endswith('report.md') else {'S2'}
        self.assertEqual(pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base, head, other), [])


if __name__ == '__main__':
    unittest.main()
