"""Host tests of tools/acceptance_auto.py (J85): every guard, the pick, stop and resume, the end of a run. Fake seams for git, job.sh, pc_deploy, the clock and the idle reading: no process starts,
no PC. `Fake.acts` holds every call that changes something, so "touches nothing" is an assertion.
"""
import argparse
import importlib.util
import json
import sys
import unittest
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core'))
spec = importlib.util.spec_from_file_location('acceptance_auto', ROOT / 'tools' / 'acceptance_auto.py')
auto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auto)
spec = importlib.util.spec_from_file_location('j85_gate', ROOT / 'tools' / 'gates' / 'pipeline.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

STATE = PurePosixPath('/state')
WT = PurePosixPath('/wt')
SRC = STATE / 'watcher' / 'src'
HEAD, MAIN, BLOB = 'a' * 40, 'b' * 40, 'c' * 40
BUILD, WSHA = 'aaaaaaaaaaaa', 'f' * 64
START = 2_000_000_000
READ_ONLY = {'status', 'rev-parse', 'for-each-ref', 'cat-file', 'show', 'merge-base', 'diff'}


class Proc:
    """acceptance.py: its lines, then its exit code. `after` runs when a line is read (a person coming back)."""
    def __init__(self, lines, rc=0, after=None):
        self.lines, self.rc, self.after, self.stopped, self.pid = list(lines), rc, after or {}, False, 4242

    def next_line(self, timeout):
        if not self.lines:
            return None
        line = self.lines.pop(0)
        if line in self.after:
            self.after[line]()
        return line

    def stop(self):
        self.stopped = True

    def wait(self):
        return self.rc


class Fake:
    def __init__(self):
        self.root, self.state, self.game, self.worktree = Path('/repo'), Path(str(STATE)), Path('/game'), Path(str(WT))
        self.adapter = {'acceptance': {'max_flakes': 1}, 'watcher_subdir': 'watcher'}
        self.session, self.offline = None, False
        self.t, self.idle, self.free, self.input = START, 3600.0, 20.0, 111
        self.mons = [{'hw': 'DEL41DB', 'primary': True}, {'hw': 'MTT1337', 'primary': False}]
        self.files = {}          # path -> bytes
        self.acts = []           # every call that changes something
        self.beat_age = 0
        self.status = {'lock': None, 'foreign_lock': None, 'profile_active': None, 'game_state': {'state': 'not_running'}, 'current_job': None, 'queue_length': 0}
        self.deploy_status = (0, 'pc_deploy status: not installed by this tool\n  exe: ok Napoleon.exe\n  git: ok\n  foreign: not checked, nothing installed by this tool')
        self.sessions = []
        self.docker = True
        self.branches = {'job/J85': (HEAD, BLOB)}
        self.rows = {('b', 'J85'): 'queued', ('h', 'J85'): 'queued'}
        self.request = {'build_id': BUILD, 'watcher_sha': WSHA, 'requested_utc': '2026-11-07T00:00:00Z'}
        self.requests = {}
        self.problems = ['rule 79: this branch changes harness/x but harness/acceptance/ledger.jsonl holds 0 consecutive acceptance passes on build aaaaaaaaaaaa, watcher 1.5.0 (need 20): run it']
        self.ledger = ''
        self.proc = Proc(['acceptance pass 1: pass (x)'])
        self.alive_pids = set()
        self.build_rc, self.built_id = 0, BUILD
        self.remote_head, self.remote_build = HEAD, BUILD
        self.rebase_rc, self.push_rc, self.commit_rc = 0, 0, 0
        self.worktree_dirty, self.ledger_changed = '', True
        self.update_verdict = 'CONFIRMED'
        self.files[str(WT / '.git')] = b'x'
        self.files[str(WT / 'core/wsc.py')] = b'x'
        for n in ('watcher.ps1', 'watch.cmd', 'update.ps1', 'dump.ps1', 'procfreeze.ps1', 'spawn_detached.ps1', 'vdisplay_probe.ps1', 'win_probe.ps1'):
            self.files[str(WT / 'core/harness' / n)] = self.files[str(SRC / n)] = b'same\r\n'
        for rel, have in (('harness/napoleon/adapter.json', 'adapter.json'), ('proxy/napoleon/identity.json', 'exe_identity.json')):
            self.files[str(WT / rel)] = self.files[str(SRC / have)] = b'{}'

    # clock and readings
    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s

    def pid(self):
        return 777

    def created(self, pid):
        return 1 if pid == 777 or pid in self.alive_pids else None

    def alive(self, pid, created):
        return pid in self.alive_pids and created == 1

    def last_input(self):
        return self.input

    def idle_s(self):
        return self.idle

    def free_gb(self):
        return self.free

    def monitors(self):
        return self.mons

    def keep_awake(self, on):
        self.acts.append(('awake', on))

    # processes
    def git(self, *args, cwd=None, input=None):
        verb = args[0]
        if verb not in READ_ONLY:
            self.acts.append(('git', *args))
        if verb == 'for-each-ref':
            return 0, ''.join(f'origin/{b} {sha}\n' for b, (sha, _) in self.branches.items())
        if verb == 'cat-file' and args[1] == '--batch-check':
            shas = {sha: blob for sha, blob in self.branches.values()}
            return 0, ''.join((f'{shas[l.split(":")[0]]} blob 10\n' if shas[l.split(':')[0]] else f'{l} missing\n') for l in input.splitlines())
        if verb == 'cat-file':
            return 0, json.dumps(self.requests.get(args[2], self.request))
        if verb == 'rev-parse':
            ref = args[1]
            if ref.endswith('origin/main'):
                return 0, MAIN + '\n'
            if cwd is not None:
                return 0, self.remote_head + '\n'
            return 0, self.branches[ref.split('origin/', 1)[1]][0] + '\n'
        if verb == 'show':
            ref, path = args[1].split(':', 1)
            job = Path(path).stem
            status = self.rows.get(('b' if ref == MAIN else 'h', job), None)
            return (0, json.dumps({'status': status})) if status else (128, '')
        if verb == 'status':
            if '--' in args:
                return 0, ' M ledger\n' if self.ledger_changed else ''
            return 0, self.worktree_dirty
        return {'commit': self.commit_rc, 'rebase': self.rebase_rc, 'push': self.push_rc}.get(verb, 0), ''

    def job_sh(self, *args, input=None, timeout=200):
        if args[0] == 'status':
            return 0, 'x\n' + json.dumps(dict(self.status, heartbeat_utc=auto.utc_of(self.t - self.beat_age)))
        self.acts.append(('job.sh', *args, input))
        if args[0] == 'unlock':
            self.status['lock'] = None
            self.status['profile_active'] = None
        if input == 'kill\n':
            self.status['game_state'] = {'state': 'not_running'}
        if input and input.startswith('update'):
            self.files['/state/update.log'] = f'[x] [update] {self.update_verdict}: done'.encode()
            for k in list(self.files):
                if k.startswith(str(SRC)) and k.endswith('update.ps1'):
                    self.files[k] = self.files[str(WT / 'core/harness/update.ps1')]
            return 0, 'update started detached (rc=0 pid=1); log: /state/update.log and watcher.log'
        return 0, ''

    def pc_deploy(self, *args, cwd=None, timeout=1800):
        if args[0] == 'status':
            return self.deploy_status
        self.acts.append(('pc_deploy', *args))
        if args[0] == 'kit':
            kind = 'harness_1' if 'harness' in args else 'kit_new'
            return 0, f'pc_deploy kit: /wt/build/kits/{kind} (9 files)'
        if args[0] == 'install':
            self.deploy_status = (0, f"pc_deploy status: kit {Path(args[2]).name} build {BUILD} installed x\n")
        if args[0] == 'uninstall':
            self.deploy_status = (0, 'pc_deploy status: not installed by this tool\n')
        return 0, ''

    def build(self, cwd):
        self.acts.append(('build',))
        return self.build_rc, ''

    def build_id(self, cwd):
        return 0, self.built_id + '\n'

    def docker_ok(self):
        return self.docker

    def agents(self):
        return self.sessions

    def start(self, argv, cwd):
        self.acts.append(('start', *argv))
        return self.proc

    def kill_tree(self, pid):
        self.acts.append(('kill_tree', pid))

    def rule79(self, branch, head, main):
        if head == self.remote_head and head != HEAD:
            return {'build_id': self.remote_build}, []
        return {'build_id': BUILD, 'watcher_sha': WSHA, 'watcher': '1.5.0', 'ledger': self.ledger}, list(self.problems)

    # files
    def read_bytes(self, p):
        return self.files.get(str(PurePosixPath(Path(p).as_posix())))

    def exists(self, p):
        p = str(PurePosixPath(Path(p).as_posix()))
        return p in self.files

    def write_text(self, p, text):
        self.files[str(PurePosixPath(Path(p).as_posix()))] = text.encode('utf-8')

    def append_text(self, p, text):
        k = str(PurePosixPath(Path(p).as_posix()))
        self.files[k] = self.files.get(k, b'') + text.encode('utf-8')

    def profile_files(self, cwd):
        return []

    # what the tests read
    def kinds(self):
        return [a[0] if a[0] != 'pc_deploy' else f'pc_deploy {a[1]}' for a in self.acts]

    def state_doc(self):
        return json.loads(self.files.get(f'{STATE}/_scratch/acceptance-auto/state.json', b'{}'))

    def result(self):
        return json.loads(self.files[f'{STATE}/_scratch/acceptance-auto/last_result.json'])

    def seed(self, doc):
        self.files[f'{STATE}/_scratch/acceptance-auto/state.json'] = json.dumps(doc).encode()


def tick(f, **kw):
    a = argparse.Namespace(**{'dry_run': False, 'present_file': None, 'branch': None, 'job': None, 'passes': None, 'ignore_session': None, **kw})
    return auto.Tick(f, a).tick()


class Base(unittest.TestCase):
    def refused(self, f, word):
        self.assertEqual(tick(f), 0)
        self.assertEqual(f.acts, [], 'a refusal touches nothing')
        self.assertEqual(f.result()['action'], 'refused')
        self.assertIn(word, f.result()['reason'])


class Guards(Base):
    def test_present_file(self):
        f = Fake()
        f.files[f'{STATE}/liam_present'] = b''
        self.refused(f, 'liam_present')

    def test_idle_under_the_threshold(self):
        f = Fake()
        f.idle = auto.IDLE_MIN_S - 1
        self.refused(f, 'idle')

    def test_idle_unreadable_fails_closed(self):
        f = Fake()
        f.idle = None
        self.refused(f, 'idle')

    def test_lock(self):
        f = Fake()
        f.status['lock'] = {'owner': 'someone'}
        self.refused(f, 'lock')

    def test_profile(self):
        f = Fake()
        f.status['profile_active'] = 'headless'
        self.refused(f, 'profile')

    def test_game_up(self):
        f = Fake()
        f.status['game_state'] = {'state': 'running'}
        self.refused(f, 'running')

    def test_dead_watcher(self):
        f = Fake()
        f.beat_age = 600
        self.refused(f, 'watcher')

    def test_exe_not_vanilla(self):
        f = Fake()
        f.deploy_status = (1, 'pc_deploy status: not installed by this tool\n  exe: FAIL not vanilla\n  git: ok')
        self.refused(f, 'not vanilla')

    def test_foreign_or_stray_files(self):
        f = Fake()
        f.deploy_status = (1, 'pc_deploy status: not installed by this tool\n  exe: ok x\n  git: ok\n  stray: d3d9.dll')
        self.refused(f, 'stray')

    def test_a_kit_this_tool_did_not_install(self):
        f = Fake()
        f.deploy_status = (0, 'pc_deploy status: kit kit_other build x installed y\n')
        self.refused(f, 'kit_other')

    def test_working_session(self):
        f = Fake()
        f.sessions = [{'name': 'J88-build', 'sessionId': 's', 'state': 'working'}]
        self.refused(f, 'J88-build')

    def test_an_unknown_session_state_counts_as_working(self):
        f = Fake()
        f.sessions = [{'name': 'x', 'sessionId': 's', 'status': 'busy'}]
        self.refused(f, 'working')

    def test_agents_unreadable_fails_closed(self):
        f = Fake()
        f.sessions = None
        self.refused(f, 'agents')

    def test_memory(self):
        f = Fake()
        f.free = 7.9
        self.refused(f, 'memory')

    def test_docker_only_when_a_build_is_needed(self):
        f = Fake()
        f.docker = False
        tick(f)
        self.assertEqual(f.result()['action'], 'refused')
        self.assertIn('Docker', f.result()['reason'])
        self.assertEqual([a[:2] for a in f.acts], [('git', 'fetch')], 'the fetch is local refs: nothing on the PC')
        f = Fake()
        f.docker = False
        f.files[f'{STATE}/kits/kit_old/manifest.json'] = b'{}'
        f.seed({'kits': {'job/J85': {'kit': 'kit_old', 'build_id': BUILD}}})
        tick(f)
        self.assertIn('pc_deploy install', f.kinds())

    def test_the_order_is_cheapest_first(self):
        f = Fake()
        f.idle, f.free, f.sessions = 1, 1, None
        f.files[f'{STATE}/liam_present'] = b''
        self.refused(f, 'liam_present')

    def test_a_second_present_file(self):
        f = Fake()
        f.files['/s/test_present'] = b''
        tick(f, present_file='/s/test_present')
        self.assertEqual(f.acts, [])

    def test_a_live_run_ends_the_tick(self):
        f = Fake()
        f.alive_pids = {50}
        f.seed({'run': {'run_id': 'r', 'pid': 50, 'pid_created': 1}})
        tick(f)
        self.assertEqual(f.acts, [])
        self.assertEqual(f.result()['action'], 'busy')


class Pick(Base):
    def idle_result(self, f, log_word=None):
        tick(f)
        self.assertEqual(f.result()['action'], 'idle')
        self.assertEqual([k for k in f.kinds() if k != 'git'], [], 'only the fetch')
        if log_word:
            self.assertIn(log_word, f.files[f'{STATE}/_scratch/acceptance-auto/tick.log'].decode())

    def test_a_branch_without_a_request_is_no_candidate(self):
        f = Fake()
        f.branches = {'job/J1': (HEAD, None), 'job/J2': ('d' * 40, None)}
        self.idle_result(f)

    def test_a_stale_branch_whose_row_is_done_is_skipped(self):
        f = Fake()
        f.rows[('b', 'J85')] = 'done'
        self.idle_result(f, 'row on main')

    def test_a_row_under_review_is_skipped(self):
        f = Fake()
        f.rows[('h', 'J85')] = 'review'
        self.idle_result(f, 'row on the branch')

    def test_a_request_for_another_build_is_skipped(self):
        f = Fake()
        f.request = dict(f.request, build_id='000000000000')
        self.idle_result(f, 'the request is for build')

    def test_a_request_for_another_watcher_is_skipped(self):
        f = Fake()
        f.request = dict(f.request, watcher_sha='0' * 64)
        self.idle_result(f, 'the request is for watcher')

    def test_rule_79_already_satisfied(self):
        f = Fake()
        f.problems = []
        self.idle_result(f, 'satisfied')

    def test_a_consumed_request_is_not_taken_again(self):
        f = Fake()
        f.seed({'consumed': {'job/J85': [BLOB]}})
        self.idle_result(f)

    def test_a_new_request_after_a_fail_is_taken(self):
        f = Fake()
        f.seed({'consumed': {'job/J85': ['0' * 40]}})
        tick(f)
        self.assertIn('build', f.kinds())

    def test_oldest_request_first(self):
        f = Fake()
        f.branches = {'job/J85': (HEAD, BLOB), 'job/J90': ('e' * 40, 'd' * 40)}
        f.rows.update({('b', 'J90'): 'queued', ('h', 'J90'): 'fix'})
        f.requests = {'d' * 40: dict(f.request, requested_utc='2026-01-01T00:00:00Z')}
        tick(f, dry_run=True)
        got = auto.Tick(f, argparse.Namespace(dry_run=True)).pick({})
        self.assertEqual(got['branch'], 'job/J90')

    def test_dry_run_changes_nothing(self):
        f = Fake()
        before = dict(f.files)
        self.assertEqual(tick(f, dry_run=True), 0)
        self.assertEqual(f.acts, [])
        self.assertEqual(f.files, before)


class Run(Base):
    def test_a_full_run(self):
        f = Fake()
        f.proc = Proc([f'acceptance pass {i}: pass (x)' for i in range(1, 21)])
        tick(f)
        self.assertEqual(f.kinds()[-1], 'awake')
        k = [x for x in f.kinds() if x not in ('git', 'awake')]
        self.assertEqual(k, ['build', 'pc_deploy kit', 'pc_deploy send', 'pc_deploy install', 'start', 'pc_deploy uninstall'])
        start = next(a for a in f.acts if a[0] == 'start')
        self.assertEqual(start[start.index('--passes') + 1], '20')
        self.assertEqual(start[start.index('--branch') + 1], 'job/J85')
        self.assertRegex(start[start.index('--owner') + 1], r'^acceptance-auto-\d{8}t\d{6}z$')
        self.assertRegex(start[start.index('--owner') + 1], r'^[a-z0-9][a-z0-9_-]{0,39}$')
        self.assertEqual(start[start.index('--owner') + 1], start[start.index('--session') + 1])
        self.assertEqual(f.result()['action'], 'complete')
        self.assertTrue(f.result()['pushed'])
        self.assertTrue(f.result()['vanilla'])
        self.assertNotIn('run', f.state_doc())
        self.assertEqual(f.t - START >= auto.INSTALL_WAIT_S, True, 'waits after the install')

    def test_a_fail_consumes_the_request(self):
        f = Fake()
        f.proc = Proc(['acceptance pass 1: FAIL (x)'], rc=1)
        tick(f)
        self.assertEqual(f.result()['action'], 'consumed')
        self.assertEqual(f.state_doc()['consumed'], {'job/J85': [BLOB]})
        self.assertIn('pc_deploy uninstall', f.kinds())
        self.assertTrue(any(a[:2] == ('git', 'push') for a in f.acts), 'the evidence of a fail goes home')

    def test_a_build_id_other_than_the_request_stops_before_the_pc(self):
        f = Fake()
        f.built_id = 'dddddddddddd-dirty'
        self.assertEqual(tick(f), 0)
        self.assertNotIn('pc_deploy install', f.kinds())
        self.assertEqual(f.result()['action'], 'refused')

    def test_a_dirty_worktree_refuses(self):
        f = Fake()
        f.worktree_dirty = ' M x\n'
        tick(f)
        self.assertEqual(f.result()['action'], 'refused')
        self.assertNotIn('build', f.kinds())

    def test_a_refused_run_keeps_the_request(self):
        f = Fake()
        f.proc = Proc(['acceptance run: refused: x'], rc=2)
        tick(f)
        self.assertEqual(f.result()['action'], 'refused')
        self.assertNotIn('consumed', f.state_doc())
        self.assertIn('pc_deploy uninstall', f.kinds())

    def test_a_crash_inside_the_run_still_reaches_the_end(self):
        f = Fake()
        f.start = lambda argv, cwd: 1 / 0
        self.assertEqual(tick(f), 0)
        self.assertIn('pc_deploy uninstall', f.kinds())
        self.assertEqual(f.result()['action'], 'stopped')

    def test_identity_is_never_a_real_session(self):
        f = Fake()
        tick(f)
        self.assertTrue(f.session.startswith('acceptance-auto-'))


class Stop(Base):
    def stopped(self, f):
        tick(f)
        self.assertTrue(f.proc.stopped)
        self.assertEqual(f.result()['action'], 'stopped')
        self.assertNotIn('consumed', f.state_doc())
        return f

    def test_present_file_stops_at_the_next_pass_line_only(self):
        f = Fake()
        came = lambda: f.files.__setitem__(f'{STATE}/liam_present', b'')
        f.proc = Proc(['starting', 'acceptance pass 1: pass (x)', 'noise', 'noise', 'acceptance pass 2: pass (x)', 'acceptance pass 3: pass (x)'], after={'acceptance pass 1: pass (x)': came})
        self.stopped(f)
        self.assertEqual(f.proc.lines, ['acceptance pass 3: pass (x)'], 'pass 2 ran out, pass 3 was not waited for')
        self.assertIn('pc_deploy uninstall', f.kinds())

    def test_input_stops(self):
        f = Fake()
        f.proc = Proc(['starting', 'acceptance pass 1: pass (x)', 'acceptance pass 2: pass (x)'], after={'starting': lambda: setattr(f, 'input', 222)})
        self.stopped(f)
        self.assertEqual(f.result()['reason'], 'input')

    def test_a_layout_change_stops_and_names_both(self):
        f = Fake()
        came = lambda: setattr(f, 'mons', [{'hw': 'MSI3CB0', 'primary': True}, {'hw': 'DEL41DB', 'primary': False}, {'hw': 'MTT1337', 'primary': False}])
        f.proc = Proc(['starting', 'acceptance pass 1: pass (x)'], after={'starting': came})
        self.stopped(f)
        self.assertIn('from D to M', f.result()['reason'])

    def test_a_game_left_up_under_the_lock_is_killed_through_job_sh(self):
        f = Fake()
        f.status_after_stop = True
        real_stop = Proc.stop

        def up(p):
            real_stop(p)
            f.status['lock'] = {'owner': f.session}
            f.status['game_state'] = {'state': 'running'}
            f.status['profile_active'] = 'headless'
        f.proc = Proc(['starting', 'acceptance pass 1: pass (x)'], after={'starting': lambda: setattr(f, 'input', 222)})
        f.proc.stop = lambda: up(f.proc)
        tick(f)
        jobs = [a for a in f.acts if a[0] == 'job.sh']
        self.assertEqual(jobs[0][-1], 'kill\n')
        self.assertEqual(jobs[1][1], 'unlock')
        self.assertLess(f.acts.index(jobs[1]), f.kinds().index('pc_deploy uninstall'))
        self.assertTrue(f.result()['clean'])

    def test_a_lock_of_someone_else_is_left_and_the_kit_stays(self):
        f = Fake()
        f.proc = Proc(['starting', 'acceptance pass 1: pass (x)'], after={'starting': lambda: f.status.__setitem__('lock', {'owner': 'other'})})
        f.proc.stop = lambda: None
        tick(f)
        self.assertFalse(f.result()['clean'])
        self.assertNotIn('pc_deploy uninstall', f.kinds())
        self.assertIn('run', f.state_doc(), 'what it owns is not forgotten')

    def test_the_hard_limit_stops(self):
        f = Fake()
        f.t = START
        f.proc = Proc(['x'], after={'x': lambda: None})
        f.proc.lines = ['tick'] + ['acceptance pass 1: pass (x)']
        f.proc.after = {'tick': lambda: setattr(f, 't', START + auto.HARD_LIMIT_S + auto.INSTALL_WAIT_S + 10)}
        self.stopped(f)
        self.assertIn('limit', f.result()['reason'])

    def test_a_silent_run_is_ended_after_the_grace(self):
        f = Fake()

        class Silent(Proc):
            def next_line(self, timeout):
                f.t += 600
                return ''
        f.proc = Silent([])
        f.input = 111
        f.status['x'] = 1
        orig = f.last_input
        f.last_input = lambda: orig() if f.t < START + 2000 else 222
        self.stopped(f)
        self.assertIn('no pass line', f.result()['reason'])

    def test_a_stop_during_the_install_wait_never_starts_the_run(self):
        f = Fake()
        real = f.pc_deploy

        def dep(*a, **k):
            r = real(*a, **k)
            if a[0] == 'install':
                f.files[f'{STATE}/liam_present'] = b''
            return r
        f.pc_deploy = dep
        tick(f)
        self.assertNotIn('start', f.kinds())
        self.assertIn('pc_deploy uninstall', f.kinds())


class Resume(Base):
    def stop_once(self):
        f = Fake()
        f.proc = Proc(['starting', 'acceptance pass 1: pass (x)'], after={'starting': lambda: f.files.__setitem__(f'{STATE}/liam_present', b'')})
        tick(f)
        del f.files[f'{STATE}/liam_present']
        f.files[f"{STATE}/kits/{f.state_doc()['kits']['job/J85']['kit']}/manifest.json"] = b'{}'
        f.acts.clear()
        f.problems = [f.problems[0].replace('holds 0 ', 'holds 7 ')]
        f.proc = Proc(['acceptance pass 1: pass (x)'])
        return f

    def test_twenty_minus_the_streak_on_the_same_kit_with_no_build(self):
        f = self.stop_once()
        kit = f.state_doc()['kits']['job/J85']['kit']
        tick(f)
        self.assertNotIn('build', f.kinds())
        install = next(a for a in f.acts if a[:2] == ('pc_deploy', 'install'))
        self.assertIn(kit, install[3])
        start = next(a for a in f.acts if a[0] == 'start')
        self.assertEqual(start[start.index('--passes') + 1], '13')

    def test_a_new_run_id_each_time(self):
        f = self.stop_once()
        f.files[str(WT / 'harness/runs' / f'{auto.stamp_of(START)[:8]}_j85auto1')] = b''
        tick(f)
        start = next(a for a in f.acts if a[0] == 'start')
        self.assertTrue(start[start.index('--run') + 1].endswith('auto2'))

    def test_a_flake_in_the_streak_lowers_the_new_runs_allowance(self):
        f = self.stop_once()
        f.ledger = '\n'.join(json.dumps({'result': r}) for r in ['fail'] + ['pass'] * 3 + ['flake'] + ['pass'] * 4) + '\n'
        tick(f)
        start = next(a for a in f.acts if a[0] == 'start')
        self.assertEqual(start[start.index('--max-flakes') + 1], '0')

    def test_a_lost_kit_builds_again(self):
        f = self.stop_once()
        for k in [k for k in f.files if k.endswith('manifest.json')]:
            del f.files[k]
        tick(f)
        self.assertIn('build', f.kinds())


class Push(Base):
    def test_a_moved_remote_head_with_a_new_build_never_pushes(self):
        f = Fake()
        f.remote_head, f.remote_build = 'e' * 40, 'dddddddddddd'
        tick(f)
        self.assertFalse(any(a[:2] == ('git', 'push') for a in f.acts))
        self.assertFalse(any(a[:2] == ('git', 'rebase') for a in f.acts))
        self.assertTrue(any(a[:2] == ('git', 'update-ref') for a in f.acts), 'the commit stays reachable')
        self.assertIs(f.result()['pushed'], False)

    def test_a_moved_remote_head_with_the_same_build_rebases_and_pushes(self):
        f = Fake()
        f.remote_head = 'e' * 40
        tick(f)
        self.assertTrue(any(a[:2] == ('git', 'rebase') for a in f.acts))
        self.assertTrue(any(a[:2] == ('git', 'push') for a in f.acts))

    def test_a_rebase_that_is_not_clean_is_aborted_and_left_local(self):
        f = Fake()
        f.remote_head, f.rebase_rc = 'e' * 40, 1
        tick(f)
        self.assertIn(('git', 'rebase', '--abort'), f.acts)
        self.assertFalse(any(a[:2] == ('git', 'push') for a in f.acts))

    def test_a_refused_push_is_left_local(self):
        f = Fake()
        f.push_rc = 1
        tick(f)
        self.assertTrue(any(a[:2] == ('git', 'update-ref') for a in f.acts))

    def test_the_trailer_passes_the_commit_rule(self):
        from warscape import trailer
        msg = auto.commit_message('J85', '20261107_j85auto1', 'stopped', 'acceptance-auto-20261107t120000z')
        self.assertIsNone(trailer.message_problem(msg))
        f = Fake()
        tick(f)
        commit = next(a for a in f.acts if a[:2] == ('git', 'commit'))
        self.assertIsNone(trailer.message_problem(commit[commit.index('-m') + 1]))
        self.assertIn(f.session, commit[commit.index('-m') + 1])

    def test_only_the_ledger_and_the_runs_folder_are_added(self):
        f = Fake()
        f.files[str(WT / auto.LEDGER)] = b''
        rid = f'{auto.stamp_of(START)[:8]}_j85auto1'
        f.proc = Proc(['go'], after={'go': lambda: f.files.__setitem__(str(WT / 'harness/runs' / rid), b'')})
        tick(f)
        add = next(a for a in f.acts if a[:2] == ('git', 'add'))
        self.assertEqual(add[3:], (auto.LEDGER, f'harness/runs/{rid}'))

    def test_never_force_no_bypass(self):
        src = (ROOT / 'tools' / 'acceptance_auto.py').read_text(encoding='utf-8')
        code = '\n'.join(l for l in src.splitlines() if not l.lstrip().startswith('#') and 'usage:' not in l)
        for bad in ('--no-verify', "'--force'", '--force-with-lease', "'-f'", 'baseline.json\'', 'report.md\''):
            self.assertNotIn(bad, code)
        self.assertNotIn("git('merge'", code)
        self.assertNotIn('reg set', code)


class Watcher(Base):
    def differs(self, f, name):
        f.files[str(WT / 'core/harness' / name)] = b'new\r\n'

    def test_crlf_is_no_difference(self):
        f = Fake()
        f.files[str(SRC / 'watcher.ps1')] = b'same\n'
        tick(f)
        self.assertNotIn(('job.sh', f.session, '-', 'update kit=harness_1\n'), f.acts)
        self.assertIn('build', f.kinds())

    def test_watch_cmd_differing_refuses_before_any_kit(self):
        f = Fake()
        self.differs(f, 'watch.cmd')
        tick(f)
        self.assertEqual(f.result()['action'], 'refused')
        self.assertIn('Install watcher.cmd', f.result()['reason'])
        self.assertEqual([k for k in f.kinds() if k.startswith('pc_deploy')], [])

    def test_an_update_goes_on_only_when_confirmed(self):
        f = Fake()
        self.differs(f, 'update.ps1')
        tick(f)
        self.assertLess(f.kinds().index('job.sh'), f.kinds().index('build'), 'the watcher follows HEAD before anything is built')
        f = Fake()
        self.differs(f, 'update.ps1')
        f.update_verdict = 'REVERTED'
        tick(f)
        self.assertEqual(f.result()['action'], 'refused')
        self.assertNotIn('build', f.kinds())


class CrashCleanup(Base):
    def dead(self, f, kit='kit_mine'):
        run = {'run_id': 'r1', 'job': 'J85', 'branch': 'job/J85', 'head': HEAD, 'blob': BLOB, 'build_id': BUILD, 'kit': kit, 'installed': kit, 'owner': 'acceptance-auto-x', 'session': 'acceptance-auto-x',
               'pid': 50, 'pid_created': 1, 'child_pid': 51, 'child_created': 1, 'layout': 'D', 'layout_key': [], 'input0': 1}
        f.seed({'run': run})
        return run

    def test_cleans_what_it_owned_and_commits(self):
        f = Fake()
        self.dead(f)
        f.deploy_status = (0, f'pc_deploy status: kit kit_mine build {BUILD} installed x\n')
        f.status.update(lock={'owner': 'acceptance-auto-x'}, game_state={'state': 'running'})
        tick(f)
        self.assertIn(('job.sh', 'acceptance-auto-x', '-', 'kill\n'), f.acts)
        self.assertIn('pc_deploy uninstall', f.kinds())
        self.assertTrue(any(a[:2] == ('git', 'push') for a in f.acts))
        self.assertNotIn('run', f.state_doc())
        self.assertNotIn('consumed', f.state_doc())

    def test_leaves_another_jobs_kit_alone(self):
        f = Fake()
        self.dead(f)
        f.deploy_status = (0, 'pc_deploy status: kit kit_other build x installed y\n')
        tick(f)
        self.assertNotIn('pc_deploy uninstall', f.kinds())
        self.assertIn('not ours', ' '.join(f.result()['notes']))

    def test_leaves_another_owners_lock_alone(self):
        f = Fake()
        self.dead(f)
        f.status['lock'] = {'owner': 'someone'}
        tick(f)
        self.assertEqual([a for a in f.acts if a[0] == 'job.sh'], [])
        self.assertIn('run', f.state_doc())

    def test_a_reused_child_pid_is_not_killed(self):
        f = Fake()
        self.dead(f)
        tick(f)
        self.assertEqual([a for a in f.acts if a[0] == 'kill_tree'], [])

    def test_a_surviving_child_is_ended(self):
        f = Fake()
        self.dead(f)
        f.alive_pids = {51}
        tick(f)
        self.assertIn(('kill_tree', 51), f.acts)

    def test_waits_for_the_person_guards(self):
        f = Fake()
        self.dead(f)
        f.idle = 5
        tick(f)
        self.assertEqual(f.acts, [])

    def test_dry_run_only_says_so(self):
        f = Fake()
        self.dead(f)
        tick(f, dry_run=True)
        self.assertEqual(f.acts, [])


class Pure(unittest.TestCase):
    def test_the_streak_is_read_from_the_gates_own_words(self):
        """Holds the regex to the one reader: a real acceptance_problems message."""
        acc = {'active': True, 'ledger': '', 'build_id': 'b', 'watcher': 'w', 'branch': 'job/J1', 'exists': lambda p: True}
        problems = gate.acceptance_problems(['harness/x.ps1'], acc)
        self.assertEqual(auto.rule79_reading(problems), (True, 0, []))
        self.assertEqual(auto.rule79_reading([problems[0].replace('holds 0 ', 'holds 12 ')]), (True, 12, []))
        self.assertEqual(auto.rule79_reading([]), (False, None, []))

    def test_layouts(self):
        d = [{'hw': 'DEL41DB', 'primary': True}, {'hw': 'MTT1337'}]
        m = [{'hw': 'MSI3CB0', 'primary': True}, {'hw': 'DEL41DB'}, {'hw': 'MTT1337'}]
        self.assertEqual((auto.layout_name(d), auto.layout_name(m), auto.layout_name([])), ('D', 'M', '?'))
        self.assertNotEqual(auto.layout_key(d), auto.layout_key(m))

    def test_flakes_in_streak(self):
        led = '\n'.join(json.dumps({'result': r}) for r in ('flake', 'pass', 'flake', 'pass')) + '\n'
        self.assertEqual(auto.flakes_in_streak(led, 1), 0)
        self.assertEqual(auto.flakes_in_streak(led, 2), 1)
        self.assertEqual(auto.flakes_in_streak('', 0), 0)

    def test_the_real_task_is_created_disabled_and_the_proof_has_no_trigger(self):
        real = auto.task_script('install', auto.TASK, 'py', 'tool.py', ['tick'], 'root')
        self.assertIn('-Disable', real)
        self.assertIn('-LogonType Interactive', real)
        self.assertIn('-MultipleInstances IgnoreNew', real)
        self.assertIn('-Minutes 30', real)
        proof = auto.task_script('install', auto.PROOF_TASK, 'py', 'tool.py', ['tick'], 'root')
        self.assertNotIn('-Disable', proof)
        self.assertNotIn('New-ScheduledTaskTrigger', proof)

    def test_overrides_are_for_a_scratch_branch_only(self):
        for argv in (['tick', '--passes', '3'], ['tick', '--branch', 'job/J85', '--job', 'J85'], ['tick', '--ignore-session', 'x'], ['tick', '--branch', 'scratch/x']):
            self.assertEqual(auto.main(argv, Fake()), 2)

    def test_git_is_refused_in_a_game_or_state_folder(self):
        s = auto.Real.__new__(auto.Real)
        s.root, s.state, s.game = ROOT, Path('C:/st'), Path('C:/game')
        s._run = lambda *a, **k: (0, '')
        for where in ('C:/st', 'C:/st/_scratch/x', 'C:/game/data'):
            with self.assertRaises(RuntimeError):
                s.git('status', cwd=where)
        self.assertEqual(s.git('status'), (0, ''))


if __name__ == '__main__':
    unittest.main()
