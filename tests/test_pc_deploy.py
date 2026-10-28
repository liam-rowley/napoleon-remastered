"""Host tests for proxy/tools/pc_deploy.py (manifest, stale-resend guard, install, byte-exact uninstall, config edits, closed check)
on a fake game folder. Runs in `wsc gates` (tests gate)."""
import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pc_deploy', ROOT / 'proxy/tools/pc_deploy.py')
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)


class Deploy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.game, self.state, self.kits, self.src = t / 'game', t / 'state', t / 'kits', t / 'src'
        (self.game / 'data').mkdir(parents=True)
        (self.game / 'Napoleon.exe').write_bytes(b'MZ' + os.urandom(4000))
        (self.game / 'data' / 'big.pack').write_bytes(os.urandom(3000))
        (self.game / 'empty_dir').mkdir()
        self.src.mkdir()
        (self.src / 'd3d9.dll').write_bytes(b'MZproxy' + os.urandom(100))
        (self.src / 'd3d9_dxvk.dll').write_bytes(b'MZdxvk' + os.urandom(100))
        (self.src / 'LICENSE.dxvk.txt').write_text('zlib')
        self.kit = pd.build_kit(self.kits, dll=self.src / 'd3d9.dll', dxvk_dir=self.src, build_id='test')

    def tearDown(self):
        self.tmp.cleanup()

    def test_kit_manifest(self):
        man, bad = pd.verify_kit(self.kit)
        self.assertEqual(bad, [])
        self.assertEqual({e['path'] for e in man['files']},
                         {'d3d9.dll', 'napoleon_remastered.ini', 'napoleon_remastered/dxvk/d3d9_dxvk.dll', 'napoleon_remastered/LICENSE.dxvk.txt'})
        for e in man['files']:
            self.assertTrue(e['staged'].startswith(e['sha256'][:12] + '__'))   # unique per content
        self.assertTrue((self.kit / 'pc_deploy.py').exists())

    def test_stale_resend_refused(self):
        man = json.loads((self.kit / 'manifest.json').read_text())
        (self.kit / man['files'][0]['staged']).write_bytes(b'old cached copy')
        with self.assertRaises(SystemExit) as e:
            pd.install(self.kit, self.game, self.state, assume_closed=True)
        self.assertIn('stale or partial', str(e.exception))
        self.assertFalse((self.game / 'd3d9.dll').exists())   # nothing installed

    def test_install_uninstall_byte_exact(self):
        before = pd.snapshot(self.game)
        pd.install(self.kit, self.game, self.state)
        self.assertEqual(pd.status(self.game, self.state), 0)
        # what the DLL and DXVK write at runtime, all inside the owned paths
        (self.game / 'napoleon_remastered' / 'logs').mkdir(parents=True)
        (self.game / 'napoleon_remastered' / 'logs' / 'proxy.log').write_text('... process detach (process exit)\n')
        (self.game / 'napoleon_remastered' / 'dxvk' / 'Napoleon_d3d9.log').write_text('dxvk')
        pd.set_keys(self.game, ['proxy.backend=system'], 'napoleon_remastered.ini')
        self.assertTrue(pd.uninstall(self.game, self.state))
        self.assertEqual(pd.diff_snapshots(before, pd.snapshot(self.game)), [])
        moved = list((self.state / '_to_delete').rglob('proxy.log'))
        self.assertEqual(len(moved), 1)   # moved, never deleted
        self.assertFalse((self.state / 'install.json').exists())

    def test_foreign_file_backed_up_and_restored(self):
        (self.game / 'd3d9.dll').write_bytes(b'someone else\'s d3d9 wrapper')
        before = pd.snapshot(self.game)
        pd.install(self.kit, self.game, self.state)
        self.assertNotEqual((self.game / 'd3d9.dll').read_bytes(), b'someone else\'s d3d9 wrapper')
        self.assertTrue(pd.uninstall(self.game, self.state))
        self.assertEqual((self.game / 'd3d9.dll').read_bytes(), b'someone else\'s d3d9 wrapper')
        self.assertEqual(pd.diff_snapshots(before, pd.snapshot(self.game)), [])

    def test_reinstall_then_uninstall(self):
        before = pd.snapshot(self.game)
        pd.install(self.kit, self.game, self.state)
        (self.src / 'd3d9.dll').write_bytes(b'MZproxy v2')
        kit2 = pd.build_kit(self.kits, dll=self.src / 'd3d9.dll', dxvk_dir=self.src, build_id='test2')
        pd.install(kit2, self.game, self.state)
        self.assertEqual((self.game / 'd3d9.dll').read_bytes(), b'MZproxy v2')
        self.assertTrue(pd.uninstall(self.game, self.state))
        self.assertEqual(pd.diff_snapshots(before, pd.snapshot(self.game)), [])

    def test_stray_file_reported(self):
        pd.install(self.kit, self.game, self.state)
        (self.game / 'Napoleon_d3d9.log').write_text('dxvk wrote into the game folder')   # what the env redirect prevents
        self.assertFalse(pd.uninstall(self.game, self.state))
        self.assertTrue((self.game / 'Napoleon_d3d9.log').exists())   # not ours: reported, never touched

    def test_running_check(self):
        log = self.game / 'napoleon_remastered' / 'logs' / 'proxy.log'
        log.parent.mkdir(parents=True)
        log.write_text('2026-10-28T20:00:00.000Z [INFO ] [t1] init done\n')
        if os.name != 'nt':
            self.assertIn('may be running', pd.running_check(self.game, 'napoleon_remastered', 'Napoleon.exe'))
            self.assertEqual(pd.running_check(self.game, 'napoleon_remastered', 'Napoleon.exe', now=time.time() + 3600), '')
            log.write_text('x\n2026-10-28T20:00:00.000Z [INFO ] [t1] process detach (process exit)\n')
            self.assertEqual(pd.running_check(self.game, 'napoleon_remastered', 'Napoleon.exe'), '')
            log.write_text('init done\n')
            with self.assertRaises(SystemExit):
                pd.install(self.kit, self.game, self.state)

    def test_edit_ini(self):
        t = '; c\r\n[proxy]\r\n; d\r\nbackend=dxvk\r\nenabled=1\r\n'
        o = pd.edit_ini(t, {'proxy.backend': 'system', 'proxy.exe_guard_force_mismatch': '1', 'other.x': '2'})
        self.assertEqual(o, '; c\r\n[proxy]\r\nexe_guard_force_mismatch=1\r\n; d\r\nbackend=system\r\nenabled=1\r\n\r\n[other]\r\nx=2\r\n')

    def test_resolve_bare_keys(self):
        t = '[proxy]\nbackend=dxvk\nenabled=1\n[other]\nenabled=0\n'
        self.assertEqual(pd.resolve_keys(t, {'backend': 'system', 'other.enabled': '1'}),
                         {'proxy.backend': 'system', 'other.enabled': '1'})
        with self.assertRaisesRegex(SystemExit, 'ambiguous'):
            pd.resolve_keys(t, {'enabled': '1'})
        with self.assertRaisesRegex(SystemExit, 'not in the file'):
            pd.resolve_keys(t, {'nope': '1'})

    def test_snapshot_big_files_by_mtime(self):
        a = pd.snapshot(self.game, big=1000)
        self.assertIsNone(a['data/big.pack']['sha256'])
        os.utime(self.game / 'data' / 'big.pack', ns=(0, 10**18))
        self.assertEqual(pd.diff_snapshots(a, pd.snapshot(self.game, big=1000)), ['touched data/big.pack (large file: same size, other mtime)'])


if __name__ == '__main__':
    unittest.main()
