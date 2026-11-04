"""Host tests for the effects discovery pass (discovery/core/effects.py, J72): synthetic packs, XML, db bytes and fake exes; no game needed."""
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'discovery', 'core'))
import diffout  # noqa: E402
import effects  # noqa: E402
from packfs import PackFS, write_pack  # noqa: E402


def xml(infos, groups, extra_group=''):
    i = ''.join(f"<SCRIPTED_EFFECT_INFO name='{n}' {a}><SCRIPTED_EFFECT_RENDERING_VARS name='r' {r}/></SCRIPTED_EFFECT_INFO>"
                for n, a, r in infos)
    g = ''.join(f"<SCRIPTED_EFFECT_GROUP name='{n}'>{extra_group}"
                + ''.join(f"<SCRIPTED_EFFECT_GROUP_ENTRY name='{e}' effect='{e}'/>" for e in es) + '</SCRIPTED_EFFECT_GROUP>'
                for n, es in groups)
    return (f"<EFFECTS_MANAGER name='m'><SCRIPTED_EFFECT_INFO_LIST name='l'>{i}</SCRIPTED_EFFECT_INFO_LIST>"
            f"<SCRIPTED_EFFECT_GROUP_INFO name='g'>{g}</SCRIPTED_EFFECT_GROUP_INFO></EFFECTS_MANAGER>").encode()


def u16(s):
    return struct.pack('<H', len(s)) + s.encode('utf-16-le')


def table(rows):
    """A version-0 db table of (key, optional effect) rows: StringU16 key, OptionalStringU16 effect."""
    b = b'\x01' + struct.pack('<I', len(rows))
    for k, e in rows:
        b += u16(k) + (b'\x01' + u16(e) if e is not None else b'\x00')
    return b


def keys_table(keys):
    return b'\x01' + struct.pack('<I', len(keys)) + b''.join(u16(k) for k in keys)


KEY = [{'name': 'key', 'type': 'StringU16', 'key': True}]
EXPL = KEY + [{'name': 'explosion_particle_effect', 'type': 'OptionalStringU16', 'key': False}]
SCHEMA = {'particle_effects_tables': [{'version': 0, 'fields': [{'name': 'key', 'type': 'StringU16', 'key': False}]}],
          'projectiles_explosions_tables': [{'version': 0, 'fields': EXPL}],
          'projectile_trails_tables': [{'version': 0, 'fields': KEY}],
          'projectiles_tables': [{'version': 0, 'fields': KEY + [{'name': 'launch_particle_effect', 'type': 'OptionalStringU16', 'key': False}]}]}
REFS = {'projectiles': ['launch_particle_effect'], 'projectiles_explosions': ['explosion_particle_effect'], 'projectile_trails': []}
SHADERS = {'fx\\particle.fx': {'status': 'changed'}, 'fx\\ribbon.fx': {'status': 'new'}}

E_LAND = xml([('smoke_a', "wind_range='1'", "fx='particle.fx' texture_1='effects\\textures\\smoke.dds'"),
              ('spark', "wind_range='1'", "fx='particle.fx'"),
              ('old', "wind_range='1'", "fx='particle.fx'")],
             [('MusketFire', ['smoke_a', 'spark'])])
N_LAND = xml([('smoke_a', "wind_range='1' ribbon_tiling1='2'", "fx='particle.fx' texture_1='effects\\textures\\smoke.dds'"),
              ('spark', "wind_range='0.5'", "fx='particle.fx'"),
              ('ribbon_smoke', "wind_range='1'", "fx='ribbon.fx' texture_1='\\Effects/Textures/Ribbon.DDS' texture_2='effects\\textures\\gone.tga'")],
             [('MusketFire', ['smoke_a', 'spark', 'ribbon_smoke'])], "<EFFECT_GROUP_AMBIENT_SETTINGS name='a' cell_size='1'/>")


