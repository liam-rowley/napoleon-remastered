"""J34 design tokens and component library: token maths, build, lint (one failing fixture per rule), the corner gate, the changes report, and the board's interactions.

The pure tests always run. The render tests need the viewer build (viewer/core/build.sh --docker build, or CI's viewer job) and Python Playwright with
Chromium; without them they skip with the reason.
"""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UIKIT = ROOT / 'uikit' / 'napoleon'
OUT = Path(os.environ.get('VIEWER_OUT', ROOT / 'build' / 'viewer' / 'out'))
BOARD = ROOT / 'viewer' / 'napoleon' / 'board'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


T = load('uikit_tokens', UIKIT / 'tokens.py')
B = load('uikit_build', UIKIT / 'build.py')
L = load('uikit_lint', UIKIT / 'lint.py')


def have_render():
    if not (OUT / 'viewer.wasm').exists():
        return False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


class Tokens(unittest.TestCase):
    def setUp(self):
        self.t = T.load_tokens()

    def test_palette_matches_language(self):
        c = self.t['color']
        self.assertEqual((c['panel'], c['control_border'], c['text'], c['accent_fill'], c['focus_ring']),
                         ('#f1f3f5', '#2a3547', '#1a2230', '#1f4e8c', '#0b5fd0'))
        self.assertNotIn(' ', ''.join(self.t['color']) + ''.join(self.t['length']))

    def test_lengths_are_integers_and_text_is_14_or_more(self):
        self.assertTrue(all(isinstance(v, int) for v in self.t['length'].values()))
        self.assertTrue(all(s['size'] >= self.t['min_text_dp'] for s in self.t['type'].values()))

    def test_derived_hover_pressed_close_to_the_draft(self):
        d = T.derived_colors(self.t)
        for name, draft in (('hover', '#d3dae2'), ('pressed', '#c4ccd6')):
            self.assertTrue(all(abs(a - b) <= 8 for a, b in zip(T.hex_to_rgb(d[name]), T.hex_to_rgb(draft))), (name, d[name]))
        self.assertGreater(T.luminance(d['hover']), T.luminance(d['pressed']))

    def test_every_declared_pair_passes(self):
        bad = [r for r in T.pair_report(self.t) if not r[4]]
        self.assertEqual(bad, [])

    def test_contrast_known_values(self):
        self.assertAlmostEqual(T.contrast('#000000', '#ffffff'), 21.0, places=2)
        self.assertAlmostEqual(T.contrast('#1a2230', '#f1f3f5'), 14.35, places=2)

    def test_france_and_britain_worked_examples(self):
        fr = T.faction_tokens(9, 79, 150, self.t)
        self.assertEqual((fr['fac'], fr['on_fac'], fr['ratio'], fr['adjusted']), ('#094f96', '#ffffff', 8.17, False))
        br = T.faction_tokens(222, 0, 0, self.t)
        self.assertEqual((br['fac'], br['on_fac'], br['ratio'], br['adjusted']), ('#de0000', '#ffffff', 5.11, False))

    def test_dark_on_colour_for_a_light_fill(self):
        r = T.faction_tokens(250, 247, 205, self.t)
        self.assertEqual(r['on_fac'], '#0b0f16')
        self.assertGreater(T.contrast(r['fac_hover'], r['on_fac']), T.contrast(r['fac'], r['on_fac']))

    def test_the_hole_is_closed_for_the_worst_case_colour(self):
        # LANGUAGE.md's rule alone gives 4.38:1 for (240, 0, 70); the fix moves the fill in 2 % steps and says so
        raw = max(T.contrast((240, 0, 70), '#0b0f16'), T.contrast((240, 0, 70), '#ffffff'))
        self.assertAlmostEqual(raw, 4.38, delta=0.02)
        r = T.faction_tokens(240, 0, 70, self.t)
        self.assertTrue(r['adjusted'])
        self.assertGreaterEqual(T.contrast(r['fac'], r['on_fac']), 4.5)
        self.assertEqual(r['fill_in'], '#f00046')

    def test_grid_sweep_on_colour_and_hover_pressed_never_lower_the_ratio(self):
        n = adjusted = 0
        for r in range(0, 256, 15):
            for g in range(0, 256, 15):
                for b in range(0, 256, 15):
                    rec = T.faction_tokens(r, g, b, self.t)
                    base = T.contrast(rec['fac'], rec['on_fac'])
                    self.assertGreaterEqual(base, 4.5, (r, g, b))
                    self.assertGreaterEqual(T.contrast(rec['fac_hover'], rec['on_fac']), base - 1e-9, (r, g, b))
                    self.assertGreaterEqual(T.contrast(rec['fac_pressed'], rec['on_fac']), base - 1e-9, (r, g, b))
                    if not rec['adjusted']:
                        self.assertEqual(rec['fac'], T.rgb_to_hex((r, g, b)))   # a colour that passes is never touched
                    n += 1
                    adjusted += rec['adjusted']
        self.assertEqual(n, 18 ** 3)
        self.assertGreater(adjusted, 0)

    def test_default_faction_is_accent_with_white(self):
        d = T.default_faction(self.t)
        self.assertEqual((d['fac'], d['on_fac']), ('#1f4e8c', '#ffffff'))

    def test_faction_sheet_has_one_rule_per_faction_and_four_variables(self):
        s = T.faction_sheet({'Test Land': (9, 79, 150), 'x': (240, 0, 70)}, self.t)
        self.assertIn('body.fac-test-land {', s)
        self.assertEqual(s.count('--fac:'), 2)
        self.assertEqual(s.count('--fac-pressed:'), 2)
        self.assertIn('fill adjusted from #f00046', s)

    def test_expand(self):
        self.assertEqual(T.expand('a: $panel; b: $row; c: $fac; d: $type.title.size;', self.t), 'a: #f1f3f5; b: 30dp; c: var(--fac); d: 21dp;')
        self.assertEqual(T.expand('/* $nothing */ x: $gap;', self.t), '/* $nothing */ x: 8dp;')
        with self.assertRaisesRegex(ValueError, 'unknown token \\$nope'):
            T.expand('x: $nope;', self.t)
        self.assertEqual(T.expand('w: $bd_w;', self.t, extra={'bd_w': 320}), 'w: 320dp;')


