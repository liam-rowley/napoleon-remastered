#!/usr/bin/env python3
"""Unattended rule 79 runs (J85): a scheduled tick that runs the acceptance passes for a job branch that asks for them, while nobody is at the PC.

purpose: a plain script, fired by a scheduled task, that takes one job branch with a committed acceptance request, checks the PC is free, brings the watcher to the branch's core, builds and installs its DLL, runs core/harness/acceptance.py, stops between passes when Liam comes back, uninstalls, and commits and pushes the ledger lines and evidence
usage: acceptance_auto.py tick [--dry-run] [--present-file F] [--branch B --job J<n> --passes N --ignore-session ID] | request --job J<n> | status | task install|remove|enable|disable [--proof [--passes N]] | launch <tick args>   (--branch, --passes and --ignore-session are for scratch/ proof branches only)
when: a builder whose final build needs its 20 passes runs `request` on the job branch, commits, pushes and ends; the task then fires `tick` every 30 minutes once Liam has run `task enable`; harness/README.md, "Unattended acceptance"
not-a-verb: a PC runner on top of core/harness/acceptance.py and job.sh, started by the Task Scheduler with no session around it; it reads the rule 79 gate, it is not a registry operation

Rules the Claude Code hook keeps for a session and no hook keeps for this script, so it keeps them itself: the game starts and stops only through job.sh, nothing is written into
a game folder except by pc_deploy.py, git never runs in a game or state folder (`Real.git` refuses), no force push, no hook bypass, no edit of baseline.json or a limit, no report.md,
no row, no merge. `<state>/liam_present` is only ever read. A reading that fails is a refusal: every guard fails closed.

One tick: a live run ends the tick; then liam_present and the idle time; then a dead run of ours is cleaned up by the stop route; then the lock and profile, pc_deploy status, a working
session and free memory; then the oldest eligible request, Docker only when it needs a build. A refusal is one log line, exit 0, nothing touched.
Identity: one id per run, acceptance-auto-<utc stamp>, as --owner, --session and the Claude-Session trailer, never a real session's id.
Passes are counted by tools/gates/pipeline.py acceptance_problems and nothing else, so a stopped run is finished by a later one on the same kit (`dll_sha256` holds).
"""
import argparse
import ctypes
import datetime
import hashlib
import importlib.util
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core'))
sys.path.insert(0, str(ROOT / 'core' / 'proxy' / 'tools'))
sys.path.insert(0, str(ROOT / 'tools'))

IDLE_MIN_S = 1800        # J85 open question 2: 30 minutes without input before a run starts
MIN_FREE_GB = 8          # J64 run 20261104_j64pc5 failed a load at 5.9 GB free
HARD_LIMIT_S = 4 * 3600  # decision 6
STOP_GRACE_S = 1800      # a stop waits for the next pass line; a pass takes about 8 minutes, so a run that is silent this long is ended where it stands
INSTALL_WAIT_S = 300     # J78's preflight: 5 minutes after the install
POLL_S = 5
UPDATE_WAIT_S = 360
TASK = 'napoleon_remastered acceptance-auto'
PROOF_TASK = 'napoleon_remastered acceptance-auto proof'
PROOF_BRANCH, PROOF_JOB = 'scratch/j85-proof', 'J85'
SCRATCH_OWNER = 'acceptance-auto'
RUNNABLE_ROWS = ('queued', 'fix')   # decision 3: so the autopilot starts no review before the passes
QUIET_SESSION = ('idle', 'done', 'blocked', 'stopped', 'failed')   # any other state counts as working: an unknown word refuses
STOP_LINE = re.compile(r'^acceptance pass \d+: pass\b|^acceptance: flake (\d+) of (\d+) allowed')
STREAK_RX = re.compile(r'holds (\d+) consecutive acceptance passes')
KIT_RX = re.compile(r'^pc_deploy kit: (.+?) \(\d+ files', re.M)
UPDATE_LOG_RX = re.compile(r'log: (\S.*?update\.log)')
UPDATE_VERDICT = re.compile(r'\b(CONFIRMED|REVERTED|REVERT COPY FAILED|ABORT|NOTHING TO DO)\b')
LEDGER = 'harness/acceptance/ledger.jsonl'


class Refused(Exception):
    """A guard said no: one log line, exit 0, nothing touched."""


