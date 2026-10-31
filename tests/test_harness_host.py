"""Gate: the harness host tests (harness/tests/Run-HostTests.ps1) run in the local `wsc gates` too, not only in CI's `harness-windows` job
(J42: a harness change looked green locally and went red only in CI). Runs in `wsc gates` (tests gate; not `--fast`, so not pre-push).

Routes, in order: harness inputs (tools/changed_inputs.py) unchanged against the merge base with origin/main -> skip in about a second;
in CI -> skip (the `harness-windows` job runs them); WSP_HARNESS_TESTS=skip -> skip with a warning; Windows PowerShell 5.1
(`powershell.exe`, the PowerShell the PC and CI run) found -> `Run-HostTests.ps1 -Suite unit` (about 20 s); else FAIL with the fix.
The integration suite is CI-only, warned: it sets the machine's time zone while it runs, kills processes named Fake*.exe
(Test-Integration.ps1 header) and takes about 6 min, over what the tests gate leaves after the proxy route; run it in CI, or with
`gh workflow run gates.yml --ref <branch> -f only='<case>'` for one case.
The route choice has its own unit tests below, with the probes injected."""
import importlib.util
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('changed_inputs', ROOT / 'tools/changed_inputs.py')
ci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ci)
RUN_TIMEOUT_S = 240   # the unit suite measured about 20 s on the PC (jobs/J42/report.md)
INTEGRATION_WARNING = ('harness integration cases NOT RUN here (CI-only, warned): they set the time zone and kill Fake*.exe; '
                       "CI's `harness-windows` job runs them (one case: gh workflow run gates.yml --ref <branch> -f only='<case>')")


def no_powershell_message():
    return ('harness host tests NOT RUN: Windows PowerShell 5.1 (powershell.exe) not found; the harness runs under it on the PC and in '
            "CI. Fix: run the gates on the Windows PC (Git Bash, CLAUDE.md \"Where agents run\"). One-off opt-out: WSP_HARNESS_TESTS=skip "
            "(CI's `harness-windows` job still runs them).")


def find_powershell(which=shutil.which):
    """Windows PowerShell 5.1, never pwsh (PowerShell 7 is not what the PC's watcher runs under)."""
    return which('powershell.exe') or which('powershell')


def choose_route(env, base, files, which=shutil.which):
    """(kind, detail): 'skip' (detail = reason), 'optout' (skip with a warning, detail = message), 'run' (detail = argv) or
    'fail' (detail = message). files None = base unknown = changed."""
    if files is not None and not ci.classify(files)['harness']:
        return 'skip', f'harness inputs unchanged against {base[:12]}'
    if env.get('GITHUB_ACTIONS'):
        return 'skip', 'covered by the `harness-windows` job'
    if env.get('WSP_HARNESS_TESTS') == 'skip':
        return 'optout', ('harness host tests skipped (WSP_HARNESS_TESTS=skip): unit and integration cases not run; '
                          "CI's `harness-windows` job still runs them")
    ps = find_powershell(which)
    if not ps:
        return 'fail', no_powershell_message()
    return 'run', [ps, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / 'core/harness/tests/Run-HostTests.ps1'), '-Suite', 'unit']


class HarnessHostTests(unittest.TestCase):
    def test_harness_host_tests(self):
        base, files = ci.local_changes(ROOT)
        kind, detail = choose_route(os.environ, base or '', files)
        if kind == 'skip':
            self.skipTest(detail)
        if kind == 'optout':
            print(f'WARNING: {detail}', file=sys.stderr)
            self.skipTest(detail)
        if kind == 'fail':
            self.fail(detail)
        try:
            p = subprocess.run(detail, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace',
                               timeout=RUN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self.fail(f'Run-HostTests.ps1 -Suite unit took over {RUN_TIMEOUT_S} s')
        out = p.stdout + p.stderr
        print(f'WARNING: {INTEGRATION_WARNING}', file=sys.stderr)
        if p.returncode != 0:
            bad = [ln for ln in out.splitlines() if ln.startswith('FAIL')] or ['(no FAIL line)']
            tail = '\n'.join(out.strip().splitlines()[-20:])
            self.fail(f'harness unit tests failed: {"; ".join(bad)}\n--- last lines ---\n{tail}')


# ---- unit tests: the route choice, probes injected ------------------------------------------------------------------------------------
def which_of(*present):
    return lambda name: f'C:/Windows/{name}' if name in present else None


def never(*_):
    raise AssertionError('probed when it should not be')


class Route(unittest.TestCase):
    def route(self, env=None, files=('harness/core/watcher.ps1',), which=which_of('powershell.exe')):
        return choose_route(env or {}, 'abcdef1234567890', None if files is None else list(files), which)

    def test_unchanged_skips_without_probing(self):
        self.assertEqual(self.route(files=['proxy/core/console.cpp'], which=never),
                         ('skip', 'harness inputs unchanged against abcdef123456'))

    def test_ci_skips(self):
        self.assertEqual(self.route(env={'GITHUB_ACTIONS': 'true'}, which=never), ('skip', 'covered by the `harness-windows` job'))

    def test_windows_powershell_runs_the_unit_suite(self):
        kind, argv = self.route()
        self.assertEqual(kind, 'run')
        self.assertEqual(argv[0], 'C:/Windows/powershell.exe')
        self.assertEqual(argv[-2:], ['-Suite', 'unit'])
        self.assertTrue(argv[argv.index('-File') + 1].endswith('Run-HostTests.ps1'))

    def test_pwsh_alone_is_not_enough(self):
        kind, msg = self.route(which=which_of('pwsh'))
        self.assertEqual(kind, 'fail')
        for s in ('powershell.exe', 'WSP_HARNESS_TESTS=skip', 'harness-windows'):
            self.assertIn(s, msg)

    def test_opt_out_warns_and_needs_no_powershell(self):
        kind, msg = self.route(env={'WSP_HARNESS_TESTS': 'skip'}, which=never)
        self.assertEqual(kind, 'optout')
        self.assertIn('WSP_HARNESS_TESTS=skip', msg)

    def test_unknown_base_counts_as_changed(self):
        self.assertEqual(self.route(files=None)[0], 'run')

    def test_integration_is_named_as_ci_only(self):
        self.assertIn('CI-only, warned', INTEGRATION_WARNING)


if __name__ == '__main__':
    unittest.main()