class Build(unittest.TestCase):
    def test_dist_is_in_step(self):
        self.assertEqual(B.check(), [])

    def test_dist_has_no_unexpanded_tokens_and_no_px(self):
        for name, text in B.build_all().items():
            self.assertNotRegex(text.replace('/* ', '').split('*/')[-1], r'\$[a-z]', name)
        lib = B.build_all()['library.rcss']
        self.assertNotIn('px;', lib)
        self.assertNotIn('flex: 1 1 auto', lib)

    def test_library_has_the_forced_state_twins(self):
        lib = (UIKIT / 'dist' / 'library.rcss').read_text(encoding='utf-8')
        for pseudo, twin in ((':hover', '.is-hover'), (':active', '.is-pressed'), (':focus-visible', '.is-focus')):
            self.assertIn(pseudo, lib)
            self.assertIn(twin, lib)
        for cls in ('.is-disabled', '.is-selected'):
            self.assertIn(cls, lib)

    def test_fonts_are_pinned(self):
        src = json.loads((UIKIT / 'fonts' / 'SOURCES.json').read_text(encoding='utf-8'))
        import hashlib
        for f in src['files']:
            data = (UIKIT / 'fonts' / f['file']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), f['sha256'], f['file'])
            self.assertTrue((UIKIT / 'fonts' / f['licence_file']).exists())


