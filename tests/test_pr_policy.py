"""Host tests for tools/pr_policy.py: the pure logic, then main() on a fixture git repository (the Claude-Session trailer check)."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / 'tools' / 'pr_policy.py'
_spec = importlib.util.spec_from_file_location('pr_policy', POLICY)
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)

ROW = {'id': 'J1', 'status': 'queued', 'brief': 'jobs/J1/brief.md'}
OTHER = {'id': 'J2', 'status': 'needs_brief'}


def files(**kw):
    return lambda p: kw.get(p)


def pp_rows_at(cwd, ref):
    """pr_policy.rows_at runs git in the current folder (as CI does, from the repo root)."""
    import os
    old = os.getcwd()
    os.chdir(cwd)
    try:
        return pp.rows_at(ref)
    finally:
        os.chdir(old)


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
        errs = self.run_check('job/J1', ['proxy/a.cpp', 'registries/jobs/J1.json'], head_rows={'J1': done, 'J2': OTHER},
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
        self.assertEqual(self.run_check('brief/J2', ['jobs/J2/brief.md', 'registries/jobs/J2.json'], head_rows={'J1': ROW, 'J2': q}), [])
        for other in ('registries/jobs/J3.json', 'registries/jobs.jsonl', 'registries/tools/wsc.jobs.json'):   # J55: its own row file only
            errs = self.run_check('brief/J2', ['jobs/J2/brief.md', 'registries/jobs/J2.json', other], head_rows={'J1': ROW, 'J2': q})
            self.assertTrue(any('may only add' in e and other in e for e in errs), other)
        errs = self.run_check('brief/J2', ['jobs/J2/brief.md', 'proxy/x.cpp'], head_rows={'J1': ROW, 'J2': q})
        self.assertTrue(any('may only add' in e for e in errs))
        errs = self.run_check('brief/J2', ['jobs/J2/brief.md'])
        self.assertTrue(any('must be `queued`' in e for e in errs))

    def test_plan_and_meta_scopes(self):
        self.assertEqual(self.run_check('plan/x', ['docs/plans/PLAN.md', 'jobs/J9/brief.md', 'registries/jobs/J9.json', 'CLAUDE.md']), [])
        self.assertTrue(self.run_check('plan/x', ['tools/a.py']))
        self.assertTrue(self.run_check('plan/x', ['registries/tools/wsc.jobs.json']))
        self.assertEqual(self.run_check('meta/x', ['.github/workflows/gates.yml', 'tools/pr_policy.py', 'tests/t.py', 'core',
                                                   'registries/tools/wsc.jobs.json', 'registries/hotkeys.jsonl', 'docs/DECISIONS.md']), [])
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

    def test_the_newest_round_verdict_decides(self):
        """D36 (J52): review.md rounds are newest first, so verdict() reads the latest round with no change to its parser."""
        r1 = '## Round 1 (2026-11-01, branch job/J1 at abc1231)\n\n**Verdict: do not merge.**\n\n'
        r2 = '## Round 2 (2026-11-02, branch job/J1 at abc1232)\n\n**Verdict: merge.**\n\n'
        done = dict(ROW, status='done', report='jobs/J1/report.md', review='jobs/J1/review.md')
        base = files(**{'jobs/J1/brief.md': 'b'})
        reverse = r2.replace('Verdict: merge.', 'Verdict: do not merge.') + r1.replace('Verdict: do not merge.', 'Verdict: merge.')
        for review, ok in (('# R\n\n' + r2 + r1, True), ('# R\n\n' + reverse, False)):
            e = pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base,
                         files(**{'jobs/J1/report.md': 'r', 'jobs/J1/review.md': review}))
            self.assertEqual(e == [], ok, e)
        self.assertEqual(pp.verdict(r2 + r1), 'merge')
        self.assertEqual(pp.verdict(r1 + r2), 'do not merge')

    def test_fix_sessions_writing_the_report_do_not_trip_the_own_review_rule(self):
        """Builder S1 writes the report, reviewer R1 round 1, fixer F1 appends Fix round 1 to the report, reviewer R2 round 2."""
        done = dict(ROW, status='done', report='jobs/J1/report.md', review='jobs/J1/review.md')
        head = files(**{'jobs/J1/report.md': 'r', 'jobs/J1/review.md': '**Verdict: merge.**'})
        base = files(**{'jobs/J1/brief.md': 'b'})
        rounds = lambda p: [{'S1'}, {'F1'}] if p.endswith('report.md') else [{'R1'}, {'R2'}]
        self.assertEqual(pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base, head, rounds), [])
        fixer_reviews = lambda p: [{'S1'}, {'F1'}] if p.endswith('report.md') else [{'R1'}, {'F1'}]
        e = pp.check('job/J1', ['x'], {'J1': ROW, 'J2': OTHER}, {'J1': done, 'J2': OTHER}, base, head, fixer_reviews)
        self.assertTrue(any('also wrote the report (F1)' in x for x in e), e)

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

    def write_rows(self, rows, layout, trailer=None):
        """The jobs registry as one JSONL (before J55) or one file per row (J55)."""
        if layout == 'jsonl':
            self.commit('registries/jobs.jsonl', ''.join(json.dumps(r) + '\n' for r in rows), trailer)
            return
        for r in rows:
            p = Path(self.d) / 'registries' / 'jobs' / f'{r["id"]}.json'
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(r, indent=2) + '\n', encoding='utf-8', newline='\n')
        (Path(self.d) / 'registries' / 'jobs.jsonl').unlink(missing_ok=True)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'rows', *(['--trailer', f'Claude-Session: {trailer}'] if trailer else []))

    def branch(self, report_session, review_session, layout='dir'):
        self.git('checkout', '-q', '-B', 'job/J1', 'main')
        self.commit('jobs/J1/report.md', 'report', report_session)
        done = dict(ROW, status='done', report='jobs/J1/report.md', review='jobs/J1/review.md')
        self.write_rows([done, OTHER], layout, review_session)
        self.commit('jobs/J1/review.md', '**Verdict: merge.**', review_session)
        return subprocess.run([sys.executable, str(POLICY), '--branch', 'job/J1', '--base', 'main'], cwd=self.d,
                              capture_output=True, text=True)

    def setUp(self, layout='dir'):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid')
        self.git('config', 'user.name', 'test')
        self.commit('jobs/J1/brief.md', 'brief')
        self.write_rows([ROW, OTHER], layout)

    def test_rows_at_reads_either_layout_the_same(self):
        dir_rows = pp_rows_at(self.d, 'main')
        self.git('checkout', '-q', '-b', 'old', 'main')
        self.write_rows([ROW, OTHER], 'jsonl')
        self.assertEqual(pp_rows_at(self.d, 'old'), dir_rows)
        self.assertEqual(sorted(dir_rows), ['J1', 'J2'])

    def test_a_base_from_before_j55_and_a_per_id_head(self):
        """J55's own pull request, and any branch that moves across it: base rows in the JSONL, head rows in files."""
        self.tearDown()
        self.setUp(layout='jsonl')
        r = self.branch('builder-session', 'reviewer-session', layout='dir')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.git('checkout', '-q', '-B', 'job/J1', 'main')   # touching another row is still refused across the layouts
        self.commit('jobs/J1/report.md', 'report', 'builder-session')
        done = dict(ROW, status='done', report='jobs/J1/report.md', review='jobs/J1/review.md')
        self.write_rows([done, dict(OTHER, status='queued')], 'dir', 'reviewer-session')
        self.commit('jobs/J1/review.md', '**Verdict: merge.**', 'reviewer-session')
        r = subprocess.run([sys.executable, str(POLICY), '--branch', 'job/J1', '--base', 'main'], cwd=self.d, capture_output=True, text=True)
        self.assertIn('only its own row; it also changes J2', r.stderr)

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
    CHECKER = (ROOT / 'core' / 'harness' / 'acceptance.py').read_text(encoding='utf-8')

    @staticmethod
    def led(n, build='abc', watcher='1.0.1', fail_at=None, evidence=True, branch='job/J9'):
        return '\n'.join(json.dumps({'pass': i, 'build_id': build, 'watcher': watcher, 'branch': branch, 'result': 'fail' if i == fail_at else 'pass',
                                     **({'run': 'harness/runs/r', 'evidence': f'harness/runs/r/pass_{i:02d}.json'} if evidence else {})})
                         for i in range(1, n + 1)) + '\n'

    def acc(self, ledger, active=True, exists=lambda p: True):
        return {'active': active, 'ledger': ledger, 'build_id': 'abc', 'watcher': '1.0.1', 'branch': 'job/J9', 'exists': exists}

    @staticmethod
    def baseline():
        kinds = ('land', 'siege', 'naval', 'historical', 'campaign')
        steps = [{'scenario': f'{k}_x', 'kind': k, 'pose': 'wide', 'load_time_s': 20.0, 'load_tolerance_pct': 50, 'shot': f'{k}.jpg',
                  'shot_threshold': 4.0, 'deterministic': True} for k in kinds]
        return {'schema': 1, 'date': '2026-10-30', 'build_id': 'abc', 'fresh_boot': True, 'size': '1920x1080', 'exe_sha1': 'pin', 'steps': steps,
                'settings_files': ['prefs']}

    def test_failing_fixture_ledger_lines_without_committed_evidence_do_not_count(self):
        # J4 review 7: a hand-written line is a claim, not evidence; the run folder's pass file must be on the branch
        errs = pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20), exists=lambda p: p != 'harness/runs/r/pass_20.json'))
        self.assertEqual(len(errs), 1)
        self.assertIn('0 consecutive', errs[0])
        self.assertIn('not committed', errs[0])
        self.assertTrue(pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc(self.led(20, evidence=False))))

    def test_a_branch_weakening_its_own_checker_cannot_switch_the_rule_off(self):
        # J4 review round 2: the base's acceptance.py judges the baseline, not the branch's copy
        b = json.dumps(self.baseline())
        weak = self.CHECKER.replace('def baseline_problems(b):', 'def baseline_problems(b):\n    return ["always"]\n\ndef _old(b):')
        self.assertFalse(pp.acceptance_active('', b, weak))           # a weakened checker would say inactive...
        self.assertTrue(pp.acceptance_active('', b, self.CHECKER))    # ...but main() passes the base's text, which says active
        src = (ROOT / 'tools' / 'pr_policy.py').read_text(encoding='utf-8')
        self.assertIn('show_first(a.base, *ACC_CHECKERS)', src)   # the base's checker, in either layout (J12)
        self.assertNotIn("spec_from_file_location('acceptance'", src)

    def test_failing_fixture_another_branchs_passes_do_not_count(self):
        # J44 review: harness/ is not in the build id, so a harness-only branch on main's build would inherit the last merged branch's 20
        errs = pp.acceptance_problems(['harness/core/ctl.py'], self.acc(self.led(20, branch='job/J8')))
        self.assertEqual(len(errs), 1)
        self.assertIn('another branch', errs[0])
        self.assertTrue(pp.acceptance_problems(['harness/core/ctl.py'], self.acc(self.led(20, branch=None))))
        self.assertIn("'branch': a.branch", (ROOT / 'tools' / 'pr_policy.py').read_text(encoding='utf-8'))

    def test_exemptions_match_segments_not_substrings(self):
        self.assertFalse(pp.acc_exempt('proxy/core/README.md.bak'))
        self.assertFalse(pp.acc_exempt('proxy/core/reruns/x.cpp'))
        self.assertTrue(pp.acc_exempt('harness/runs/x/a.json'))

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

    def test_a_ledger_without_a_valid_baseline_does_not_activate_it(self):
        # J4 review 1: the empty ledger alone switched the rule on, and nothing could satisfy it (no baseline, run not wired)
        self.assertFalse(pp.acceptance_active('', None, self.CHECKER))
        self.assertFalse(pp.acceptance_active('', '{"schema": 1}', self.CHECKER))
        self.assertFalse(pp.acceptance_active('', 'not json', self.CHECKER))
        self.assertFalse(pp.acceptance_active('', json.dumps(self.baseline()), None))
        self.assertEqual(pp.acceptance_problems(['proxy/core/dev.cpp'], self.acc('', active=pp.acceptance_active('', None, self.CHECKER))), [])

    def test_a_ledger_and_a_valid_baseline_activate_it(self):
        b = self.baseline()
        self.assertTrue(pp.acceptance_active('', json.dumps(b), self.CHECKER))
        self.assertFalse(pp.acceptance_active(None, json.dumps(b), self.CHECKER))

    def _repo_with_passes(self, d):
        """A fixture repo holding the DLL inputs (the real build_id.py), and 20 passes on its content id for job/J9."""
        g = lambda *a: subprocess.run(['git', *a], cwd=d, capture_output=True, text=True, check=True)
        g('init', '-q', '-b', 'job/J9'); g('config', 'user.email', 't@example.invalid'); g('config', 'user.name', 'test')
        for rel, data in (('proxy/core/a.cpp', b'int a;\n'), ('proxy/napoleon/adapter.cpp', b'int b;\n'), ('proxy/tools/build.sh', b'#!\n'),
                          ('proxy/tools/fetch_lua.py', b'#\n'), ('proxy/tools/build_id.py', (ROOT / 'core/proxy/tools/build_id.py').read_bytes())):
            (Path(d) / rel).parent.mkdir(parents=True, exist_ok=True)
            (Path(d) / rel).write_bytes(data)
        g('add', '-A'); g('commit', '-q', '-m', 'J9: proxy change')
        built = pp.dll_build_id(d)
        acc = lambda: dict(self.acc(self.led(20, build=built)), build_id=pp.dll_build_id(d))
        return g, acc

    def test_failing_fixture_a_reword_after_the_20_passes_still_passes(self):
        # J44 review 2: the id was the commit hash of the last input change, so this reword cost J44 a whole 20-pass run (J45)
        with tempfile.TemporaryDirectory() as d:
            g, acc = self._repo_with_passes(d)
            g('commit', '-q', '--amend', '-m', 'J9: proxy change (reworded, trailer added)')
            self.assertEqual(pp.acceptance_problems(['proxy/core/a.cpp'], acc()), [])

    def test_failing_fixture_an_input_change_after_the_20_passes_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            g, acc = self._repo_with_passes(d)
            (Path(d) / 'proxy/core/a.cpp').write_text('int a2;\n')
            g('commit', '-q', '-am', 'J9: one more proxy change')
            errs = pp.acceptance_problems(['proxy/core/a.cpp'], acc())
            self.assertEqual(len(errs), 1)
            self.assertIn('0 consecutive', errs[0])

    def test_check_wires_it_into_job_branches(self):
        errs = pp.check('job/J1', ['proxy/core/dev.cpp'], {'J1': ROW}, {'J1': ROW}, files(), files(), None, self.acc(self.led(3)))
        self.assertTrue(any('rule 79' in e for e in errs))


if __name__ == '__main__':
    unittest.main()
