"""Gate: the proxy's C++ host tests (proxy/tests/test_*.cpp) run in the local `wsc gates` too, not only in CI's `proxy` job (J41: J15's
review commit 6316cb9 broke test_console's lint and only CI saw it). Runs in `wsc gates` (tests gate; not `--fast`, so not pre-push).

Routes, in order: proxy inputs (wsc.toml [ci] inputs) unchanged against the merge base with origin/main -> skip in about a second;
in CI -> skip (the `proxy` job runs them); these exact inputs already passed in this worktree -> a pass with one line naming the stamp
(J109: build/proxy/host_tests.stamp holds the hash of the inputs, so a changed input cannot match, and a fresh worktree has none, so a
reviewer's run is a real one); native mingw-w64 and g++ on PATH -> `proxy/tools/build.sh all`; Docker answering ->
`build.sh --docker all`; else no toolchain -> a skip naming the suites not run (core 0.4.0's tests gate shows it as a warn,
J41; it failed until that tag was pinned, J12). build.sh always
runs through Git Bash on Windows (tools/verbs/setup.py git_bash), never the WSL `bash` on PATH.
After `all` passes, the wine smoke test runs on the same route (J42: PR #50's smoke failure was seen only by CI): `--docker smoke`
(the container plus wine), native `smoke` when wine is on PATH, else a warning that it is CI-only, and then no stamp is written.
Measured 2026-11-07 (J109 runs m1 and m2, jobs/J109/report.md): `--docker all` 277 s in a fresh worktree, 216 s with build/ warm, packages
about 30 s of either; `--docker smoke` 67 s, packages about 53 s of that.
The route choice and the input set have their own unit tests below, with git and the toolchain probes injected."""
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(Path(__file__).resolve().parent))
from ci_inputs import ci  # noqa: E402  (the input sets are wsc.toml [ci] since J62)
sv = _load('setup_verb', 'tools/verbs/setup.py')
# The two together stay inside the tests gate's timeout_s (Budget checks it), so a slow build fails here with its own message.
BUILD_TIMEOUT_S = 420   # `--docker all` measured 277 s in a fresh worktree (J109 m1, 2026-11-07), 330 s for J85's proof (run 20261107_j85auto1)
SMOKE_TIMEOUT_S = 150   # `--docker smoke` measured 67 s with apt and wine (J109 m1, 2026-11-07)
STAMP = ROOT / 'build' / 'proxy' / 'host_tests.stamp'   # ignored and per worktree: never committed, never shared (J109 decision 4)


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


def inputs_digest(root=ROOT, git=ci.git, wanted=lambda f: ci.classify([f])['proxy']):
    """sha256 over the path and content of every proxy input as it stands on disk, uncommitted and untracked files included, or None when
    git cannot list them. A submodule (the core) counts file by file, so a local edit in it moves the hash as its pin does."""
    h = hashlib.sha256()

    def add(base, prefix, keep):
        rc, names = git(base, 'ls-files', '--cached', '--others', '--exclude-standard')
        if rc != 0:
            return False
        for name in sorted(set(names)):
            if not keep(prefix + name):
                continue
            p = Path(base) / name
            if (p / '.git').exists():
                if not add(p, f'{prefix}{name}/', lambda _: True):
                    return False
                continue
            h.update(f'{prefix}{name}\0'.encode())
            h.update(p.read_bytes() if p.is_file() else b'\0not a file')
        return True

    return h.hexdigest() if add(root, '', wanted) else None


def stamp_line(stamp, digest):
    """The line to print when `stamp` holds `digest`, else None: a missing stamp, another hash or no hash at all is a miss."""
    try:
        held = Path(stamp).read_text(encoding='utf-8').strip()
    except OSError:
        return None
    return f'proxy host tests and wine smoke passed on these inputs already: {stamp} ({digest[:12]})' if digest and held == digest else None


def write_stamp(stamp, digest):
    if digest:
        Path(stamp).parent.mkdir(parents=True, exist_ok=True)
        Path(stamp).write_text(digest + '\n', encoding='utf-8')


def choose_route(env, base, files, which=shutil.which, docker_ok=docker_answers, names=None, stamped=lambda: None):
    """(kind, detail): kind is 'skip' (detail = reason), 'stamp' (a pass: detail = the line to print), 'native' or 'docker' (detail =
    build.sh arguments), or 'none' (no toolchain: a skip whose reason names the suites not run). files None = base unknown = changed.
    stamped() is asked after the CI check, so CI never reads a stamp."""
    if files is not None and not ci.classify(files)['proxy']:
        return 'skip', f'proxy inputs unchanged against {base[:12]}'
    if env.get('GITHUB_ACTIONS'):
        return 'skip', 'covered by the `proxy` job'
    line = stamped()
    if line:
        return 'stamp', line
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
        digest = []   # taken before the build, so an edit made while it runs cannot be stamped as passed

        def stamped():
            digest.append(inputs_digest())
            return stamp_line(STAMP, digest[0])

        kind, detail = choose_route(os.environ, base or '', files, stamped=stamped)
        if kind == 'stamp':
            print(detail, file=sys.stderr)
            return
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
        write_stamp(STAMP, digest[0])


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

    def test_a_stamp_hit_is_a_pass_before_any_toolchain_probe(self):
        got = choose_route({}, 'abcdef1234567890', ['proxy/core/console.cpp'], no_docker, no_docker, self.NAMES, stamped=lambda: 'the line')
        self.assertEqual(got, ('stamp', 'the line'))

    def test_a_stamp_miss_takes_the_real_route(self):
        got = choose_route({}, 'abcdef1234567890', ['proxy/core/console.cpp'], which_of('g++'), lambda: True, self.NAMES, stamped=lambda: None)
        self.assertEqual(got, ('docker', ['--docker', 'all']))

    def test_ci_and_unchanged_inputs_never_read_the_stamp(self):
        self.assertEqual(choose_route({'GITHUB_ACTIONS': 'true'}, 'abcdef1234567890', ['proxy/core/console.cpp'], stamped=no_docker)[0], 'skip')
        self.assertEqual(choose_route({}, 'abcdef1234567890', ['docs/x.md'], stamped=no_docker)[0], 'skip')

    def test_failed_suites(self):
        self.assertEqual(failed_suites('x\nbuild.sh: test_console FAILED\n', self.NAMES), ['test_console'])
        self.assertEqual(failed_suites('/src/proxy/tests/test_guard.cpp:12:3: error: x', self.NAMES), ['test_guard'])
        self.assertEqual(failed_suites('docker: not found', self.NAMES), [])


