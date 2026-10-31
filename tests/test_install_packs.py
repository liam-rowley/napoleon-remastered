"""Host tests: upscale/pc/install_packs.ps1 leaves data\\ as it found it when an install fails (J50 review round 1).

Runs the script under Windows PowerShell 5.1 against a temporary fake game folder; skipped where there is no powershell.exe
(the PC and the Windows CI job have it) and when the script refuses because a game is running.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'upscale', 'pc', 'install_packs.ps1')
PS = shutil.which('powershell.exe') or shutil.which('powershell')


@unittest.skipUnless(PS, 'Windows PowerShell (powershell.exe) not found')
class InstallPacks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.game = os.path.join(self.tmp, 'game')
        self.data = os.path.join(self.game, 'data')
        self.src = os.path.join(self.tmp, 'src')
        self.trash = os.path.join(self.tmp, 'trash')
        os.makedirs(self.data)
        os.makedirs(self.src)
        self.write(os.path.join(self.data, 'data.pack'), b'vanilla')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, path, body):
        with open(path, 'wb') as f:
            f.write(body)

    def pack(self, name, body, manifest_sha=None):
        p = os.path.join(self.src, name)
        self.write(p, body)
        with open(p + '.json', 'w', encoding='utf-8') as f:
            json.dump({'sha256': manifest_sha or hashlib.sha256(body).hexdigest()}, f)
        return p

    def run_ps(self, *args):
        """Called the way a watcher job calls it (`& <script> ... -Packs @(a, b)`); a list argument becomes a PowerShell array."""
        def q(v):
            return "'" + v.replace("'", "''") + "'"
        parts = ['@(' + ', '.join(q(x) for x in a) + ')' if isinstance(a, list) else (a if a.startswith('-') else q(a))
                 for a in ('-Game', self.game, *args)]
        cmd = f"& {q(SCRIPT)} {' '.join(parts)}; exit $LASTEXITCODE"
        r = subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', cmd], capture_output=True, text=True, timeout=120)
        out = json.loads(r.stdout)
        if out['status'] == 'refused' and out['reason'].startswith('a game is running'):
            self.skipTest(out['reason'])
        return r.returncode, out

    def packs_in_data(self):
        return sorted(n for n in os.listdir(self.data) if n != 'data.pack')

    def test_install_then_uninstall(self):
        a = self.pack('ui_art_2x5_icon.pack', b'aaaa')
        code, out = self.run_ps('-Mode', 'install', '-Packs', a, '-Trash', self.trash)
        self.assertEqual((code, out['status']), (0, 'ok'), out)
        self.assertEqual(self.packs_in_data(), ['ui_art_2x5_icon.pack'])
        code, out = self.run_ps('-Mode', 'uninstall', '-Names', 'ui_art_2x5_icon.pack', '-Trash', self.trash)
        self.assertEqual((code, out['status']), (0, 'ok'), out)
        self.assertEqual(self.packs_in_data(), [])

    def test_bad_manifest_on_a_later_pack_copies_nothing(self):
        a = self.pack('ui_art_2x5_icon.pack', b'aaaa')
        b = self.pack('ui_art_2x5_flag.pack', b'bbbb', manifest_sha='0' * 64)
        code, out = self.run_ps('-Mode', 'install', '-Packs', [a, b], '-Trash', self.trash)
        self.assertEqual((code, out['status']), (1, 'failed'), out)
        self.assertEqual(self.packs_in_data(), [], 'a failed install must leave no pack in data\\')

    def test_install_needs_trash(self):
        a = self.pack('ui_art_2x5_icon.pack', b'aaaa')
        code, out = self.run_ps('-Mode', 'install', '-Packs', a)
        self.assertEqual((code, out['status']), (2, 'refused'), out)
        self.assertEqual(self.packs_in_data(), [])


if __name__ == '__main__':
    unittest.main()
