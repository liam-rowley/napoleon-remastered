"""Host tests for core/proxy/tools/build_id.py (J45): the DLL build id follows the inputs' content, not the history, and build.sh and rule 79
(tools/pr_policy.py) compute the same id. Each test runs on a throwaway git repository holding copies of the real id tool and build.sh."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bi = _load('build_id', 'core/proxy/tools/build_id.py')
pp = _load('pr_policy', 'tools/pr_policy.py')
sv = _load('setup_verb', 'tools/verbs/setup.py')


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name) / 'repo'
        self.d.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.invalid')
        self.git('config', 'user.name', 'test')
        self.git('config', 'core.autocrlf', 'false')
        self.write('proxy/core/a.cpp', 'int a;\n')
        self.write('proxy/napoleon/adapter.cpp', 'int b;\n')
        self.write('proxy/tools/fetch_lua.py', '# lua\n')
        for rel in ('proxy/tools/build.sh', 'proxy/tools/build_id.py', 'proxy/tools/layout.py'):
            self.write(rel, (ROOT / 'core' / rel).read_bytes())   # the tools live in the core since J12; the fixture keeps the flat layout
        self.write('wsc.toml', '# the repo marker layout.py looks for' + chr(10))
        self.write('docs/x.md', 'x\n')
        self.commit('inputs')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a, cwd=None):
        return subprocess.run(['git', *a], cwd=cwd or self.d, capture_output=True, text=True, check=True).stdout.strip()

    def write(self, rel, data):
        p = self.d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode())

    def commit(self, msg):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', msg)

    def bid(self, root=None, dirty=True):
        return bi.build_id(root or self.d, 'HEAD', dirty=dirty)


class ContentNotHistory(Fixture):
    def test_failing_fixture_a_reworded_or_amended_commit_keeps_the_id(self):
        before = self.bid()
        old = self.git('log', '-1', '--format=%h', '--abbrev=12', '--', 'proxy/core')   # the J44 incident: the old id moves...
        self.git('commit', '-q', '--amend', '-m', 'inputs, reworded')
        self.assertNotEqual(old, self.git('log', '-1', '--format=%h', '--abbrev=12', '--', 'proxy/core'))
        self.assertEqual(self.bid(), before)                                            # ...the content id does not
        self.assertRegex(before, r'^[0-9a-f]{12}$')

    def test_failing_fixture_a_rebased_branch_keeps_the_id(self):
        self.git('checkout', '-q', '-b', 'job/J9')
        self.write('proxy/core/a.cpp', 'int a2;\n')
        self.commit('change core')
        on_branch = self.bid()
        self.git('checkout', '-q', 'main')
        self.write('docs/x.md', 'main moved\n')
        self.commit('main moves, no inputs')
        self.git('checkout', '-q', 'job/J9')
        self.git('rebase', '-q', 'main')
        self.assertEqual(self.bid(), on_branch)
        self.write('jobs/J9/report.md', 'report\n')   # a later report commit keeps it too
        self.commit('report')
        self.assertEqual(self.bid(), on_branch)

    def test_a_change_to_any_one_input_changes_the_id(self):
        seen = {self.bid()}
        for _, rel, _, _ in bi.locate(self.d):
            p = self.d / rel
            target = next(p.glob('*')) if p.is_dir() else p
            target.write_bytes(target.read_bytes() + b'\n# changed\n')
            self.commit(f'change {rel}')
            new = self.bid()
            self.assertNotIn(new, seen, rel)
            seen.add(new)

    def test_a_moved_input_with_the_same_content_keeps_its_role(self):
        # role names, not paths, are hashed: the same objects under the same roles are the same id
        oids = bi.object_ids(self.d)
        self.assertEqual(bi.content_id(oids), bi.content_id([(r, 'elsewhere/' + p, o) for r, p, o in oids]))
        self.assertNotEqual(bi.content_id(oids), bi.content_id([(r + 'x', p, o) for r, p, o in oids]))

    def test_failing_fixture_an_uncommitted_input_change_is_dirty(self):
        clean = self.bid()
        self.write('proxy/napoleon/adapter.cpp', 'int b2;\n')
        self.assertEqual(self.bid(), clean + '-dirty')
        self.assertEqual(self.bid(dirty=False), clean)
        self.git('checkout', '-q', '--', '.')
        self.write('docs/x.md', 'not an input\n')
        self.assertEqual(self.bid(), clean)

    def test_failing_fixture_a_shallow_clone_gives_the_same_id(self):
        self.write('docs/x.md', 'later\n')
        self.commit('later, no inputs')
        shallow = Path(self.tmp.name) / 'shallow'
        subprocess.run(['git', 'clone', '-q', '--depth', '1', self.d.as_uri(), str(shallow)], check=True, capture_output=True)
        self.assertEqual(self.git('rev-parse', '--is-shallow-repository', cwd=shallow), 'true')
        self.assertEqual(self.bid(shallow), self.bid())

    def test_an_untracked_input_is_refused_not_guessed(self):
        self.git('rm', '-q', '--cached', 'proxy/tools/fetch_lua.py')   # still on disk, gone from the commit
        self.git('commit', '-q', '-m', 'untrack fetch_lua')
        with self.assertRaises(ValueError) as e:
            self.bid()
        self.assertIn('proxy/tools/fetch_lua.py', str(e.exception))
        self.assertTrue(pp.dll_build_id(self.d).startswith('nogit'))   # rule 79 then matches no ledger line

    def test_outside_git_is_nogit(self):
        plain = Path(self.tmp.name) / 'plain'
        plain.mkdir()
        self.assertEqual(bi.build_id(plain), 'nogit')


class MovedToTheCore(Fixture):
    """J12: after the move the core sources and the build tools live in the `core` submodule (proxy/src, proxy/tools); the same
    content under the same roles must give the same id, read through the gitlink, and a change there must still be seen."""
    def make_moved(self):
        core = Path(self.tmp.name) / 'core_origin'
        core.mkdir()
        g = lambda *a, cwd=core: self.git(*a, cwd=cwd)
        g('init', '-q', '-b', 'main'); g('config', 'user.email', 't@example.invalid'); g('config', 'user.name', 'test')
        g('config', 'core.autocrlf', 'false')
        for src, dst in (('proxy/core/a.cpp', 'proxy/src/a.cpp'), ('proxy/tools/build.sh', 'proxy/tools/build.sh'),
                         ('proxy/tools/build_id.py', 'proxy/tools/build_id.py'), ('proxy/tools/fetch_lua.py', 'proxy/tools/fetch_lua.py'),
                         ('proxy/tools/layout.py', 'proxy/tools/layout.py'), ('wsc.toml', 'wsc.toml')):
            (core / dst).parent.mkdir(parents=True, exist_ok=True)
            (core / dst).write_bytes((self.d / src).read_bytes())
        g('add', '-A'); g('commit', '-q', '-m', 'core')
        game = Path(self.tmp.name) / 'game'
        subprocess.run(['git', '-c', 'core.autocrlf=false', 'clone', '-q', self.d.as_uri(), str(game)], check=True, capture_output=True)
        gg = lambda *a: g(*a, cwd=game)
        gg('config', 'user.email', 't@example.invalid'); gg('config', 'user.name', 'test'); gg('config', 'core.autocrlf', 'false')
        gg('rm', '-q', '-r', 'proxy/core', 'proxy/tools')
        gg('-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', core.as_uri(), 'core')
        gg('commit', '-q', '-m', 'move')
        return game

    def test_failing_fixture_the_moved_layout_keeps_the_id(self):
        flat = self.bid()
        game = self.make_moved()
        self.assertEqual(bi.build_id(game, 'HEAD'), flat)
        paths = {role: path for role, path, _ in bi.object_ids(game)}
        self.assertEqual(paths['core'], 'core/proxy/src')
        self.assertEqual(paths['build_sh'], 'core/proxy/tools/build.sh')
        self.assertEqual(paths['adapter'], 'proxy/napoleon')

    def test_failing_fixture_a_change_inside_the_submodule_is_seen(self):
        flat = self.bid()
        game = self.make_moved()
        (game / 'core/proxy/src/a.cpp').write_text('int a3;' + chr(10))
        self.assertEqual(bi.build_id(game, 'HEAD'), flat + '-dirty')           # uncommitted in the submodule
        g = lambda *a: subprocess.run(['git', *a], cwd=game / 'core', capture_output=True, text=True, check=True)
        g('config', 'user.email', 't@example.invalid'); g('config', 'user.name', 'test'); g('commit', '-q', '-am', 'core change')
        self.assertEqual(bi.build_id(game, 'HEAD'), flat + '-dirty')           # committed there, not pinned by the game repo
        subprocess.run(['git', 'commit', '-q', '-am', 'pin'], cwd=game, check=True, capture_output=True)
        new = bi.build_id(game, 'HEAD')
        self.assertNotIn('-dirty', new)
        self.assertNotEqual(new, flat)


class OneImplementation(Fixture):
    def test_build_sh_and_rule_79_agree(self):
        bash = sv.git_bash()
        if not bash:
            self.skipTest('no Git Bash to run build.sh (`python3 core/wsc.py setup` says why)')
        env = None
        if shutil.which('python3') is None:   # build.sh calls python3; give it this interpreter
            import os
            shim = Path(self.tmp.name) / 'bin'
            shim.mkdir()
            (shim / 'python3').write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n')
            env = dict(os.environ, PATH=f'{shim}{os.pathsep}{os.environ["PATH"]}')
        r = subprocess.run([bash, 'proxy/tools/build.sh', 'id'], cwd=self.d, capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), pp.dll_build_id(self.d))
        self.assertEqual(r.stdout.strip(), self.bid())

    def test_neither_computes_its_own_id(self):
        sh = (ROOT / 'core/proxy/tools/build.sh').read_text(encoding='utf-8')
        pol = (ROOT / 'tools/pr_policy.py').read_text(encoding='utf-8')
        self.assertIn('proxy/tools/build_id.py', sh)
        self.assertIn('proxy/tools/build_id.py', pol)
        for src in (sh, pol):
            self.assertNotIn('--abbrev=12', src)
            self.assertNotIn('is-shallow-repository', src)


if __name__ == '__main__':
    unittest.main()