class LintRules(unittest.TestCase):
    def screen(self, rml='<rml><body><div class="btn bd-x">x</div></body></rml>', rcss='.bd-x { color: $text; }', lua='', lengths=None):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name)
        (p / 'screen.json').write_text(json.dumps({'title': 't', 'document': 's.rml', 'prefix': 'bd-', 'library': True, 'lengths': lengths or {},
                                                   'files': ['s.rml', 's.rcss', 's.lua'], 'fonts': []}), encoding='utf-8')
        (p / 's.rml').write_text(rml, encoding='utf-8')
        (p / 's.rcss').write_text(rcss, encoding='utf-8')
        (p / 's.lua').write_text(lua, encoding='utf-8')
        return L.lint_screen(p).findings

    def rules(self, findings):
        return {f['rule'] for f in findings}

    def test_clean_screen_passes(self):
        self.assertEqual(self.screen(), [])

    def test_the_library_and_the_board_are_clean(self):
        lib = L.lint_library('none')
        self.assertEqual(lib.findings, [])
        self.assertEqual(L.lint_screen(BOARD).findings, [])

    def test_rule1_literal_colour_and_bare_length(self):
        self.assertIn('1 tokens only', self.rules(self.screen(rcss='.bd-x { color: #ff0000; }')))
        self.assertIn('1 tokens only', self.rules(self.screen(rcss='.bd-x { margin: 12dp; }')))
        self.assertIn('1 tokens only', self.rules(self.screen(rcss='.bd-x { color: rgba(1,2,3,0.5); }')))
        self.assertIn('1 tokens only', self.rules(self.screen(rml='<rml><body><div class="bd-x" style="color: #fff;">x</div></body></rml>')))
        self.assertEqual(self.screen(rcss='.bd-x { margin: 0 $gap; width: 50%; opacity: 0.5; }'), [])

    def test_rule1_screen_length_tokens_need_the_prefix(self):
        self.assertEqual(self.screen(rcss='.bd-x { width: $bd_w; }', lengths={'bd_w': 300}), [])
        self.assertIn('7 token names exist', self.rules(self.screen(rcss='.bd-x { width: $w; }', lengths={'w': 300})))

    def test_rule2_unknown_class(self):
        self.assertIn('2 library classes', self.rules(self.screen(rml='<rml><body><div class="mystery">x</div></body></rml>')))
        self.assertIn('2 library classes', self.rules(self.screen(rcss='.stray { color: $text; }')))
        self.assertIn('2 library classes', self.rules(self.screen(lua='el:SetClass("is-mystery", true)')))

    def test_rule3_dp_only(self):
        self.assertIn('3 dp only', self.rules(self.screen(rcss='.bd-x { margin: 12px; }')))
        self.assertIn('3 dp only', self.rules(self.screen(rcss='.bd-x { margin: 1.5em; }')))

    def test_rule4_text_size(self):
        self.assertIn('4 text size', self.rules(self.screen(rcss='.bd-x { font-size: 12dp; }')))
        t = copy.deepcopy(T.load_tokens())
        t['type']['label']['size'] = 12
        lint = L.Lint(t)
        lint.min_text_tokens()
        self.assertIn('4 text size', self.rules(lint.findings))

    def test_rule5_contrast(self):
        t = copy.deepcopy(T.load_tokens())
        t['color']['text_dim'] = '#9aa5b3'   # too light on paper
        lint = L.Lint(t)
        lint.contrast('none')
        self.assertIn('5 contrast', self.rules(lint.findings))

    def test_rule6_perf_and_layout(self):
        for css in ('.bd-x { flex: 1 1 auto; }', '.bd-x { opacity: 0; }', '* { color: $text; }', '.bd-a .bd-b .bd-c .bd-d { color: $text; }',
                    '.bd-x { color: $text !important; }', '.bd-x { filter: blur(2dp); }', '.bd-x { outline: 1px; }',
                    '.bd-x { box-shadow: 0 0 $gap 0 $panel; }', '.bd-x { box-shadow: 0 $gap 0 0 $hatch_row; }'):
            self.assertIn('6 perf and layout', self.rules(self.screen(rcss=css)), css)
        self.assertEqual(self.screen(rcss='.bd-x { flex: 1 1 0; display: none; box-shadow: inset 0 0 0 $gap $hatch_row; }'), [])

    def test_rule7_unknown_token(self):
        self.assertIn('7 token names exist', self.rules(self.screen(rcss='.bd-x { color: $no_such; }')))


class Changes(unittest.TestCase):
    def test_compare_and_lock(self):
        C = load('uikit_changes', UIKIT / 'changes.py')
        cur = {'board': {'a': '1', 'b': '2'}, 'other': {'a': '9'}}
        base = {'board': {'a': '1', 'b': 'x'}, 'gone': {'a': '0'}}
        rows = C.compare(cur, base, {'board'})
        self.assertIn(('board', 'b', 'changed', True), rows)
        self.assertIn(('other', 'a', 'new', False), rows)
        self.assertIn(('gone', 'a', 'removed', False), rows)
        self.assertNotIn(('board', 'a', 'changed', True), rows)

    def test_no_lock_file_is_committed_by_this_job(self):
        self.assertFalse((UIKIT / 'LOCK.json').exists(), 'LOCK.json is Liam\'s; the job never writes it')


