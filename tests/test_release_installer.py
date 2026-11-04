"""Host tests of the player installer (release/core/installer/rr.ps1, J38) on a synthetic game folder: install and uninstall with the PowerShell
installer and with core/proxy/tools/pc_deploy.py and compare the resulting snapshots (behaviour parity is the contract), the refusals (non-vanilla
exe), check, repair, a game update, the UI cache move, and the support bundle's redaction. Windows only (Windows PowerShell 5.1); skipped elsewhere."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core' / 'proxy' / 'tools'))
import pc_deploy  # noqa: E402

RR = ROOT / 'release' / 'core' / 'installer' / 'rr.ps1'
PS = shutil.which('powershell') if os.name == 'nt' else None
EXE = b'MZ vanilla exe ' * 100
MOD, INI = 'napoleon_remastered', 'napoleon_remastered.ini'
PAYLOAD = {   # target -> (component, bytes, config)
    'd3d9.dll': ('proxy', b'proxy dll bytes' * 50, False),
    INI: ('proxy', b'[proxy]\r\nbackend=dxvk\r\n', True),
    f'{MOD}/dxvk/d3d9_dxvk.dll': ('proxy', b'dxvk' * 300, False),
    f'{MOD}/ui/a.rules': ('ui', b'redirect a -> b\r\n', False),
    'data/ui_scale_x.pack': ('ui', b'PACK' * 500, False),
}
STEAM_ID = '76561198012345678'
PLANTED = {'user': 'zzTestUser', 'machine': 'ZZ-TESTBOX', 'profile': 'C:\\Users\\zzTestUser'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def make_release(tmp, exe=EXE):
    """A release folder in the real layout (manifest.json, installer\\rr.ps1, installer\\exe_identity.json, payload\\<component>\\...)."""
    rel = Path(tmp) / 'Napoleon Remastered 9.9.9'
    (rel / 'installer').mkdir(parents=True)
    shutil.copy(RR, rel / 'installer' / 'rr.ps1')
    ident = {'game': 'Test Game', 'exe_name': 'Napoleon.exe', 'sha1': hashlib.sha1(exe).hexdigest(), 'config_file': INI, 'mod_dir': MOD}
    ib = json.dumps(ident).encode()
    (rel / 'installer' / 'exe_identity.json').write_bytes(ib)
    files = []
    for target, (comp, data, cfg) in PAYLOAD.items():
        p = rel / 'payload' / comp / target
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        files.append({'path': target, 'component': comp, 'size': len(data), 'sha256': sha(data), 'payload': f'payload/{comp}/{target}', 'config': cfg})
    man = {'product': 'Napoleon Remastered', 'version': '9.9.9', 'dll_build_id': 'abc123abc123', 'core_tag': 'v0.0.0', 'commit': 'f' * 40,
           'game': {'name': 'Test Game', 'exe_name': 'Napoleon.exe', 'mod_dir': MOD, 'config_file': INI, 'steam_folder': 'Napoleon Total War',
                    'other_exes': ['Empire.exe'], 'appdata_subpath': 'Test\\Napoleon'},
           'state_dir_name': 'napoleon_remastered', 'clear_ui_cache': True,
           'runtime_globs': [f'{MOD}/logs/*', f'{MOD}/dumps/*', f'{MOD}/dxvk/*', f'{MOD}/EXE_MISMATCH.txt'],
           'exe_identity': {'name': 'installer/exe_identity.json', 'sha256': sha(ib)},
           'owned': ['d3d9.dll', 'data/ui_scale_x.pack', INI, f'{MOD}/'],
           'components': [{'id': 'proxy'}, {'id': 'ui'}], 'files': files, 'extras': []}
    (rel / 'manifest.json').write_text(json.dumps(man), encoding='utf-8')
    return rel


def make_game(tmp, name='game', exe=EXE, foreign_dll=True):
    g = Path(tmp) / name
    (g / 'data').mkdir(parents=True)
    (g / 'data' / 'empty_dir').mkdir()
    (g / 'Napoleon.exe').write_bytes(exe)
    (g / 'data' / 'vanilla.pack').write_bytes(b'vanilla pack' * 40)
    (g / 'readme.txt').write_bytes(b'hello')
    if foreign_dll:
        (g / 'd3d9.dll').write_bytes(b'someone else\'s d3d9 wrapper')   # a foreign file at an owned path: backed up, restored by the uninstall
    return g


def make_kit(tmp, rel):
    """The same release as a pc_deploy kit (flat staged names), so both implementations install identical bytes."""
    man = json.loads((rel / 'manifest.json').read_text(encoding='utf-8'))
    kit = Path(tmp) / 'kit_test'
    kit.mkdir()
    files = []
    for e in man['files']:
        staged = f"{e['sha256'][:12]}__{e['path'].replace('/', '__')}"
        shutil.copy(rel / e['payload'], kit / staged)
        files.append({'path': e['path'], 'staged': staged, 'sha256': e['sha256'], 'size': e['size'], 'role': 'x'})
    shutil.copy(rel / 'installer' / 'exe_identity.json', kit / pc_deploy.IDENTITY_COPY)
    km = {'kit_id': 'kit_test', 'build_id': man['dll_build_id'], 'game': 'Test Game', 'exe_name': 'Napoleon.exe', 'other_exes': ['Empire.exe'], 'mod_dir': MOD,
          'config_file': INI, 'owned': man['owned'], 'files': files, 'game_config_files': [], 'packs': {},
          'exe_identity': {'name': pc_deploy.IDENTITY_COPY, 'sha256': man['exe_identity']['sha256']}}
    (kit / 'manifest.json').write_text(json.dumps(km), encoding='utf-8')
    return kit


def view(game):
    """path -> (size, sha256 or None) of every file and the empty folders: what 'identical' means, without mtimes."""
    return {k: (v.get('size'), v.get('sha256')) if not v.get('dir') else 'dir' for k, v in pc_deploy.snapshot(game).items()}


class Installer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PS:   # J74: on the Windows CI runner a missing PowerShell is a failure, never a silent skip
            if os.name == 'nt' and os.environ.get('CI') == 'true':
                raise AssertionError('Windows PowerShell is missing on the Windows CI runner: the installer tests must run there, not skip')
            raise unittest.SkipTest('needs Windows PowerShell 5.1')

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.tmp = self._t.name
        self.rel = make_release(self.tmp)
        self.state = Path(self.tmp) / 'state'
        self.appdata = Path(self.tmp) / 'appdata'
        (self.appdata / 'ui_cache').mkdir(parents=True)
        (self.appdata / 'ui_cache' / 'components.cache').write_bytes(b'cache')

    def tearDown(self):
        self._t.cleanup()

    def rr(self, verb, game, *extra, state=None):
        cmd = [PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(self.rel / 'installer' / 'rr.ps1'), verb, '-GamePath', str(game),
               '-StateDir', str(state or self.state), '-AppDataDir', str(self.appdata), '-AssumeClosed', *extra]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return r.returncode, r.stdout + r.stderr

    # ---- parity with pc_deploy.py -------------------------------------------------------------------------------------------------
    def test_install_uninstall_parity_with_pc_deploy(self):
        a, b = make_game(self.tmp, 'game_py'), make_game(self.tmp, 'game_ps')
        pre = view(a)
        self.assertEqual(pre, view(b))
        kit = make_kit(self.tmp, self.rel)
        state_py = Path(self.tmp) / 'state_py'
        pc_deploy.install(kit, a, state_py, assume_closed=True)
        code, out = self.rr('install', b)
        self.assertEqual(code, 0, out)
        self.assertEqual(view(a), view(b), 'the installed game folders differ between pc_deploy and rr.ps1')
        self.assertIn('d3d9.dll', json.loads((self.state / 'install.json').read_text())['backups'][0]['path'])
        rec_py = json.loads((state_py / 'install.json').read_text())
        rec_ps = json.loads((self.state / 'install.json').read_text())
        self.assertEqual(sorted(rec_py['owned']), sorted(rec_ps['owned']))
        self.assertEqual(sorted((f['path'], f['sha256']) for f in rec_py['files']), sorted((f['path'], f['sha256']) for f in rec_ps['files']))
        self.assertEqual([x['path'] for x in rec_py['backups']], [x['path'] for x in rec_ps['backups']])
        self.assertFalse((self.appdata / 'ui_cache' / 'components.cache').exists(), 'the UI cache file was not moved aside')
        self.assertTrue(any(self.state.joinpath('_to_delete').rglob('components.cache')))
        # the dll the game would load is the release's, the foreign one is out of the way
        self.assertEqual((b / 'd3d9.dll').read_bytes(), PAYLOAD['d3d9.dll'][1])
        # the game wrote runtime files at owned paths: the uninstall must take those too
        for g in (a, b):
            (g / MOD / 'logs').mkdir(parents=True, exist_ok=True)
            (g / MOD / 'logs' / 'proxy.log').write_bytes(b'log')
        self.assertTrue(pc_deploy.uninstall(a, state_py, assume_closed=True))
        code, out = self.rr('uninstall', b)
        self.assertEqual(code, 0, out)
        self.assertIn('identical to the pre-install snapshot', out)
        self.assertEqual(view(a), pre)
        self.assertEqual(view(b), pre, 'rr.ps1 uninstall did not reproduce the snapshot byte for byte')
        self.assertEqual(pc_deploy.diff_snapshots(json.loads(next((state_py / 'snapshots').glob('pre_install_*.json')).read_text()), pc_deploy.snapshot(b)), [])
        self.assertFalse((self.state / 'install.json').exists())   # the record moved to _to_delete, history kept
        self.assertTrue(any((self.state / 'history').glob('install_*.json')))

    def test_uninstall_reports_a_difference(self):
        g = make_game(self.tmp)
        self.assertEqual(self.rr('install', g)[0], 0)
        (g / 'data' / 'vanilla.pack').write_bytes(b'tampered')   # something outside the install changed: the uninstall must say so and exit 1
        code, out = self.rr('uninstall', g)
        self.assertEqual(code, 1, out)
        self.assertIn('DIFFERS', out)
        self.assertIn('changed data/vanilla.pack', out)

    def test_refuses_a_non_vanilla_exe_and_changes_nothing(self):
        g = make_game(self.tmp, exe=EXE + b'patched')
        pre = view(g)
        code, out = self.rr('install', g)
        self.assertEqual(code, 2, out)
        self.assertIn('MISMATCH', out)
        self.assertIn('nothing was installed', out)
        self.assertEqual(view(g), pre)
        self.assertFalse(self.state.exists() and (self.state / 'install.json').exists())
        with self.assertRaises(SystemExit):   # parity: pc_deploy refuses the same game folder
            pc_deploy.install(make_kit(self.tmp, self.rel), g, Path(self.tmp) / 'st2', assume_closed=True)

    def test_refuses_a_damaged_release_before_any_copy(self):
        g = make_game(self.tmp)
        pre = view(g)
        (self.rel / 'payload' / 'proxy' / 'd3d9.dll').write_bytes(b'stale or partial copy')
        code, out = self.rr('install', g)
        self.assertEqual(code, 2, out)
        self.assertIn('does not verify', out)
        self.assertEqual(view(g), pre)

    def test_refuses_while_the_game_runs(self):
        g = make_game(self.tmp)
        tool = Path(self.tmp) / 'Empire.exe'   # the other title counts too (pc_deploy: either title)
        shutil.copy(Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'System32' / 'PING.EXE', tool)
        p = subprocess.Popen([str(tool), '-n', '60', '127.0.0.1'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x00000008)
        try:
            cmd = [PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(self.rel / 'installer' / 'rr.ps1'), 'install', '-GamePath', str(g), '-StateDir', str(self.state)]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn('is running', r.stdout)
            self.assertFalse((g / 'd3d9.dll.bak').exists())
        finally:
            p.kill()

    # ---- check and repair -----------------------------------------------------------------------------------------------------------
    def test_check_repair_and_foreign_files(self):
        g = make_game(self.tmp, foreign_dll=False)
        code, out = self.rr('check', g)
        self.assertEqual(code, 0, out)
        self.assertIn('not installed by this tool', out)
        self.assertEqual(self.rr('install', g)[0], 0)
        code, out = self.rr('check', g)
        self.assertEqual(code, 0, out)
        self.assertIn('rr check: clean', out)
        (g / MOD / 'logs').mkdir(parents=True, exist_ok=True)
        (g / MOD / 'logs' / 'proxy.log').write_bytes(b'runtime file: not foreign')
        (g / MOD / 'dxvk' / 'cache.dxvk-cache').write_bytes(b'runtime file: not foreign')
        self.assertEqual(self.rr('check', g)[0], 0)
        (g / MOD / 'stray.dll').write_bytes(b'x')
        code, out = self.rr('check', g)
        self.assertEqual(code, 1, out)
        self.assertIn(f'FOREIGN {MOD}/stray.dll', out)
        (g / MOD / 'stray.dll').unlink()
        # a settings file the player edited is kept, not an error
        (g / INI).write_bytes(b'[proxy]\r\nbackend=system\r\n')
        code, out = self.rr('check', g)
        self.assertEqual(code, 0, out)
        self.assertIn('edited', out)
        # one owned file deleted (Steam Verify only adds files, so this is the simulated damage) and one changed
        (g / 'd3d9.dll').unlink()
        (g / MOD / 'dxvk' / 'd3d9_dxvk.dll').write_bytes(b'changed')
        code, out = self.rr('check', g)
        self.assertEqual(code, 1, out)
        self.assertIn('MISSING d3d9.dll', out)
        self.assertIn(f'CHANGED {MOD}/dxvk/d3d9_dxvk.dll', out)
        code, out = self.rr('repair', g)
        self.assertEqual(code, 0, out)
        self.assertIn('kept your edited settings file', out)
        self.assertEqual((g / 'd3d9.dll').read_bytes(), PAYLOAD['d3d9.dll'][1])
        self.assertEqual((g / INI).read_bytes(), b'[proxy]\r\nbackend=system\r\n')
        self.assertEqual(self.rr('check', g)[0], 0)
        # and the uninstall still ends identical after the repair
        pre = json.loads(next((self.state / 'snapshots').glob('pre_install_*.json')).read_text())
        code, out = self.rr('uninstall', g)
        self.assertEqual(code, 0, out)
        self.assertEqual(pc_deploy.diff_snapshots(pre, pc_deploy.snapshot(g)), [])
        code, out = self.rr('check', g)   # after the uninstall: nothing of ours is left
        self.assertEqual(code, 0, out)

    def test_game_update_makes_repair_say_so_and_change_nothing(self):
        g = make_game(self.tmp, foreign_dll=False)
        self.assertEqual(self.rr('install', g)[0], 0)
        (g / 'Napoleon.exe').write_bytes(EXE + b' updated by Steam')
        (g / MOD / 'EXE_MISMATCH.txt').write_bytes(b'notice')
        (g / 'd3d9.dll').unlink()
        before = view(g)
        code, out = self.rr('repair', g)
        self.assertEqual(code, 3, out)
        self.assertIn('game updated, remaster is inactive until a build for this exe exists', out)
        self.assertEqual(view(g), before)
        code, out = self.rr('check', g)
        self.assertEqual(code, 1, out)
        self.assertIn('MISMATCH', out)
        self.assertIn('EXE_MISMATCH.txt present', out)
        # the uninstall still works and reports the exe as it is (it never refuses and never touches the exe)
        code, out = self.rr('uninstall', g)
        self.assertIn('rr uninstall: exe: MISMATCH', out)

    def test_finds_the_game_from_the_scripts_own_location(self):
        g = make_game(self.tmp, foreign_dll=False)
        inside = g / 'Napoleon Remastered 9.9.9'
        shutil.copytree(self.rel, inside)
        cmd = [PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(inside / 'installer' / 'rr.ps1'), 'check', '-StateDir', str(self.state)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        self.assertIn(f'game folder {g}', r.stdout)

    # ---- the support bundle -------------------------------------------------------------------------------------------------------
    def plant(self, g):
        text = (f"launch 1\r\npath {PLANTED['profile']}\\AppData\\Local\\Temp\\x user={PLANTED['user']} host={PLANTED['machine'].lower()}\r\n"
                f"steam {STEAM_ID} C:\\Program Files (x86)\\Steam\\userdata\\123456789\\config S-1-5-21-111111111-222222222-333333333-1001 "
                f"in {PLANTED['profile'].replace(chr(92), '/')}/x\r\nprocess detach\r\n")
        (g / MOD / 'logs').mkdir(parents=True, exist_ok=True)
        (g / MOD / 'logs' / 'proxy.log').write_text(text, encoding='utf-8')
        (g / MOD / 'logs' / 'proxy.prev.log').write_text(text, encoding='utf-8')
        (g / MOD / 'EXE_MISMATCH.txt').write_text(text, encoding='utf-8')
        (g / MOD / 'dumps').mkdir(exist_ok=True)
        (g / MOD / 'dumps' / 'crash1.dmp').write_bytes(b'MDMP process memory ' + PLANTED['user'].encode())
        (g / 'saves').mkdir(exist_ok=True)
        (g / 'saves' / 'mine.save').write_bytes(b'a save game')
        return text

    def bundle(self, g, *extra):
        out = Path(self.tmp) / 'out'
        code, o = self.rr('support', g, '-OutDir', str(out), '-RedactUser', PLANTED['user'], '-RedactMachine', PLANTED['machine'], '-RedactProfile', PLANTED['profile'], *extra)
        self.assertEqual(code, 0, o)
        zips = list(out.glob('napoleon_remastered_support_*.zip'))
        self.assertEqual(len(zips), 1, o)
        return zipfile.ZipFile(zips[0])

    def test_support_bundle_redacts_personal_data(self):
        g = make_game(self.tmp, foreign_dll=False)
        self.assertEqual(self.rr('install', g)[0], 0)
        self.plant(g)
        z = self.bundle(g)
        names = z.namelist()
        for want in ('proxy.log', 'proxy.prev.log', INI, 'EXE_MISMATCH.txt', 'install.json', 'check.txt', 'versions.txt', 'dumps.txt', 'README.txt'):
            self.assertIn(want, names)
        self.assertFalse([n for n in names if n.endswith('.dmp')], 'a dump is only in the bundle with -IncludeDumps')
        self.assertFalse([n for n in names if 'save' in n.lower() and n != 'README.txt'])
        blob = '\n'.join(z.read(n).decode('utf-8', 'replace') for n in names)
        for secret in (PLANTED['user'], PLANTED['machine'], PLANTED['machine'].lower(), PLANTED['profile'], STEAM_ID, '123456789', '111111111',
                       os.environ.get('USERPROFILE', 'C:\\Users\\nobody'), os.environ.get('USERNAME', '\0'), os.environ.get('COMPUTERNAME', '\0')):
            self.assertNotIn(secret.lower(), blob.lower(), f'{secret!r} leaked into the support bundle')
        for marker in ('<user>', '<machine>', '%USERPROFILE%', '<steamid>', '<sid>'):
            self.assertIn(marker, blob)
        self.assertIn('crash1.dmp', z.read('dumps.txt').decode())       # listed either way
        self.assertIn('Napoleon Remastered 9.9.9', z.read('versions.txt').decode())
        self.assertIn('rr check', z.read('check.txt').decode() + 'rr check') # the Check output is in it
        self.assertIn('ok      d3d9.dll', z.read('check.txt').decode())

    def test_support_bundle_includes_dumps_only_when_asked(self):
        g = make_game(self.tmp, foreign_dll=False)
        self.assertEqual(self.rr('install', g)[0], 0)
        self.plant(g)
        z = self.bundle(g, '-IncludeDumps')
        self.assertIn('dump_crash1.dmp', z.namelist())
        self.assertIn('included: dump_crash1.dmp', z.read('dumps.txt').decode())

    def test_redact_verb(self):
        src, dst = Path(self.tmp) / 'a.txt', Path(self.tmp) / 'b.txt'
        src.write_text(f"{PLANTED['user']} {PLANTED['machine']} {STEAM_ID} userdata\\987654321\\x keepme", encoding='utf-8')
        cmd = [PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(RR_COPY(self.rel)), 'redact', '-In', str(src), '-Out', str(dst),
               '-RedactUser', PLANTED['user'], '-RedactMachine', PLANTED['machine']]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(dst.read_text(encoding='utf-8'), '<user> <machine> <steamid> userdata\\<steamid>\\x keepme')


class CrashDumpTool(unittest.TestCase):
    """G1 (J74): the shipped crash-dump tool works from a folder outside the repo (no wsc.toml above it), as it does on a player's PC.
    Runs wer_localdumps.ps1 in -Mode status only: no admin rights, nothing written. The generated .cmd itself is never run (UAC prompt, HKLM)."""

    @classmethod
    def setUpClass(cls):
        if not PS:
            if os.name == 'nt' and os.environ.get('CI') == 'true':
                raise AssertionError('Windows PowerShell is missing on the Windows CI runner: the installer tests must run there, not skip')
            raise unittest.SkipTest('needs Windows PowerShell 5.1')

    def run_ps(self, *args):
        return subprocess.run([PS, '-NoProfile', '-ExecutionPolicy', 'Bypass', *args], capture_output=True, text=True, timeout=120)

    def test_status_outside_the_repo_with_the_generated_arguments(self):
        sys.path.insert(0, str(ROOT / 'release' / 'core'))
        import build_release as br
        ident = json.loads((ROOT / 'proxy' / 'napoleon' / 'identity.json').read_text(encoding='utf-8'))
        text = br.crash_dump_cmd('enable', ident)
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp) / 'tools'
            tools.mkdir()
            self.assertFalse(any((p / 'wsc.toml').exists() for p in [tools, *tools.parents]), 'the temp folder must be outside any repo')
            script = tools / 'wer_localdumps.ps1'
            shutil.copy(ROOT / 'core' / 'proxy' / 'tools' / 'wer' / 'wer_localdumps.ps1', script)
            (tools / 'Enable crash dumps.cmd').write_bytes(text.encode('ascii'))
            # the inner command exactly as the elevated powershell receives it: undo the batch (%%, %~dp0) and the PowerShell ('') quoting
            inner = text.split("'-Command','", 1)[1].split(' *> ', 1)[0]
            inner = inner.replace("''", "'").replace('%~dp0', str(tools) + '\\').replace('%%', '%').replace('-Mode enable', '-Mode status')
            r = self.run_ps('-Command', inner)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('WER LOCALDUMPS:', r.stdout)
            self.assertIn(ident['exe_name'], r.stdout)
            self.assertIn('%LOCALAPPDATA%\\CrashDumps\\' + ident['mod_dir'], r.stdout.replace('DumpFolder=', '') + inner)
            # control: without the two arguments it needs the repo and fails, so the test fails if the arguments are ever dropped
            c = self.run_ps('-File', str(script), '-Mode', 'status')
            self.assertNotEqual(c.returncode, 0)
            self.assertIn('no -ExeName', c.stdout + c.stderr)


def RR_COPY(rel):
    return rel / 'installer' / 'rr.ps1'


class Scripts(unittest.TestCase):
    def test_installer_is_ascii_and_builds_cmd_files(self):
        """Windows PowerShell 5.1 reads a script without a BOM as ANSI: a non-ASCII byte would be misread (pc_deploy.norm_for_pc has the same rule)."""
        RR.read_bytes().decode('ascii')

    def test_uses_no_python_git_or_repo(self):
        text = RR.read_text(encoding='ascii').lower()
        for banned in ('python', ' git ', 'git.exe', 'wsc.toml', 'core/', 'bash'):
            self.assertNotIn(banned, [l for l in text.splitlines() if not l.lstrip().startswith('#')].__str__(), banned)


if __name__ == '__main__':
    unittest.main()
