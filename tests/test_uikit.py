"""J34 design tokens and component library: token maths, build, lint (one failing fixture per rule), the corner gate, the changes report, and the board's interactions.

The pure tests always run. The render tests need the viewer build (viewer/core/build.sh --docker build, or CI's viewer job) and Python Playwright with
Chromium; without them they skip with the reason.
"""
import copy
import hashlib
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


# G12 (J80): design/napoleon/tokens.draft.json (D43) became tokens.json by hand. Each draft name has a home here; DraftTrace checks the values, and that neither side has a name nobody explained.
TYPE_FIELDS = ('family', 'weight', 'size', 'line')
DRAFT_MAP = {
    **{f'color.{n}': f'color.{n}' for n in ('bg_deep', 'panel', 'panel_raised', 'control_border', 'text', 'text_dim', 'accent_fill', 'accent_text',
                                            'positive', 'negative', 'warning', 'focus_ring')},
    'color.line (decorative)': 'color.line',
    'color_derived.on_faction_dark': 'color.on_faction_dark',
    'color_derived.on_faction_light': 'color.on_faction_light',
    'color_derived.hover': 'derived.hover',       # computed in tokens.py: compared within 8 levels per channel
    'color_derived.pressed': 'derived.pressed',
    'faction.default_fill': 'faction.default_fill',
    'faction.default_on': 'faction.default_on',
    **{f'type.{s}.{f}': f'type.{s}.{f}' for s in ('title', 'section_head', 'body', 'label', 'description', 'numeral', 'big_numeral') for f in TYPE_FIELDS},
    'type.min_text_dp': 'min_text_dp',
    **{f'space_dp.{n}': f'length.{n}' for n in ('row', 'control_height', 'panel_padding', 'gap', 'section_gap', 'bar_height', 'badge_height', 'checkbox', 'order_button',
                                                'ability_slot', 'manoeuvre_button', 'region_panel_width', 'unit_popup_width')},
    **{f'border_dp.{n}': f'length.{n}' for n in ('hairline', 'ring_inner', 'ring_outer', 'card_top_edge', 'radius')},
    'border_dp.focus_ring': 'length.focus_width',   # `focus_ring` is the colour in tokens.json
    'icon_dp.sizes.0': 'length.icon_s',
    'icon_dp.sizes.1': 'length.icon_m',
    'icon_dp.sizes.2': 'length.icon_l',
    'icon_dp.sizes.3': 'length.icon_xl',
}
DRAFT_DROPPED = {
    '_note': 'a comment on the draft, not a token',
    'faction.source': 'prose: the db columns the host reads (LANGUAGE.md section 2), not a design value',
    'faction.on_colour_rule': 'prose: now code, faction_tokens in tokens.py with faction.dark_on and faction.light_on',
    'faction.hover_pressed_rule': 'prose: now the numbers faction.hover_step and faction.pressed_step',
    'faction.outline': 'prose: the library draws it with $hairline and $control_border',
    'icon_dp.grid': 'how new glyphs are drawn (LANGUAGE.md section 6), an art rule and never a screen length',
    'icon_dp.stroke': 'how new glyphs are drawn (LANGUAGE.md section 6), an art rule and never a screen length',
    'icon_dp.master_px': 'the pixel size of a glyph master (LANGUAGE.md section 6), not a dp length',
}
# draft name: (tokens.json home, draft value, tokens.json value, why). Both values are checked, so an entry goes stale when either side moves.
DRAFT_CHANGED = {
    'faction.min_on_ratio_all_77': ('faction.min_ratio', 4.75, 4.5, 'the draft records the worst ratio measured over the 77 rows; tokens.json holds the rule all colours are held to '
                                    '(jobs/J34/report.md "The fixed on-colour case": "until 4.5:1 is reached")'),
}
NO_LANGUAGE_LINE = 'J34 choice with no line in LANGUAGE.md: '
TOKENS_ADDED = {
    'derived.hatch_row': 'LANGUAGE.md Hatching: ink at 8 % on rows',
    'derived.hatch_bar': 'LANGUAGE.md Hatching, bars; a lighter tint of a variable colour is not possible (jobs/J34/report.md "Hatched bar fill")',
    'derived.shadow': 'the plate shadow as an opaque colour (jobs/J34/report.md "No blurred drop shadow")',
    'derived.row_hatched': 'the worst case under a hatch line, for the contrast pairs',
    'type.tip_title': 'LANGUAGE.md section 7 Tooltip: title serif 15 bold',
    'type.tip_body': 'LANGUAGE.md section 3: tooltip body stays Public Sans 14 / 19',
    'length.row_inner': 'list row 30 less its 1 dp bottom border (LANGUAGE.md section 7)',
    'length.control_inner': 'control 36 less two 1 dp borders',
    'length.badge_inner': 'badge 22 less two 1 dp borders',
    'length.order_radius': 'half of the 56 dp round order button',
    'length.seg_w': 'LANGUAGE.md section 7 Progress bar: segments 12 x 10',
    'length.seg_h': 'LANGUAGE.md section 7 Progress bar: segments 12 x 10',
    'length.card_padding': 'LANGUAGE.md section 7 Card frame: 12 padding',
    'length.tooltip_max': 'LANGUAGE.md Tooltip: max width 340 dp',
    'length.tooltip_pad_x': 'LANGUAGE.md section 7 Tooltip: 12 x 14 padding',
    'length.tooltip_pad_y': 'LANGUAGE.md section 7 Tooltip: 12 x 14 padding',
    'length.inset_outer': 'LANGUAGE.md frame recipe: inset 0 0 0 2px',
    'length.inset_inner': 'LANGUAGE.md frame recipe: inset 0 0 0 3px',
    'length.ring_gap': 'the second line of the double rule, 2 dp up (jobs/J34/report.md "Header and section double rules")',
    'length.plate_shadow_y': 'the hard 6 dp plate shadow (jobs/J34/report.md "No blurred drop shadow")',
    **{f'length.{n}': NO_LANGUAGE_LINE + why for n, why in (
        ('btn_pad_x', 'button padding'), ('btn_pad_y', 'button and tab padding'), ('tab_pad_x', 'tab padding'), ('gap_s', 'the small gap'), ('badge_pad', 'badge padding'),
        ('check_mark', 'the checkbox mark'), ('check_pad', 'the checkbox mark inset'), ('flag_w', 'the flag box'), ('flag_h', 'the flag box'),
        ('scrollbar', 'scrollbar width'), ('scroll_min', 'scrollbar thumb minimum'))},
}


