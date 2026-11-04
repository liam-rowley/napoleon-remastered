"""Host tests for the pure parts of tools/verbs/setup.py (`wsc setup`): version parsing, which bash is on PATH, CR detection, the
pinned core tag, core.hooksPath and the main clone behind a worktree. Runs in `wsc gates` (tests gate)."""
import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('setup_verb', ROOT / 'tools/verbs/setup.py')
sv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sv)


class Setup(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(sv.parse_version('Python 3.12.4'), (3, 12))
        self.assertEqual(sv.parse_version('3.15.2'), (3, 15))
        self.assertIsNone(sv.parse_version('Python was not found; run without arguments to install from the Microsoft Store'))
        self.assertLess(sv.parse_version('Python 3.11.9'), sv.MIN_PY)

    def test_bash_kind(self):
        self.assertEqual(sv.bash_kind(r'C:\Program Files\Git\usr\bin\bash.EXE', nt=True), 'git')
        self.assertEqual(sv.bash_kind(r'C:\Windows\System32\bash.exe', nt=True), 'wsl')
        self.assertEqual(sv.bash_kind(r'C:\Users\x\AppData\Local\Microsoft\WindowsApps\bash.exe', nt=True), 'wsl')
        self.assertEqual(sv.bash_kind(r'C:\msys64\usr\bin\bash.exe', nt=True), 'other')
        self.assertEqual(sv.bash_kind('/usr/bin/bash', nt=False), 'posix')
        self.assertIsNone(sv.bash_kind(None))

    def test_bash_check_reports_both_bashes(self):
        git, wsl = r'C:\Program Files\Git\usr\bin\bash.exe', r'C:\Users\x\AppData\Local\Microsoft\WindowsApps\bash.exe'
        ok, detail, _ = sv.bash_check(git, git, 'MINGW64', nt=True)   # started from Git Bash
        self.assertTrue(ok)
        self.assertIn(f'bash on PATH: {git} (git)', detail)
        self.assertIn(f'repo tools use: {git}', detail)
        self.assertNotIn('warn', detail)
        ok, detail, _ = sv.bash_check(wsl, git, None, nt=True)   # WSL first on PATH: a warning, not a failure
        self.assertTrue(ok)
        self.assertIn('(wsl)', detail)
        self.assertIn('warn:', detail)
        self.assertIn(r'C:\Program Files\Git\usr\bin', detail)
        ok, detail, fix = sv.bash_check(wsl, None, None, nt=True)   # no Git Bash at all: the one failure
        self.assertFalse(ok)
        self.assertIn('Git for Windows', fix)
        self.assertEqual(sv.bash_check('/usr/bin/bash', '/usr/bin/bash', None, nt=False)[:2], (True, 'bash at /usr/bin/bash'))
        self.assertFalse(sv.bash_check(None, None, None, nt=False)[0])

    def test_bash_for_tests(self):
        git = r'C:\Program Files\Git\bin\bash.exe'
        self.assertEqual(sv.bash_for_tests(nt=True, find=lambda nt: git), (git, None))
        b, why = sv.bash_for_tests(nt=True, find=lambda nt: None)   # Windows, no Git Bash: skip with the reason, never the WSL bash
        self.assertIsNone(b)
        self.assertIn('python3 core/wsc.py setup', why)
        self.assertEqual(sv.bash_for_tests(nt=False, find=lambda nt: None), ('bash', None))   # off Windows a missing bash fails later
        self.assertEqual(sv.bash_for_tests(nt=False, find=lambda nt: '/usr/bin/bash'), ('/usr/bin/bash', None))

    def test_watcher_check_without_git_bash_fails_with_a_fix(self):
        with mock.patch.object(sv, 'git_bash', lambda: None):
            ok, detail, fix = sv.check_watcher(ROOT, False)
        self.assertFalse(ok)
        self.assertIn('no Git Bash', detail)
        self.assertIn('Git for Windows', fix)

    def test_watcher_check_runs_the_core_job_sh(self):
        # J70: the check ran harness/core/job.sh (the pre-J12 path), so bash exited 127 with the watcher up. The fake _run answers
        # like job.sh status only for an existing script; the real job.sh never runs, so CI needs no watcher.
        calls = []

        def fake_run(cmd, cwd=None, timeout=60):
            calls.append(cmd)
            if Path(cmd[1]).is_file() and cmd[2:] == ['status']:
                return 0, '{"state": "idle"}'
            return 127, f'{cmd[1]}: No such file or directory'

        with mock.patch.object(sv, 'git_bash', lambda: 'stub-bash'), mock.patch.object(sv, '_run', fake_run):
            ok, detail, fix = sv.check_watcher(ROOT, False)
        self.assertTrue(ok, detail)
        self.assertEqual(len(calls), 1)
        want = ROOT / 'core' / 'harness' / 'job.sh'
        self.assertTrue(want.is_file(), want)
        self.assertEqual(Path(calls[0][1]).resolve(), want.resolve())

    def test_watcher_check_with_job_sh_missing_names_the_path_and_runs_no_bash(self):
        # J70: a root without core/harness/job.sh (submodule not initialised) is its own failure, found before bash runs.
        def fake_run(cmd, cwd=None, timeout=60):
            if any(str(c).replace('\\', '/').endswith('job.sh') for c in cmd):
                self.fail(f'bash ran a missing job.sh: {cmd}')
            return 0, ''

        with tempfile.TemporaryDirectory() as d, mock.patch.object(sv, 'git_bash', lambda: 'stub-bash'), \
                mock.patch.object(sv, '_run', fake_run):
            ok, detail, fix = sv.check_watcher(Path(d), False)
        self.assertFalse(ok)
        self.assertIn('core/harness/job.sh', detail)
        self.assertIn('missing', detail)
        self.assertIn('submodule', fix)

    STATUS = ('{\n  "version": "1.9",\n  "heartbeat_utc": "2026-11-04T10:00:00Z",\n  "queue_length": 0,\n'
              '  "game_state": {\n    "state": "not_running",\n    "pid": null\n  },\n  "lock": null\n}\n')

    def test_watcher_detail_reads_the_status_json(self):
        # J70 Later 1: the ok line was the JSON's last line, a stray `}`; it now shows the game state and the heartbeat age
        from datetime import datetime, timezone
        now = datetime(2026, 11, 4, 10, 0, 7, tzinfo=timezone.utc)
        d = sv.watcher_detail(0, self.STATUS, now=now)
        self.assertEqual(d, 'job.sh status exit 0: watcher 1.9, game not_running, heartbeat 7s old, queue 0')
        locked = self.STATUS.replace('"lock": null', '"lock": {"owner": "J75", "age_s": 3}')
        self.assertIn('lock held by J75', sv.watcher_detail(0, locked, now=now))
        late = sv.watcher_detail(1, self.STATUS + 'watcher heartbeat is 300s old: the watcher is not running\n', now=now)
        self.assertTrue(late.startswith('job.sh status exit 1: watcher 1.9') and late.endswith('the watcher is not running'), late)
        # no JSON, or JSON without a heartbeat: the first output line
        self.assertEqual(sv.watcher_detail(1, 'no watcher.alive in X: the watcher has never run here\n'),
                         'job.sh status exit 1: no watcher.alive in X: the watcher has never run here')
        self.assertEqual(sv.watcher_detail(0, '{\n  "state": "idle"\n}\n'), 'job.sh status exit 0: {')
        self.assertEqual(sv.watcher_detail(0, ''), 'job.sh status exit 0: ')

    def test_watcher_check_failing_exit_keeps_its_fix(self):
        with mock.patch.object(sv, 'git_bash', lambda: 'stub-bash'), \
                mock.patch.object(sv, '_run', lambda cmd, cwd=None, timeout=60: (1, self.STATUS + 'heartbeat is 300s old\n')):
            ok, detail, fix = sv.check_watcher(ROOT, False)
        self.assertFalse(ok)
        self.assertNotEqual(detail.split(': ', 1)[1], '}')
        self.assertIn('game not_running', detail)
        self.assertIn('watch.cmd', fix)

    def test_git_bash_roots_skip_localappdata_git(self):
        # J41 Later 4: %LOCALAPPDATA%\Git is not an install folder; %LOCALAPPDATA%\Programs\Git is the per-user one
        env = {'ProgramFiles': r'C:\PF', 'ProgramW6432': r'C:\PF64', 'LOCALAPPDATA': r'C:\Users\x\AppData\Local'}
        probed = []
        with mock.patch.dict(sv.os.environ, env, clear=True):
            self.assertIsNone(sv.git_bash(nt=True, which=lambda _: None, git_exec_path='', isfile=lambda p: probed.append(p) or False))
        roots = sorted({p.rsplit('\\bin\\', 1)[0].removesuffix('\\usr') for p in probed})
        self.assertEqual(roots, [r'C:\PF64\Git', r'C:\PF\Git', r'C:\Users\x\AppData\Local\Programs\Git'])
        want = r'C:\Users\x\AppData\Local\Programs\Git\bin\bash.exe'
        with mock.patch.dict(sv.os.environ, env, clear=True):
            self.assertEqual(sv.git_bash(nt=True, which=lambda _: None, git_exec_path='', isfile=lambda p: p == want), want)
        with mock.patch.dict(sv.os.environ, {}, clear=True):   # no LOCALAPPDATA: no root under the drive root
            probed.clear()
            sv.git_bash(nt=True, which=lambda _: None, git_exec_path='', isfile=lambda p: probed.append(p) or False)
            self.assertEqual(probed, [])

    def test_pillow_result_warns_never_fails(self):
        ok, detail, fix = sv.pillow_result(0, '12.0.0 for C:\\Python313\\python.exe')
        self.assertTrue(ok)
        self.assertEqual(detail, 'Pillow 12.0.0 for C:\\Python313\\python.exe')
        ok, detail, fix = sv.pillow_result(1, "Traceback ...\nModuleNotFoundError: No module named 'PIL'")
        self.assertTrue(ok)
        self.assertTrue(detail.startswith('warn: python3 cannot import PIL'), detail)
        self.assertIn('pip install pillow', detail)
        self.assertIn('pip install pillow', fix)
        self.assertIn('pillow', sv.CHECKS)

    def test_cr_files(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'a.sh').write_bytes(b'echo hi\n')
            (Path(t) / 'b.sh').write_bytes(b'echo hi\r\n')
            self.assertEqual(sv.cr_files(t, ['a.sh', 'b.sh']), ['b.sh'])

    def test_pinned_version_reads_the_core_section(self):
        toml = '[registries]\nversion = "nope"\n\n[core]\nversion = "v0.2.0"\n\n[tools]\nexempt = []\n'
        self.assertEqual(sv.pinned_version(toml), 'v0.2.0')
        self.assertEqual(sv.pinned_version((ROOT / 'wsc.toml').read_text(encoding='utf-8'))[0], 'v')

    def test_hooks_path_must_be_relative(self):
        self.assertTrue(sv.hooks_path_ok('core/.githooks'))
        self.assertFalse(sv.hooks_path_ok(r'C:\Users\x\repos\napoleon-remastered\core\.githooks'))
        self.assertFalse(sv.hooks_path_ok(''))

    def test_main_clone_from_a_worktree_common_dir(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'repos' / 'napoleon-remastered' / '.git').mkdir(parents=True)
            self.assertEqual(sv.main_clone(Path(t) / 'repos' / 'napoleon-remastered' / '.git'),
                             (Path(t) / 'repos' / 'napoleon-remastered').resolve())

    def test_pc_rules_present_absent_and_failing(self):
        pd = sv.load_pc_deploy(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            game, state, emp = t / 'game', t / 'state', t / 'empire'
            self.assertIsNone(sv.pc_rules_result(pd, game, state, [emp], None))   # absent: skipped (CI, other hosts)
            for d in (game, state, emp):
                d.mkdir()
            (game / 'Napoleon.exe').write_bytes(b'MZ fake')
            ident = {'exe_name': 'Napoleon.exe', 'sha1': hashlib.sha1(b'MZ fake').hexdigest()}
            ok, detail = sv.pc_rules_result(pd, game, state, [emp], ident)
            self.assertTrue(ok, detail)
            self.assertIn('exe: ok', detail)
            self.assertIn('foreign: not checked', detail)
            (emp / '.git').mkdir()
            ok, detail = sv.pc_rules_result(pd, game, state, [emp], ident)
            self.assertFalse(ok)
            self.assertIn('git (empire): FAIL', detail)
            (emp / '.git').rmdir()
            ok, detail = sv.pc_rules_result(pd, game, state, [emp], dict(ident, sha1='0' * 40))
            self.assertFalse(ok)
            self.assertIn('MISMATCH', detail)
            self.assertFalse(sv.pc_rules_result(pd, game, state, [emp], None)[0])   # cannot check is not a pass

    def test_every_check_has_a_function(self):
        for c in sv.CHECKS:
            self.assertTrue(callable(getattr(sv, f'check_{c}', None)), c)


if __name__ == '__main__':
    unittest.main()