def utc_of(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def stamp_of(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y%m%dt%H%M%Sz')


def lf(b):
    return None if b is None else b.replace(b'\r\n', b'\n')


def request_path(job):
    return f'jobs/{job}/acceptance_request.json'


# ---- pure readings ------------------------------------------------------------------------------------------------------
def layout_name(monitors):
    """J101's letters from the vendor ids: the MSI present is M, the Dell without it D (never a resolution: DPI scaling misleads)."""
    ids = [m['hw'][:3].upper() for m in monitors]
    return 'M' if 'MSI' in ids else 'D' if 'DEL' in ids else '?'


def layout_key(monitors):
    """What a layout change is: the monitors present and the primary, not their rects (a launch changes the virtual display's mode on purpose)."""
    return sorted(m['hw'] + ('*' if m.get('primary') else '') for m in monitors)


def deploy_problem(rc, text):
    """Why `pc_deploy.py status` refuses a run, or None. Nothing may be installed at the start of a run: ours is uninstalled at the end of every run."""
    first = (text.strip().splitlines() or [''])[0]
    if 'not installed by this tool' not in first:
        return f"something is installed: {first or 'pc_deploy status said nothing'}"
    if rc != 0:
        return 'pc_deploy status fails: ' + ' | '.join(l.strip() for l in text.splitlines()[1:] if not re.match(r'\s*(?:exe: ok|git: ok|foreign: not checked)', l))
    return None


def working_sessions(rows, ignore=None):
    return [r.get('name') or r.get('sessionId') or '?' for r in rows if (r.get('state') or r.get('status') or 'unknown') not in QUIET_SESSION and r.get('sessionId') != ignore]


def rule79_reading(problems):
    """(needed, streak, other problems) from acceptance_problems' answer. The count is that function's own: this file holds no second streak counter."""
    mine = [p for p in problems if p.startswith('rule 79:')]
    other = [p for p in problems if not p.startswith('rule 79:')]
    if not mine:
        return False, None, other
    m = STREAK_RX.search(mine[0])
    return True, int(m.group(1)) if m else None, other


def flakes_in_streak(ledger, n):
    """Flake lines among the last `n` passes: the gate allows a line's flakes_allowed across the whole streak, while a run's allowance starts again, so a resumed run gets what is left."""
    seen = flakes = 0
    for line in reversed([l for l in (ledger or '').splitlines() if l.strip()]):
        if seen >= n:
            break
        r = json.loads(line).get('result')
        seen += r == 'pass'
        flakes += r == 'flake'
    return flakes


def stop_point(line):
    """Where a wanted stop may end the run: after a pass, or a flake the allowance covers. A FAIL, or the flake that spends the allowance, goes on to acceptance.py's own exit 1, so it consumes the request (decision 9)."""
    m = STOP_LINE.match(line)
    return bool(m) and (m.group(1) is None or int(m.group(1)) <= int(m.group(2)))


def commit_message(job, run_id, outcome, session):
    """The ledger commit: the trailer alone in the last paragraph, where git reads one (core/warscape/trailer.py)."""
    return f'{job}: acceptance run {run_id}, {outcome}\n\nClaude-Session: {session}\n'


def task_script(action, name, python, tool, args, root):
    """The PowerShell for `task <action>`. install: the current user, interactive logon, no admin, created disabled, every 30 minutes (a proof task has no time trigger)."""
    q = lambda s: "'" + str(s).replace("'", "''") + "'"
    if action == 'remove':
        return f'Unregister-ScheduledTask -TaskName {q(name)} -Confirm:$false -ErrorAction Stop'
    if action == 'enable':
        return f'Enable-ScheduledTask -TaskName {q(name)} -ErrorAction Stop | Out-Null'
    if action == 'disable':
        return f'Disable-ScheduledTask -TaskName {q(name)} -ErrorAction Stop | Out-Null'
    arg = ' '.join(f'"{a}"' if ' ' in str(a) else str(a) for a in (tool, 'launch', *args))
    proof = name == PROOF_TASK
    lines = [f'$a = New-ScheduledTaskAction -Execute {q(python)} -Argument {q(arg)} -WorkingDirectory {q(root)}',
             '$u = "$env:USERDOMAIN\\$env:USERNAME"',
             '$p = New-ScheduledTaskPrincipal -UserId $u -LogonType Interactive -RunLevel Limited',
             '$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew' + ('' if proof else ' -Disable')]
    if proof:
        lines.append(f'Register-ScheduledTask -TaskName {q(name)} -Action $a -Principal $p -Settings $s -Description {q("J85 proof: on demand only")} -Force | Out-Null')
    else:
        lines.append('$t = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 30)')
        lines.append(f'Register-ScheduledTask -TaskName {q(name)} -Action $a -Trigger $t -Principal $p -Settings $s -Description {q("J85: unattended rule 79 runs; only Liam enables it")} -Force | Out-Null')
    lines.append(f'$x = Get-ScheduledTask -TaskName {q(name)}; "$($x.TaskName) state=$($x.State) action=$($x.Actions[0].Execute) $($x.Actions[0].Arguments)"')
    return '; '.join(lines)


# ---- the PC: every side effect goes through this, and the tests replace it --------------------------------------------------
class RunProc:
    """acceptance.py as a child, its output through a queue so the loop can look up between lines."""
    def __init__(self, argv, cwd, env):
        self.p = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', bufsize=1)
        self.pid = self.p.pid
        self.q = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.p.stdout:
            self.q.put(line.rstrip('\r\n'))
        self.q.put(None)

    def next_line(self, timeout):
        """A line, '' on a timeout, None at the end of the output."""
        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return ''

    def stop(self):
        kill_tree(self.pid)

    def wait(self):
        return self.p.wait()


def kill_tree(pid):
    """Ends acceptance.py and its bash children. The game is the watcher's child and is not in this tree: it goes through job.sh."""
    subprocess.run(['taskkill', '/T', '/F', '/PID', str(pid)], capture_output=True)


class Real:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.adapter = json.loads((self.root / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
        self.state = Path(os.environ.get('NAPOLEON_STATE_DIR') or self.adapter['state_dir'])
        self.game = Path(self.adapter['game_dir'])
        self.session = None   # the run's id, exported to job.sh and pc_deploy.py
        self.offline = False  # a dry run fetches nothing
        common = self._common_dir()
        self.worktree = common / '.claude' / 'worktrees' / 'acceptance-auto'

    def _common_dir(self):
        # CREATE_NO_WINDOW: under pythonw (the task's first process) a console child would open a window
        r = subprocess.run(['git', '-C', str(self.root), 'rev-parse', '--path-format=absolute', '--git-common-dir'], capture_output=True, text=True, creationflags=0x08000000)
        return Path(r.stdout.strip()).parent if r.returncode == 0 and r.stdout.strip() else self.root

    # clock and readings
    def now(self):
        return time.time()

    def sleep(self, s):
        time.sleep(s)

    def pid(self):
        return os.getpid()

    def last_input(self):
        """GetLastInputInfo's tick, or None when it cannot be read (needs the logon session)."""
        class LII(ctypes.Structure):
            _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
        li = LII(ctypes.sizeof(LII), 0)
        return li.dwTime if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)) else None

    def idle_s(self):
        t = self.last_input()
        if t is None:
            return None
        ctypes.windll.kernel32.GetTickCount.restype = ctypes.c_uint
        return ((ctypes.windll.kernel32.GetTickCount() - t) & 0xffffffff) / 1000

    def free_gb(self):
        class MS(ctypes.Structure):
            _fields_ = [('l', ctypes.c_uint), ('load', ctypes.c_uint), ('total', ctypes.c_ulonglong), ('avail', ctypes.c_ulonglong), ('tpf', ctypes.c_ulonglong), ('apf', ctypes.c_ulonglong),
                        ('tv', ctypes.c_ulonglong), ('av', ctypes.c_ulonglong), ('ave', ctypes.c_ulonglong)]
        m = MS(ctypes.sizeof(MS))
        return m.avail / 2**30 if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)) else None

    def monitors(self):
        """[{hw, primary}], no process start: EnumDisplayDevices, the vendor and product from each attached monitor's interface name."""
        from ctypes import wintypes as w

        class DD(ctypes.Structure):
            _fields_ = [('cb', w.DWORD), ('DeviceName', w.WCHAR * 32), ('DeviceString', w.WCHAR * 128), ('StateFlags', w.DWORD), ('DeviceID', w.WCHAR * 128), ('DeviceKey', w.WCHAR * 128)]
        enum, out, i = ctypes.windll.user32.EnumDisplayDevicesW, [], 0
        while True:
            a = DD()
            a.cb = ctypes.sizeof(a)
            if not enum(None, i, ctypes.byref(a), 0):
                return out
            i += 1
            if not a.StateFlags & 1:
                continue
            m = DD()
            m.cb = ctypes.sizeof(m)
            if enum(a.DeviceName, 0, ctypes.byref(m), 1):
                parts = m.DeviceID.split('#')
                out.append({'hw': parts[1] if len(parts) > 1 else m.DeviceString, 'primary': bool(a.StateFlags & 4)})

    def alive(self, pid, created):
        now = self.created(pid) if pid else None
        return now is not None and now == created

    def created(self, pid):
        """The process's start time, so a reused pid is no match; None when it is gone."""
        k = ctypes.windll.kernel32
        k.OpenProcess.restype = ctypes.c_void_p
        h = k.OpenProcess(0x1000, False, int(pid))
        if not h:
            return None
        h = ctypes.c_void_p(h)
        try:
            c, e, kk, u, code = (ctypes.c_ulonglong() for _ in range(5))
            ok = k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kk), ctypes.byref(u))
            k.GetExitCodeProcess(h, ctypes.byref(code))
            return c.value if ok and (code.value & 0xffffffff) == 259 else None
        finally:
            k.CloseHandle(h)

    def keep_awake(self, on):
        """SetThreadExecutionState for this thread: no power plan is changed."""
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 if on else 0x80000000)

    # processes
    def env(self):
        e = dict(os.environ, PYTHONUNBUFFERED='1', PYTHONUTF8='1')
        e.pop('CLAUDE_CODE_SESSION_ID', None)   # never a real session's id: the run's own, or none
        if self.session:
            e['WSC_SESSION_ID'] = self.session
        return e

    def _run(self, argv, cwd=None, input=None, timeout=None):
        try:
            p = subprocess.run(argv, cwd=str(cwd or self.root), env=self.env(), input=input, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
            return p.returncode, (p.stdout or '') + (p.stderr or '')
        except (OSError, subprocess.TimeoutExpired) as e:
            return 124, f'{type(e).__name__}: {e}'

    def git(self, *args, cwd=None, input=None):
        where = Path(cwd or self.root).resolve()
        for bad in (self.state, self.game):
            if where == bad.resolve() or bad.resolve() in where.parents:
                raise RuntimeError(f'git refused in {where}: never in a game or state folder')
        return self._run(['git', *args], cwd=where, input=input)

    def bash(self, *args, cwd=None, input=None, timeout=None):
        from warscape import gitbash
        return self._run([gitbash.git_bash() or 'bash', *args], cwd=cwd, input=input, timeout=timeout)

    def job_sh(self, *args, input=None, timeout=200):
        return self.bash(str(self.root / 'core' / 'harness' / 'job.sh'), *args, input=input, timeout=timeout)

    def pc_deploy(self, *args, cwd=None, timeout=1800):
        base = Path(cwd or self.root)
        return self._run([sys.executable, str(base / 'core' / 'proxy' / 'tools' / 'pc_deploy.py'), *args], cwd=base, timeout=timeout)

    def build(self, cwd):
        return self.bash('core/proxy/tools/build.sh', '--docker', 'all', cwd=cwd, timeout=3600)

    def build_id(self, cwd):
        return self._run([sys.executable, 'core/proxy/tools/build_id.py'], cwd=cwd, timeout=120)

    def docker_ok(self):
        return self._run(['docker', 'version', '--format', '{{.Server.Version}}'], timeout=30)[0] == 0

    def agents(self):
        """`claude agents --json`, or None when it cannot be read."""
        exe = shutil.which('claude') or str(Path.home() / '.local' / 'bin' / 'claude.exe')
        rc, out = self._run([exe, 'agents', '--json'], timeout=60)
        try:
            return json.loads(out[out.index('['):]) if rc == 0 else None
        except ValueError:
            return None

    def start(self, argv, cwd):
        return RunProc(argv, cwd, self.env())

    def kill_tree(self, pid):
        kill_tree(pid)

    def powershell(self, script):
        return self._run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script], timeout=120)

    # the gate: the only reader of rule 79
    def rule79(self, branch, head, main):
        """(acc, problems) from tools/gates/pipeline.py for this branch at this head, or (None, [why])."""
        rc, pin = self.git('rev-parse', f'{head}:core')
        if rc == 0 and not self.offline and self.git('cat-file', '-e', pin.strip(), cwd=self.root / 'core')[0] != 0:
            self.git('fetch', 'origin', pin.strip(), cwd=self.root / 'core')
        rc, mb = self.git('merge-base', main, head)
        if rc:
            return None, [f'no merge base with main: {mb.strip()}']
        mb = mb.strip()
        rc, names = self.git('diff', '--name-only', '--no-renames', mb, head)
        if rc:
            return None, [f'git diff failed: {names.strip()}']
        changed = [l for l in names.splitlines() if l]
        spec = importlib.util.spec_from_file_location('j85_pipeline', self.root / 'tools' / 'gates' / 'pipeline.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        acc = mod.collect_acceptance(self.root, {'repo': str(self.root), 'head': head, 'base': main, 'merge_base': mb, 'changed': changed, 'branch': branch})
        return acc, mod.acceptance_problems(changed, acc)

    # files
    def read_bytes(self, p):
        try:
            return Path(p).read_bytes()
        except OSError:
            return None

    def exists(self, p):
        return Path(p).exists()

    def write_text(self, p, text):
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(p) + '.tmp')
        tmp.write_text(text, encoding='utf-8', newline='\n')
        tmp.replace(p)

    def append_text(self, p, text):
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'a', encoding='utf-8', newline='\n') as f:
            f.write(text)

    def profile_files(self, cwd):
        base = Path(cwd) / 'harness' / 'napoleon' / 'profiles'
        return [p.relative_to(base).as_posix() for p in sorted(base.rglob('*')) if p.is_file()]


