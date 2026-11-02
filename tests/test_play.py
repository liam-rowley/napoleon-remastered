"""Host tests: upscale/pc/play.py, the play-test install and uninstall (J53), against a fake game folder, state folder and proxy kit.

The wrapper composes pc_deploy.py (imported) and install_packs.ps1 (run under Windows PowerShell 5.1), so these tests are skipped
where there is no powershell.exe, and when a real game is running (the wrapper refuses then, by design). The exe identity is a fake
one: the fake Napoleon.exe's sha1, in the kit's identity copy and in place of the repo's identity.json.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'upscale', 'pc'))
PS = shutil.which('powershell.exe') or shutil.which('powershell')

import play  # noqa: E402

MOD, INI = 'napoleon_remastered', 'napoleon_remastered.ini'


def sha(b):
    return hashlib.sha256(b).hexdigest()


@unittest.skipUnless(PS, 'Windows PowerShell (powershell.exe) not found')
class Play(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.game = os.path.join(self.tmp, 'game')
        self.state = os.path.join(self.tmp, 'state')
        self.packs = os.path.join(self.tmp, 'packs_play')
        for d in (os.path.join(self.game, 'data'), self.state, self.packs):
            os.makedirs(d)
        exe = b'MZ fake napoleon'
        self.write(os.path.join(self.game, 'Napoleon.exe'), exe)
        self.write(os.path.join(self.game, 'data', 'data.pack'), b'vanilla')
        self.ident = {'game': 'Napoleon: Total War', 'exe_name': 'Napoleon.exe', 'sha1': hashlib.sha1(exe).hexdigest(),
                      'config_file': INI, 'mod_dir': MOD}
        self.kit()
        for role in ('ui_art', 'icon', 'panel_frame', 'button_state', 'flag'):
            self.pack(role, ('PFH0 ' + role).encode())
        self.start = play.pc_deploy.snapshot(self.game)
        p = mock.patch.object(play.pc_deploy, 'default_identity', return_value=self.ident)
        p.start()
        self.addCleanup(p.stop)
        self.out = io.StringIO()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, path, body):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(body)

    def kit(self):
        k = os.path.join(self.state, 'kits', 'kit_20261102T000000Z_test')
        files = []
        for path, body in (('d3d9.dll', b'proxy dll'), (INI, b'[dev]\r\nskip_intro=0\r\n'), (MOD + '/dxvk/d3d9_dxvk.dll', b'dxvk')):
            staged = sha(body)[:12] + '__' + path.replace('/', '__')
            self.write(os.path.join(k, staged), body)
            files.append({'path': path, 'staged': staged, 'sha256': sha(body), 'size': len(body), 'role': 'proxy'})
        ib = json.dumps(self.ident).encode()
        self.write(os.path.join(k, 'exe_identity.json'), ib)
        man = {'kit_id': os.path.basename(k), 'build_id': 'test', 'exe_name': 'Napoleon.exe', 'other_exes': ['Empire.exe'], 'mod_dir': MOD,
               'config_file': INI, 'owned': ['d3d9.dll', INI, MOD + '/'], 'files': files, 'game_config_files': [INI], 'packs': {},
               'exe_identity': {'name': 'exe_identity.json', 'sha256': sha(ib)}}
        self.write(os.path.join(k, 'manifest.json'), json.dumps(man).encode())

    def pack(self, role, body, manifest_sha=None):
        p = os.path.join(self.packs, f'ui_art_play_{role}.pack')
        self.write(p, body)
        self.write(p + '.json', json.dumps({'sha256': manifest_sha or sha(body), 'bytes': len(body), 'entries': 1,
                                            'held_back': []}).encode())

    def run_play(self, *argv):
        with contextlib.redirect_stdout(self.out):
            code = play.main([*argv, '--game', self.game, '--state', self.state, '--packs', self.packs])
        if code == 2 and 'running' in self.out.getvalue().splitlines()[-1]:
            self.skipTest('a game is running on this machine: ' + self.out.getvalue().splitlines()[-1])
        return code

    def data(self):
        return sorted(os.listdir(os.path.join(self.game, 'data')))

    def test_install_then_uninstall_is_identical(self):
        self.assertEqual(self.run_play('install'), 0, self.out.getvalue())
        self.assertEqual(self.data(), ['data.pack'] + [f'ui_art_play_{r}.pack' for r in ('button_state', 'icon', 'panel_frame', 'ui_art')])
        self.assertTrue(os.path.exists(os.path.join(self.game, 'd3d9.dll')))
        with open(os.path.join(self.game, INI), encoding='utf-8') as f:
            self.assertIn('skip_intro=1', f.read())
        self.assertEqual(self.run_play('status'), 0, self.out.getvalue())
        self.assertEqual(self.run_play('install'), 2)                      # a second install is refused while one is in
        self.assertIn('already in', self.out.getvalue().splitlines()[-1])
        self.assertEqual(self.run_play('uninstall'), 0, self.out.getvalue())
        self.assertEqual(play.pc_deploy.diff_snapshots(self.start, play.pc_deploy.snapshot(self.game)), [])
        trash = [d for d in os.listdir(os.path.join(self.state, '_to_delete')) if d.startswith('play_')]
        self.assertEqual(len(os.listdir(os.path.join(self.state, '_to_delete', trash[0]))), 4)   # moved, never deleted
        self.assertFalse(os.path.exists(play.record_path(self.state)))
        self.assertEqual(self.run_play('status'), 0)

    def test_roles_by_name_and_a_missing_pack(self):
        self.assertEqual(self.run_play('install', '--roles', 'flag'), 0, self.out.getvalue())
        self.assertEqual(self.data(), ['data.pack', 'ui_art_play_flag.pack'])
        self.assertEqual(self.run_play('uninstall'), 0, self.out.getvalue())
        self.assertEqual(self.run_play('install', '--roles', 'portrait'), 2)
        self.assertIn('no play pack for', self.out.getvalue())
        self.assertEqual(play.pc_deploy.diff_snapshots(self.start, play.pc_deploy.snapshot(self.game)), [])

    def test_a_pack_already_in_data_is_refused_before_any_change(self):
        self.write(os.path.join(self.game, 'data', 'ui_art_play_icon.pack'), b'someone else')
        start = play.pc_deploy.snapshot(self.game)
        self.assertEqual(self.run_play('install'), 2)
        self.assertIn('never overwritten', self.out.getvalue())
        self.assertEqual(play.pc_deploy.diff_snapshots(start, play.pc_deploy.snapshot(self.game)), [])
        self.assertFalse(os.path.exists(os.path.join(self.state, 'install.json')))

    def test_a_bad_sha_is_refused_before_any_change(self):
        self.pack('icon', b'PFH0 icon', manifest_sha='0' * 64)
        self.assertEqual(self.run_play('install'), 2)
        self.assertIn('ui_art_play_icon.pack sha256', self.out.getvalue())
        self.assertEqual(play.pc_deploy.diff_snapshots(self.start, play.pc_deploy.snapshot(self.game)), [])
        self.assertFalse(os.path.exists(play.record_path(self.state)))

    def test_a_foreign_file_is_reported_and_the_uninstall_says_it_differs(self):
        self.assertEqual(self.run_play('install'), 0, self.out.getvalue())
        self.write(os.path.join(self.game, 'data', 'stray.pack'), b'not ours')
        self.run_play('status')
        self.assertIn('foreign: 1', self.out.getvalue())
        self.assertIn('data/stray.pack', self.out.getvalue())
        self.assertEqual(self.run_play('uninstall'), 1)
        self.assertIn('DIFFERS', self.out.getvalue())
        self.assertIn('added   data/stray.pack', self.out.getvalue())

    def test_a_non_vanilla_exe_is_refused(self):
        self.write(os.path.join(self.game, 'Napoleon.exe'), b'MZ patched')
        self.assertEqual(self.run_play('install'), 2)
        self.assertIn('MISMATCH', self.out.getvalue())

    def test_an_agent_lock_is_refused(self):
        self.write(os.path.join(self.state, 'watcher', 'game.lock'), b'owner=J99 session=x purpose=test\n')
        with mock.patch.object(play.pc_deploy, 'running_check', return_value=''):   # no live watcher heartbeat in the fake state
            self.assertEqual(self.run_play('install'), 2)
        self.assertIn('game lock', self.out.getvalue())


if __name__ == '__main__':
    unittest.main()