def flatten(node, prefix=''):
    """{dotted name: value} of the draft; a type style's array becomes its four fields, any other array its indexes."""
    out = {}
    for k, v in (node.items() if isinstance(node, dict) else enumerate(node)):
        name = f'{prefix}{k}'
        if isinstance(v, list) and prefix == 'type.':
            out.update({f'{name}.{f}': x for f, x in zip(TYPE_FIELDS, v)})
        elif isinstance(v, (dict, list)):
            out.update(flatten(v, f'{name}.'))
        else:
            out[name] = v
    return out


def token_at(tokens, path):
    node = tokens
    for part in path.split('.'):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def draft_problems(draft, tokens):
    """Every way the draft and tokens.json have parted: names on either side nobody explained, and mapped values that differ."""
    names = flatten(draft)
    errs = [f'{n}: draft name in none of DRAFT_MAP, DRAFT_DROPPED, DRAFT_CHANGED' for n in names if n not in DRAFT_MAP and n not in DRAFT_DROPPED and n not in DRAFT_CHANGED]
    errs += [f'{n}: listed here but not in the draft' for n in (*DRAFT_MAP, *DRAFT_DROPPED, *DRAFT_CHANGED) if n not in names]
    derived = T.derived_colors(tokens)
    for n, home in DRAFT_MAP.items():
        if n not in names:
            continue
        if home.startswith('derived.'):
            have = derived.get(home.split('.')[1])
            if have is None or any(abs(a - b) > 8 for a, b in zip(T.hex_to_rgb(have), T.hex_to_rgb(names[n]))):
                errs.append(f'{n}: {names[n]} is more than 8 levels from {home} {have}')
        elif token_at(tokens, home) is None:
            errs.append(f'{n}: its home {home} is not in tokens.json')
        elif token_at(tokens, home) != names[n]:
            errs.append(f'{n}: {names[n]!r} differs from {home} {token_at(tokens, home)!r}: list it in DRAFT_CHANGED with the reason, never edit tokens.json to pass')
    for n, (home, was, now, _) in DRAFT_CHANGED.items():
        if n in names and (names[n] != was or token_at(tokens, home) != now):
            errs.append(f'{n}: DRAFT_CHANGED says {was!r} became {home} {now!r}; found {names[n]!r} and {token_at(tokens, home)!r}')
    homes = set(DRAFT_MAP.values()) | {v[0] for v in DRAFT_CHANGED.values()}
    ours = [f'{g}.{k}' for g in ('color', 'derived', 'length') for k in tokens[g]] + [f'type.{s}' for s in tokens['type'] if f'type.{s}.family' not in homes]
    errs += [f'{n}: in tokens.json with no draft name and no TOKENS_ADDED reason' for n in ours if n not in homes and n not in TOKENS_ADDED]
    errs += [f'{n}: in TOKENS_ADDED but mapped from the draft or not in tokens.json' for n in TOKENS_ADDED if n in homes or n not in ours]
    return errs