# ---- the tick ---------------------------------------------------------------------------------------------------------------
class Tick:
    def __init__(self, s, a):
        self.s, self.a = s, a
        self.dry = s.offline = bool(getattr(a, 'dry_run', False))
        self.info, self.owner = None, None
        self.scratch = s.state / '_scratch' / SCRATCH_OWNER
        self.state_file, self.log_file, self.result_file = self.scratch / 'state.json', self.scratch / 'tick.log', self.scratch / 'last_result.json'
        self.present = [s.state / 'liam_present'] + ([Path(a.present_file)] if getattr(a, 'present_file', None) else [])

    # state and logs
    def load(self):
        b = self.s.read_bytes(self.state_file)
        return json.loads(b.decode('utf-8')) if b else {}

    def save(self, st):
        self.s.write_text(self.state_file, json.dumps(st, indent=1) + '\n')

    def log(self, msg):
        line = f'{utc_of(self.s.now())} {msg}'
        print(line, flush=True)
        if not self.dry:
            self.s.append_text(self.log_file, line + '\n')

    def done(self, action, reason, **extra):
        """The tick's one result: the log line, and last_result.json (what the last tick or run did and why)."""
        self.log(f'{action}: {reason}')
        if not self.dry:
            self.s.write_text(self.result_file, json.dumps({'utc': utc_of(self.s.now()), 'action': action, 'reason': reason, **extra}, indent=1) + '\n')
        return 0

    # decision 4, cheapest first
    def person_guards(self):
        for f in self.present:
            if self.s.exists(f):
                raise Refused(f'{f} exists')
        idle = self.s.idle_s()
        if idle is None:
            raise Refused('the idle time cannot be read')
        if idle < IDLE_MIN_S:
            raise Refused(f'idle {int(idle)} s, under {IDLE_MIN_S} s')

    def pc_guards(self):
        st = self.watcher_status()
        if st.get('lock') or st.get('foreign_lock'):
            raise Refused(f"the game lock is held ({(st.get('lock') or st.get('foreign_lock'))})")
        if st.get('profile_active'):
            raise Refused(f"a profile is active ({st['profile_active']})")
        if (st.get('game_state') or {}).get('state') != 'not_running':
            raise Refused(f"the game is {(st.get('game_state') or {}).get('state')}")
        if st.get('zombie') or st.get('needs_reboot'):
            raise Refused('the watcher reports a zombie or needs a reboot')
        why = deploy_problem(*self.deploy('status'))
        if why:
            raise Refused(why)
        rows = self.s.agents()
        if rows is None:
            raise Refused('claude agents cannot be read')
        busy = working_sessions(rows, getattr(self.a, 'ignore_session', None))
        if busy:
            raise Refused(f"a session is working: {', '.join(busy)}")
        free = self.s.free_gb()
        if free is None or free < MIN_FREE_GB:
            raise Refused(f'free memory {free if free is None else round(free, 1)} GB, under {MIN_FREE_GB} GB')

    def watcher_status(self):
        rc, out = self.s.job_sh('status')
        try:
            st = json.loads(out[out.index('{'):])
        except ValueError:
            raise Refused(f'job.sh status cannot be read (exit {rc})') from None
        beat = st.get('heartbeat_utc')
        try:
            age = self.s.now() - datetime.datetime.strptime(beat, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()
        except (TypeError, ValueError):
            raise Refused('the watcher reports no heartbeat') from None
        if age > 60:
            raise Refused(f'the watcher is not running (heartbeat {int(age)} s old)')
        return st

    def deploy(self, verb, *args, cwd=None):
        return self.s.pc_deploy(verb, *args, '--game', str(self.s.game), '--state', str(self.s.state), cwd=cwd)

    # decision 3
    def requests(self, st):
        """[(branch, job, head, blob, doc)], oldest request first, without the ones a fail consumed."""
        a = self.a
        if getattr(a, 'branch', None):
            rc, out = self.s.git('rev-parse', f'refs/remotes/origin/{a.branch}')
            refs = [(a.branch, a.job, out.strip())] if rc == 0 else []
        else:
            rc, out = self.s.git('for-each-ref', '--format=%(refname:short) %(objectname)', 'refs/remotes/origin/job/')
            refs = []
            for line in out.splitlines() if rc == 0 else []:
                name, sha = line.split()
                branch = name.split('/', 1)[1]
                refs.append((branch, branch.split('/', 1)[1], sha))
        if not refs:
            return []
        rc, out = self.s.git('cat-file', '--batch-check', input=''.join(f'{sha}:{request_path(job)}\n' for _, job, sha in refs))
        got = []
        for (branch, job, sha), line in zip(refs, out.splitlines()):
            if ' blob ' not in line:
                continue
            blob = line.split()[0]
            if blob in st.get('consumed', {}).get(branch, []):
                continue
            rc, text = self.s.git('cat-file', 'blob', blob)
            try:
                got.append((branch, job, sha, blob, json.loads(text)))
            except ValueError:
                self.log(f'skip {branch}: {request_path(job)} is not JSON')
        return sorted(got, key=lambda r: (str(r[4].get('requested_utc') or ''), r[0]))

    def row(self, ref, job):
        rc, text = self.s.git('show', f'{ref}:registries/jobs/{job}.json')
        try:
            return json.loads(text) if rc == 0 else None
        except ValueError:
            return None

    def why_not(self, branch, job, head, doc, main):
        """Why this request is not taken, or None and fills self.info."""
        on_main, here = self.row(main, job), self.row(head, job)
        if on_main is None or on_main.get('status') == 'done':
            return f"the row on main is {on_main and on_main.get('status')}"
        if here is None or here.get('status') not in RUNNABLE_ROWS:
            return f"the row on the branch is {here and here.get('status')}"
        acc, problems = self.s.rule79(branch, head, main)
        if acc is None:
            return problems[0]
        if acc.get('build_id') != doc.get('build_id'):
            return f"the request is for build {doc.get('build_id')}, head is {acc.get('build_id')}"
        if acc.get('watcher_sha') and acc['watcher_sha'] != doc.get('watcher_sha'):
            return f"the request is for watcher {str(doc.get('watcher_sha'))[:12]}, head is {acc['watcher_sha'][:12]}"
        needed, streak, other = rule79_reading(problems)
        if other:
            return f'the ledger or evidence is refused: {other[0]}'
        if not needed:
            return 'rule 79 is satisfied'
        if streak is None:
            return 'rule 79 fails but names no count'
        self.info = {'build_id': acc['build_id'], 'watcher_sha': acc.get('watcher_sha'), 'watcher': acc.get('watcher'), 'streak': streak, 'ledger': acc.get('ledger')}
        return None

    def pick(self, st):
        if not self.dry:
            self.s.git('fetch', '--quiet', 'origin', '+refs/heads/main:refs/remotes/origin/main', '+refs/heads/job/*:refs/remotes/origin/job/*',
                       *([f'+refs/heads/{self.a.branch}:refs/remotes/origin/{self.a.branch}'] if getattr(self.a, 'branch', None) else []))
        rc, main = self.s.git('rev-parse', 'refs/remotes/origin/main')
        if rc:
            raise Refused('origin/main cannot be read')
        main = main.strip()
        for branch, job, head, blob, doc in self.requests(st):
            why = self.why_not(branch, job, head, doc, main)
            if why is None:
                return {'branch': branch, 'job': job, 'head': head, 'blob': blob, **self.info}
            self.log(f'skip {branch}: {why}')
        return None

    # decision 5
    def watcher_diff(self, cwd):
        """The installed files the checkout's core or adapter differs from, with LF line endings, as acceptance.py compares."""
        import pc_deploy
        root = self.s.state / self.s.adapter.get('watcher_subdir', 'watcher')
        cwd = Path(cwd)
        pairs = [(cwd / 'core' / 'harness' / n, root / 'src' / n, 'src/' + n) for n in pc_deploy.HARNESS_SRC]
        pairs.append((cwd / 'harness' / 'napoleon' / 'adapter.json', root / 'src' / 'adapter.json', 'src/adapter.json'))
        pairs.append((cwd / 'proxy' / 'napoleon' / 'identity.json', root / 'src' / 'exe_identity.json', 'src/exe_identity.json'))
        pairs += [(cwd / 'harness' / 'napoleon' / 'profiles' / n, root / 'profiles' / n, 'profiles/' + n) for n in self.s.profile_files(cwd)]
        return [rel for want, have, rel in pairs if lf(self.s.read_bytes(want)) != lf(self.s.read_bytes(have))]

    def follow_watcher(self, cwd):
        diff = self.watcher_diff(cwd)
        if not diff:
            return
        if 'src/watch.cmd' in diff:
            raise Refused("watch.cmd differs: `Install watcher.cmd` is Liam's, a double-click (J64 open question 4)")
        self.log(f"the watcher differs from the core: {', '.join(diff)}")
        rc, out = self.s.pc_deploy('kit', '--what', 'harness', cwd=cwd)
        m = KIT_RX.search(out)
        if rc or not m:
            raise Refused(f'pc_deploy kit --what harness failed: {out.strip()[-200:]}')
        kit = Path(m.group(1))
        rc, out = self.s.pc_deploy('send', '--kit', str(kit), '--state', str(self.s.state), cwd=cwd)
        if rc:
            raise Refused(f'pc_deploy send failed: {out.strip()[-200:]}')
        rc, out = self.s.job_sh(self.owner, '-', input=f'update kit={kit.name}\n')
        m = UPDATE_LOG_RX.search(out)
        if rc or not m:
            raise Refused(f'the update job failed (exit {rc}): {out.strip()[-200:]}')
        verdict = self.update_verdict(Path(m.group(1)))
        if verdict != 'CONFIRMED':
            raise Refused(f'the update of kit {kit.name} ended {verdict}')
        self.log(f'watcher updated from kit {kit.name}: CONFIRMED')

    def update_verdict(self, path):
        for _ in range(UPDATE_WAIT_S // POLL_S):
            b = self.s.read_bytes(path)
            hits = UPDATE_VERDICT.findall(b.decode('utf-8', 'replace')) if b else []
            if hits:
                return hits[-1]
            self.s.sleep(POLL_S)
        return f'with no verdict in {UPDATE_WAIT_S} s'

    # decision 6
    def prepare_worktree(self, head):
        wt = self.s.worktree
        if not self.s.exists(wt / '.git'):
            rc, out = self.s.git('worktree', 'add', '--detach', str(wt), head)
            if rc:
                raise Refused(f'git worktree add failed: {out.strip()[-200:]}')
        else:
            rc, out = self.s.git('status', '--porcelain', cwd=wt)
            if rc or out.strip():
                raise Refused(f'the worktree is not clean: {out.strip()[:200]}')
            rc, out = self.s.git('checkout', '--quiet', '--detach', head, cwd=wt)
            if rc:
                raise Refused(f'git checkout failed: {out.strip()[-200:]}')
        rc, out = self.s.git('submodule', 'update', '--init', cwd=wt)
        if rc or not self.s.exists(wt / 'core' / 'wsc.py'):   # the commit hook needs core/wsc.py, or every commit is refused
            raise Refused(f'the core submodule did not initialise: {out.strip()[-200:]}')
        return wt

    def build_kit(self, wt, want):
        """Build, check the id, kit and send; the kit id. A build that fails or names another id stops before anything reaches the PC."""
        rc, out = self.s.build(wt)
        if rc:
            raise Refused(f'build.sh --docker all failed (exit {rc}): {out.strip()[-200:]}')
        rc, out = self.s.build_id(wt)
        if out.strip() != want:
            raise Refused(f'build_id.py says {out.strip()}, the request {want}')
        rc, out = self.s.pc_deploy('kit', '--what', 'proxy', cwd=wt)
        m = KIT_RX.search(out)
        if rc or not m:
            raise Refused(f'pc_deploy kit failed: {out.strip()[-200:]}')
        rc, out = self.s.pc_deploy('send', '--kit', m.group(1), '--state', str(self.s.state), cwd=wt)
        if rc:
            raise Refused(f'pc_deploy send failed: {out.strip()[-200:]}')
        return Path(m.group(1)).name

    def run_id(self, job, wt):
        day = stamp_of(self.s.now())[:8]
        n = 1
        while True:
            rid = f'{day}_{job.lower()}auto{n}'
            if not self.s.exists(wt / 'harness' / 'runs' / rid) and not self.s.exists(self.s.state / 'acceptance' / rid):
                return rid
            n += 1

    def passes(self, streak):
        need = 20 - streak
        cap = getattr(self.a, 'passes', None)
        return min(need, cap) if cap else need

    def max_flakes(self, c):
        allowed = (self.s.adapter.get('acceptance') or {}).get('max_flakes', 1)
        return max(0, allowed - flakes_in_streak(c.get('ledger'), c['streak']))

    def start(self, st, c):
        """Decisions 5 to 9 for the picked request. Refusals before the install touch nothing on the PC."""
        kit = st.get('kits', {}).get(c['branch'])
        reuse = bool(kit and kit.get('build_id') == c['build_id'] and self.s.exists(self.s.state / 'kits' / kit['kit'] / 'manifest.json'))
        if not reuse and not self.s.docker_ok():
            raise Refused('Docker does not answer and a build is needed')
        n = self.passes(c['streak'])
        if self.dry:
            return self.done('would run', f"{c['branch']} at {c['head'][:12]}: {n} passes after a streak of {c['streak']}, {'kit ' + kit['kit'] if reuse else 'a new build'}")
        t = self.s.now()
        self.owner = self.s.session = f'{SCRATCH_OWNER}-{stamp_of(t)}'
        wt = self.prepare_worktree(c['head'])
        self.follow_watcher(wt)
        if not reuse:
            kit = {'kit': self.build_kit(wt, c['build_id']), 'build_id': c['build_id']}
            st.setdefault('kits', {})[c['branch']] = kit
            self.save(st)
        mons = self.s.monitors()
        run = {'job': c['job'], 'branch': c['branch'], 'head': c['head'], 'blob': c['blob'], 'build_id': c['build_id'], 'run_id': self.run_id(c['job'], wt), 'owner': self.owner, 'session': self.owner,
               'kit': kit['kit'], 'reused_kit': reuse, 'passes': n, 'streak_before': c['streak'], 'max_flakes': self.max_flakes(c), 'pid': self.s.pid(), 'pid_created': self.s.created(self.s.pid()), 'child_pid': None, 'child_created': None, 'started_utc': utc_of(t),
               'layout': layout_name(mons), 'layout_key': layout_key(mons), 'input0': self.s.last_input(), 'installed': None}
        st['run'] = run
        self.save(st)
        self.log(f"run {run['run_id']} on {c['branch']} {c['head'][:12]}: {n} passes after a streak of {c['streak']}, kit {kit['kit']} ({'reused' if reuse else 'built'}), layout {run['layout']}, owner {self.owner}")
        self.s.keep_awake(True)
        outcome, why = 'stopped', 'an unexpected error'
        try:
            outcome, why = self.execute(st, run, wt)
        except Exception:   # noqa: BLE001  a bug here must still reach the clean-up
            why = traceback.format_exc()[-400:]
            self.log(f'error: {why}')
        finally:
            self.finish(st, run, wt, outcome, why)
            self.s.keep_awake(False)
        return 0

    def execute(self, st, run, wt):
        run['installed'] = run['kit']   # before the install: a crash in it still leaves the clean-up looking for this kit
        self.save(st)
        rc, out = self.s.pc_deploy('install', '--kit', str(self.s.state / 'kits' / run['kit']), '--game', str(self.s.game), '--state', str(self.s.state), '--owner', run['owner'], '--session', run['session'], cwd=wt)
        if rc:
            return 'refused', f'pc_deploy install failed: {out.strip()[-200:]}'
        end = self.s.now() + INSTALL_WAIT_S
        while self.s.now() < end:
            why = self.stop_reason(run)
            if why:
                return 'stopped', why
            self.s.sleep(POLL_S)
        argv = [sys.executable, 'core/harness/acceptance.py', 'run', '--passes', str(run['passes']), '--run', run['run_id'], '--branch', run['branch'],
                '--owner', run['owner'], '--session', run['session'], '--max-flakes', str(run['max_flakes'])]
        proc = self.s.start(argv, wt)
        run['child_pid'], run['child_created'] = proc.pid, self.s.created(proc.pid)
        self.save(st)
        return self.supervise(run, proc)

    def stop_reason(self, run):
        """Decision 7: Liam is back, by file or by input, or the layout changed."""
        for f in self.present:
            if self.s.exists(f):
                return f'{f} exists'
        if self.s.last_input() != run['input0']:
            return 'input'
        mons = self.s.monitors()
        if layout_key(mons) != run['layout_key']:
            return f"the layout changed from {run['layout']} to {layout_name(mons)}"
        return None

    def supervise(self, run, proc):
        """Read the run; on a stop reason end it at the next pass line, so no finished pass is lost. (outcome, why)."""
        out_file, idle_file = self.scratch / f"{run['run_id']}.out", self.scratch / f"{run['run_id']}.idle.log"
        start = self.s.now()
        wanted, wanted_at, minute = None, None, 0
        while True:
            line = proc.next_line(POLL_S)
            if line is None:
                break
            if line:
                self.s.append_text(out_file, line + '\n')
                if wanted and stop_point(line):
                    self.log(f'stop after: {line}')
                    proc.stop()
                    proc.wait()
                    return 'stopped', wanted
            t = self.s.now()
            if t - start >= minute * 60:
                minute += 1
                idle, free, mons = self.s.idle_s(), self.s.free_gb(), self.s.monitors()
                self.s.append_text(idle_file, f"{utc_of(t)} idle_s={idle} last_input={self.s.last_input()} free_gb={None if free is None else round(free, 1)} layout={layout_name(mons)}\n")
            if not wanted:
                wanted = self.stop_reason(run) or ('the 4 hour limit' if t - start >= HARD_LIMIT_S else None)
                if wanted:
                    wanted_at = t
                    self.log(f'stop wanted: {wanted}; waiting for the next pass line')
            elif t - wanted_at >= STOP_GRACE_S:
                self.log(f'no pass line in {STOP_GRACE_S} s after the stop: ending the run where it stands')
                proc.stop()
                proc.wait()
                return 'stopped', f'{wanted}, with no pass line in time'
        rc = proc.wait()
        if wanted and rc != 1:
            return ('complete' if rc == 0 else 'refused'), f'{wanted} came with the last pass; exit {rc}'
        return {0: ('complete', 'every pass ran'), 1: ('consumed', 'a fail, or the flake allowance spent')}.get(rc, ('refused', f'acceptance.py run exit {rc}: see the .out file'))

    # decisions 7, 9, 10
    def clear_game(self, run):
        """What the run left, through job.sh as its own owner: the check is whether a game is up under the lock, not whether the run looks finished. True when nothing of it is left."""
        self.s.session = run['session']
        for _ in range(12):   # a request that was in flight when the run ended
            st = self.watcher_status()
            if not st.get('current_job') and not st.get('queue_length'):
                break
            self.s.sleep(POLL_S)
        lock = st.get('lock')
        if isinstance(lock, dict) and lock.get('owner') == run['owner']:
            if (st.get('game_state') or {}).get('state') != 'not_running':
                rc, out = self.s.job_sh(run['owner'], '-', input='kill\n')
                self.log(f'kill: exit {rc}')
            rc, out = self.s.job_sh('unlock', run['owner'])
            self.log(f'unlock: exit {rc}')
        elif lock:
            self.log(f"the lock is not this run's: {lock}")
            return False
        for _ in range(24):
            st = self.watcher_status()
            if st.get('lock') is None and st.get('profile_active') is None:
                return (st.get('game_state') or {}).get('state') == 'not_running'
            self.s.sleep(POLL_S)
        return False

    def finish(self, st, run, wt, outcome, why):
        """The end of every run, whatever happened (decision 9). A step that fails does not stop the ones after it: evidence comes home in any case."""
        notes = []
        if self.s.alive(run.get('child_pid'), run.get('child_created')):   # the start time guards a reused pid: only the run's own child
            self.s.kill_tree(run['child_pid'])
        try:
            clean = self.clear_game(run)
        except Refused as e:
            clean = False
            notes.append(str(e))
        if not clean:
            notes.append('the game, lock or profile is not clear')
        vanilla = False
        if run.get('installed') and clean:
            first = (self.deploy('status')[1].strip().splitlines() or [''])[0]
            if run['installed'] in first:
                rc, out = self.deploy('uninstall', '--owner', run['owner'], '--session', run['session'], cwd=wt)
                if rc:
                    notes.append(f'uninstall failed: {out.strip()[-200:]}')
            elif 'not installed by this tool' not in first:
                notes.append(f'left alone, not ours: {first}')
        rc, out = self.deploy('status')
        vanilla = deploy_problem(rc, out) is None
        if not vanilla:
            notes.append('pc_deploy status does not say vanilla')
        pushed = self.commit_push(run, wt, outcome)
        if outcome == 'consumed':
            st.setdefault('consumed', {}).setdefault(run['branch'], []).append(run['blob'])
        if clean:   # else the next tick finds the dead run and tries the same route again: what it owns is not forgotten
            st.pop('run', None)
        self.save(st)
        self.done(outcome, why, run=run['run_id'], branch=run['branch'], build_id=run['build_id'], kit=run['kit'], layout=run['layout'], vanilla=vanilla, clean=clean, pushed=pushed, notes=notes)

    def commit_push(self, run, wt, outcome):
        rid, branch = run['run_id'], run['branch']
        paths = [LEDGER, f'harness/runs/{rid}']
        rc, out = self.s.git('status', '--porcelain', '--', *paths, cwd=wt)
        if rc or not out.strip():
            self.log('nothing to commit')
            return None
        self.s.git('add', '--', *[p for p in paths if self.s.exists(wt / p)], cwd=wt)
        rc, out = self.s.git('commit', '--quiet', '-m', commit_message(run['job'], rid, outcome, run['session']), cwd=wt)
        if rc:
            self.log(f'commit failed: {out.strip()[-300:]}')
            return False
        self.s.git('fetch', '--quiet', 'origin', f'+refs/heads/{branch}:refs/remotes/origin/{branch}', cwd=wt)
        rc, remote = self.s.git('rev-parse', f'refs/remotes/origin/{branch}', cwd=wt)
        remote = remote.strip()
        if rc == 0 and remote != run['head']:
            acc, _ = self.s.rule79(branch, remote, 'refs/remotes/origin/main')
            if acc is None or acc.get('build_id') != run['build_id']:
                return self.keep_local(run, wt, f"the remote head {remote[:12]} has another build")
            rc, out = self.s.git('rebase', '--quiet', remote, cwd=wt)
            if rc:
                self.s.git('rebase', '--abort', cwd=wt)
                return self.keep_local(run, wt, 'the rebase on the moved remote head is not clean')
        rc, out = self.s.git('push', '--quiet', 'origin', f'HEAD:refs/heads/{branch}', cwd=wt)
        if rc:
            return self.keep_local(run, wt, f'push failed: {out.strip()[-300:]}')
        self.log(f'pushed {rid} to {branch}')
        return True

    def keep_local(self, run, wt, why):
        ref = f"refs/acceptance-auto/{run['run_id']}"
        self.s.git('update-ref', ref, 'HEAD', cwd=wt)
        self.log(f'left local as {ref}: {why}')
        return False

    def cleanup(self, st, run):
        """Decision 10: its own state file with no live process (a reboot, a crash, a logoff). Only what that run owned, by the stop route, then what it finds is committed."""
        self.log(f"clean-up of dead run {run['run_id']} (pid {run['pid']})")
        self.owner = run['owner']
        self.s.session = run['session']
        self.finish(st, run, self.s.worktree, 'stopped', 'the run died (reboot, crash or logoff)')
        return 0

    def tick(self):
        st = self.load()
        run = st.get('run')
        if run and self.s.alive(run['pid'], run.get('pid_created')):
            return self.done('busy', f"run {run['run_id']} is live, pid {run['pid']}")
        try:
            self.person_guards()
            if run:
                return self.done('would clean up', run['run_id']) if self.dry else self.cleanup(st, run)
            self.pc_guards()
            c = self.pick(st)
            if not c:
                return self.done('idle', 'no branch asks for a run')
            return self.start(st, c)
        except Refused as e:
            return self.done('refused', str(e))


# ---- the other verbs ----------------------------------------------------------------------------------------------------------
def cmd_request(s, a):
    """Write jobs/<id>/acceptance_request.json for this checkout's HEAD. The builder commits and pushes it, leaves the row at queued or fix and ends."""
    rc, out = s.build_id(s.root)
    build = out.strip()
    if rc or not re.fullmatch(r'[0-9a-f]{12}', build):
        print(f'request: refused: build_id.py says {build!r}: commit the DLL inputs first', file=sys.stderr)
        return 2
    wsrc = s.read_bytes(s.root / 'core' / 'harness' / 'watcher.ps1')
    doc = {'build_id': build, 'watcher_sha': hashlib.sha256(lf(wsrc)).hexdigest(), 'requested_utc': utc_of(s.now())}
    p = s.root / request_path(a.job)
    s.write_text(p, json.dumps(doc, indent=1) + '\n')
    print(f'request: {p}: commit it on job/{a.job}, push, leave the row at queued or fix and end the session')
    return 0


def cmd_status(s, a):
    t = Tick(s, a)
    for name, p in (('state', t.state_file), ('last result', t.result_file)):
        b = s.read_bytes(p)
        print(f"{name}: {b.decode('utf-8').strip() if b else 'none'}")
    b = s.read_bytes(t.log_file)
    tally = {}
    for line in (b.decode('utf-8', 'replace').splitlines() if b else []):
        m = re.match(r'\S+ refused: (.{0,24})', line)
        if m:
            tally[m.group(1)] = tally.get(m.group(1), 0) + 1
    print(f'refusals by reason: {tally or "none"}')
    print(s.powershell(f"Get-ScheduledTask -TaskName '{TASK}*' -ErrorAction SilentlyContinue | ForEach-Object {{ \"$($_.TaskName): $($_.State)\" }}")[1].strip() or 'no task registered')
    return 0


def proof_args(a, s):
    t = Tick(s, a)
    out = ['tick', '--branch', PROOF_BRANCH, '--job', PROOF_JOB, '--present-file', str(t.scratch / 'test_present')]
    if a.passes:
        out += ['--passes', str(a.passes)]
    sid = os.environ.get('CLAUDE_CODE_SESSION_ID')
    return out + (['--ignore-session', sid] if sid else [])


def cmd_task(s, a):
    if a.passes and not a.proof:
        print('task: refused: --passes is for the proof task only', file=sys.stderr)
        return 2
    name = PROOF_TASK if a.proof else TASK
    if a.proof and a.action in ('enable', 'disable'):
        print('task: refused: the proof task has no time trigger: it is fired by hand and removed', file=sys.stderr)
        return 2
    args = proof_args(a, s) if a.proof else ['tick']
    py = Path(sys.executable).with_name('pythonw.exe')
    rc, out = s.powershell(task_script(a.action, name, py, Path(__file__).resolve(), args, s.root))
    print(out.strip())
    return rc


def cmd_launch(s, a, rest):
    """What a task runs, under pythonw: no console of its own, so nothing flashes; python.exe starts with CREATE_NO_WINDOW, a console with no window, and every child inherits it.
    A child console on the virtual display fails a pass (J64)."""
    t = Tick(s, a)
    log = t.scratch / 'launch.out'
    log.parent.mkdir(parents=True, exist_ok=True)
    env = {'utc': utc_of(s.now()), 'python': sys.executable, 'path': os.environ.get('PATH'), 'pillow': importlib.util.find_spec('PIL') is not None,
           'which': {n: shutil.which(n) for n in ('python3', 'git', 'bash', 'claude', 'docker')}, 'idle_s': s.idle_s(), 'user': os.environ.get('USERNAME'), 'args': rest}
    s.write_text(t.scratch / 'task_env.json', json.dumps(env, indent=1) + '\n')
    py = Path(sys.executable).with_name('python.exe')
    with open(log, 'a', encoding='utf-8') as f:
        return subprocess.call([str(py), str(Path(__file__).resolve()), *rest], cwd=str(s.root), stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, creationflags=0x08000000)


def parser():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('tick')
    t.add_argument('--dry-run', action='store_true', help='say what it would do, change nothing')
    t.add_argument('--present-file', help='a second file that means Liam is here (the proof)')
    t.add_argument('--branch', help='proof only: this scratch/ branch instead of the requests on job/*')
    t.add_argument('--job', help='proof only: the job row of --branch')
    t.add_argument('--passes', type=int, help='proof only: at most this many passes')
    t.add_argument('--ignore-session', help='proof only: the session running the proof, which shows as working')
    r = sub.add_parser('request')
    r.add_argument('--job', required=True)
    sub.add_parser('status')
    k = sub.add_parser('task')
    k.add_argument('action', choices=['install', 'remove', 'enable', 'disable'])
    k.add_argument('--proof', action='store_true')
    k.add_argument('--passes', type=int)
    return ap


def main(argv=None, s=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['launch']:
        return cmd_launch(s or Real(), argparse.Namespace(), argv[1:])
    a = parser().parse_args(argv)
    if a.cmd == 'tick' and (a.passes or a.ignore_session or a.branch) and not (a.branch or '').startswith('scratch/'):
        print('tick: refused: --branch, --passes and --ignore-session are for a scratch/ proof branch only', file=sys.stderr)
        return 2
    if a.cmd == 'tick' and a.branch and not a.job:
        print('tick: refused: --branch needs --job', file=sys.stderr)
        return 2
    s = s or Real()
    return {'tick': lambda: Tick(s, a).tick(), 'request': lambda: cmd_request(s, a), 'status': lambda: cmd_status(s, a), 'task': lambda: cmd_task(s, a)}[a.cmd]()


if __name__ == '__main__':
    sys.exit(main())
