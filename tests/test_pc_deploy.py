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

    def test_failed_install_still_uninstalls(self):
        """A copy failing half-way (disk full, file locked) must leave a record the uninstall can restore from (review of J1)."""
        (self.game / 'd3d9.dll').write_bytes(b'someone else\'s d3d9 wrapper')
        before = pd.snapshot(self.game)
        real, calls = pd.shutil.copyfile, []
        def flaky(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError('disk full')
            return real(src, dst)
        pd.shutil.copyfile = flaky
        try:
            with self.assertRaises(OSError):
                pd.install(self.kit, self.game, self.state)
        finally:
            pd.shutil.copyfile = real
        self.assertTrue((self.state / 'install.json').exists())
        self.assertTrue(pd.uninstall(self.game, self.state))
        self.assertEqual((self.game / 'd3d9.dll').read_bytes(), b'someone else\'s d3d9 wrapper')
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


class HarnessKit(unittest.TestCase):
    """The watcher kit (J2): unique ids, sha-checked manifest, CRLF/ASCII guard for PC scripts, and the install-time game check that
    asks the watcher (not the device VM) which processes run."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_kit_manifest_and_stale_guard(self):
        kit = pd.build_harness_kit(self.t / 'kits', build_id='test')
        man, bad = pd.verify_harness_kit(kit)
        self.assertEqual(bad, [])
        self.assertEqual(man['kind'], 'harness')
        self.assertTrue(man['kit_id'].startswith('harness_'))
        paths = {e['path'] for e in man['files']}
        for want in ('src/watcher.ps1', 'src/watch.cmd', 'src/update.ps1', 'src/adapter.json', 'profiles/vanilla/profile.json',
                     'profiles/vanilla/mod_ini.absent', 'profiles/proxy-dxvk/mod_ini.set'):
            self.assertIn(want, paths)
        self.assertEqual({k['name'] for k in man['kit_files']}, {'install.ps1', 'Install watcher.cmd', 'Uninstall watcher.cmd', 'job.sh', 'adapter.json'})
        self.assertRegex(man['watcher_version'], r'^\d+\.\d+\.\d+')
        self.assertTrue(man['watcher_root'].endswith('\\watcher'))
        for e in man['files']:
            self.assertTrue(e['staged'].startswith(e['sha256'][:12] + '__'))
        # every Windows script in the kit is CRLF and ASCII, whatever the checkout had
        for e in man['files']:
            if e['path'].endswith(('.ps1', '.cmd')):
                b = (kit / e['staged']).read_bytes()
                self.assertNotIn(b'\n', b.replace(b'\r\n', b''), e['path'])
                b.decode('ascii')
        # a stale resend of one staged file is caught
        (kit / man['files'][0]['staged']).write_bytes(b'old cached copy')
        self.assertTrue(pd.verify_harness_kit(kit)[1])
        (kit / 'install.ps1').write_bytes(b'old installer')
        self.assertTrue(any('install.ps1' in x for x in pd.verify_harness_kit(kit)[1]))

    def test_new_id_every_time(self):
        a = pd.build_harness_kit(self.t / 'kits', build_id='a')
        b = pd.build_harness_kit(self.t / 'kits', build_id='b')
        self.assertNotEqual(a.name, b.name)

    def test_norm_for_pc(self):
        self.assertEqual(pd.norm_for_pc('x.cmd', b'a\nb\r\nc\n'), b'a\r\nb\r\nc\r\n')
        self.assertEqual(pd.norm_for_pc('x.json', b'a\nb\n'), b'a\nb\n')
        with self.assertRaises(SystemExit) as e:
            pd.norm_for_pc('x.ps1', 'caf\u00e9'.encode('utf-8'))
        self.assertIn('non-ASCII', str(e.exception))

    def _status(self, procs, age=1.0, alive=True):
        w = self.t / 'state' / 'watcher'
        w.mkdir(parents=True, exist_ok=True)
        (w / 'watcher.status').write_text(json.dumps({'processes': procs}), encoding='utf-8')
        if alive:
            (w / 'watcher.alive').write_text('x')
            os.utime(w / 'watcher.alive', (time.time() - age, time.time() - age))
        return self.t / 'state'

    def test_running_check_asks_the_watcher_for_both_titles(self):
        game = self.t / 'game'
        game.mkdir()
        st = self._status([{'image': 'Empire.exe', 'pid': 42}])
        why = pd.running_check(game, 'napoleon_remastered', 'Napoleon.exe', state=st, other_exes=['Empire.exe'])
        self.assertIn('Empire.exe (pid 42)', why)
        st = self._status([{'image': 'Napoleon.exe', 'pid': 7}])
        self.assertIn('Napoleon.exe (pid 7)', pd.running_check(game, 'napoleon_remastered', 'Napoleon.exe', state=st, other_exes=['Empire.exe']))
        st = self._status([])
        self.assertEqual(pd.running_check(game, 'napoleon_remastered', 'Napoleon.exe', state=st, other_exes=['Empire.exe']), '')

    def test_stale_watcher_cannot_vouch_and_no_watcher_falls_back(self):
        game = self.t / 'game'
        game.mkdir()
        st = self._status([], age=120)
        self.assertIn('heartbeat is', pd.running_check(game, 'm', 'Napoleon.exe', state=st))
        # the status file says nothing was running but nobody is watching: refuse rather than guess
        self.assertEqual(pd.running_check(game, 'm', 'Napoleon.exe', state=self.t / 'nowatcher'), '')   # never installed: the old log heuristic
        log = game / 'm' / 'logs' / 'proxy.log'
        log.parent.mkdir(parents=True)
        log.write_text('launch x\nstarted\n')
        self.assertIn('may be running', pd.running_check(game, 'm', 'Napoleon.exe', state=self.t / 'nowatcher'))


if __name__ == '__main__':
    unittest.main()
