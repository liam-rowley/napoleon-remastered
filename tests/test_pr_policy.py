"""Host tests for tools/pr_policy.py: the pure logic, then main() on a fixture git repository (the Claude-Session trailer check)."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

POLICY = Path(__file__).resolve().parent.parent / 'tools' / 'pr_policy.py'
_spec = importlib.util.spec_from_file_location('pr_policy', POLICY)
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
        same = lambda p: [{'S1'}] if p.endswith('report.md') else [{'S2'}, {'S1'}]
        e = pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base, head, same)
        self.assertTrue(any('session that also wrote the report' in x for x in e), e)
        other = lambda p: [{'S1'}] if p.endswith('report.md') else [{'S2'}]
        self.assertEqual(pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base, head, other), [])

    def test_a_commit_without_a_trailer_fails_closed(self):
        done = {'id': 'J1', 'status': 'done', 'brief': 'jobs/J1/brief.md', 'report': 'jobs/J1/report.md', 'review': 'jobs/J1/review.md'}
        head = files(**{'jobs/J1/report.md': 'r', 'jobs/J1/review.md': '**Verdict: merge.**'})
        base = files(**{'jobs/J1/brief.md': 'b'})
        for s in (lambda p: [set()], lambda p: [{'S1'}] if p.endswith('report.md') else [{'S2'}, set()]):
            e = pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base, head, s)
            self.assertTrue(any('no `Claude-Session:` trailer' in x for x in e), e)


class PolicyOnGit(unittest.TestCase):
    """main() on a real fixture repository: job branches whose report and review carry no trailer, or distinct ones."""

    def git(self, *a):
        subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *a], cwd=self.d, check=True, capture_output=True, text=True)

    def commit(self, path, text, trailer=None):
        p = Path(self.d) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8', newline='\n')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', f'write {path}', *(['--trailer', f'Claude-Session: {trailer}'] if trailer else []))

    def branch(self, report_session, review_session):
        self.git('checkout', '-q', '-B', 'job/J1', 'main')
        self.commit('jobs/J1/report.md', 'report', report_session)
        done = dict(ROW, status='done', report='jobs/J1/report.md', review='jobs/J1/review.md')
        self.commit('registries/jobs.jsonl', json.dumps(done) + '\n' + json.dumps(OTHER) + '\n', review_session)
        self.commit('jobs/J1/review.md', '**Verdict: merge.**', review_session)
        return subprocess.run([sys.executable, str(POLICY), '--branch', 'job/J1', '--base', 'main'], cwd=self.d,
                              capture_output=True, text=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid')
        self.git('config', 'user.name', 'test')
        self.commit('jobs/J1/brief.md', 'brief')
        self.commit('registries/jobs.jsonl', json.dumps(ROW) + '\n' + json.dumps(OTHER) + '\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_trailers_refused_distinct_trailers_pass(self):
        r = self.branch(None, None)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('report.md has 1 commit(s) with no `Claude-Session:` trailer', r.stderr)
        self.assertIn('review.md has 1 commit(s)', r.stderr)
        r = self.branch('builder-session', 'reviewer-session')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.branch('same-session', 'same-session')
        self.assertEqual(r.returncode, 1)
        self.assertIn('also wrote the report (same-session)', r.stderr)


    def test_decisions_are_append_only(self):
        base = '| # | Date |\n|---|---|\n| D1 | 2026-10-28 | Liam | A. | yes |\n| D2 | 2026-10-28 | Liam | B. | no |\n'
        good = base + '| D3 | 2026-10-29 | agent (J5) | C. | yes |\n'
        self.assertEqual(pp.decisions_problems(base, good), [])
        self.assertIn('append only', pp.decisions_problems(base, base.replace('B.', 'B changed.'))[0])
        self.assertIn('should be D3', pp.decisions_problems(base, base + '| D4 | 2026-10-29 | x | C. | yes |\n')[0])
        self.assertIn('is not', pp.decisions_problems(base, base + '| D3 | today | x | C. | maybe |\n')[0])
        e = pp.check('plan/x', ['docs/DECISIONS.md'], {'J1': ROW}, {'J1': ROW}, files(**{'docs/DECISIONS.md': base}),
                     files(**{'docs/DECISIONS.md': base.replace('B.', 'Bee.')}))
        self.assertTrue(any('append only' in x for x in e), e)


class Rule79(unittest.TestCase):
    """J4 rule 79: a job branch that changes proxy/ or harness/ needs 20 consecutive acceptance passes on its final build."""
    @staticmethod
    def led(n, build='abc', watcher='1.0.1', fail_at=None):
        return '\n'.join(json.dumps({'pass': i, 'build_id': build, 'watcher': watcher, 'result': 'fail' if i == fail_at else 'pass'}) for i in range(1, n + 1)) + '\n'

    def acc(self, ledger, active=True):
        return {'active': active, 'ledger': ledger, 'build_id': 'abc', 'watcher': '1.0.1'}

    def test_failing_fixture_a_code_change_without_20_passes_is_refused(self):
        errs = pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(19)))
        self.assertEqual(len(errs), 1)
        self.assertIn('19 consecutive', errs[0])

    def test_20_passes_on_this_build_pass(self):
        self.assertEqual(pp.acceptance_problems(['harness/core/job.sh'], self.acc(self.led(20))), [])

    def test_a_fail_resets_the_count(self):
        self.assertTrue(pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(25, fail_at=10))))   # 15 after the fail

    def test_another_build_or_watcher_does_not_count(self):
        self.assertTrue(pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20, build='old'))))
        self.assertTrue(pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20, watcher='0.9'))))

    def test_runs_docs_and_non_code_changes_are_exempt(self):
        for p in ('proxy/runs/x/README.md', 'harness/runs/y/raw/a.log', 'proxy/README.md', 'harness/acceptance/ledger.jsonl', 'docs/a.md', 'registries/x.jsonl'):
            self.assertEqual(pp.acceptance_problems([p], self.acc('')), [], p)

    def test_inactive_until_the_ledger_is_on_the_base(self):
        self.assertEqual(pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc('', active=False)), [])
        self.assertEqual(pp.acceptance_problems(['proxy/core/dev.cpp'], None), [])

    def test_check_wires_it_into_job_branches(self):
        errs = pp.check('job/J1', ['proxy/core/dev.cpp'], {'J1': ROW}, {'J1': ROW}, files(), files(), None, self.acc(self.led(3)))
        self.assertTrue(any('rule 79' in e for e in errs))


if __name__ == '__main__':
    unittest.main()
