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
        self.assertEqual(names, ['shadow_extrusion', 'shadow_height_cutoff', 'shadow_map_large',
                                 'backend', 'dxvk_path', 'enabled', 'log_level', 'minidump', 'runtime_patches'])
        self.assertIn('[gfx]', ini)
        self.assertNotIn('shadow_focus=', ini)                                         # a gfx key not in keep_ids stays omitted
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
        self.assertTrue(with_('gfx.shadow_focus', release_value=True))                # the same for a gfx key not in keep_ids (J24)
        self.assertEqual(with_('proxy.log_level', release_value='info'), [])

    def test_every_dev_key_is_off_or_inert(self):
        for k in KEYS:
            if k['id'].startswith('dev.') and k['id'] not in REL['release_values']['inert_parameters']:
                self.assertFalse(br.not_off(k.get('release_value', k['default'])), k['id'])


def ledger_text(*rows):
    """A fake acceptance ledger: rows are (build_id, result); every row names a run and an evidence file."""
    return ''.join(json.dumps({'pass': i + 1, 'build_id': b, 'result': r, 'run': 'harness/runs/x', 'evidence': f'harness/runs/x/pass_{i + 1}.json'}) + '\n'
                   for i, (b, r) in enumerate(rows))


class DllMarker(unittest.TestCase):
    """G4 (J74): the DLL must carry the clean id as a whole token, and the ledger must hold 20 passes on it."""
    ID = 'cb34c06baf42'

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)

    def dll(self, data):
        d = Path(self._t.name) / 'd3d9.dll'
        d.write_bytes(data)
        return d

    def acc(self, text, passes=20, exists=None):
        return {'text': text, 'passes': passes, 'exists': exists or (lambda p: True)}

    def test_dirty_neighbour_is_not_the_id(self):
        self.assertTrue(br.dll_problem(self.dll(b'MZ\0' + self.ID.encode() + b'-dirty\0'), self.ID))

    def test_empty_or_malformed_id_is_refused(self):
        d = self.dll(b'MZ\0' + self.ID.encode() + b'\0')
        for bad in ('', 'abc', 'CB34C06BAF42', 'cb34c06baf4', 'cb34c06baf42a', self.ID + '-dirty'):
            self.assertTrue(br.dll_problem(d, bad), repr(bad))

    def test_prefix_of_a_longer_run_is_not_the_id(self):
        self.assertTrue(br.dll_problem(self.dll(b'MZ\0' + self.ID.encode() + b'ff\0'), self.ID))
        self.assertTrue(br.dll_problem(self.dll(b'MZ\0ff' + self.ID.encode() + b'\0'), self.ID))

    def test_delimited_id_is_accepted(self):
        self.assertEqual(br.dll_problem(self.dll(b'MZ\0' + self.ID.encode() + b'\0rest'), self.ID), '')
        self.assertEqual(br.dll_problem(self.dll(b'MZ..build ' + self.ID.encode() + b' ..'), self.ID), '')

    def test_a_dll_that_also_carries_the_dirty_literal_is_refused(self):
        i = self.ID.encode()
        self.assertTrue(br.dll_problem(self.dll(b'\0' + i + b'\0' + i + b'-dirty\0'), self.ID))

    def test_twenty_passes_are_needed(self):
        d = self.dll(b'\0' + self.ID.encode() + b'\0')
        i = self.ID
        self.assertEqual(br.dll_problem(d, i, self.acc(ledger_text(*[(i, 'pass')] * 20))), '')
        msg = br.dll_problem(d, i, self.acc(ledger_text(*[(i, 'pass')] * 19)))
        self.assertTrue(msg and i in msg and '19' in msg and '20' in msg, msg)
        self.assertTrue(br.dll_problem(d, i, self.acc(ledger_text(*([(i, 'pass')] * 20 + [(i, 'fail')])))))
        self.assertEqual(br.dll_problem(d, i, self.acc(ledger_text(*([(i, 'fail')] + [(i, 'pass')] * 20)))), '')

    def test_other_ids_and_dirty_rows_do_not_count(self):
        d = self.dll(b'\0' + self.ID.encode() + b'\0')
        i = self.ID
        rows = [(i, 'pass')] * 10 + [(i + '-dirty', 'pass')] * 5 + [('000000000000', 'pass')] * 5 + [(i, 'pass')] * 9
        self.assertTrue(br.dll_problem(d, i, self.acc(ledger_text(*rows))))
        rows = [(i, 'pass')] * 10 + [(i + '-dirty', 'pass')] * 5 + [('000000000000', 'pass')] * 5 + [(i, 'pass')] * 10
        self.assertEqual(br.dll_problem(d, i, self.acc(ledger_text(*rows))), '')

    def test_missing_evidence_ends_the_streak(self):
        d = self.dll(b'\0' + self.ID.encode() + b'\0')
        i = self.ID
        text = ledger_text(*[(i, 'pass')] * 20)
        self.assertTrue(br.dll_problem(d, i, self.acc(text, exists=lambda p: not p.endswith('pass_20.json'))))
        self.assertTrue(br.dll_problem(d, i, self.acc(text, exists=lambda p: not p.endswith('pass_5.json'))))

    def test_real_ledger_clears_main(self):
        a = REL['acceptance']
        self.assertEqual(a['passes'], 20)
        n = br.acceptance_streak((ROOT / a['ledger']).read_text(encoding='utf-8'), self.ID, lambda p: (ROOT / p).is_file())
        self.assertGreaterEqual(n, 20)


