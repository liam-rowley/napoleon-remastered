"""Host tests of tools/pc_state.py (J79, audit G14): the uiscale and upscale verbs and uiscale/napoleon/cli.py take the PC state folder
from the adapter (default) or $NAPOLEON_STATE_DIR (override), not from a path literal of their own. No PC needed.
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import pc_state  # noqa: E402


def verb(name):
    spec = importlib.util.spec_from_file_location(f'{name}_verb', ROOT / 'tools' / 'verbs' / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class StateDir(unittest.TestCase):
    def test_default_is_the_adapter_state_dir(self):
        ad = json.loads((ROOT / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
        base = Path(ad['state_dir'])
        self.assertEqual(pc_state.state_dir(ROOT, {}), base)
        self.assertEqual(pc_state.state_dir(ROOT, {pc_state.ENV: ''}), base)          # empty is unset
        self.assertEqual(pc_state.art_python(ROOT, {}), base / 'upscale' / 'art_build' / 'py' / 'python.exe')
        self.assertEqual(pc_state.upscale_work(ROOT, {}), base / 'upscale' / 'work')
        self.assertEqual(pc_state.uiscale_work(ROOT, {}), base / 'uiscale' / 'work')

    def test_environment_override(self):
        env = {pc_state.ENV: str(Path('/elsewhere/state'))}
        self.assertEqual(pc_state.state_dir(ROOT, env), Path('/elsewhere/state'))
        self.assertEqual(pc_state.upscale_root(ROOT, env), Path('/elsewhere/state') / 'upscale')
        self.assertEqual(pc_state.uiscale_work(ROOT, env), Path('/elsewhere/state') / 'uiscale' / 'work')

    def test_no_state_literal_left_in_the_verbs_or_the_uiscale_config(self):
        for p in ('tools/verbs/uiscale.py', 'tools/verbs/upscale.py', 'uiscale/napoleon/cli.py'):
            self.assertNotIn('napoleon_remastered_pc', (ROOT / p).read_text(encoding='utf-8').lower(), p)
        cfg = json.loads((ROOT / 'uiscale' / 'napoleon' / 'config.json').read_text(encoding='utf-8'))
        self.assertFalse({'work', 'upscale_work'} & set(cfg))


class Verbs(unittest.TestCase):
    """each verb looks for the art_build Python under the resolved state folder (override: a temp folder with none in it)"""

    def run_verb(self, name, action, state):
        m = verb(name)
        out = io.StringIO()
        with mock.patch.dict(os.environ, {pc_state.ENV: state}), contextlib.redirect_stdout(out):
            rc = m.run(types.SimpleNamespace(action=action, rest=[]), types.SimpleNamespace(root=str(ROOT)))
        return rc, out.getvalue()

    def test_uiscale_verb_uses_the_override(self):
        with tempfile.TemporaryDirectory() as t:
            rc, out = self.run_verb('uiscale', 'status', t)
        self.assertEqual(rc, 1)
        self.assertIn(str(Path(t) / 'upscale' / 'art_build' / 'py' / 'python.exe'), out)

    def test_upscale_verb_uses_the_override(self):
        with tempfile.TemporaryDirectory() as t:
            rc, out = self.run_verb('upscale', 'env', t)
        self.assertEqual(rc, 1)
        self.assertIn(str(Path(t) / 'upscale' / 'art_build' / 'py' / 'python.exe'), out)


if __name__ == '__main__':
    unittest.main()