class Stamp(unittest.TestCase):
    def test_hit_miss_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            stamp = Path(d) / 'build' / 'proxy' / 'host_tests.stamp'
            self.assertIsNone(stamp_line(stamp, 'a' * 64), 'a missing stamp is a miss')
            write_stamp(stamp, 'a' * 64)
            self.assertIn(str(stamp), stamp_line(stamp, 'a' * 64))
            self.assertIsNone(stamp_line(stamp, 'b' * 64), 'another hash is a miss')
            self.assertIsNone(stamp_line(stamp, None), 'no hash cannot match')

    def test_no_hash_writes_no_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            write_stamp(Path(d) / 'host_tests.stamp', None)
            self.assertEqual(list(Path(d).iterdir()), [])

    def digest(self, root, listed=('proxy/a.cpp', 'proxy/new.cpp', 'docs/x.md')):
        def git(base, *args):
            self.assertEqual(args, ('ls-files', '--cached', '--others', '--exclude-standard'))
            return (0, ['a.cpp']) if Path(base).name == 'core' else (0, ['core', *listed])
        return inputs_digest(root, git, lambda f: f == 'core' or f.startswith('proxy/'))

    def test_the_hash_follows_content_of_inputs_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'core' / '.git').mkdir(parents=True)
            (root / 'proxy').mkdir()
            (root / 'docs').mkdir()
            (root / 'core' / 'a.cpp').write_text('int c;')
            (root / 'proxy' / 'a.cpp').write_text('int a;')
            (root / 'docs' / 'x.md').write_text('one')
            first = self.digest(root)
            self.assertEqual(self.digest(root), first)
            (root / 'docs' / 'x.md').write_text('two')
            self.assertEqual(self.digest(root), first, 'a file outside the set moved the hash')
            (root / 'proxy' / 'a.cpp').write_text('int b;')
            second = self.digest(root)
            self.assertNotEqual(second, first, 'an edited input')
            (root / 'proxy' / 'new.cpp').write_text('int n;')
            third = self.digest(root)
            self.assertNotEqual(third, second, 'a new untracked input')
            (root / 'core' / 'a.cpp').write_text('int d;')
            self.assertNotEqual(self.digest(root), third, 'a local edit in the submodule')

    def test_git_failing_gives_no_hash(self):
        self.assertIsNone(inputs_digest(ROOT, lambda *_: (128, [])))


class Budget(unittest.TestCase):
    def test_the_two_builds_fit_inside_the_gate_deadline(self):
        self.assertLess(BUILD_TIMEOUT_S + SMOKE_TIMEOUT_S, ci.tests_timeout_s())

    def test_the_stamp_is_ignored(self):
        self.assertEqual(ci.git(ROOT, 'check-ignore', '-q', 'build/proxy/host_tests.stamp')[0], 0)


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

    def test_the_proxy_set_covers_every_input_of_the_dll_build_id(self):
        # J73 (audit P4): the input list is the checked-out core's build_id.INPUTS, never a copy; fails naming the role and path
        bid = _load('build_id_inputs', 'core/proxy/tools/build_id.py')
        missed = []
        for role, path, _ in bid.object_ids(ROOT, 'HEAD'):
            probes = ['core'] if path.startswith('core/') else [path, path + '/probe'] if (ROOT / path).is_dir() else [path]
            if not all(ci.classify([p])['proxy'] for p in probes):
                missed.append(f'{role} {path}')
        self.assertEqual(missed, [], 'DLL build id inputs the CI proxy set does not cover: wsc.toml [ci.inputs] proxy')

    def test_the_ui_pins_file_runs_the_proxy_and_viewer_jobs(self):
        got = ci.classify(['viewer/pins.json'])
        self.assertTrue(got['proxy'] and got['viewer'], got)

    def test_workflow_change_runs_all(self):
        self.assertEqual(ci.classify(['.github/workflows/gates.yml']), {'proxy': True, 'harness': True, 'viewer': True})

    def test_harness_set(self):
        self.assertEqual(ci.classify(['core']), {'proxy': True, 'harness': True, 'viewer': False})   # the pin: the proxy and harness live there (J12)
        self.assertEqual(ci.classify(['harness/napoleon/adapter.json']), {'proxy': False, 'harness': True, 'viewer': False})
        # J22: the Windows step of harness-windows runs the Python tests that run bash
        for f in ('tests/test_job_sh.py', 'tests/test_claude_hook.py', 'tests/test_setup.py', 'tests/test_proxy_host.py',
                  'tools/verbs/setup.py', 'tools/claude_hook.py', '.claude/settings.json'):
            self.assertEqual(ci.classify([f]), {'proxy': False, 'harness': True, 'viewer': False}, f)
        self.assertEqual(ci.classify(['tests/test_jobs_hooks.py', 'tools/gates/pipeline.py']), {'proxy': False, 'harness': False, 'viewer': False})

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
