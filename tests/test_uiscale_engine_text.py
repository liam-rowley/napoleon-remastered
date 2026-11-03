"""Host tests for J37 engine text: the exe font model, the engine-text plan per factor, the slot check, the inventory and the licence record.

No game and no PC: synthetic layouts and packs, plus the committed data files (font_slots.json, engine_text.json, font_licences.json).
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ('uiscale/core', 'uiscale/napoleon', 'discovery/core'):
    sys.path.insert(0, os.path.join(ROOT, p))

import cuf_encode  # noqa: E402
import engine_text  # noqa: E402
import fontcheck  # noqa: E402
import licences  # noqa: E402
import scale  # noqa: E402


def load(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return json.load(f)


SLOTS = load('uiscale/napoleon/font_slots.json')
J66_2X = ['ingame_18.cuf', 'ingame_24.cuf', 'ingame_b_24.cuf', 'frontend_24.cuf', 'frontend_38.cuf']   # run 2026-11-02_j66 fonts pack


def state(name, font, text=True):
    st = {'name': 'NewState', 'font': font, 'w': 10, 'h': 10, 'images': []}
    if text:
        st.update(text_key=name + '_Text', text_len=5)
    return st


def surface(comps, fonts):
    return {'components': [{'path': p, 'name': p.split('/')[-1], 'states': [s]} for p, s in comps], 'fonts': fonts, 'opened_by': []}


class Model(unittest.TestCase):
    def setUp(self):
        self.m = fontcheck.Model(SLOTS['engine'])

    def test_list_and_default(self):
        self.assertEqual(len(self.m.names), 19)
        self.assertEqual(self.m.default, 'Ingame 12, Normal')
        self.assertEqual(self.m.file_of('Ingame 24, Bold'), 'ingame_b_24.cuf')
        self.assertEqual(self.m.file_of('Tooltip 24, Normal'), 'ingame_12.cuf')   # unlisted: the default id
        self.assertEqual(self.m.file_of('Ingame 20, Normal'), 'ingame_12.cuf')

    def test_getfont_clamp(self):
        self.assertEqual(self.m.file_of('Frontend 38, Normal'), 'frontend_32.cuf')
        self.assertEqual(self.m.file_for('Frontend', 22, False), 'frontend_22.cuf')
        self.assertEqual(self.m.file_for('frontend', 23, False), 'frontend_22.cuf')
        self.assertEqual(self.m.file_for('ingame', 3, True), 'ingame_b_6.cuf')
        self.assertNotIn('frontend_38.cuf', self.m.opened())
        self.assertEqual(self.m.opened()['frontend_32.cuf'], ['Frontend 38, Normal'])


class Plan(unittest.TestCase):
    def test_factor_one_and_conflicts(self):
        rows = SLOTS['engine_text']
        p1 = fontcheck.plan_engine(rows, 1.0, set(J66_2X))
        self.assertEqual(p1['render'], {})
        p2 = fontcheck.plan_engine(rows, 2.0, set(J66_2X))
        self.assertIn('frontend_22.cuf', p2['render'])
        self.assertEqual(p2['alias'], {'frontend_32.cuf': {'of': 'frontend_38.cuf', 'items': ['layouts naming Frontend 38, Normal']}})
        clash = fontcheck.plan_engine(rows, 2.0, set(J66_2X) | {'frontend_22.cuf'})
        self.assertNotIn('frontend_22.cuf', clash['render'])
        self.assertIn('layout slot', clash['skipped']['frontend_22.cuf'])
        no38 = fontcheck.plan_engine(rows, 2.0, {'ingame_24.cuf'})
        self.assertEqual(no38['alias'], {})

    def test_per_factor_manifest(self):
        """the slot names follow the 2x choice at every factor (scale.SLOT_FACTOR), so the engine plan has the same files at 1.25, 1.5 and 2;
        only the rendered height changes"""
        files = None
        for f in (1.25, 1.5, 2.0):
            p = fontcheck.plan_engine(SLOTS['engine_text'], f, set(J66_2X))
            got = (sorted(p['render']), sorted(p['alias']))
            files = files or got
            self.assertEqual(got, files)
        self.assertEqual([cuf_encode.scaled_h2(20, f) for f in (1.25, 1.5, 2.0)], [25, 30, 40])   # frontend_22: h2 20
        self.assertEqual(cuf_encode.scaled_h2(18, 1.25), 23)   # round half up, as scale.px


class Check(unittest.TestCase):
    def setUp(self):
        self.m = fontcheck.Model(SLOTS['engine'])
        self.names = {'Ingame 24, Normal': 100, 'Ingame 24, Bold': 5, 'Frontend 24, Normal': 3, 'Frontend 38, Normal': 9, 'Ingame 18, Normal': 2}
        self.plan = fontcheck.plan_engine(SLOTS['engine_text'], 2.0, {scale.font_file(n) for n in self.names})

    def pack(self, files):
        return {f: 'sha-' + f for f in files}

    def test_j66_pack_misses_the_clamp_target(self):
        probs, notes = fontcheck.check(self.m, self.names, self.plan, self.pack(J66_2X))
        self.assertTrue(any(p.startswith('frontend_32.cuf (for Frontend 38, Normal)') for p in probs), probs)
        self.assertTrue(any('frontend_38.cuf' in n and 'never opens' in n for n in notes), notes)

    def test_complete_pack_and_missing_slot(self):
        full = self.pack(J66_2X + sorted(self.plan['render']))
        full['frontend_32.cuf'] = full['frontend_38.cuf']
        probs, _ = fontcheck.check(self.m, self.names, self.plan, full)
        self.assertEqual(probs, [])
        gone = dict(full)
        del gone['frontend_22.cuf']
        probs, _ = fontcheck.check(self.m, self.names, self.plan, gone)
        self.assertEqual(len(probs), 1)
        self.assertIn('frontend_22.cuf (engine text', probs[0])
        bad_alias = dict(full)
        bad_alias['frontend_32.cuf'] = 'other'
        probs, _ = fontcheck.check(self.m, self.names, self.plan, bad_alias)
        self.assertTrue(any('same bytes as frontend_38.cuf' in p for p in probs))

    def test_unlisted_name_and_vanilla_font(self):
        full = self.pack(J66_2X + sorted(self.plan['render']))
        full['frontend_32.cuf'] = full['frontend_38.cuf']
        names = dict(self.names, **{'Tooltip 24, Normal': 4})
        probs, _ = fontcheck.check(self.m, names, self.plan, full)
        self.assertTrue(any("'Tooltip 24, Normal'" in p and 'not in the exe name list' in p for p in probs))
        probs, _ = fontcheck.check(self.m, self.names, self.plan, full, vanilla_sha={full['ingame_24.cuf']: 'font\\ingame_24.cuf'})
        self.assertTrue(any('byte-identical to the vanilla' in p for p in probs))

    def test_vanilla_shas_cover_every_shipped_font(self):
        import cli
        shas = cli.vanilla_font_shas()
        files = load('discovery/diff/fonts.json')['detail']['napoleon_files']
        self.assertEqual(len(files), 74)   # napoleon.diff.fonts.cuf
        self.assertTrue(all(v['sha256'] in shas for v in files.values()))   # several files share bytes (46 distinct)


class Inventory(unittest.TestCase):
    def synthetic(self):
        return {
            'battle ui/lb_unit_id': surface([('root', state('root', 'Ingame 12, Normal', False)),
                                             ('root/LB_unit_ID/flag', state('flag', 'Ingame 12, Normal', False))], ['Ingame 12, Normal']),
            'campaign ui/city_info_bar': surface([('root/city_info_bar/name_bar', state('name_bar', 'Ingame 12, Normal')),
                                                  ('root/city_info_bar/x', state('x', 'Ingame 14, Bold', False))], ['Ingame 12, Normal', 'Ingame 14, Bold']),
            'frontend ui/main': surface([('root/title', state('title', 'Frontend 22, Normal'))], ['Frontend 22, Normal']),
        }

    def test_synthetic_banner_and_label(self):
        d = engine_text.build(self.synthetic(), SLOTS, [2.0])
        it = {i['id']: i for i in d['items']}
        self.assertEqual(it['banner.land']['state'], 'art_not_text')
        self.assertEqual(it['banner.naval']['state'], 'open')   # not in this atlas
        lab = it['campaign.city_info_bar']
        self.assertEqual(lab['state'], 'covered_by_j66')
        self.assertEqual(lab['fonts'], {'Ingame 12, Normal': {'vanilla_file': 'ingame_12.cuf',
                                                              'at': {'2': {'name': 'Ingame 24, Normal', 'file': 'ingame_24.cuf'}}}})
        self.assertEqual(it['engine.ribbon_text']['state'], 'built_here')
        self.assertEqual(it['engine.dev_text']['state'], 'vanilla_left')
        self.assertEqual(engine_text.dumps(d), engine_text.dumps(engine_text.build(self.synthetic(), SLOTS, [2.0])))

    def test_layout_slot_wins_over_engine_text(self):
        """a factor where a scaled layout uses frontend_22 as its own slot leaves the engine text vanilla, with the reason"""
        s = copy.deepcopy(SLOTS)
        orig = scale.font_slot
        try:
            scale.font_slot = lambda n, c: 'Frontend 22, Normal' if n.startswith('Frontend 22') else orig(n, c)
            d = engine_text.build(self.synthetic(), s, [2.0])
        finally:
            scale.font_slot = orig
        it = {i['id']: i for i in d['items']}
        self.assertEqual(it['engine.ribbon_text']['state'], 'vanilla_left')
        self.assertIn('layout slot', it['engine.ribbon_text']['at']['2']['frontend_22.cuf'])

    def test_committed_inventory_is_current(self):
        with open(engine_text.OUT, encoding='utf-8') as f:
            self.assertEqual(f.read(), engine_text.dumps(engine_text.generate()))


class Licences(unittest.TestCase):
    def rows(self):
        return load('uiscale/napoleon/font_licences.json')['fonts']

    def test_committed_record(self):
        self.assertEqual(licences.check(self.rows()), [])

    def test_missing_field_and_changed_sha(self):
        r = self.rows()
        del r[0]['spdx']
        self.assertEqual(licences.check(r), ['Lora (variable, wght 400-700), the face every re-rendered .cuf in ui_scale_<f>x_fonts.pack is drawn from: missing spdx'])
        r = self.rows()
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, 'uiscale', 'fonts'))
            shutil.copy(os.path.join(ROOT, r[0]['licence_file']), os.path.join(td, r[0]['licence_file']))
            self.assertEqual(licences.check(r, root=td), [])
            with open(os.path.join(td, r[0]['licence_file']), 'ab') as f:
                f.write(b'\n')
            self.assertEqual(len(licences.check(r, root=td)), 1)
            face = os.path.join(td, 'uiscale', 'fonts', 'Lora-Variable.ttf')
            with open(face, 'wb') as f:
                f.write(b'not the pinned face')
            self.assertTrue(any('differs from the pin' in p for p in licences.check(r, root=td)))


if __name__ == '__main__':
    unittest.main()