@unittest.skipUnless(have_render(), f'no {OUT}/viewer.wasm or no Python Playwright with Chromium: run viewer/core/build.sh --docker build')
class Render(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.G = load('uikit_gate', UIKIT / 'gate.py')
        cls.r = cls.G.R
        cls.tmp = tempfile.TemporaryDirectory()
        cls.site = Path(cls.tmp.name) / 'site'
        cls.r.stage(BOARD, cls.site, OUT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def play(self, drive, size=(1920, 4400), ratio=1.0):
        seen = {}
        self.r.render(self.site, size, ratio, actions=lambda page: drive(page, seen))
        return seen

    def test_board_corner_gate_has_no_findings(self):
        res = self.G.render_corners(BOARD, OUT, site=Path(self.tmp.name) / 'gate_site')
        self.assertEqual([r['corner'] for r in res], ['1080p_85', '4k_125', '21x9_100', '16x10_100'])
        for r in res:
            self.assertEqual(r['findings'], [], r['corner'])
        self.assertEqual({(r['w'], r['h']) for r in res}, {(1920, 1080), (3840, 2160), (3440, 1440), (1920, 1200)})

    def test_gate_catches_an_overflowing_screen(self):
        d = Path(self.tmp.name) / 'bad'
        d.mkdir()
        (d / 'screen.json').write_text(json.dumps({'title': 'bad', 'document': 'bad.rml', 'library': True, 'prefix': 'bx-', 'files': ['bad.rml', 'bad.rcss'],
                                                   'fonts': ['PublicSans-Regular.ttf'], 'lengths': {'bx_w': 6000, 'bx_small': 100}}), encoding='utf-8')
        (d / 'bad.rml').write_text('<rml><head><link type="text/rcss" href="uikit/base.rcss"/><link type="text/rcss" href="uikit/library.rcss"/>'
                                   '<link type="text/rcss" href="bad.rcss"/></head><body><div class="bx-wide">wide</div>'
                                   '<div class="bx-small">a label far too long for this little box</div></body></rml>', encoding='utf-8')
        (d / 'bad.rcss').write_text('.bx-wide { width: $bx_w; height: $gap; }\n.bx-small { width: $bx_small; height: $row; }\n', encoding='utf-8')
        res = self.G.render_corners(d, OUT, corners=self.G.CORNERS[:1])
        kinds = {f['kind'] for f in res[0]['findings']}
        self.assertIn('outside_viewport', kinds)
        self.assertTrue(kinds & {'text_wider_than_box', 'outside_parent'}, kinds)

    def test_faction_picker_changes_the_tint_live(self):
        def drive(page, seen):
            el = lambda i: page.evaluate('id => window.viewer.element(id)', i)
            b = el('france')
            page.evaluate(f'window.viewer.mouseMove({int(b["x"] + 8)}, {int(b["y"] + 8)}); window.viewer.mouseDown(0); window.viewer.frame(); window.viewer.mouseUp(0); window.viewer.frame()')
            seen['root'] = el('root')['class']
            seen['france'] = el('france')['class']
            seen['readout'] = el('sec-faction')['rml']
        seen = self.play(drive)
        self.assertIn('fac-france', seen['root'])
        self.assertIn('is-selected', seen['france'])
        self.assertIn('#094f96', seen['readout'])

    def test_hover_press_tab_keyboard_focus(self):
        def drive(page, seen):
            el = lambda i: page.evaluate('id => window.viewer.element(id)', i)
            b = el('live-btn')
            cx, cy = int(b['x'] + b['w'] / 2), int(b['y'] + b['h'] / 2)
            page.evaluate(f'window.viewer.mouseMove({cx}, {cy}); window.viewer.frame()')
            seen['hover'] = el('live-btn')['hover']
            page.evaluate('window.viewer.mouseDown(0); window.viewer.frame()')
            seen['active'] = el('live-btn')['active']
            page.evaluate('window.viewer.mouseUp(0); window.viewer.frame()')
            seen['toggled'] = el('live-btn')['class']
        seen = self.play(drive)
        self.assertTrue(seen['hover'])
        self.assertTrue(seen['active'])
        self.assertIn('is-selected', seen['toggled'])

    def test_tab_key_focuses_the_first_control_and_sets_focus_visible(self):
        def drive(page, seen):
            page.evaluate('window.viewer.key("Tab", true, 0); window.viewer.key("Tab", false, 0); window.viewer.frame()')
            seen['first'] = page.evaluate('id => window.viewer.element(id)', 'default')
        seen = self.play(drive)
        self.assertTrue(seen['first']['focus'])
        self.assertTrue(seen['first']['focus_visible'])

    def test_render_is_deterministic_and_matches_the_baseline(self):
        base = json.loads((UIKIT / 'baseline.json').read_text(encoding='utf-8'))['screens']['board']
        res = {r['corner']: r['rgba_sha256'] for r in self.G.render_corners(BOARD, OUT, site=Path(self.tmp.name) / 'det_site')}
        self.assertEqual(res, base, 'the board changed: run python3 uikit/napoleon/changes.py and, if intended, --accept')


if __name__ == '__main__':
    unittest.main()
