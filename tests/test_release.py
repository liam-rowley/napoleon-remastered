"""Host tests for the pure parts of the release builder (J38): version rules, component ownership, the player ini, the release-value gate, the licence
data and its gate, the manifest check and the notes generation. No game, no PowerShell. The installer itself is tests/test_release_installer.py."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'release' / 'core'))
sys.path.insert(0, str(ROOT / 'core' / 'proxy' / 'tools'))
import build_release as br  # noqa: E402
import gen_licenses as gl  # noqa: E402


def rj(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))


KEYS = [json.loads(l) for l in (ROOT / 'registries' / 'config_keys.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
REL = rj('release/napoleon/release.json')
COMPS = rj('release/napoleon/components.json')
LIC = rj('release/napoleon/licenses.json')
IDENT = rj('proxy/napoleon/identity.json')


class Versions(unittest.TestCase):
    def test_form(self):
        self.assertEqual(br.parse_version('0.1.0'), (0, 1, 0))
        for bad in ('1.0', '01.0.0', '1.0.0-rc1', 'v1.0.0', '', '1.2.3.4'):
            with self.assertRaises(ValueError, msg=bad):
                br.parse_version(bad)

    def test_must_rise(self):
        rels = [{'version': '0.1.0', 'jobs_done': []}]
        self.assertTrue(br.version_problems('0.1.0', rels))
        self.assertTrue(br.version_problems('0.0.9', rels))
        self.assertFalse(br.version_problems('0.1.1', rels))
        self.assertFalse(br.version_problems('0.10.0', rels))   # numeric, not text, order
        self.assertFalse(br.version_problems('0.1.0', []))
        self.assertEqual(br.parse_version((ROOT / 'release' / 'napoleon' / 'VERSION').read_text().strip()), (0, 1, 0))

    def test_jobs_since(self):
        rows = [{'id': 'J2', 'status': 'done', 'title': 'b'}, {'id': 'J10', 'status': 'done', 'title': 'c'}, {'id': 'J3', 'status': 'queued', 'title': 'x'},
                {'id': 'J1', 'status': 'done', 'title': 'a'}]
        self.assertEqual([i for i, _ in br.jobs_since(rows, [])], ['J1', 'J2', 'J10'])
        self.assertEqual([i for i, _ in br.jobs_since(rows, [{'version': '0.1.0', 'jobs_done': ['J1', 'J2']}])], ['J10'])


class Ownership(unittest.TestCase):
    def test_owned_paths(self):
        self.assertEqual(br.owned_paths(['d3d9.dll', 'napoleon_remastered/a/b.dll', 'napoleon_remastered/c', 'data/x.pack'], 'napoleon_remastered'),
                         ['d3d9.dll', 'data/x.pack', 'napoleon_remastered/'])

    def test_real_rows_are_clean(self):
        self.assertEqual(br.ownership_problems(COMPS), [])

    def test_duplicate_escape_and_unowned(self):
        c = copy.deepcopy(COMPS)
        c['components'][1]['files'].append({'target': 'D3D9.dll', 'source': 'dll'})
        self.assertTrue(any('also owned' in e for e in br.ownership_problems(c)))
        c = copy.deepcopy(COMPS)
        c['components'][0]['files'].append({'target': '../evil.dll', 'source': 'dll'})
        self.assertTrue(any('relative' in e for e in br.ownership_problems(c)))
        c = copy.deepcopy(COMPS)
        c['components'][0]['files'].append({'target': 'C:/x.dll', 'source': 'dll'})
        self.assertTrue(br.ownership_problems(c))
        errs = br.ownership_problems(COMPS, ['d3d9.dll', 'data/stray.pack'])
        self.assertEqual(len(errs), 1)
        self.assertIn('data/stray.pack', errs[0])
        c = copy.deepcopy(COMPS)
        c['components'][1]['requires'] = ['nothing']
        self.assertTrue(br.ownership_problems(c))


class PlayerIni(unittest.TestCase):
    def test_lists_only_player_keys(self):
        ini = br.player_ini(KEYS, REL, IDENT)
        names = [l.split('=')[0] for l in ini.splitlines() if '=' in l and not l.startswith(';')]
        self.assertEqual(names, ['backend', 'dxvk_path', 'enabled', 'log_level', 'minidump', 'runtime_patches'])
        for omitted in ('exe_guard', 'capture_dir', 'autostart', 'enabled=0'):
            self.assertNotIn(omitted + '=', ini.replace('enabled=1', ''))
        self.assertIn('minidump=2', ini)
        self.assertTrue(ini.endswith('\r\n'))

    def test_component_keys_are_added(self):
        ini = br.player_ini(KEYS, REL, IDENT, {'dev.file_rules': 'napoleon_remastered\\ui\\x.rules'})
        self.assertIn('[dev]', ini)
        self.assertIn('file_rules=napoleon_remastered\\ui\\x.rules', ini)

    def test_built_dll_default_matches_release_minidump(self):
        """J1 open question 1, closed: the compiled default of proxy.minidump (generated tables.h) and the ini value are both 2."""
        tables = (ROOT / 'proxy' / 'napoleon' / 'generated' / 'tables.h').read_text(encoding='utf-8')
        self.assertIn('{ "proxy.minidump", kInt, "2" }', tables)
        self.assertIn('minidump=2', br.player_ini(KEYS, REL, IDENT))


class ReleaseValues(unittest.TestCase):
    """The release-value gate (J38): runs with `wsc gates` (the tests gate)."""

    def test_registry_passes(self):
        import gen_tables
        dev_ini = (ROOT / 'proxy' / 'napoleon' / IDENT['config_file']).read_bytes().decode('utf-8')
        want = gen_tables.render_ini(IDENT, sorted(KEYS, key=lambda k: k['id']))
        self.assertEqual(br.value_problems(KEYS, REL, dev_ini, want), [])

    def test_catches_each_rule(self):
        def with_(kid, **chg):
            ks = copy.deepcopy(KEYS)
            for k in ks:
                if k['id'] == kid:
                    k.update(chg)
            return br.value_problems(ks, REL)
        self.assertTrue(with_('dev.ctl', release_value=True))                         # a dev key on
        self.assertTrue(with_('dev.autostart', release_value='frontend'))
        self.assertTrue(with_('gfx.tree_lod_proof', release_value=True))              # a proof key on
        self.assertTrue(with_('headless.test_off_thread', release_value=True))        # a test key on
        self.assertTrue(with_('proxy.exe_guard', release_value=0))                    # the exe guard off
        self.assertTrue(with_('proxy.exe_guard_force_mismatch', release_value=1))     # forced mismatch on
        self.assertTrue(with_('proxy.minidump', release_value=1))
        self.assertTrue(with_('dev.ctl', default=True))                               # omitted key whose DLL default differs from the release value
        self.assertEqual(with_('proxy.log_level', release_value='info'), [])

    def test_every_dev_key_is_off_or_inert(self):
        for k in KEYS:
            if k['id'].startswith('dev.') and k['id'] not in REL['release_values']['inert_parameters']:
                self.assertFalse(br.not_off(k.get('release_value', k['default'])), k['id'])


class Licences(unittest.TestCase):
    def test_gate_passes_and_text_is_the_pinned_dxvk_text(self):
        self.assertEqual(gl.problems(LIC, COMPS, ROOT), [])
        import fetch_dxvk
        dx = next(e for e in LIC['entries'] if e['id'] == 'dxvk')
        self.assertEqual(hashlib.sha256(dx['text'].encode('utf-8')).hexdigest(), fetch_dxvk.PIN['license_sha256'])
        self.assertIn('3.1.1', dx['name'])
        self.assertIn(fetch_dxvk.PIN['version'], dx['name'])

    def test_shipped_without_entry_and_entry_without_component(self):
        c = copy.deepcopy(COMPS)
        c['components'][0]['licences'].append('nonesuch')
        self.assertTrue(any('nonesuch' in e for e in gl.problems(LIC, c, ROOT)))
        lic = copy.deepcopy(LIC)
        next(e for e in lic['entries'] if e['id'] == 'rmlui')['shipped'] = True
        self.assertTrue(any('rmlui' in e and 'no component' in e for e in gl.problems(lic, COMPS, ROOT)))
        c = copy.deepcopy(COMPS)
        c['components'][0]['licences'].append('rmlui')   # a component ships it while its entry says shipped=false
        self.assertTrue(any('shipped=false' in e for e in gl.problems(LIC, c, ROOT)))

    def test_text_hash_pin(self):
        lic = copy.deepcopy(LIC)
        next(e for e in lic['entries'] if e['id'] == 'dxvk')['text'] += ' '
        self.assertTrue(any('sha256' in e for e in gl.problems(lic, COMPS, ROOT)))

    def test_render(self):
        t = gl.render(LIC, ROOT)
        self.assertIn('not legal advice', t)
        self.assertIn('Permission is granted', t)            # the zlib text
        self.assertIn('SIL OPEN FONT LICENSE', t)
        self.assertIn('[pending', t)                          # both decisions of Liam read pending until he decides
        self.assertIn('NOT IN THIS RELEASE', t)
        self.assertIn('RmlUi 6.3', t)
        self.assertEqual(gl.pending(LIC), ['statement', 'own_code_licence'])
        self.assertNotIn('\n', t.replace('\r\n', ''))

    def test_models_credit_lines(self):
        t = gl.render(LIC, ROOT)
        for credit in ('2xHFA2kCompact by Philip Hofmann', '2xNomosUni_esrgan_multijpg by Philip Hofmann'):
            self.assertIn(credit, t)
        models = rj('upscale/napoleon/models.json')['models']
        for m in models.values():
            self.assertIn(m['credit'], t)


class Notes(unittest.TestCase):
    def test_notes_and_readme(self):
        infos = [{'id': 'proxy', 'title': 'P', 'files': 4, 'size': 8_400_000, 'licences': ['dxvk']}]
        t = br.notes_text(REL, '0.1.0', infos, [('J1', 'Skeleton')], [('proxy.minidump', '2')], [('napoleon.x', '[open] claim')], 'abc123abc123', 'v0.9.0', 'f' * 40, '')
        for want in ('0.1.0', 'J1: Skeleton', 'proxy.minidump = 2', 'napoleon.x', 'Multiplayer is untested', '8.0 MB', 'abc123abc123'):
            self.assertIn(want, t)
        self.assertTrue(t.isascii())
        r = br.readme_text(REL, IDENT, '0.1.0', COMPS, LIC)
        self.assertTrue(r.isascii())
        for want in ('Install.cmd', 'Uninstall.cmd', 'Support.cmd', 'EXCEPT inside the game folder'):
            self.assertIn(want, r)

    def test_limit_facts_exist(self):
        self.assertEqual(len(br.load_facts(REL['limit_facts'])), len(REL['limit_facts']))

    def test_cmd_entry_points(self):
        for name, (verb, extra, blurb) in br.CMDS.items():
            t = br.cmd_text(verb, extra, blurb)
            self.assertIn(f'rr.ps1" {verb}', t)
            self.assertIn('%~dp0installer', t)
            self.assertTrue(t.isascii() and '\r\n' in t)


class Folder(unittest.TestCase):
    """check_folder on a hand-made folder: missing, changed and unlisted files, wrong folder name."""

    def make(self, tmp):
        f = Path(tmp) / 'Napoleon Remastered 0.1.0'
        (f / 'payload' / 'proxy').mkdir(parents=True)
        (f / 'installer').mkdir()
        data = b'dll'
        (f / 'payload' / 'proxy' / 'd3d9.dll').write_bytes(data)
        (f / 'installer' / 'exe_identity.json').write_bytes(b'{}')
        extras = [{'path': 'installer/exe_identity.json', 'component': 'installer', 'size': 2, 'sha256': hashlib.sha256(b'{}').hexdigest()}]
        for c in br.CMDS:
            (f / c).write_bytes(b'x')
            extras.append({'path': c, 'component': 'installer', 'size': 1, 'sha256': hashlib.sha256(b'x').hexdigest()})
        man = {'product': 'Napoleon Remastered', 'version': '0.1.0', 'dll_build_id': 'abc', 'owned': ['d3d9.dll'],
               'components': [{'id': 'proxy'}], 'exe_identity': {'name': 'installer/exe_identity.json', 'sha256': hashlib.sha256(b'{}').hexdigest()},
               'files': [{'path': 'd3d9.dll', 'component': 'proxy', 'size': 3, 'sha256': hashlib.sha256(data).hexdigest(), 'payload': 'payload/proxy/d3d9.dll', 'config': False}],
               'extras': extras}
        (f / 'manifest.json').write_text(json.dumps(man))
        return f

    def test_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = self.make(tmp)
            self.assertEqual(br.check_folder(f), [])
            (f / 'payload' / 'proxy' / 'd3d9.dll').write_bytes(b'dlX')
            self.assertTrue(any('differs' in b for b in br.check_folder(f)))
            (f / 'payload' / 'proxy' / 'd3d9.dll').unlink()
            self.assertTrue(any('missing' in b for b in br.check_folder(f)))
            (f / 'payload' / 'proxy' / 'd3d9.dll').write_bytes(b'dll')
            (f / 'stray.txt').write_text('x')
            self.assertTrue(any('stray.txt' in b for b in br.check_folder(f)))
            (f / 'stray.txt').unlink()
            f2 = f.rename(f.parent / 'Napoleon Remastered 0.2.0')
            self.assertTrue(any('folder name' in b for b in br.check_folder(f2)))

    def test_dll_build_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / 'd3d9.dll'
            d.write_bytes(b'MZ..build 715e9dfc0727 ..')
            self.assertEqual(br.dll_problem(d, '715e9dfc0727'), '')
            self.assertIn('does not carry', br.dll_problem(d, '000000000000'))
            self.assertIn('dirty', br.dll_problem(d, '715e9dfc0727-dirty'))


if __name__ == '__main__':
    unittest.main()
