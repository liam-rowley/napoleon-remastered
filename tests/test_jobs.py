"""Host tests for tools/verbs/jobs.py (`wsc jobs`): bad fixtures fail, good ones pass, and this repo's own queue passes.

The last test is what makes `jobs check` a gate today: the `tests` gate (CI and full `wsc gates`) runs it on the real queue,
until warscape-core supports game gates (backlog B1).
"""
import html
import importlib.util
import json
import re
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
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
REPORT = '# J1 report: thing\n\n## What exists\nx\n\n## Deviations from the brief, and why\nnone\n\n## Open questions\nnone\n'
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
        read = lambda p: {'jobs/J1/brief.md': BRIEF, 'jobs/J1/report.md': REPORT, 'jobs/J1/review.md': REVIEW,
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
        read = lambda p: {'jobs/J1/brief.md': BRIEF, 'jobs/J1/report.md': REPORT,
                          'jobs/J1/review.md': '# Review\n\n**Verdict: merge after fixes.**\n'}.get(p)
        e = self.errs(rows, read)
        self.assertTrue(any('verdict is "merge after fixes"' in x for x in e), e)
        self.assertTrue(any('no date' in x for x in e), e)

    def test_dependencies_done_before_review_and_no_cycles(self):
        rows = [row(status='review', brief='jobs/J1/brief.md', report='jobs/J1/report.md', depends_on=['J2']),
                row('J2', depends_on=['J1'])]
        e = self.errs(rows, lambda p: {'jobs/J1/brief.md': BRIEF, 'jobs/J1/report.md': REPORT}.get(p))
        self.assertTrue(any('dependencies J2 are not done' in x for x in e), e)
        self.assertTrue(any('dependency cycle' in x for x in e), e)

    def test_report_shape(self):
        self.assertEqual(jv.report_problems('J1', REPORT), [])
        bad = jv.report_problems('J1', '# Report\n\n## What exists\n')
        self.assertEqual(len(bad), 3, bad)

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


class Ledger(unittest.TestCase):
    def test_codeable_later_rows_naming_the_job(self):
        led = ('| # | Rule | Source | Before | After | Why |\n|---|---|---|---|---|---|\n'
               '| 7 | Settle before checking | N:PLAN.md:1 | CL | CL | J4 |\n'
               '| 8 | Poses by id | N:PLAN.md:2 | CL | CL | J4, J13 |\n'
               '| 9 | Not this one | N:PLAN.md:3 | CL | E | J4 |\n'
               '| 10 | Nor this | N:PLAN.md:4 | CL | CL | J40 |\n')
        self.assertEqual(jv.waiting_rules(led, 'J4'), ['row 7: Settle before checking', 'row 8: Poses by id'])
        self.assertEqual(jv.waiting_rules(led, 'J13'), ['row 8: Poses by id'])
        self.assertEqual(jv.waiting_rules(led, 'J5'), [])


class View(unittest.TestCase):
    def test_lanes_follow_status_branches_and_dependencies(self):
        by = {r['id']: r for r in [row('J1', status='done'), row('J2', status='queued', depends_on=['J1']),
                                   row('J3', status='queued', depends_on=['J4']), row('J4'), row('J5', status='queued')]}
        lane = lambda j, b=(): jv.lane(by[j], by, set(b))[0]
        self.assertEqual(lane('J1'), 'done')
        self.assertEqual(lane('J2'), 'ready')
        self.assertEqual(lane('J2', ['job/J2']), 'progress')
        self.assertEqual(lane('J3'), 'waiting')
        self.assertEqual(lane('J4'), 'brief')
        self.assertEqual(lane('J4', ['brief/J4']), 'progress')

    def test_page_escapes_and_embeds_docs(self):
        page = jv.render_view([row('J1', status='queued', brief='jobs/J1/brief.md', title='a <b> & c')],
                              files(jobs__J1__brief_md=BRIEF + '</script>'), set(), 'now')
        self.assertIn('a &lt;b&gt; &amp; c', page)
        self.assertIn('Next to pick up: <a href="#J1">', page)
        self.assertIn('&lt;/script&gt;', page)               # a doc cannot break out of the page
        self.assertNotIn('id="lane-review"', page)            # empty lanes are left out


# The launch fixture: one launchable job per action, and one that is not.
LROWS = [row('J1', status='done'), row('J2', status='queued', depends_on=['J1']), row('J3', model='sonnet'),
         row('J4', status='queued', model='sonnet'), row('J5', status='queued', depends_on=['J3'])]
LBRANCHES = {'job/J4'}
LON_BRANCH = {'J4': (row('J4', status='review', model='sonnet'), False)}
LBY = {r['id']: r for r in LROWS}


class Ready(unittest.TestCase):
    def why(self, action, jid, branches=LBRANCHES, on_branch=LON_BRANCH):
        return jv.not_ready(action, jid, LBY, set(branches), on_branch)

    def test_launchable(self):
        self.assertIsNone(self.why('build', 'J2'))
        self.assertIsNone(self.why('brief', 'J3'))
        self.assertIsNone(self.why('review', 'J4'))

    def test_each_refusal(self):
        self.assertEqual(self.why('build', 'J99'), 'J99 is not a row of the jobs registry')
        self.assertEqual(self.why('build', 'J1'), 'J1 is done, not queued')
        self.assertEqual(self.why('build', 'J5'), 'J5 (queued): waits for J3')
        self.assertEqual(self.why('build', 'J2', {'job/J2'}), 'J2 (queued): in progress on job/J2')
        self.assertEqual(self.why('brief', 'J3', {'brief/J3'}), 'J3 (needs_brief): in progress on brief/J3')
        self.assertEqual(self.why('build', 'J4'), 'J4 (queued): in progress on job/J4')
        self.assertEqual(self.why('review', 'J2', set(), {}), 'J2 has no job/J2 branch on origin')
        self.assertIn('not review', self.why('review', 'J4', on_branch={'J4': (row('J4', status='queued'), False)}))
        self.assertIn('no J4 row', self.why('review', 'J4', on_branch={'J4': (None, False)}))
        self.assertIn('already reviewed', self.why('review', 'J4', on_branch={'J4': (row('J4', status='review'), True)}))

    def test_id_on_the_command_line(self):
        def wsc(*a):
            return subprocess.run([sys.executable, str(ROOT / 'core' / 'wsc.py'), '--root', str(ROOT), 'jobs', *a, '--offline'],
                                  capture_output=True, text=True, timeout=120)
        p = wsc('next', '--id', 'J99')
        self.assertEqual((p.returncode, p.stderr.strip()), (1, 'jobs: J99 is not a row of the jobs registry'))
        done = next(r['id'] for r in jv.load_rows((ROOT / 'registries' / 'jobs.jsonl').read_text(encoding='utf-8'))
                    if r['status'] == 'done')
        p = wsc('next', '--id', done)
        self.assertEqual(p.returncode, 1)
        self.assertIn('not queued or needs_brief', p.stderr)
        self.assertEqual(wsc('review', '--id', 'J99').returncode, 1)


def argv(jid, action, model):
    prompt = {'brief': f'Write the brief for job {jid}: git pull, then run python3 core/wsc.py jobs next --id {jid} and follow it.',
              'build': f'Pick up job {jid}: git pull, then run python3 core/wsc.py jobs next --id {jid} and follow it.',
              'review': f'Review job {jid}: git pull, then run python3 core/wsc.py jobs review --id {jid} and follow docs/REVIEW.md.'}
    return ['claude', '--bg', '--name', f'{jid}-{action}', '--model', model, '--effort', 'medium', prompt[action]]


class Buttons(unittest.TestCase):
    def buttons(self, page):
        return sorted(re.findall(r'data-id="(J\d+)" data-act="(\w+)"', page))

    def test_only_on_launchable_cards(self):
        page = jv.render_view(LROWS, files(), LBRANCHES, 'now', LON_BRANCH)
        self.assertEqual(self.buttons(page), [('J2', 'build'), ('J3', 'brief'), ('J4', 'review')])
        self.assertEqual(self.buttons(jv.render_view(LROWS, files(), LBRANCHES, 'now')), [('J2', 'build'), ('J3', 'brief')])

    def test_copy_mode_and_served_mode(self):
        page = jv.render_view(LROWS, files(), LBRANCHES, 'now', LON_BRANCH, root='/repo')   # POSIX on every host: CI runs on Linux
        self.assertIn('const SERVE = null;', page)
        cmd = html.unescape(re.search(r'data-act="build" data-cmd="([^"]*)"', page).group(1))
        self.assertEqual(cmd, 'cd "/repo"; claude --bg --name J2-build --model opus --effort medium "' + argv('J2', 'build', 'opus')[-1] + '"')
        page = jv.render_view(LROWS, files(), LBRANCHES, 'now', LON_BRANCH, token='tok123')
        self.assertIn('const SERVE = {"token": "tok123"};', page)


class Serve(unittest.TestCase):
    def start(self, agents=lambda: [], dry_run=False, which=lambda n: n):
        self.launched = []
        def launch(a):
            self.launched.append(a)
            return 'abcd1234'
        srv = jv.JobServer(lambda: (LROWS, files(), set(LBRANCHES), LON_BRANCH), agents, launch, which=which, dry_run=dry_run)
        srv.log = False
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        self.srv = srv
        return srv

    def post(self, body, token=None, origin=None, ctype='application/json'):
        s = self.srv
        data = json.dumps({'token': s.token if token is None else token, **body}).encode()
        req = urllib.request.Request(s.url + 'launch', data=data, method='POST',
                                     headers={'Content-Type': ctype, 'Origin': origin or s.url.rstrip('/')})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as x:
            with x:
                return x.code, json.loads(x.read())

    def test_launch_each_action_with_the_exact_argv(self):
        self.start()
        for jid, action, model in (('J2', 'build', 'opus'), ('J3', 'brief', 'sonnet'), ('J4', 'review', 'sonnet')):
            code, j = self.post({'id': jid, 'action': action})
            self.assertEqual(code, 200, j)
            self.assertEqual(j['message'], f'started {jid}-{action}: claude attach abcd1234')
            self.assertEqual(self.launched[-1], argv(jid, action, model))

    def test_page_is_served_with_the_token_only_to_its_own_host(self):
        srv = self.start()
        with urllib.request.urlopen(srv.url, timeout=10) as r:
            self.assertIn(f'"token": "{srv.token}"', r.read().decode())
        req = urllib.request.Request(srv.url, headers={'Host': f'evil.example:{srv.server_address[1]}'})
        with self.assertRaises(urllib.error.HTTPError) as x:
            urllib.request.urlopen(req, timeout=10)
        x.exception.close()
        self.assertEqual(x.exception.code, 403)

    def test_bad_token_foreign_origin_and_form_post_are_refused(self):
        self.start()
        ok = {'id': 'J2', 'action': 'build'}
        self.assertEqual(self.post(ok, token='wrong')[0], 403)
        self.assertEqual(self.post(ok, token='')[0], 403)
        self.assertEqual(self.post(ok, origin='https://evil.example')[0], 403)
        self.assertEqual(self.post(ok, ctype='application/x-www-form-urlencoded')[0], 415)
        self.assertEqual(self.post({'id': 'J99', 'action': 'build'})[0], 400)
        self.assertEqual(self.post({'id': 'J2', 'action': 'rm -rf'})[0], 400)
        self.assertEqual(self.launched, [])

    def test_unready_job_is_409(self):
        self.start()
        for body in ({'id': 'J5', 'action': 'build'}, {'id': 'J2', 'action': 'review'}, {'id': 'J2', 'action': 'brief'}):
            code, j = self.post(body)
            self.assertEqual(code, 409, j)
        self.assertEqual(self.post({'id': 'J5', 'action': 'build'})[1]['message'], 'refused: J5 (queued): waits for J3')
        self.assertEqual(self.launched, [])

    def test_no_count_cap_but_one_session_per_name(self):
        busy = [{'name': n, 'state': 'working'} for n in ('j13 status brief', 'other', 'third')]
        self.start(agents=lambda: busy + [{'name': 'old', 'state': 'done'}])
        self.assertEqual(self.post({'id': 'J2', 'action': 'build'})[0], 200)   # D34: Liam decides how many run at once
        self.srv.agents = lambda: [{'name': 'j2-BUILD', 'state': 'working'}]
        code, j = self.post({'id': 'J2', 'action': 'build'})
        self.assertEqual((code, j['message']), (429, 'refused: J2-build is already running'))
        self.srv.agents = lambda: [{'name': 'J2-build', 'state': 'done'}]   # finished sessions do not count
        self.assertEqual(self.post({'id': 'J2', 'action': 'build'})[0], 200)

    def test_failing_agent_list_or_missing_claude_refuses(self):
        def broken():
            raise ValueError('claude agents --json exited 1')
        self.start(agents=broken)
        code, j = self.post({'id': 'J2', 'action': 'build'})
        self.assertEqual(code, 503)
        self.assertIn('cannot list the running sessions', j['message'])
        self.srv.agents, self.srv.which = (lambda: []), (lambda n: None)
        self.assertEqual(self.post({'id': 'J2', 'action': 'build'})[1]['message'], 'refused: claude is not on PATH')
        self.assertEqual(self.launched, [])

    def test_dry_run_returns_the_argv_without_launching(self):
        self.start(dry_run=True)
        code, j = self.post({'id': 'J3', 'action': 'brief'})
        self.assertEqual((code, j['argv']), (200, argv('J3', 'brief', 'sonnet')))
        self.assertTrue(j['message'].startswith('dry run, would start: claude --bg --name J3-brief'))
        self.assertEqual(self.launched, [])


class StartSession(unittest.TestCase):
    def test_runs_claude_in_the_repo_root(self):
        seen = {}
        def fake_run(argv, **kw):
            seen.update(kw, argv=argv)
            kw['stdout'].write('started 1a2b3c4d' + chr(10))
            return subprocess.CompletedProcess(argv, 0)
        which, run = jv.shutil.which, jv.subprocess.run
        jv.shutil.which, jv.subprocess.run = (lambda n: '/bin/claude'), fake_run
        try:
            sid = jv.start_session(argv('J2', 'build', 'opus'), Path('/repo'))
        finally:
            jv.shutil.which, jv.subprocess.run = which, run
        self.assertEqual((sid, seen['cwd'], seen['argv'][1:]), ('1a2b3c4d', Path('/repo'), argv('J2', 'build', 'opus')[1:]))

class RedPullRequests(unittest.TestCase):
    """J42: next, review and view print open pull requests with a failed check first, from one gh call; --offline skips it."""
    PRS = [{'number': 7, 'headRefName': 'job/J9', 'statusCheckRollup': [
               {'__typename': 'CheckRun', 'name': 'gates', 'conclusion': 'SUCCESS', 'detailsUrl': 'u1'},
               {'__typename': 'CheckRun', 'name': 'harness-windows', 'conclusion': 'FAILURE', 'detailsUrl': 'https://x/runs/1'},
               {'__typename': 'CheckRun', 'name': 'proxy', 'conclusion': None, 'status': 'IN_PROGRESS'}]},
           {'number': 3, 'headRefName': 'brief/J4', 'statusCheckRollup': [
               {'__typename': 'StatusContext', 'context': 'policy', 'state': 'ERROR', 'targetUrl': 'https://x/runs/2'}]},
           {'number': 9, 'headRefName': 'plan/x', 'statusCheckRollup': None}]

    def test_only_failed_checks_are_listed_oldest_pull_request_first(self):
        self.assertEqual(jv.failed_prs(self.PRS), ['PR #3 brief/J4: policy failed, run https://x/runs/2',
                                                   'PR #7 job/J9: harness-windows failed, run https://x/runs/1'])

    def test_offline_makes_no_call(self):
        def boom(*a, **k):
            raise AssertionError('gh was called')
        self.assertEqual(jv.red_prs(ROOT, True, run=boom), [])

    def test_one_gh_call_and_its_failures_become_a_line_not_an_exception(self):
        calls = []

        def fake(argv, **k):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, json.dumps(self.PRS), '')
        self.assertEqual(len(jv.red_prs(ROOT, False, run=fake)), 2)
        self.assertEqual(len(calls), 1)
        self.assertIn('statusCheckRollup', calls[0][-1])
        down = jv.red_prs(ROOT, False, run=lambda argv, **k: subprocess.CompletedProcess(argv, 1, '', 'not logged in'))
        self.assertEqual(len(down), 1)
        self.assertIn('not logged in', down[0])

        def missing(argv, **k):
            raise FileNotFoundError('gh')
        self.assertIn('could not list', jv.red_prs(ROOT, False, run=missing)[0])

    def test_next_names_the_local_policy_route(self):
        self.assertIn('python3 tools/pr_policy.py --branch job/J1 --base origin/main', jv.build_steps(row(status='queued')))


