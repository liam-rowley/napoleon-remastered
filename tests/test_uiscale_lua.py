"""J67 host tests: the Lua patch applier and list, the pixel-constant classifier, the font slot table and the factor check.

Synthetic chunks are assembled with core/discovery/luachunk.py, so nothing here needs the game. The committed list's asserts and the
generated files are checked against the vanilla scripts when they are on this machine (the game, or an extract folder), else skipped.
"""
import json
import os
import struct
import sys
import unittest
from unittest import mock

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in ('uiscale/core', 'core/discovery', 'uiscale/napoleon'):
    sys.path.insert(0, os.path.join(REPO, p))
import luachunk as L  # noqa: E402
import lua_consts  # noqa: E402
import lua_patch  # noqa: E402


def rd(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def chunk(lines, consts=()):
    """a one-function Lua 5.1 chunk from assembler lines (literal constants are added as the lines name them)"""
    f = L.Func()
    f.source, f.line, f.lastline = b'@test', 0, 0
    f.nups, f.nparams, f.vararg, f.maxstack = 0, 0, 2, 40
    f.k = [f.kval(c) for c in consts]
    f.code, f.protos, f.locals, f.upvals = [], [], [], []
    for pc, text in enumerate(lines):
        f.code.append(L.asm(f, text, pc))
    f.lineinfo = [1] * len(f.code)
    return L.Chunk(L.HEADER, f).serialise()


RESIZE = ["GETGLOBAL R0 'c'", "SELF R1 R0 'Resize'", 'LOADK R3 #16', 'LOADK R4 #200', 'CALL R1 4 1', 'RETURN R0 1']


def kval(data, func, k):
    t, v = L.parse(data).func(func).k[k]
    return struct.unpack('<f', v)[0]


class Applier(unittest.TestCase):
    def setUp(self):
        self.data = chunk(RESIZE)
        f = L.parse(self.data).main
        self.k16 = f.find_const(16.0)
        self.k200 = f.find_const(200.0)

    def test_scale_at_three_factors_with_px_rounding(self):
        items = [f'main:{self.k16}[16]', f'main:{self.k200}[200]']
        for factor, a, b in ((1.25, 20, 250), (1.5, 24, 300), (2.0, 32, 400)):
            out, _ = lua_patch.apply(self.data, items, factor)
            self.assertEqual((kval(out, 'main', self.k16), kval(out, 'main', self.k200)), (a, b))
        self.assertEqual([lua_patch.px(x) for x in (12.5, 13.5, -2.5, 17.5 * 1.0)], [13, 14, -2, 18])   # floor(x + 0.5)

    def test_factor_one_changes_nothing_and_a_rerun_is_byte_identical(self):
        items = [f'main:{self.k16}[16]', f'main@3[LOADK R4 #200]=LOADK R4 $200']
        self.assertEqual(lua_patch.apply(self.data, items, 1.0)[0], self.data)
        self.assertEqual(lua_patch.apply(self.data, items, 1.5)[0], lua_patch.apply(self.data, items, 1.5)[0])

    def test_set_is_in_vanilla_pixels(self):
        out, _ = lua_patch.apply(self.data, [f'main:{self.k200}[200]=450'], 2.0)
        self.assertEqual(kval(out, 'main', self.k200), 900)

    def test_an_assert_fails_on_a_changed_constant_or_instruction(self):
        with self.assertRaisesRegex(ValueError, 'the list says 17'):
            lua_patch.apply(self.data, [f'main:{self.k16}[17]'], 2.0)
        with self.assertRaisesRegex(ValueError, 'expected'):
            lua_patch.apply(self.data, ['main@2[LOADK R3 #99]=LOADK R3 $99'], 2.0)
        bad = lua_patch.check([('s', [f'main:{self.k16}[17]'])], {'s': self.data})
        self.assertEqual(len(bad), 1)

    def test_replace_with_a_dollar_literal_and_insert(self):
        out, log = lua_patch.apply(self.data, ['main@2[LOADK R3 #16]=LOADK R3 $16', 'main@4[CALL R1 4 1]+ADD R3 R3 $8'], 1.5)
        f = L.parse(out).main
        self.assertEqual(L.fmt(f, f.code[2], 2), 'LOADK R3 #24')
        self.assertEqual(L.fmt(f, f.code[4], 4), 'ADD R3 R3 #12')
        self.assertEqual(len(f.code), len(RESIZE) + 1)
        self.assertEqual(L.parse(out).serialise(), out)

    def test_float32_constants(self):
        data = chunk(["GETGLOBAL R0 'c'", "SELF R1 R0 'MoveTo'", 'LOADK R3 #0.30000001192092896', 'LOADK R4 #7', 'CALL R1 4 1', 'RETURN R0 1'])
        k = L.parse(data).main.find_const(7.0)
        out, _ = lua_patch.apply(data, ['main@2[LOADK R3 #0.30000001192092896]=LOADK R3 #0.3', f'main:{k}[7]'], 1.25)
        self.assertEqual(kval(out, 'main', k), 9)

    def test_list_parse_refuses_a_script_twice_and_a_bad_item(self):
        with self.assertRaisesRegex(ValueError, 'twice'):
            lua_patch.parse_list('a | main:1[2]\na | main:2[3]\n')
        with self.assertRaises(ValueError):
            lua_patch.parse_list('a | main:1\n')             # no vanilla assert

    def test_the_committed_list_parses(self):
        entries = lua_patch.parse_list(rd(os.path.join(REPO, 'uiscale/napoleon/lua_patches.txt')))
        self.assertGreater(sum(len(i) for _, i in entries), 100)
        ids = {s for s, _ in entries}
        self.assertIn('ui/huds.luac', ids)                    # the battle radar group (napoleon.ui.radar_placement)
        self.assertIn('ui/templates/template.map_image.luac', ids)


class Classifier(unittest.TestCase):
    def rows(self, lines):
        doc = lua_consts.classify({'t.luac': chunk(lines)})
        return {(r['value'], r['class']) for r in doc['rows']}

    def test_offset_ratio_and_pitch(self):
        lines = ["GETGLOBAL R0 'c'", "SELF R1 R0 'Width'", 'CALL R1 2 2', 'ADD R2 R1 #10', 'MUL R3 R1 #0.5',
                 "SELF R4 R0 'MoveTo'", 'MOVE R6 R2', 'MOVE R7 R3', 'CALL R4 4 1',
                 'LOADK R8 #1', 'LOADK R9 #5', 'LOADK R10 #1', 'FORPREP R8 ->18',
                 'MUL R12 R11 #66', "SELF R13 R0 'MoveTo'", 'MOVE R15 R12', 'LOADK R16 #0', 'CALL R13 4 1', 'FORLOOP R8 ->13', 'RETURN R0 1']
        rows = self.rows(lines)
        self.assertIn((10, 'scale'), rows)                    # an offset added to a pixel value
        self.assertIn((0.5, 'leave'), rows)                   # a ratio of a pixel value
        self.assertIn((66, 'scale'), rows)                    # a grid pitch: loop index x 66
        self.assertNotIn((5, 'scale'), rows)                  # a loop count never reaches a pixel
        self.assertTrue(all(c in ('scale', 'set', 'leave', 'manual') for _, c in rows))

    def test_a_clamp_constant_stored_with_a_pixel_value(self):
        lines = ["GETGLOBAL R0 'c'", "SELF R1 R0 'Bounds'", 'CALL R1 2 2', "SETGLOBAL R1 'w'", "GETGLOBAL R1 'w'",
                 'LT 0 #1280 R1', 'JMP ->9', 'LOADK R1 #1280', "SETGLOBAL R1 'w'", 'RETURN R0 1']
        self.assertIn((1280, 'scale'), self.rows(lines))       # huds.luac RegisterHud: if w > 1280 then w = 1280


class Tables(unittest.TestCase):
    def test_no_wrapped_refuses_the_play_install_work_folder(self):
        import cli
        for work in (None, str(cli.pc_state.uiscale_work(cli.REPO))):
            with self.assertRaisesRegex(SystemExit, 'scratch folder'):
                cli.build(1.5, work=work, no_wrapped=True)

    def test_no_wrapped_knows_the_scripts_the_dev_wrappers_replace(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('uiscale_cli', os.path.join(REPO, 'uiscale', 'napoleon', 'cli.py'))   # by path: the suite has other `cli` modules
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        w = cli.wrapped_paths()
        self.assertIn('ui\\battle ui\\root.luac', w)
        self.assertIn('ui\\frontend ui\\main.advert.luac', w)
        self.assertEqual(len(w), 4)

    def test_font_slot_table_at_2x_is_j66s_set_at_its_own_size(self):
        t = json.loads(rd(os.path.join(REPO, 'uiscale/napoleon/font_slots.json')))
        two = {r['slot']: r for r in t['layouts'] if r['factor'] == 2.0}
        self.assertEqual(sorted(two), ['frontend_24.cuf', 'frontend_38.cuf', 'ingame_18.cuf', 'ingame_24.cuf', 'ingame_b_24.cuf'])
        self.assertTrue(all(r['render_scale'] == 1.0 for r in two.values()))
        self.assertEqual(two['frontend_24.cuf']['spaced_h2'], 28)   # cuf_encode.SPACED_H2: the J66 pack stays byte-identical
        cfg = json.loads(rd(os.path.join(REPO, 'uiscale/napoleon/config.json')))
        for f in cfg['factors']:
            rows = [r for r in t['layouts'] if r['factor'] == f]
            self.assertEqual(sorted(r['slot'] for r in rows), sorted(two))
            self.assertTrue(all(abs(r['render_scale'] - f / 2) < 1e-9 for r in rows))
        self.assertIn(cfg['resolution_factor']['2560x1440'], cfg['factors'])


def vanilla_scripts():
    import cli
    games = json.loads(rd(os.path.join(REPO, 'discovery/napoleon/games.json')))
    ex = os.path.join(REPO, games['extract'], 'napoleon')
    try:
        if os.path.isdir(ex):
            return cli.lua_scripts(ex)
        if os.path.isdir(os.path.join(games['napoleon']['root'], games['napoleon']['data'])):
            return cli.lua_scripts()
    except Exception:
        return None
    return None


class FactorCheck(unittest.TestCase):
    def comp(self, name, x, w, children=()):
        return {'name': name, 'x': x, 'y': 0, 'states': [{'w': w, 'h': 20}], 'children': list(children), 'images': []}

    def test_only_the_date_cells_own_shift_is_allowed_between_abutting_cells(self):
        import check
        import scale
        for f in (1.25, 1.5, 2.0):
            shift = scale.px(scale.DATE_CELL_SHIFT * f)
            cases = ((self.comp('save_date', 100, 50), shift, 0), (self.comp('save_date', 100, 50), shift + 1, 1), (self.comp('other', 100, 50), shift, 1))
            for b, d, want in cases:
                van = {'root': self.comp('row', 0, 200, [self.comp('turn', 50, 50), b])}
                sc = {'root': self.comp('row', 0, 200, [self.comp('turn', 50, 50), dict(b, x=100 - d)])}
                with mock.patch.object(check.uic, 'parse', side_effect=[van]), mock.patch.object(check.scale, 'scale_layout', return_value=sc):
                    self.assertEqual(len(check.check_layouts([('ui/x', b'')], f, 3840, 2160)['abutting']), want, (f, b['name'], d))

    def test_templates_off_lists_only_pairs_the_scaled_file_broke(self):
        import check

        def tga(w, h):
            return bytes(12) + struct.pack('<HH', w, h) + bytes(2)

        def doc(tw, iw):
            return {'textures': [{'path': 'a.tga', 'tga': tga(tw, tw)}, {'path': 'odd.tga', 'tga': tga(4, 4)}],
                    'root': {'images': [{'path': 'a.tga', 'w': iw, 'h': iw}, {'path': 'odd.tga', 'w': 8, 'h': 8}, {'path': '', 'w': 1, 'h': 1}], 'children': []}}
        rec = [{'name': 'r', 'legacy': False}]
        with mock.patch.object(check.tpl, 'split', return_value=rec), mock.patch.object(check.tpl, 'parse_record', side_effect=[doc(16, 16), doc(32, 32)]):
            self.assertEqual(check.templates_off(b'', b''), [])          # odd.tga is off in vanilla too
        with mock.patch.object(check.tpl, 'split', return_value=rec), mock.patch.object(check.tpl, 'parse_record', side_effect=[doc(16, 16), doc(32, 16)]):
            self.assertEqual(check.templates_off(b'', b''), ['r: a.tga 16x16 on a 32x32 TGA'])


class AgainstTheGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scripts = vanilla_scripts()

    def setUp(self):
        if not self.scripts:
            self.skipTest('no vanilla UI scripts on this machine (no game, no extract/napoleon)')

    def test_every_assert_holds_and_factor_one_is_identity(self):
        entries = lua_patch.parse_list(rd(os.path.join(REPO, 'uiscale/napoleon/lua_patches.txt')))
        self.assertEqual(lua_patch.check(entries, self.scripts), [])
        for sid, items in entries:
            self.assertEqual(lua_patch.apply(self.scripts[sid], items, 1.0)[0], self.scripts[sid], sid)
            for f in (1.25, 1.5, 2.0):
                out, _ = lua_patch.apply(self.scripts[sid], items, f)
                self.assertEqual(L.parse(out).serialise(), out)

    def test_the_generated_files_are_current(self):
        import cli
        doc = cli.lua_consts_doc(self.scripts)
        self.assertEqual(json.dumps(doc, indent=0) + '\n', rd(cli.LUA_CONSTS),
                         'run python3 core/wsc.py uiscale lua-consts')
        self.assertEqual(lua_patch.write_list(doc, self.scripts, cli.LUA_HEADER), rd(cli.LUA_PATCHES))
        self.assertNotIn('unclassified', {r['class'] for r in doc['rows']})

    def test_the_check_is_green_at_every_factor(self):
        import check
        import cli
        layouts = cli.layouts_from()
        for f, w, h in ((2.0, 3840, 2160), (1.5, 2560, 1440), (1.25, 2560, 1440)):
            rep = check.check_layouts(layouts, f, w, h)
            self.assertEqual((rep['loses_content'], rep['abutting']), ([], []), f)


if __name__ == '__main__':
    unittest.main()
