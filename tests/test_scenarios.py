"""Host tests (J44): the scenarios registry and the battle presets the control API loads agree (the `tests` gate). A battle row (land, siege,
naval, historical) has proxy/napoleon/lua/battles/<id>.txt with the type its kind needs, the row's map, and the weather and time-of-day option
indexes the row's text names; its launch is `ctl.py scene <id>` (optionally `--deploy end`); no preset is without a row; stored camera poses
lie inside the kind's pitch clamp (adapter ctl.routes.camera); campaign rows that ctl.py loads name their autostart target first in `save`."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BATTLES = ROOT / 'proxy' / 'napoleon' / 'lua' / 'battles'
TYPE = {'land': 'classic', 'siege': 'siege', 'naval': 'naval', 'historical': 'historic'}


def rows():
    return [json.loads(l) for l in (ROOT / 'registries' / 'scenarios.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]


def preset(sid):
    out = {}
    for line in (BATTLES / f'{sid}.txt').read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if s and not s.startswith('#') and '=' in s:
            k, v = s.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def option(text):
    m = re.search(r'option (\d+)', text or '')
    return m.group(1) if m else None


class Agree(unittest.TestCase):
    def test_battle_rows_and_presets_agree(self):
        for r in rows():
            if r['kind'] not in TYPE:
                continue
            with self.subTest(r['id']):
                self.assertTrue((BATTLES / f"{r['id']}.txt").exists(), 'a battle row needs its preset')
                p = preset(r['id'])
                self.assertEqual(p.get('type'), TYPE[r['kind']])
                self.assertEqual(p.get('map'), r['map'])
                self.assertEqual(p.get('weather'), option(r.get('weather')), 'weather option index')
                self.assertEqual(p.get('time_of_day'), option(r.get('time_of_day')), 'time-of-day option index')
                self.assertRegex(r['launch'], rf"^ctl\.py scene {re.escape(r['id'])}( --deploy end)?$")

    def test_no_preset_without_a_row(self):
        ids = {r['id'] for r in rows()}
        for f in BATTLES.glob('*.txt'):
            self.assertIn(f.stem, ids, f'{f.name} has no scenarios row')

    def test_poses_inside_the_pitch_clamp(self):
        cam = json.loads((ROOT / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))['ctl']['routes']['camera']
        for r in rows():
            kind = 'naval' if r['kind'] == 'historical' and preset(r['id']).get('terrain', '').endswith('nile') else r['kind']
            lo, hi = cam.get(kind if kind != 'historical' else 'land', {}).get('clamps', {}).get('pitch', [-90, 90])
            for pid, pose in (r.get('camera_poses') or {}).items():
                with self.subTest(f"{r['id']}:{pid}"):
                    self.assertTrue(lo <= pose['pitch'] <= hi, f"pitch {pose['pitch']} outside [{lo}, {hi}]")

    def test_campaign_rows_loaded_by_ctl_name_their_target(self):
        for r in rows():
            if r['kind'] == 'campaign' and r['launch'].startswith('ctl.py scene'):
                self.assertTrue(r['save'].startswith('campaign:'), r['id'])

    def test_acceptance_order_covers_every_kind_and_ends_on_a_battle(self):
        ad = json.loads((ROOT / 'harness' / 'napoleon' / 'adapter.json').read_text(encoding='utf-8'))
        by = {r['id']: r for r in rows()}
        order = ad['acceptance']['order']
        self.assertEqual({by[s]['kind'] for s in order}, {'land', 'siege', 'naval', 'historical', 'campaign'})
        self.assertIn(by[order[-1]]['kind'], ('land', 'siege', 'naval'), 'the warm reset runs from a plain battle')


if __name__ == '__main__':
    unittest.main()
