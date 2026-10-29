"""Host tests for tools/verbs/jobs.py (`wsc jobs`): bad fixtures fail, good ones pass, and this repo's own queue passes.

The last test is what makes `jobs check` a gate today: the `tests` gate (CI and full `wsc gates`) runs it on the real queue,
until warscape-core supports game gates (backlog B1).
"""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('jobs_verb', ROOT / 'tools' / 'verbs' / 'jobs.py')
jv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jv)

BRIEF = '''# J1: thing

Model: Opus, reason: DLL work (D15). Budget about 100 tool calls; at the cap, stop.

## Kill criteria
- It breaks twice: stop.

## Finish
Write `jobs/J1/report.md`. Then `wsc reg set jobs J1 status=review report=jobs/J1/report.md`.
'''
REVIEW = '# Review of J1\n\n2026-10-29, fresh chat.\n\n**Verdict: merge.**\n'


def row(jid='J1', **kw):
    r = {'id': jid, 'description': 'd', 'title': 't', 'phase': 1, 'status': 'needs_brief', 'model': 'opus', 'needs_pc': False,
         'depends_on': []}
    r.update(kw)
    return r


def files(**kw):
    m = {k.replace('__', '/').replace('_md', '.md'): v for k, v in kw.items()}
    return lambda p: m.get(p)


class Check(unittest.TestCase):
    def errs(self, rows, read=None, folders=()):
        return jv.problems(rows, read or files(), folders)

    def test_good_queue_passes(self):
        rows = [row(status='done', brief='jobs/J1/brief.md', report='jobs/J1/report.md', review='jobs/J1/review.md'),
                row('J2', status='queued', brief='jobs/J2/brief.md', depends_on=['J1'], model='sonnet'), row('J3')]
        read = lambda p: {'jobs/J1/brief.md': BRIEF, 'jobs/J1/report.md': 'r', 'jobs/J1/review.md': REVIEW,
                          'jobs/J2/brief.md': BRIEF.replace('J1', 'J2').replace('Opus, reason: DLL work', 'Sonnet medium')}.get(p)
        self.assertEqual(self.errs(rows, read, ['J1', 'J2']), [])

    def test_status_needs_its_files(self):
        e = self.errs([row(status='review', brief='jobs/J1/brief.md', report='jobs/J1/report.md')], lambda p: None)
        self.assertTrue(any('brief=jobs/J1/brief.md but the file does not exist' in x for x in e), e)
        self.assertTrue(any('report=jobs/J1/report.md but the file does not exist' in x for x in e), e)

    def test_link_to_another_jobs_file(self):
        e = self.errs([row(status='queued', brief='jobs/J2/brief.md')], lambda p: BRIEF if p == 'jobs/J2/brief.md' else None)
        self.assertTrue(any('points at another job' in x for x in e), e)

    def test_brief_present_but_needs_brief(self):
        e = self.errs([row()], lambda p: BRIEF if p == 'jobs/J1/brief.md' else None)
        self.assertTrue(any('still needs_brief' in x for x in e), e)

    def test_done_needs_merge_verdict_and_date(self):
        rows = [row(status='done', brief='jobs/J1/brief.md', report='jobs/J1/report.md', review='jobs/J1/review.md')]
        read = lambda p: {'jobs/J1/brief.md': BRIEF, 'jobs/J1/report.md': 'r',
                          'jobs/J1/review.md': '# Review\n\n**Verdict: merge after fixes.**\n'}.get(p)
        e = self.errs(rows, read)
        self.assertTrue(any('verdict is "merge after fixes"' in x for x in e), e)
        self.assertTrue(any('no date' in x for x in e), e)

    def test_dependencies_done_before_review_and_no_cycles(self):
        rows = [row(status='review', brief='jobs/J1/brief.md', report='jobs/J1/report.md', depends_on=['J2']),
                row('J2', depends_on=['J1'])]
        e = self.errs(rows, lambda p: {'jobs/J1/brief.md': BRIEF, 'jobs/J1/report.md': 'r'}.get(p))
        self.assertTrue(any('dependencies J2 are not done' in x for x in e), e)
        self.assertTrue(any('dependency cycle' in x for x in e), e)

    def test_folder_without_row(self):
        self.assertEqual(self.errs([], folders=['J9']), ['jobs/J9/ has no row in the jobs registry'])

    def test_brief_shape(self):
        r = row(status='queued', brief='jobs/J1/brief.md')
        self.assertEqual(jv.brief_problems('J1', r, BRIEF), [])
        bad = jv.brief_problems('J1', r, '# J1: thing\n\nModel: Opus. No budget.\n\n## Kill criteria\nnone\n')
        for want in ('without "reason:"', 'no call budget', 'Kill criteria', 'Finish'):
            self.assertTrue(any(want in x for x in bad), (want, bad))
        self.assertTrue(any('row says sonnet' in x for x in jv.brief_problems('J1', row(model='sonnet'), BRIEF)))
        wrapped = BRIEF.replace('Budget about 100 tool calls', 'Budget\nabout 100 tool\ncalls')
        self.assertEqual(jv.brief_problems('J1', r, wrapped), [])


class Next(unittest.TestCase):
    ROWS = [row('J1', status='done'), row('J2', status='queued', depends_on=['J1']), row('J3', status='queued', depends_on=['J4']),
            row('J4', depends_on=['J1']), row('J10', status='queued', depends_on=['J1'])]

    def test_lowest_ready_queued_job_without_a_branch(self):
        self.assertEqual(jv.pick_next(self.ROWS, set())[1]['id'], 'J2')
        self.assertEqual(jv.pick_next(self.ROWS, {'job/J2'})[1]['id'], 'J10')   # numeric order, not text order

    def test_then_a_brief_then_nothing(self):
        kind, r, _ = jv.pick_next(self.ROWS, {'job/J2', 'job/J10'})
        self.assertEqual((kind, r['id']), ('brief', 'J4'))
        kind, r, waiting = jv.pick_next(self.ROWS, {'job/J2', 'job/J10', 'brief/J4'})
        self.assertIsNone(kind)
        self.assertTrue(any(w.startswith('J3') and 'J4' in w for w in waiting), waiting)

    def test_review_pick(self):
        self.assertEqual(jv.pick_review({'J3': (row('J3', status='review'), False), 'J2': (row('J2', status='review'), True),
                                         'J1': (row('J1', status='done'), True)}), 'J3')
        self.assertIsNone(jv.pick_review({'J1': (None, False)}))


class ThisRepo(unittest.TestCase):
    def test_the_queue_passes_jobs_check(self):
        p = subprocess.run([sys.executable, str(ROOT / 'core' / 'wsc.py'), '--root', str(ROOT), 'jobs', 'check'],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == '__main__':
    unittest.main()