class Fixture:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        e, n = os.path.join(root, 'e'), os.path.join(root, 'n')
        os.makedirs(os.path.join(e, 'effects'))
        os.makedirs(n)
        write_pack(os.path.join(e, 'main.pack'), {
            'effects\\landbattle.xml': b'<EFFECTS_MANAGER/>', 'effects\\naval.xml': xml([('w', '', "fx='particle.fx'")], []),
            'effects\\textures\\smoke.dds': b'SMOKE', 'effects\\textures\\old.dds': b'OLD', 'effects\\textures\\tweak.dds': b'T1',
            'db\\particle_effects_tables\\particle_effects': keys_table(['MusketFire', 'Gone']),
            'db\\projectiles_explosions_tables\\projectiles_explosions': table([('ex', 'MusketFire'), ('ex2', None)]),
            'db\\projectile_trails_tables\\projectile_trails': keys_table(['t']),
            'db\\projectiles_tables\\projectiles': table([('musket', 'MusketFire')])})
        write_pack(os.path.join(e, 'patch.pack'), {'effects\\landbattle.xml': E_LAND}, pack_type=2)
        with open(os.path.join(e, 'effects', 'mod.xml'), 'wb') as f:
            f.write(b'<x/>')
        write_pack(os.path.join(n, 'data.pack'), {
            'effects\\landbattle.xml': N_LAND, 'effects\\naval.xml': xml([('w', '', "fx='particle.fx'")], []),
            'effects\\textures\\smoke.dds': b'SMOKE', 'effects\\textures\\ribbon.dds': b'RIB', 'effects\\textures\\tweak.dds': b'T2',
            'effects\\unit_dust_parameters.txt': b'version 1.0\r\n// c\r\ninf_walk 0.05\r\ncav 0.1\r\n',
            'db\\particle_effects_tables\\particle_effects': keys_table(['MusketFire', 'Nouveau']),
            'db\\projectiles_explosions_tables\\projectiles_explosions': table([('ex', 'MusketFire'), ('ex2', 'Nouveau')]),
            'db\\projectile_trails_tables\\projectile_trails': keys_table(['t']),
            'db\\projectiles_tables\\projectiles': table([('musket', 'MusketFire')])})
        exe_e = b'\0SCRIPTED_EFFECT_INFO\0' + b'\0\0' + 'wind_range'.encode('utf-16-le') + b'\0\0'
        exe_n = exe_e + b'\0\0' + 'ribbon_tiling1'.encode('utf-16-le') + b'\0\0' + 'cell_size'.encode('utf-16-le') * 2 + b'\0ribbon.fx\0'
        self.games = {'empire': {'fs': PackFS(e, ['main', 'patch']), 'exe': exe_e, 'schema': SCHEMA},
                      'napoleon': {'fs': PackFS(n, ['data']), 'exe': exe_n, 'schema': SCHEMA}}

    def build(self):
        return effects.build(self.games, SHADERS, REFS)


class EffectsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()
        cls.rows, cls.d = cls.fx.build()

    @classmethod
    def tearDownClass(cls):
        cls.fx.tmp.cleanup()

    def test_file_verdicts_shadow_and_loose(self):
        f = self.d['files']
        self.assertEqual(f['effects\\textures\\smoke.dds']['status'], 'identical')
        self.assertEqual(f['effects\\textures\\tweak.dds']['status'], 'changed')
        self.assertEqual(f['effects\\textures\\ribbon.dds']['status'], 'new')
        self.assertEqual(f['effects\\textures\\old.dds']['status'], 'gone')
        self.assertEqual(f['effects\\landbattle.xml']['empire']['pack'], 'patch.pack')
        self.assertEqual([s['pack'] for s in self.d['empire_shadowed']], ['main.pack'])
        self.assertEqual(self.d['empire_loose_skipped'], ['effects\\mod.xml'])
        self.assertNotIn('effects\\mod.xml', f)

    def test_definition_name_and_attribute_diff(self):
        d = self.d['definitions']['effects\\landbattle.xml']
        i = d['infos']
        self.assertEqual(i['smoke_a']['status'], 'changed')
        self.assertTrue(i['smoke_a']['add_only'])
        self.assertEqual(i['smoke_a']['attrs_added'], ['ribbon_tiling1'])
        self.assertEqual(i['spark']['attrs_changed'], ['wind_range'])
        self.assertFalse(i['spark']['add_only'])
        self.assertEqual((i['ribbon_smoke']['status'], i['old']['status']), ('new', 'gone'))
        self.assertEqual(d['tags_new'], ['EFFECT_GROUP_AMBIENT_SETTINGS'])
        self.assertEqual(self.d['format']['attr_names_new_to_empire'], ['cell_size', 'ribbon_tiling1', 'texture_2'])
        self.assertEqual(self.d['definitions']['effects\\naval.xml']['info_counts']['identical'], 1)
        self.assertEqual(self.d['text_files']['effects\\unit_dust_parameters.txt']['napoleon']['records'], 2)

    def test_reference_normalisation_and_lookup(self):
        self.assertEqual(effects.norm_ref('\\Effects/Textures/Ribbon.DDS'), 'effects\\textures\\ribbon.dds')
        r = self.d['references']['refs']
        self.assertEqual(r['effects\\textures\\smoke.dds']['empire'], 'same')
        self.assertEqual(r['effects\\textures\\ribbon.dds']['empire'], 'missing')
        self.assertEqual(r['effects\\textures\\gone.tga']['empire'], 'absent_in_both')
        self.assertEqual((r['particle.fx']['empire'], r['ribbon.fx']['empire']), ('changed', 'missing'))
        self.assertEqual(self.d['references']['lacking_by_info']['effects\\landbattle.xml'],
                         {'ribbon_smoke': ['effects\\textures\\ribbon.dds', 'ribbon.fx']})

    def test_exe_name_counts_ascii_and_utf16(self):
        c = effects.name_counts(b'\0\0' + 'cell_size'.encode('utf-16-le') + b'\0\0xcell_size', 'cell_size')
        self.assertEqual(c, {'ascii': 1, 'utf16': 1, 'ascii_exact': 0, 'utf16_exact': 1})
        p = self.d['exe_names']['probe']
        self.assertEqual(p['ribbon.fx']['napoleon']['ascii_exact'], 1)
        self.assertEqual(p['cell_size']['napoleon']['utf16'], 2)
        self.assertEqual(p['cell_size']['empire']['utf16'], 0)
        self.assertEqual(self.d['exe_names']['summary']['probe_in_empire'], 0)

    def test_db_and_smoke(self):
        k = self.d['db']['particle_effects']['keys']
        self.assertEqual((k['identical'], k['new'], k['gone']), (['MusketFire'], ['Nouveau'], ['Gone']))
        k = self.d['db']['projectiles_explosions']['keys']
        self.assertEqual((k['identical'], k['changed']), (['ex'], ['ex2']))
        sm = self.d['smoke']['primary']
        self.assertEqual(sorted(sm), ['MusketFire', 'Nouveau'])
        h = sm['MusketFire']['definitions'][0]
        self.assertEqual((h['tag'], h['how'], h['verdict']), ('SCRIPTED_EFFECT_GROUP', 'exact', 'changed'))
        self.assertEqual(h['entry_infos'], {'changed': 1, 'changed_add_only': 1, 'new': 1})
        self.assertEqual(h['lacking_in_empire'], ['effects\\textures\\ribbon.dds', 'ribbon.fx'])
        self.assertEqual(sm['Nouveau']['definitions'], [])
        self.assertIn('smoke_a', self.d['smoke']['secondary']['effects\\landbattle.xml']['infos'])

    def test_rows_valid_and_deterministic(self):
        a = diffout.dumps('effects', self.rows, self.d)
        rows, d = self.fx.build()
        self.assertEqual(a, diffout.dumps('effects', rows, d))
        self.assertEqual(diffout.problems(json.loads(a)), [])
        self.assertNotIn('variance', a)

    def test_check_mismatch(self):
        orig = effects.load_inputs
        effects.load_inputs = lambda _: (self.fx.games, SHADERS, REFS)
        try:
            out = os.path.join(self.fx.tmp.name, 'effects.json')
            self.assertEqual(effects.main(['--out', out]), 0)
            self.assertEqual(effects.main(['--out', out, '--check']), 0)
            with open(out, 'a', encoding='utf-8') as f:
                f.write(' ')
            self.assertEqual(effects.main(['--out', out, '--check']), 1)
        finally:
            effects.load_inputs = orig


if __name__ == '__main__':
    unittest.main()
