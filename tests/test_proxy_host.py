"""Gate: the proxy's C++ host tests (proxy/tests/test_*.cpp) run in the local `wsc gates` too, not only in CI's `proxy` job (J41: J15's
review commit 6316cb9 broke test_console's lint and only CI saw it). Runs in `wsc gates` (tests gate; not `--fast`, so not pre-push).

Routes, in order: proxy inputs (tools/changed_inputs.py) unchanged against the merge base with origin/main -> skip in about a second;
in CI -> skip (the `proxy` job runs them); native mingw-w64 and g++ on PATH -> `proxy/tools/build.sh all`; Docker answering ->
`build.sh --docker all` (~1 min); else no toolchain -> a skip naming the suites not run (core 0.4.0's tests gate shows it as a warn,
J41; it failed until that tag was pinned, J12). build.sh always
runs through Git Bash on Windows (tools/verbs/setup.py git_bash), never the WSL `bash` on PATH.
After `all` passes, the wine smoke test runs on the same route (J42: PR #50's smoke failure was seen only by CI): `--docker smoke`
(the container plus wine, about 70 s on the PC), native `smoke` when wine is on PATH, else a warning that it is CI-only.
The route choice and the input set have their own unit tests below, with git and the toolchain probes injected."""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ci = _load('changed_inputs', 'tools/changed_inputs.py')
sv = _load('setup_verb', 'tools/verbs/setup.py')
BUILD_TIMEOUT_S = 540   # under the tests gate's 600 s; `--docker all` measured about 93 s with apt (jobs/J41/report.md), 57 s (J42)
SMOKE_TIMEOUT_S = 300   # `--docker smoke` measured 70 s on the PC with apt and wine (jobs/J42/report.md)


def suites(root=ROOT):
    return sorted(p.stem for p in (Path(root) / 'core/proxy/tests').glob('test_*.cpp'))


def no_toolchain_message(names):
    return (f'proxy host tests NOT RUN (no toolchain): {", ".join(names)}. Fix: start Docker Desktop (Linux containers) and wait for '
            f'"Engine running", or run `python3 core/wsc.py setup` and follow its docker line (proxy/README.md "Build"); '
            f'CI\'s `proxy` job runs them.')


