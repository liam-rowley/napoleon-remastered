"""Host tests for the J10 UI atlas: the script walk (ui_walk.py) and the atlas helpers (ui_atlas.py) on synthetic fixtures."""
import gzip
import hashlib
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'discovery', 'core'))
sys.path.insert(0, os.path.join(ROOT, 'core', 'proxy', 'tools'))
import luachunk  # noqa: E402
import ui_atlas  # noqa: E402
import ui_walk  # noqa: E402
from luachunk import enc  # noqa: E402

TABLES = ['BattleUI', 'CampaignUI', 'Component', 'FrontEnd']


def _func(k, code, protos=(), locals_=(), nparams=0, nups=0):
    f = luachunk.Func()
    f.k = [('str', s.encode()) for s in k]
    f.code, f.protos, f.locals, f.upvals, f.nparams, f.nups = list(code), list(protos), list(locals_), [], nparams, nups
    return f


def _chunk():
    """local d = CampaignUI.RetrieveDetails(); x = d.Name; function OnClick() CampaignUI.EndTurn() end"""
    k = ['CampaignUI', 'RetrieveDetails', 'Name', 'x', 'OnClick', 'EndTurn']
    on_click = _func(k, [enc('GETGLOBAL', 0, bx=0), enc('GETTABLE', 0, 0, 256 + 5), enc('CALL', 0, 1, 1), enc('RETURN', 0, 1)])
    return _func(k, [enc('GETGLOBAL', 0, bx=0), enc('GETTABLE', 0, 0, 256 + 1), enc('CALL', 0, 1, 2),
                     enc('GETTABLE', 1, 0, 256 + 2), enc('SETGLOBAL', 1, bx=3),
                     enc('CLOSURE', 2, bx=0), enc('SETGLOBAL', 2, bx=4), enc('RETURN', 0, 1)],
                 protos=[on_click], locals_=[(b'd', 3, 8)])


class Walk(unittest.TestCase):
    def setUp(self):
        w = ui_walk.Walker(TABLES)
        w.walk(_chunk())
        self.r = w.result()

    def test_engine_calls_and_fields(self):
        self.assertEqual(sorted(self.r['calls']), ['CampaignUI.EndTurn', 'CampaignUI.RetrieveDetails'])
        self.assertEqual(self.r['fields'], {'CampaignUI.RetrieveDetails()': ['.Name']})
        self.assertEqual(self.r['aliases']['d'], 'CampaignUI.RetrieveDetails()')

    def test_handler_and_its_engine_calls(self):
        self.assertEqual(self.r['handlers'], ['OnClick'])
        self.assertEqual(self.r['func_calls']['OnClick'], ['CampaignUI.EndTurn'])

    def test_inline_facts(self):
        f = ui_walk.inline_facts('function OnSelect()\n  CampaignUI.ShowDiplomacy()\n  Component.Call("x")\nend', TABLES)
        self.assertEqual(f['handlers'], ['OnSelect'])
        self.assertEqual(f['calls'], {'CampaignUI.ShowDiplomacy': 1, 'Component.Call': 1})


class Resolve(unittest.TestCase):
    SCRIPTS = {'campaign ui/foo_scripts/foo.luac': {}, 'campaign ui/shared.luac': {}, 'templates/template.list.luac': {}}

    def test_script_paths(self):
        rs = ui_atlas.resolve_script
        self.assertEqual(rs('campaign ui\\foo', 'foo.lua', self.SCRIPTS), 'campaign ui/foo_scripts/foo.luac')
        self.assertEqual(rs('campaign ui\\foo', '../shared.lua', self.SCRIPTS), 'campaign ui/shared.luac')
        self.assertEqual(rs('campaign ui\\foo', 'template.list.lua', self.SCRIPTS), 'templates/template.list.luac')
        self.assertIsNone(rs('campaign ui\\foo', 'template.button_standard.lua', self.SCRIPTS))

    def test_art_ids(self):
        assets = {'ui\\campaign ui\\skins\\a b.tga': 'ui/campaign_ui/skins/a_b.tga'}
        self.assertEqual(ui_atlas.art_id('UI/Campaign UI/Skins/a b.tga', assets), 'ui/campaign_ui/skins/a_b.tga')
        self.assertEqual(ui_atlas.art_id('data\\UI\\Campaign UI\\Skins\\a b.tga', assets), 'ui/campaign_ui/skins/a_b.tga')
        self.assertEqual(ui_atlas.art_id('C:\\Empire\\data\\UI\\Campaign UI\\Skins\\a b.tga', assets), 'ui/campaign_ui/skins/a_b.tga')
        self.assertTrue(ui_atlas.art_id('C:\\Docs\\golden_bullet.tga', assets).startswith('editor_path:'))
        self.assertTrue(ui_atlas.art_id('ui/missing.tga', assets).startswith('unresolved:'))

    def test_nine_slice_group(self):
        def c(name, w=16, h=16):
            return dict(path=f'root/p/{name}', name=name, parent='root/p', w=w, h=h, states=[dict(images=[f'art/{name}'])])
        comps = [dict(path='root/p', name='p', parent='root', w=100, h=100, states=[])]
        comps += [c(f'frame_{k}') for k in ('TL', 'T', 'TR', 'L', 'R', 'BL', 'B', 'BR')]
        g = ui_atlas.frame_groups(comps)
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]['insets'], [16, 16, 16, 16])
        self.assertEqual(g[0]['pieces']['TL'], ['art/frame_TL'])