class IniSetGate(unittest.TestCase):
    """G2 (J74): the components' ini_set keys go through the same release-value gate as the registry."""

    def vp(self, ini_set, allowed=None):
        rel = copy.deepcopy(REL)
        rel['release_values']['allowed_dev_keys'] = allowed or {}
        return br.value_problems(KEYS, rel, ini_set=ini_set)

    def test_a_dev_key_on_is_refused(self):
        errs = self.vp({'dev.ctl': 1})
        self.assertTrue(any('dev.ctl' in e for e in errs), errs)

    def test_allow_list_with_a_decision_passes(self):
        self.assertEqual(self.vp({'dev.file_rules': 'x\\y.rules'}, {'dev.file_rules': 'D46: the UI scale stop-gap'}), [])
        self.assertTrue(self.vp({'dev.file_rules': 'x\\y.rules'}))     # not listed

    def test_the_allow_list_does_not_excuse_other_keys(self):
        self.assertTrue(self.vp({'dev.ctl': 1}, {'dev.file_rules': 'D46: x'}))

    def test_required_key_changed_is_refused(self):
        self.assertTrue(any('proxy.exe_guard' in e for e in self.vp({'proxy.exe_guard': 0})))

    def test_unknown_key_is_refused(self):
        self.assertTrue(any('no.such_key' in e for e in self.vp({'no.such_key': 1})))

    def test_stale_or_reasonless_or_unknown_allow_entries_are_refused(self):
        self.assertTrue(any('dev.file_rules' in e for e in self.vp({}, {'dev.file_rules': 'D46: x'})))     # no component sets it
        self.assertTrue(self.vp({'dev.file_rules': 'x'}, {'dev.file_rules': 'because we said so'}))         # no decision id
        self.assertTrue(any('dev.nope' in e for e in self.vp({}, {'dev.nope': 'D46: x'})))                   # not a registry key

    def test_shipped_ini_is_checked_too(self):
        rel = copy.deepcopy(REL)
        rel['release_values']['allowed_dev_keys'] = {'dev.file_rules': 'D46: x'}
        ok = '[proxy]\r\nenabled=1\r\n\r\n[dev]\r\nfile_rules=a\r\n'
        self.assertEqual(br.shipped_ini_problems(ok, rel), [])
        self.assertTrue(br.shipped_ini_problems('[dev]\r\nctl=1\r\n', rel))
        self.assertTrue(br.shipped_ini_problems('[headless]\r\nenabled=1\r\n', rel))
        rel['release_values']['allowed_dev_keys'] = {}
        self.assertTrue(br.shipped_ini_problems(ok, rel))

    def test_real_release_is_clean(self):
        ini_set = br.component_ini_set(COMPS)
        self.assertEqual(list(ini_set), ['dev.file_rules'])
        self.assertEqual(list(REL['release_values']['allowed_dev_keys']), ['dev.file_rules'])
        self.assertEqual(br.value_problems(KEYS, REL, ini_set=ini_set), [])
        self.assertEqual(br.shipped_ini_problems(br.player_ini(KEYS, REL, IDENT, ini_set), REL), [])


