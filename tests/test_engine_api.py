"""discovery/core/engine_api.py: probe-line parsing, the last-block rule for a state probed twice, kinds and J6 answers (synthetic logs)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'discovery' / 'core'))
import engine_api  # noqa: E402

T = '2026-11-01T16:24:13.170Z [INFO ] [t1] lua: '


class Parse(unittest.TestCase):
    def write(self, d, name, lines):
        p = Path(d) / name
        p.write_text(''.join(T + l + '\n' for l in lines), encoding='utf-8')
        return str(p)

    def test_last_block_wins_and_kinds(self):
        with tempfile.TemporaryDirectory() as d:
            log = self.write(d, 'a_proxy.log', [
                'api land@frontend G FrontEnd:table',                     # a stale request run in the front end
                'api land@frontend G.FrontEnd StartCampaign:function',
                'api land@frontend __end total=2',
                'api land@battle G BattleUI:table CampaignUI:nil',
                'api land@battle G.BattleUI CameraZoomTo:function OnUpdate:function',
                'api land@battle R.UIComponent TriggerAnimation:function',
                'api land@battle __end total=5',
            ])
            seen, totals, dropped = engine_api.parse_logs([log])
            self.assertEqual(totals, {'land': 5})
            self.assertEqual(dropped, [{'state': 'land@frontend', 'log': 'a_proxy.log', 'probe_total': 2}])
            self.assertNotIn('G.FrontEnd', seen['land'])
            names = engine_api.merge(seen)
            self.assertEqual(names['G.BattleUI:CameraZoomTo']['kind'], 'function')
            self.assertEqual(names['G.BattleUI:OnUpdate']['kind'], 'event')
            self.assertEqual(names['R.UIComponent:TriggerAnimation']['kind'], 'method')
            self.assertEqual(names['G:BattleUI']['states'], ['land'])

    def test_logs_without_probe_lines_are_not_listed(self):
        # a proof launch's proxy log added to the run later must not change the table (J9 review round 1: the committed table went stale)
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / 'raw'
            raw.mkdir()
            self.write(raw, 'a_proxy.log', ['api land G BattleUI:table', 'api land __end total=1'])
            self.write(raw, 'b_proxy.log', ['loaded probe file other.lua'])
            doc = engine_api.build(d)
            self.assertEqual([Path(p).name for p in doc['logs']], ['a_proxy.log'])

    def test_j6_answers(self):
        with tempfile.TemporaryDirectory() as d:
            diff = Path(d) / 'lua_api.json'
            diff.write_text(json.dumps({'detail': {'names': {
                'BattleUI.*': {'BattleUI.CameraZoomTo': 'new', 'BattleUI.Gone': 'gone', 'BattleUI.Same': 'same'},
                'component methods': {'Component.TriggerAnimation': 'new', 'Component.Missing': 'new'}}}}), encoding='utf-8')
            names = {'G.BattleUI:CameraZoomTo': {'owner': 'G.BattleUI', 'name': 'CameraZoomTo', 'states': ['land']},
                     'R.UIComponent:TriggerAnimation': {'owner': 'R.UIComponent', 'name': 'TriggerAnimation', 'states': ['land']}}
            a = engine_api.j6_answers(names, str(diff))
            self.assertEqual(a['BattleUI.*']['new']['at_runtime'], ['BattleUI.CameraZoomTo'])
            self.assertEqual(a['BattleUI.*']['gone']['not_at_runtime'], ['BattleUI.Gone'])
            self.assertEqual(a['component methods']['found'], ['TriggerAnimation'])
            self.assertEqual(a['component methods']['not_found'], ['Missing'])


class Committed(unittest.TestCase):
    def test_table_current(self):
        out = Path(engine_api.OUT)
        if not out.exists():
            self.skipTest('no committed engine_api.json')
        doc = json.loads(out.read_text(encoding='utf-8'))
        run = Path(engine_api.REPO) / doc['run']
        if not (run / 'raw').is_dir():
            self.skipTest(f'{run}/raw not present')
        self.assertEqual(engine_api.main(['build', '--run', str(run), '--check']), 0, 'discovery/napoleon/engine_api.json is stale: rebuild it')


if __name__ == '__main__':
    unittest.main()