def _atlas(scripts):
    at = object.__new__(ui_atlas.Atlas)
    at.tables, at.scripts, at.memo = set(TABLES), scripts, {}
    at.links = {}
    for rel, r in sorted(scripts.items()):
        for _, _, f, j, lab in r['links']:
            at.links.setdefault((f, j), []).append((rel, lab))
    return at


def _script(**kw):
    base = dict(aliases={}, links=[], other_calls={}, defines=[], func_calls={})
    base.update(kw)
    return base


class Trace(unittest.TestCase):
    def test_engine_alias_and_parameter(self):
        a = _script(aliases={'m': 'CampaignUI.Details()'}, links=[['LuaCall', None, 'Initialise', 0, 'CampaignUI.Details().Region']])
        b = _script()
        at = _atlas({'a.luac': a, 'b.luac': b})
        self.assertEqual(at.resolve('CampaignUI.Details()', a)[0], 'CampaignUI.Details')
        self.assertEqual(at.resolve('^m', a)[0], 'CampaignUI.Details')
        self.assertEqual(at.resolve('Initialise#arg1', b)[0], 'CampaignUI.Details.Region')

    def test_callers_that_disagree_resolve_nothing(self):
        a = _script(links=[['LuaCall', None, 'Init', 0, 'CampaignUI.A()']])
        b = _script(links=[['LuaCall', None, 'Init', 0, 'BattleUI.B()']])
        at = _atlas({'a.luac': a, 'b.luac': b, 'c.luac': _script()})
        label, kind, why = at.resolve('Init#arg1', at.scripts['c.luac'])
        self.assertIsNone(label)
        self.assertIn('different', why)
        # the unit's own caller wins over the others
        self.assertEqual(at.resolve('Init#arg1', at.scripts['c.luac'], scope=frozenset({'a.luac', 'c.luac'}))[0], 'CampaignUI.A')

    def test_modules_are_code(self):
        a = _script(other_calls={'^utils.Format': 3})
        at = _atlas({'a.luac': a})
        self.assertEqual(at.resolve('^utils', a)[1], 'code')
        self.assertEqual(at.resolve('panel_manager', a)[1], 'code')
        self.assertEqual(at.resolve('^other', a)[1], 'upvalue')


class Handlers(unittest.TestCase):
    def test_owner_order(self):
        scripts = {'x.luac': {'defines': ['OnSelect']}, 'y.luac': {'defines': []}}
        comps = {'root': dict(path='root', parent=None, script='x.luac'), 'root/b': dict(path='root/b', parent='root', script='y.luac'),
                 'root/m': dict(path='root/m', parent='root', script='missing:template.button_standard.lua')}
        own = ui_atlas.handler_owner
        self.assertEqual(own(comps['root/b'], comps, 'OnSelect', scripts, {}, []), 'x.luac')
        self.assertEqual(own(comps['root/b'], comps, 'call Root.LuaCall,TransitionBack', scripts, {}, []), 'engine command')
        self.assertIn('not shipped', own(comps['root/m'], comps, 'UpdateSlider', scripts, {}, []))
        self.assertEqual(own(comps['root/b'], comps, 'Play', scripts, {}, [], {'Play': ['G.BattleUI']}), 'engine: BattleUI.Play')


class Check(unittest.TestCase):
    def test_problems_catch_a_changed_file_and_rows(self):
        with tempfile.TemporaryDirectory() as d:
            shas = {}
            for f in ui_atlas.ATLAS_FILES:
                shas[f] = ui_atlas.jdump(os.path.join(d, f), {'f': f}, gz=True)
            with open(os.path.join(d, 'summary.json'), 'w', encoding='utf-8') as fh:
                json.dump(dict(sha256=shas, units={'campaign.x': {'screen': 'campaign.x'}}), fh)
            rows = os.path.join(d, 'rows.jsonl')
            with open(rows, 'w', encoding='utf-8') as fh:
                fh.write(json.dumps(dict(id='campaign.x', screen='campaign.x', status='atlas')) + '\n')
            self.assertEqual(ui_atlas.problems(d, rows), [])
            with open(os.path.join(d, 'battle.json.gz'), 'rb') as fh:
                raw = fh.read()
            self.assertEqual(raw[4:8], b'\0\0\0\0')
            self.assertEqual(hashlib.sha256(gzip.decompress(raw)).hexdigest(), shas['battle.json.gz'])
            ui_atlas.jdump(os.path.join(d, 'battle.json.gz'), {'f': 'changed'}, gz=True)
            with open(rows, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(dict(id='campaign.y', screen='campaign.y', status='atlas')) + '\n')
            bad = ui_atlas.problems(d, rows)
            self.assertTrue(any('battle.json.gz' in b for b in bad))
            self.assertTrue(any('ids differ' in b for b in bad))


if __name__ == '__main__':
    unittest.main()