class CrashDumpCmd(unittest.TestCase):
    """G1 (J74): the shipped crash-dump .cmd files are generated with the game's exe name and dump folder."""

    def test_generated_text(self):
        for mode in ('enable', 'disable'):
            t = br.crash_dump_cmd(mode, IDENT)
            self.assertTrue(t.isascii())
            self.assertEqual(t.count('\n'), t.count('\r\n'))
            self.assertIn(f'-Mode {mode} ', t)
            self.assertIn("-ExeName ''Napoleon.exe''", t)
            self.assertIn("-DumpFolder ''%%LOCALAPPDATA%%\\CrashDumps\\napoleon_remastered''", t)
            self.assertIn('%~dp0wer_localdumps.ps1', t)
            self.assertIn(f'rr_wer_{mode}.txt', t)
        other = br.crash_dump_cmd('enable', dict(IDENT, exe_name='Other.exe', mod_dir='other_mod'))
        self.assertIn("-ExeName ''Other.exe''", other)
        self.assertIn('CrashDumps\\other_mod', other)
        self.assertNotIn('Napoleon.exe', other)

    def test_proxy_component_ships_the_generated_files(self):
        src = {x['path']: x['source'] for c in COMPS['components'] for x in c.get('extras', [])}
        self.assertEqual(src['tools/Enable crash dumps.cmd'], 'crash_cmd:enable')
        self.assertEqual(src['tools/Disable crash dumps.cmd'], 'crash_cmd:disable')
        self.assertEqual(src['tools/wer_localdumps.ps1'], 'repo:core/proxy/tools/wer/wer_localdumps.ps1')
        c = next(c for c in COMPS['components'] if c['id'] == 'proxy')
        got = br.resolve({'source': 'crash_cmd:enable', 'target': 'x'}, c, {'ident': IDENT})
        self.assertEqual(got, br.crash_dump_cmd('enable', IDENT).encode('ascii'))


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
        for want in ('Install.cmd', 'Uninstall.cmd', 'Support.cmd', 'Clean.cmd', 'changed by the game update, not by this tool'):
            self.assertIn(want, r)

    def test_one_discovery_story(self):
        """G14d (J81): rr.ps1 Find-Game searches upward from the release folder first, so README.txt must not forbid unzipping inside the game folder."""
        r = br.readme_text(REL, IDENT, '0.1.0', COMPS, LIC)
        self.assertNotIn('EXCEPT', r)
        self.assertIn('the installer still finds the game, but verify-and-reinstall in Steam deletes it', r)
        self.assertNotIn('EXCEPT', (ROOT / 'release' / 'README.md').read_text(encoding='utf-8'))

    def test_limit_facts_exist(self):
        self.assertEqual(len(br.load_facts(REL['limit_facts'])), len(REL['limit_facts']))

    def test_cmd_entry_points(self):
        self.assertEqual(br.CMDS['Clean.cmd'][0], 'clean')   # G6 (J81): the release ships Clean.cmd
        for name, (verb, extra, blurb) in br.CMDS.items():
            t = br.cmd_text(verb, extra, blurb)
            self.assertIn(f'rr.ps1" {verb}', t)
            self.assertIn('%~dp0installer', t)
            self.assertTrue(t.isascii() and '\r\n' in t)
            self.assertEqual(t.count('\n'), t.count('\r\n'))
        self.assertIn('game update', br.CMDS['Uninstall.cmd'][2])

    def test_key_text_is_gone(self):
        """G14c (J81): the dead helper (it imported gen_tables, nothing called it)."""
        self.assertFalse(hasattr(br, 'key_text'))