class ThisRepo(unittest.TestCase):
    def test_the_queue_passes_jobs_check(self):
        p = subprocess.run([sys.executable, str(ROOT / 'core' / 'wsc.py'), '--root', str(ROOT), 'jobs', 'check'],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


class PcState(unittest.TestCase):
    """Rule 75 (J44): on the PC the view shows the lock holder, the watcher version, the installed kit, the last acceptance pass and a usage source."""
    def test_reads_the_state_folder_and_the_ledger(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            state, repo = d / 'state', d / 'repo'
            (state / 'watcher').mkdir(parents=True)
            (repo / 'harness' / 'napoleon').mkdir(parents=True)
            (repo / 'harness' / 'acceptance').mkdir(parents=True)
            (repo / 'harness' / 'napoleon' / 'adapter.json').write_text(json.dumps({'state_dir': str(state), 'watcher_subdir': 'watcher'}))
            (state / 'watcher' / 'game.lock').write_text('owner=j44 session=s purpose=p started=t\n')
            (state / 'watcher' / 'watcher.status').write_text(json.dumps({'version': '1.0.1', 'game_state': {'state': 'not_running'}}))
            (state / 'watcher' / 'watcher.alive').write_text('x')
            (state / 'install.json').write_text(json.dumps({'kit_id': 'kit_1', 'build_id': 'abc'}))
            (repo / 'harness' / 'acceptance' / 'ledger.jsonl').write_text(json.dumps({'pass': 3, 'result': 'pass', 'build_id': 'abc', 'watcher': '1.0.1', 'utc': 'u', 'run': 'r'}) + '\n')
            pc = jv.pc_state(repo)
            self.assertIn('owner=j44', pc['lock'])
            self.assertEqual((pc['watcher'], pc['kit'], pc['last_acceptance']['pass'], pc['last_acceptance']['result']), ('1.0.1', 'kit_1', 3, 'pass'))
            self.assertTrue(pc['usage'])
            block = jv.pc_block(pc)
            for want in ('owner=j44', '1.0.1', 'kit_1', 'pass 3 pass', 'usage source'):
                self.assertIn(want, block)

    def test_off_the_pc_there_is_no_block(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'harness' / 'napoleon').mkdir(parents=True)
            (Path(d) / 'harness' / 'napoleon' / 'adapter.json').write_text(json.dumps({'state_dir': str(Path(d) / 'nope')}))
            self.assertIsNone(jv.pc_state(d))
            self.assertEqual(jv.pc_block(None), '')


if __name__ == '__main__':
    unittest.main()