class Tokens(unittest.TestCase):
    def setUp(self):
        self.t = T.load_tokens()

    def test_names_have_no_spaces(self):
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

    def test_lock_file_if_present_is_valid(self):
        C = load('uikit_changes', UIKIT / 'changes.py')
        self.assertEqual(C.lock_problems(), [])   # the real file, the day Liam commits one
        with tempfile.TemporaryDirectory() as d:
            lock = Path(d) / 'LOCK.json'
            self.assertEqual(C.lock_problems(lock), [])   # none: nothing is locked
            lock.write_text('{"locked": ["board"]}', encoding='utf-8')
            self.assertEqual(C.lock_problems(lock), [])
            lock.write_text('{"locked": ["board", "no_such_screen"]}', encoding='utf-8')
            self.assertEqual(len(C.lock_problems(lock)), 1)
            self.assertIn('no_such_screen', C.lock_problems(lock)[0])
            for text in ('{"locked": "board"}', '["board"]', '{"other": []}', '{not json'):
                lock.write_text(text, encoding='utf-8')
                self.assertEqual(len(C.lock_problems(lock)), 1, text)


TOL = {'channel_tolerance': 2, 'max_changed_pixels': 0.02, 'max_delta': 24}


def flat_image(w=10, h=10, rgba=(10, 20, 30, 255)):
    return bytes(rgba) * (w * h)


def poked(buf, w, pixels, delta):
    """A copy of an RGBA buffer with the first channel of each (x, y) moved by delta."""
    b = bytearray(buf)
    for x, y in pixels:
        b[(y * w + x) * 4] += delta
    return bytes(b)