class External(unittest.TestCase):
    """G14a (J81): an external build output is taken only with its .json sidecar naming its sha256 (and the pinned build id when a row pins one)."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.d = Path(self._t.name)
        (self.d / 'x.pack').write_bytes(b'PACK' * 10)

    def res(self, **cf):
        return br.resolve(dict({'source': 'external:ext:x.pack', 'target': 'data/x.pack'}, **cf), {}, {'external': {'ext': str(self.d)}})

    def side(self, **m):
        (self.d / 'x.pack.json').write_text(json.dumps(m), encoding='utf-8')

    def test_missing_sidecar_is_refused(self):
        with self.assertRaises(SystemExit) as e:
            self.res()
        self.assertIn('sidecar', str(e.exception))

    def test_other_sha256_is_refused(self):
        self.side(sha256='0' * 64)
        with self.assertRaises(SystemExit):
            self.res()
        self.side(file='x.pack')   # names no sha256
        with self.assertRaises(SystemExit):
            self.res()

    def test_matching_sidecar_and_pin(self):
        good = hashlib.sha256(b'PACK' * 10).hexdigest()
        self.side(sha256=good)
        self.assertEqual(self.res(), self.d / 'x.pack')
        with self.assertRaises(SystemExit):
            self.res(build_id='abcabcabcabc')   # the row pins a build the sidecar does not name
        self.side(sha256=good, build_id='abcabcabcabc')
        self.assertEqual(self.res(build_id='abcabcabcabc'), self.d / 'x.pack')


class Record(unittest.TestCase):
    """G14b (J81): --record writes version, manifest sha256 and build id into releases.json; a rebuild with other content is refused."""
    MAN = {'product': 'Napoleon Remastered', 'version': '0.1.0', 'created_utc': '2026-11-04T00:00:00Z', 'dll_build_id': 'cb34c06baf42',
           'files': [{'path': 'd3d9.dll', 'sha256': 'a' * 64}]}

    def entry(self, man):
        return {'version': man['version'], 'manifest_sha256': br.content_sha256(man), 'build_id': man['dll_build_id'], 'jobs_done': [], 'published': False}

    def test_record_then_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            rp = Path(tmp) / 'releases.json'
            rp.write_text(json.dumps({'_note': 'kept', 'releases': []}), encoding='utf-8')
            br.record_release(rp, self.entry(self.MAN))
            rels = json.loads(rp.read_text(encoding='utf-8'))
            self.assertEqual(rels['_note'], 'kept')
            self.assertEqual([(r['version'], r['build_id'], r['published']) for r in rels['releases']], [('0.1.0', 'cb34c06baf42', False)])
            releases = rels['releases']
            same = dict(self.MAN, created_utc='2026-11-05T00:00:00Z')   # an identical rebuild a day later
            self.assertEqual(br.version_problems('0.1.0', releases), [])
            self.assertEqual(br.record_problems('0.1.0', br.content_sha256(same), releases), [])
            changed = dict(self.MAN, files=[{'path': 'd3d9.dll', 'sha256': 'b' * 64}])
            errs = br.record_problems('0.1.0', br.content_sha256(changed), releases)
            self.assertTrue(errs and 'recorded with another content' in errs[0] and '--rebuild-unreleased' in errs[0], errs)
            with self.assertRaises(SystemExit):
                br.record_release(rp, self.entry(changed))
            self.assertEqual(br.record_problems('0.1.0', br.content_sha256(changed), releases, rebuild_unreleased=True), [])
            br.record_release(rp, self.entry(changed), rebuild_unreleased=True)
            rels = json.loads(rp.read_text(encoding='utf-8'))['releases']
            self.assertEqual(len(rels), 1)
            self.assertEqual(rels[0]['manifest_sha256'], br.content_sha256(changed))

    def test_published_entries_are_final(self):
        pub = [{'version': '0.1.0', 'manifest_sha256': 'c' * 64, 'build_id': 'x', 'jobs_done': [], 'published': True}]
        self.assertTrue(br.version_problems('0.1.0', pub))
        self.assertTrue(br.record_problems('0.1.0', 'd' * 64, pub, rebuild_unreleased=True))
        self.assertTrue(br.version_problems('0.1.0', [{'version': '0.1.0', 'jobs_done': []}]))   # a hand entry (no sha) counts as published
        self.assertFalse(br.version_problems('0.1.1', pub))

    def test_the_real_file_reads(self):
        rels = rj('release/napoleon/releases.json')['releases']
        self.assertEqual(br.version_problems((ROOT / 'release' / 'napoleon' / 'VERSION').read_text().strip(), rels), [])


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
            (f / 'Clean.cmd').unlink()   # J81: the folder rule covers the new entry point
            self.assertTrue(any(b == 'Clean.cmd: missing' for b in br.check_folder(f)))
            (f / 'Clean.cmd').write_bytes(b'x')
            f2 = f.rename(f.parent / 'Napoleon Remastered 0.2.0')
            self.assertTrue(any('folder name' in b for b in br.check_folder(f2)))

    def test_crash_dump_cmd_without_its_arguments_is_flagged(self):
        """G1: today's core copy of the .cmd names wer_localdumps.ps1 with no -ExeName and -DumpFolder; it only works inside the repo."""
        with tempfile.TemporaryDirectory() as tmp:
            f = self.make(tmp)
            (f / 'tools').mkdir()
            core = ROOT / 'core' / 'proxy' / 'tools' / 'wer'
            (f / 'tools' / 'Enable crash dumps.cmd').write_bytes((core / 'Enable crash dumps.cmd').read_bytes())
            (f / 'tools' / 'wer_localdumps.ps1').write_bytes((core / 'wer_localdumps.ps1').read_bytes())
            self.assertTrue([b for b in br.check_folder(f) if 'Enable crash dumps.cmd' in b and '-ExeName' in b])
            (f / 'tools' / 'Enable crash dumps.cmd').write_bytes(br.crash_dump_cmd('enable', IDENT).encode('ascii'))
            self.assertEqual([b for b in br.check_folder(f) if 'crash dumps' in b and '-ExeName' in b], [])
            (f / 'tools' / 'wer_localdumps.ps1').unlink()
            self.assertTrue([b for b in br.check_folder(f) if 'wer_localdumps.ps1' in b and 'beside' in b])

    def test_dll_build_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / 'd3d9.dll'
            d.write_bytes(b'MZ..build 715e9dfc0727 ..')
            self.assertEqual(br.dll_problem(d, '715e9dfc0727'), '')
            self.assertIn('does not carry', br.dll_problem(d, '000000000000'))
            self.assertIn('dirty', br.dll_problem(d, '715e9dfc0727-dirty'))



class Provenance(unittest.TestCase):
    """J79 (audit G13): the shipped ui_scale_2x pack is an external PC build; components.json names the 2.5x masters it was made from"""

    def test_real_components_name_the_masters(self):
        comps = br.read_json(ROOT / 'release' / 'napoleon' / 'components.json')
        self.assertEqual(br.provenance_problems(comps), [])
        m = comps['external_provenance']['uiscale']['masters']
        self.assertEqual((len(m['sha256']), m['files'] <= m['entries']), (64, True))

    def test_bad_rows_are_refused(self):
        comps = {'external': {'uiscale': 'x'}, 'external_provenance': {'uiscale': {'masters': {'sha256': 'ab', 'files': 0}}, 'other': {}}}
        errs = br.provenance_problems(comps)
        self.assertEqual(len(errs), 3, errs)


if __name__ == '__main__':
    unittest.main()
