"""Host tests for the pure parts of tools/verbs/setup.py (`wsc setup`): version parsing, which bash is on PATH, CR detection, the
pinned core tag, core.hooksPath and the main clone behind a worktree. Runs in `wsc gates` (tests gate)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

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

    def test_every_check_has_a_function(self):
        for c in sv.CHECKS:
            self.assertTrue(callable(getattr(sv, f'check_{c}', None)), c)


if __name__ == '__main__':
    unittest.main()