class PixelDiff(unittest.TestCase):
    """J80 Decision 3 on synthetic buffers: no browser, no build."""

    @classmethod
    def setUpClass(cls):
        cls.P = load('uikit_pixeldiff', UIKIT / 'pixeldiff.py')

    def judge(self, cur, ref=None, w=10, h=10, tol=TOL):
        return self.P.judge((w, h, ref or flat_image(w, h)), (w, h, cur), tol)

    def test_identical(self):
        r = self.judge(flat_image())
        self.assertEqual((r['verdict'], r['changed'], r['max_delta']), ('unchanged', 0, 0))

    def test_one_pixel_by_one_level_is_within_tolerance(self):
        r = self.judge(poked(flat_image(), 10, [(3, 4)], 1))
        self.assertEqual((r['verdict'], r['changed'], r['max_delta']), ('within tolerance', 0, 1))

    def test_one_pixel_over_max_delta_is_changed(self):
        r = self.judge(poked(flat_image(), 10, [(3, 4)], 200))
        self.assertEqual((r['verdict'], r['changed'], r['max_delta']), ('changed', 1, 200))

    def test_the_changed_pixel_budget(self):
        r = self.judge(poked(flat_image(), 10, [(0, 0), (1, 0)], 10))   # 2 of 100 pixels: the budget of 0.02
        self.assertEqual((r['verdict'], r['changed'], r['budget']), ('within tolerance', 2, 2))
        r = self.judge(poked(flat_image(), 10, [(0, 0), (1, 0), (2, 0)], 10))
        self.assertEqual((r['verdict'], r['changed']), ('changed', 3))

    def test_different_dimensions_are_always_changed(self):
        r = self.P.judge((10, 10, flat_image()), (10, 11, flat_image(10, 11)), TOL)
        self.assertEqual(r['verdict'], 'changed')
        self.assertIn('10x10', r['reason'])
        self.assertIn('10x11', r['reason'])

    def test_png_round_trip_and_a_format_it_does_not_know(self):
        G = load('uikit_gate', UIKIT / 'gate.py')
        cur = poked(flat_image(4, 3), 4, [(1, 2)], 9)
        self.assertEqual(self.P.decode_png(G.R.png_bytes(4, 3, cur)), (4, 3, cur))
        with self.assertRaisesRegex(ValueError, 'PNG'):
            self.P.decode_png(b'not a png')

    def test_the_diff_png_marks_exactly_the_changed_pixels(self):
        spots = [(3, 4), (9, 9), (0, 0)]
        cur = poked(flat_image(), 10, spots, 100)
        r = self.judge(cur)
        w, h, px = self.P.decode_png(self.P.diff_png(10, 10, cur, r['pixels']))
        self.assertEqual((w, h), (10, 10))
        red = {(i % 10, i // 10) for i in range(100) if px[i * 4:i * 4 + 4] == bytes((255, 0, 0, 255))}
        self.assertEqual(red, set(spots))
        self.assertEqual(px[4:8], bytes((7, 14, 21, 255)))   # the render 30 % dimmed under the marks


class Judged(unittest.TestCase):
    """J80 Decisions 2 and 3 through changes.py without a browser: the wasm comes first, the verdicts come from the reference PNGs, --accept writes them."""

    def setUp(self):
        self.C = load('uikit_changes', UIKIT / 'changes.py')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.d = Path(tmp.name)
        self.refs = self.d / 'baseline'
        self.refs.mkdir()
        self.ref = flat_image()
        (self.refs / 'board_a.png').write_bytes(self.C.G.R.png_bytes(10, 10, self.ref))
        self.base = {'wasm_sha256': 'a' * 64, 'tolerance': TOL, 'screens': {'board': {'a': self.sha(self.ref)}}}

    def sha(self, b):
        return hashlib.sha256(b).hexdigest()

    def details(self, rgba):
        return {'board': [{'corner': 'a', 'w': 10, 'h': 10, 'rgba': rgba, 'rgba_sha256': self.sha(rgba)}]}

    def judged(self, rgba, wasm='a' * 64, locked=()):
        return self.C.judge(self.details(rgba), self.base, set(locked), wasm, ref_dir=self.refs, out_dir=self.d / 'out')

    def test_wasm_finding_comes_before_any_pixel_row_and_fails_alone(self):
        lines, status, rows = self.judged(poked(self.ref, 10, [(1, 1)], 1), wasm='b' * 64)
        self.assertEqual(lines[0], f"changes: viewer.wasm differs from the baseline's ({'b' * 12} vs {'a' * 12}): pixel changes below may come from the viewer build; rebuild and re-accept together")
        self.assertEqual(status, 1)
        self.assertEqual([r['verdict'] for r in rows], ['within tolerance'])
        self.assertIn('within tolerance', lines[1])
        self.assertIn('(wasm differs)', lines[1])

    def test_within_tolerance_is_listed_and_does_not_fail(self):
        lines, status, rows = self.judged(poked(self.ref, 10, [(1, 1)], 1))
        self.assertEqual(status, 0)
        self.assertEqual(len(lines), 1)
        self.assertIn('board a: within tolerance', lines[0])
        self.assertNotIn('wasm', lines[0])

    def test_changed_writes_a_diff_png_and_fails(self):
        lines, status, rows = self.judged(poked(self.ref, 10, [(1, 1)], 100))
        self.assertEqual(status, 1)
        diff = self.d / 'out' / 'board_a.diff.png'
        self.assertTrue(diff.exists())
        self.assertIn(str(diff), lines[0])
        self.assertEqual(rows[0]['verdict'], 'changed')

    def test_equal_hashes_read_no_png(self):
        (self.refs / 'board_a.png').unlink()
        lines, status, rows = self.judged(self.ref)
        self.assertEqual((status, rows), (0, []))

    def test_a_locked_screen_stays_flagged_within_tolerance(self):
        lines, status, rows = self.judged(poked(self.ref, 10, [(1, 1)], 1), locked=['board'])
        self.assertEqual(status, 1)
        self.assertIn('CHANGED SINCE LOCK', lines[0])

    def test_a_missing_reference_is_changed_not_skipped(self):
        (self.refs / 'board_a.png').unlink()
        lines, status, rows = self.judged(poked(self.ref, 10, [(1, 1)], 1))
        self.assertEqual((status, rows[0]['verdict']), (1, 'changed'))
        self.assertIn('no reference PNG', lines[0])

    def test_accept_writes_the_pngs_the_tolerance_and_the_review_line(self):
        cur = poked(self.ref, 10, [(1, 1)], 50)
        path, refs = self.d / 'new' / 'baseline.json', self.d / 'new' / 'baseline'
        path.parent.mkdir()
        msg = self.C.accept(self.details(cur), {'screens': {}}, 'c' * 64, baseline=path, ref_dir=refs)
        d = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual((d['wasm_sha256'], d['screens'], d['tolerance']), ('c' * 64, {'board': {'a': self.sha(cur)}}, self.C.DEFAULT_TOLERANCE))
        self.assertEqual(self.C.P.decode_png((refs / 'board_a.png').read_bytes()), (10, 10, cur))
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
        self.assertEqual(msg, f'baseline written; it is not accepted until the reviewer adds "Baseline accepted: {blob}" to jobs/<id>/review.md')

    def test_accept_keeps_the_tolerance_already_in_the_baseline(self):
        path = self.d / 'baseline.json'
        self.C.accept(self.details(self.ref), self.base, 'c' * 64, baseline=path, ref_dir=self.refs)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['tolerance'], TOL)

    def test_every_baseline_corner_has_a_reference_png_with_its_pixels(self):
        # the review line names the blob of baseline.json only: this is what ties the PNGs to it, so a PNG edited after the review fails here
        base = json.loads((UIKIT / 'baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(set(base['tolerance']), {'channel_tolerance', 'max_changed_pixels', 'max_delta'})
        names = set()
        for screen, corners in base['screens'].items():
            for corner, sha in corners.items():
                names.add(f'{screen}_{corner}.png')
                self.assertEqual(self.sha(self.C.P.decode_png((UIKIT / 'baseline' / f'{screen}_{corner}.png').read_bytes())[2]), sha, (screen, corner))
        self.assertEqual({p.name for p in (UIKIT / 'baseline').iterdir()}, names)


class DraftTrace(unittest.TestCase):
    """G12: every name of the D43 draft reaches tokens.json through DRAFT_MAP, and every tokens.json colour and length comes from the draft or says why not."""

    def setUp(self):
        self.draft = json.loads((ROOT / 'design' / 'napoleon' / 'tokens.draft.json').read_text(encoding='utf-8'))
        self.t = T.load_tokens()

    def test_every_draft_name_and_value_reaches_tokens_json(self):
        self.assertEqual(draft_problems(self.draft, self.t), [])

    def test_a_changed_value_and_an_unknown_name_on_either_side_are_named(self):
        d, t = copy.deepcopy(self.draft), copy.deepcopy(self.t)
        d['color']['panel'] = '#000000'
        d['color']['texty'] = d['color'].pop('text')
        t['length']['mystery'] = 7
        t['color']['ghost'] = '#123456'
        got = '\n'.join(draft_problems(d, t))
        for name in ('color.panel', 'color.texty', 'color.text', 'length.mystery', 'color.ghost'):
            self.assertIn(name, got)

    def test_a_derived_colour_beyond_8_levels_and_a_stale_changed_entry_are_named(self):
        d = copy.deepcopy(self.draft)
        d['color_derived']['hover'] = '#000000'
        d['faction']['min_on_ratio_all_77'] = 9
        got = '\n'.join(draft_problems(d, self.t))
        self.assertIn('color_derived.hover', got)
        self.assertIn('faction.min_on_ratio_all_77', got)


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
        # J80: the viewer build first, then the corners; judge writes a diff PNG for a changed corner where CI's artifact keeps it, even though this test fails before changes.py runs
        C = load('uikit_changes', UIKIT / 'changes.py')
        base = json.loads((UIKIT / 'baseline.json').read_text(encoding='utf-8'))
        details = {'board': self.G.render_corners(BOARD, OUT, site=Path(self.tmp.name) / 'det_site', keep_rgba=True)}
        lines, status, rows = C.judge(details, {**base, 'screens': {'board': base['screens']['board']}}, set(), C.wasm_sha(OUT), out_dir=OUT / 'uikit_gate')
        self.assertEqual(status, 0, 'the board or the viewer build changed: run python3 uikit/napoleon/changes.py and, if intended, --accept\n' + '\n'.join(lines))


if __name__ == '__main__':
    unittest.main()