def docker_answers():
    try:
        return subprocess.run(['docker', 'info'], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def choose_route(env, base, files, which=shutil.which, docker_ok=docker_answers, names=None):
    """(kind, detail): kind is 'skip' (detail = reason), 'native' or 'docker' (detail = build.sh arguments), or 'none' (no toolchain:
    a skip whose reason names the suites not run). files None = base unknown = changed."""
    if files is not None and not ci.classify(files)['proxy']:
        return 'skip', f'proxy inputs unchanged against {base[:12]}'
    if env.get('GITHUB_ACTIONS'):
        return 'skip', 'covered by the `proxy` job'
    if (which('i686-w64-mingw32-g++-win32') or which('i686-w64-mingw32-g++')) and which('g++'):
        return 'native', ['all']
    if docker_ok():
        return 'docker', ['--docker', 'all']
    return 'none', no_toolchain_message(names if names is not None else suites())


def smoke_route(kind, which=shutil.which):
    """(build.sh arguments, None) to run the wine smoke test after `all` on route `kind`, or (None, warning) when it cannot run here."""
    if kind == 'docker':
        return ['--docker', 'smoke'], None
    if kind == 'native' and which('wine'):
        return ['smoke'], None
    return None, ('proxy wine smoke test NOT RUN (CI-only, warned): no wine here and not the Docker route. '
                  'Run `core/proxy/tools/build.sh --docker smoke` with Docker Desktop up, or rely on CI\'s `proxy` job.')


def failed_suites(output, names):
    """The suites build.sh reported as failed, or whose source a compile error names; [] when the failure names none."""
    out = set(re.findall(r'build\.sh: (test_\w+) FAILED', output))
    out |= {n for n in names if re.search(rf'proxy/tests/{n}\.cpp:\d+', output)}
    return sorted(out)


class ProxyHostTests(unittest.TestCase):
    def test_proxy_host_tests(self):
        base, files = ci.local_changes(ROOT)
        kind, detail = choose_route(os.environ, base or '', files)
        if kind == 'skip':
            self.skipTest(detail)
        if kind == 'none':
            self.skipTest(detail)   # the core's tests gate reports it as a warn with this reason (J41)
        bash = sv.git_bash()
        self.assertIsNotNone(bash, 'no Git Bash found to run core/proxy/tools/build.sh (`python3 core/wsc.py setup` says why)')

        def build(args, timeout):
            try:
                p = subprocess.run([bash, 'core/proxy/tools/build.sh', *args], cwd=ROOT, capture_output=True, text=True,
                                   encoding='utf-8', errors='replace', timeout=timeout)
            except subprocess.TimeoutExpired:
                self.fail(f'build.sh {" ".join(args)} took over {timeout} s')
            return p.returncode, p.stdout + p.stderr

        rc, out = build(detail, BUILD_TIMEOUT_S)
        if rc != 0:
            bad = failed_suites(out, suites()) or ['(the build failed before a suite ran)']
            tail = '\n'.join(out.strip().splitlines()[-30:])
            self.fail(f'proxy host tests failed ({kind}): {", ".join(bad)}\n--- last lines of build.sh {" ".join(detail)} ---\n{tail}')
        smoke, warn = smoke_route(kind)
        if warn:
            print(f'WARNING: {warn}', file=sys.stderr)
            return
        rc, out = build(smoke, SMOKE_TIMEOUT_S)
        if rc != 0:
            tail = '\n'.join(out.strip().splitlines()[-30:])
            self.fail(f'proxy wine smoke test failed ({kind}): build.sh {" ".join(smoke)}\n--- last lines ---\n{tail}')


# ---- unit tests: the route choice and the input set, git and toolchain probes injected ----------------------------------------------
def which_of(*present):
    return lambda name: f'/usr/bin/{name}' if name in present else None


def no_docker(*_):
    raise AssertionError('docker probed when it should not be')


class Route(unittest.TestCase):
    NAMES = ['test_console', 'test_guard']

    def route(self, env=None, files=('proxy/core/console.cpp',), which=which_of(), docker=False):
        return choose_route(env or {}, 'abcdef1234567890', None if files is None else list(files), which,
                            docker if callable(docker) else (lambda: docker), self.NAMES)

    def test_unchanged_skips_without_probing(self):
        self.assertEqual(self.route(files=['docs/x.md'], which=no_docker, docker=no_docker),
                         ('skip', 'proxy inputs unchanged against abcdef123456'))

    def test_ci_skips(self):
        self.assertEqual(self.route(env={'GITHUB_ACTIONS': 'true'}, docker=no_docker), ('skip', 'covered by the `proxy` job'))

    def test_native(self):
        self.assertEqual(self.route(which=which_of('i686-w64-mingw32-g++', 'g++'), docker=no_docker), ('native', ['all']))
        self.assertEqual(self.route(which=which_of('i686-w64-mingw32-g++-win32', 'g++'), docker=no_docker), ('native', ['all']))

    def test_docker_when_native_incomplete(self):
        self.assertEqual(self.route(which=which_of('g++'), docker=True), ('docker', ['--docker', 'all']))

    def test_no_toolchain_is_a_skip_naming_suites(self):
        kind, msg = self.route()
        self.assertEqual(kind, 'none')
        for s in ('test_console', 'test_guard', 'Docker Desktop', 'wsc.py setup'):
            self.assertIn(s, msg)

    def test_unknown_base_counts_as_changed(self):
        self.assertEqual(self.route(files=None)[0], 'none')

    def test_suites_are_the_cpp_stems(self):
        self.assertIn('test_console', suites())
        self.assertNotIn('smoke_host', suites())

    def test_smoke_follows_the_route(self):
        self.assertEqual(smoke_route('docker', which=no_docker), (['--docker', 'smoke'], None))
        self.assertEqual(smoke_route('native', which=which_of('wine')), (['smoke'], None))
        args, warn = smoke_route('native', which=which_of())
        self.assertIsNone(args)
        self.assertIn('CI-only, warned', warn)
        self.assertIn('--docker smoke', warn)

    def test_failed_suites(self):
        self.assertEqual(failed_suites('x\nbuild.sh: test_console FAILED\n', self.NAMES), ['test_console'])
        self.assertEqual(failed_suites('/src/proxy/tests/test_guard.cpp:12:3: error: x', self.NAMES), ['test_guard'])
        self.assertEqual(failed_suites('docker: not found', self.NAMES), [])


class FakeGit:
    """Answers the git calls changed_inputs makes, from a table; anything else fails."""
    def __init__(self, committed=(), worktree=(), untracked=(), shallow=False, origin_main=True):
        self.t = {('rev-parse', '--is-shallow-repository'): (0, ['true' if shallow else 'false']),
                  ('merge-base', 'origin/main', 'HEAD'): (0, ['b' * 40]) if origin_main else (128, []),
                  ('cat-file', '-e', 'b' * 40 + '^{commit}'): (0, []),
                  ('diff', '--name-only', 'b' * 40, 'HEAD'): (0, list(committed)),
                  ('diff', '--name-only', 'HEAD'): (0, list(worktree)),
                  ('ls-files', '--others', '--exclude-standard'): (0, list(untracked))}

    def __call__(self, root, *args):
        return self.t.get(args, (1, []))


class InputSet(unittest.TestCase):
    def proxy(self, **kw):
        return ci.classify(ci.local_changes(ROOT, FakeGit(**kw))[1])['proxy']

    def test_untracked_proxy_file_is_a_change(self):
        self.assertTrue(self.proxy(untracked=['proxy/tests/test_new.cpp']))

    def test_uncommitted_edit_is_a_change(self):
        self.assertTrue(self.proxy(worktree=['proxy/core/console.cpp']))

    def test_config_keys_registry_is_a_change(self):
        self.assertTrue(self.proxy(committed=['registries/config_keys.jsonl']))
        self.assertTrue(self.proxy(committed=['registries/engine_sites.jsonl']))

    def test_docs_only_is_unchanged(self):
        self.assertFalse(self.proxy(committed=['docs/DECISIONS.md'], worktree=['jobs/J41/report.md'], untracked=['docs/new.md']))
        self.assertFalse(self.proxy(committed=['registries/jobs/J41.json']))

    def test_pc_run_evidence_is_not_a_proxy_input(self):
        # J42 (J41 review later item 2): proxy/runs/ holds committed PC run evidence; it builds nothing
        self.assertEqual(ci.classify(['proxy/runs/2026-10-29_j15/console.log']), {'proxy': False, 'harness': False, 'viewer': False})
        self.assertTrue(ci.classify(['proxy/runs/x.log', 'proxy/core/console.cpp'])['proxy'])
        self.assertTrue(ci.classify(['proxy/runsheet.md'])['proxy'])

    def test_workflow_change_runs_all(self):
        self.assertEqual(ci.classify(['.github/workflows/gates.yml']), {'proxy': True, 'harness': True, 'viewer': True})

    def test_harness_set(self):
        self.assertEqual(ci.classify(['core']), {'proxy': True, 'harness': True, 'viewer': False})   # the pin: the proxy and harness live there (J12)
        self.assertEqual(ci.classify(['harness/core/job.sh']), {'proxy': False, 'harness': True, 'viewer': False})
        # J22: the Windows step of harness-windows runs the Python tests that run bash
        for f in ('tests/test_job_sh.py', 'tests/test_claude_hook.py', 'tests/test_setup.py', 'tests/test_proxy_host.py',
                  'tools/verbs/setup.py', 'tools/claude_hook.py', '.claude/settings.json'):
            self.assertEqual(ci.classify([f]), {'proxy': False, 'harness': True, 'viewer': False}, f)
        self.assertEqual(ci.classify(['tests/test_jobs.py', 'tools/verbs/jobs.py']), {'proxy': False, 'harness': False, 'viewer': False})

    def test_viewer_set(self):
        # J31: viewer/ and its test build the viewer; viewer/runs/ is committed evidence
        self.assertEqual(ci.classify(['viewer/core/src/viewer.cpp']), {'proxy': False, 'harness': False, 'viewer': True})
        self.assertEqual(ci.classify(['tests/test_viewer.py'])['viewer'], True)
        self.assertEqual(ci.classify(['viewer/runs/20261031_j31/a.png'])['viewer'], False)

    def test_unknown_base_means_changed(self):
        self.assertIsNone(ci.local_changes(ROOT, FakeGit(shallow=True))[1])
        self.assertIsNone(ci.local_changes(ROOT, FakeGit(origin_main=False))[1])
        self.assertEqual(ci.classify(None), {'proxy': True, 'harness': True, 'viewer': True})
        self.assertIsNone(ci.changed_files(ROOT, '', FakeGit()))


class GitBash(unittest.TestCase):
    def test_off_windows_is_bash_on_path(self):
        self.assertEqual(sv.git_bash(nt=False, which=which_of('bash')), '/usr/bin/bash')

    def test_windows_git_bash_on_path(self):
        b = r'C:\Program Files\Git\usr\bin\bash.exe'
        self.assertEqual(sv.git_bash(nt=True, which=lambda n: b, git_exec_path=''), b)

    def test_windows_wsl_on_path_finds_git_install(self):
        found = sv.git_bash(nt=True, which=lambda n: r'C:\Windows\System32\bash.exe',
                            git_exec_path='D:/Tools/Git/mingw64/libexec/git-core', isfile=lambda p: p == r'D:\Tools\Git\bin\bash.exe')
        self.assertEqual(found, r'D:\Tools\Git\bin\bash.exe')

    def test_windows_none(self):
        self.assertIsNone(sv.git_bash(nt=True, which=lambda n: None, git_exec_path='', isfile=lambda p: False))


if __name__ == '__main__':
    unittest.main()
