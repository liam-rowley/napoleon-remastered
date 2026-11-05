"""Host tests of the 2x font builder (J66, uiscale/core/cuf_encode.py) and its golden shas (J79, uiscale/napoleon/font_golden.json).

Game-free, always run: the vendored Lora face's sha256 and font_golden.json's shape (five slot fonts, the pack, the package pins).
With freetype-py: encoding without uharfbuzz raises (no GPOS fallback, J79). With freetype-py and uharfbuzz (upscale/requirements.txt;
CI installs upscale/requirements-ci.txt): the encoder on a synthetic vanilla .cuf, and the GPOS reader as a cross-check of HarfBuzz's kerning.
With those and the game (the vanilla .cuf files through core/discovery/packfs.py): the five slot fonts render to their golden sha256s and,
packed as the build packs them, give the golden fonts pack sha256. "Byte-identical to Empire's" means exactly that: the golden shas are
those of the J66/J68 pack, which D42 compared with Empire's on the PC.
"""
import hashlib
import json
import os
import re
import struct
import sys
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.join(ROOT, 'uiscale', 'core'), os.path.join(ROOT, 'core', 'discovery'), os.path.join(ROOT, 'upscale', 'core')]

from cuf import Cuf, Glyph  # noqa: E402

try:
    import freetype  # noqa: F401
    HAVE_FT = True
except ImportError:
    HAVE_FT = False
try:
    import uharfbuzz  # noqa: F401
    HAVE_HB = True
except ImportError:
    HAVE_HB = False
if HAVE_FT:
    import cuf_encode
# the face the build uses (uiscale/napoleon/cli.py): the first of config.json font_faces that exists, so the tests run wherever a build can
with open(os.path.join(ROOT, 'uiscale', 'napoleon', 'config.json'), encoding='utf-8') as _f:
    _FACES = [os.path.join(ROOT, p) for p in json.load(_f)['font_faces']]
FACE = next((p for p in _FACES if os.path.isfile(p)), _FACES[0])
VENDORED = os.path.join(ROOT, 'uiscale', 'fonts', 'Lora-Variable.ttf')
with open(os.path.join(ROOT, 'uiscale', 'napoleon', 'font_golden.json'), encoding='utf-8') as _f:
    GOLDEN = json.load(_f)
HEADER = [21, 16, 24, -1, 1, 18, -5, 7, 1, 24, 29]       # vanilla ingame_24.cuf
SLOTS = {'ingame_24.cuf', 'ingame_b_24.cuf', 'frontend_24.cuf', 'frontend_38.cuf', 'ingame_18.cuf'}   # napoleon.ui.font_slots_2x
HEX64 = re.compile(r'^[0-9a-f]{64}$')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def synthetic_vanilla():
    """A small CUF0 font in the vanilla shape: ASCII 32..126, one PUA glyph the face lacks, pair table over '!'..'~'."""
    c = Cuf()
    c.header = list(HEADER)
    cps = list(range(32, 127)) + [0xE300]
    for i, cp in enumerate(cps):
        c.cmap[cp] = i
        if cp == 32:
            c.glyphs.append(Glyph(-128, 6, 0, 0, b''))
        else:
            c.glyphs.append(Glyph(12, 9, 3, 4, bytes(range(10, 130, 10))))
    c.pair_first = 33
    n = 126 - 33 + 1
    c.pairs = [bytearray([9] * n) for _ in range(n)]
    return c.serialise()


def vanilla_fonts():
    """(PackFS of the installed game, None) or (None, reason): the vanilla .cuf files come from the game folder via the discovery tools."""
    try:
        with open(os.path.join(ROOT, 'discovery', 'napoleon', 'games.json'), encoding='utf-8') as f:
            g = json.load(f)
        if not os.path.isdir(os.path.join(g['napoleon']['root'], g['napoleon']['data'])):
            return None, 'Napoleon is not installed here (discovery/napoleon/games.json root)'
        import packfs
        return packfs.PackFS.from_games(g, 'napoleon'), None
    except (OSError, KeyError, ImportError) as e:
        return None, f'the vanilla fonts are not readable here: {e}'


def requirement_pins():
    """{name: version} of upscale/requirements.txt"""
    out = {}
    with open(os.path.join(ROOT, 'upscale', 'requirements.txt'), encoding='utf-8') as f:
        for line in f:
            m = re.match(r'^([A-Za-z0-9_.-]+)==([^\s#]+)', line)
            if m:
                out[m.group(1).lower()] = m.group(2)
    return out


class GoldenShape(unittest.TestCase):
    """game-free and package-free: runs everywhere, CI included"""

    def test_vendored_face_is_the_golden_face(self):
        with open(VENDORED, 'rb') as f:
            data = f.read()
        self.assertEqual(GOLDEN['face']['path'], 'uiscale/fonts/Lora-Variable.ttf')
        self.assertEqual((sha(data), len(data)), (GOLDEN['face']['sha256'], GOLDEN['face']['size']))
        self.assertEqual(os.path.normpath(_FACES[0]), VENDORED)                    # the build reads the vendored face first

    def test_golden_file_shape(self):
        fonts = GOLDEN['fonts']
        self.assertEqual({f['name'] for f in fonts}, SLOTS)
        self.assertEqual([f['name'] for f in fonts], sorted(f['name'] for f in fonts))   # pack order
        for f in fonts:
            self.assertRegex(f['sha256'], HEX64)
            self.assertRegex(f['vanilla_sha256'], HEX64)
            self.assertIsInstance(f['size'], int)
        self.assertRegex(GOLDEN['pack']['sha256'], HEX64)
        self.assertTrue(GOLDEN['pack']['sha256'].startswith('5f510b27afa3'))       # J66 after D42, J68
        idx = sum(4 + len('font\\' + f['name']) + 1 for f in fonts)
        self.assertEqual(GOLDEN['pack']['size'], 24 + idx + sum(f['size'] for f in fonts))   # PFH0 header + index + the five

    def test_package_versions_are_the_requirement_pins(self):
        pins = requirement_pins()
        self.assertEqual(GOLDEN['packages']['freetype-py'], pins['freetype-py'])
        self.assertEqual(GOLDEN['packages']['uharfbuzz'], pins['uharfbuzz'])


@unittest.skipUnless(HAVE_FT and os.path.isfile(FACE), 'freetype-py or the Lora face missing (upscale/requirements.txt)')
class NoHarfBuzz(unittest.TestCase):
    def test_encoding_without_uharfbuzz_raises(self):
        saved = sys.modules.get('uharfbuzz', False)
        sys.modules['uharfbuzz'] = None                                           # import uharfbuzz -> ImportError
        try:
            with self.assertRaises(RuntimeError) as cm:
                cuf_encode.encode(FACE, synthetic_vanilla(), 23.0, 500)
        finally:
            if saved is False:
                del sys.modules['uharfbuzz']
            else:
                sys.modules['uharfbuzz'] = saved
        self.assertIn('uharfbuzz', str(cm.exception))
        self.assertIn('upscale/requirements.txt', str(cm.exception))


@unittest.skipUnless(HAVE_FT and HAVE_HB and os.path.isfile(FACE), 'freetype-py, uharfbuzz or the Lora face missing (upscale/requirements.txt)')
class EncodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.van = synthetic_vanilla()
        cls.out = cuf_encode.encode(FACE, cls.van, 23.0, 500)

    def test_deterministic(self):
        self.assertEqual(cuf_encode.encode(FACE, self.van, 23.0, 500), self.out)

    def test_a_slot_drawn_smaller_takes_a_scaled_header(self):
        # J67: with the vanilla ascent over smaller glyphs the text sat low in its cell and was clipped (1.25x, run 2026-11-05_j67pc)
        v = Cuf.parse(self.van)
        data, _ = cuf_encode.render_set(['ingame_24.cuf'], lambda n: self.van, FACE, scale={'ingame_24.cuf': 0.625})['ingame_24.cuf']
        self.assertLess(Cuf.parse(data).header[0], v.header[0])
        full, _ = cuf_encode.render_set(['ingame_24.cuf'], lambda n: self.van, FACE)['ingame_24.cuf']
        self.assertEqual(Cuf.parse(full).header[0], v.header[0])                 # the 2x slots keep theirs: the golden pack depends on it

    def test_a_scaled_header_gives_the_widest_glyph_its_cell(self):
        # J67: h9 is the glyph cell width; left at the vanilla value, a scaled font lost the right of its wide glyphs in the credits
        o = Cuf.parse(cuf_encode.encode(FACE, self.van, 46.0, 500, keep_header=False, set_h2=48))
        self.assertEqual(o.header[9], max(g.w for g in o.glyphs))
        self.assertGreater(o.header[9], Cuf.parse(self.van).header[9])

    def test_parses_and_keeps_glyph_order_and_header(self):
        v, o = Cuf.parse(self.van), Cuf.parse(self.out)
        self.assertEqual(o.cmap, v.cmap)
        self.assertEqual(len(o.glyphs), len(v.glyphs))
        self.assertEqual((o.pair_first, len(o.pairs)), (v.pair_first, len(v.pairs)))
        self.assertEqual([h for k, h in enumerate(o.header) if k != 1], [h for k, h in enumerate(v.header) if k != 1])
        self.assertEqual(o.header[1], o.glyphs[o.cmap[ord('H')]].top)            # h1 = measured cap height

    def test_face_glyphs_are_rendered_and_missing_ones_fall_back(self):
        v, o = Cuf.parse(self.van), Cuf.parse(self.out)
        a = o.glyphs[o.cmap[ord('a')]]
        self.assertNotEqual(a.bitmap, v.glyphs[v.cmap[ord('a')]].bitmap)
        pua = o.cmap[0xE300]
        self.assertEqual(o.glyphs[pua].bitmap, v.glyphs[pua].bitmap)

    def test_gpos_kerning_reaches_the_pair_table(self):
        """the GPOS reader (kept only as this cross-check, J79) against HarfBuzz's kerning, and the kerning reaches the pair table.
        The reader is approximate: at wght 500, em 23 it agrees with HarfBuzz within 2/64 px on 4574 of 5184 letter, digit and
        punctuation pairs (J79, 2026-11-04) and under-kerns most of the rest (bV, eV, ...), which is why it is no fallback."""
        import uharfbuzz as hb
        face = freetype.Face(FACE)
        gid = lambda ch: face.get_char_index(ord(ch))
        with open(FACE, 'rb') as fh:
            data = fh.read()
        k400, k700 = (cuf_encode.Gpos(data, {'wght': w}).pair(gid('A'), gid('T'))[0] for w in (400, 700))
        self.assertLess(k400, 0)
        self.assertNotEqual(k400, k700)                                            # variation deltas applied
        em, upem = 23.0, face.units_per_EM
        font = hb.Font(hb.Face(hb.Blob.from_file_path(FACE), 0))
        font.scale = (int(round(em * 64)),) * 2
        font.set_variations({'wght': 500.0})
        gpos = cuf_encode.Gpos(data, {'wght': 500.0})

        def hb_adv(pair, kern):
            buf = hb.Buffer()
            buf.add_str(pair)
            buf.guess_segment_properties()
            hb.shape(font, buf, {'kern': kern, 'dist': kern, 'liga': False, 'clig': False, 'calt': False})
            p = buf.glyph_positions
            return p[0].x_advance + p[1].x_offset - p[0].x_offset
        def diff(pair):
            xa, xp1, xp2 = gpos.pair(gid(pair[0]), gid(pair[1]))
            return (hb_adv(pair, True) - hb_adv(pair, False)) - (xa + xp2 - xp1) * em * 64 / upem
        for pair in ('AT', 'To', 'LT', 'Yo'):
            self.assertAlmostEqual(diff(pair), 0, delta=2, msg=pair)
        chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,:;!?()-\''
        agree = sum(abs(diff(a + b)) <= 2 for a in chars for b in chars)
        self.assertGreaterEqual(agree, 0.85 * len(chars) ** 2)                   # 4574 / 5184 measured
        o = Cuf.parse(self.out)
        g = lambda ch: o.cmap[ord(ch)]
        self.assertLess(o.step(g('T'), g('o')), o.glyphs[g('T')].adv)            # kerned pair steps tighter

    def test_render_set_spaced_slot_and_width_fit(self):
        res = cuf_encode.render_set(['frontend_24.cuf', 'ingame_24.cuf', 'ingame_b_24.cuf'], lambda n: self.van, FACE)
        self.assertEqual(Cuf.parse(res['frontend_24.cuf'][0]).header[2], 28)     # long-form slot: line pitch 30
        self.assertEqual(Cuf.parse(res['ingame_24.cuf'][0]).header[2], 24)
        self.assertIn('wght 700', res['ingame_b_24.cuf'][1])
        again = cuf_encode.render_set(['ingame_b_24.cuf'], lambda n: self.van, FACE)
        self.assertEqual(again['ingame_b_24.cuf'], res['ingame_b_24.cuf'])


FS, NO_GAME = vanilla_fonts()


@unittest.skipUnless(HAVE_FT and HAVE_HB, 'freetype-py or uharfbuzz missing (upscale/requirements.txt)')
@unittest.skipUnless(FS is not None, NO_GAME or '')
class Golden(unittest.TestCase):
    """the five slot fonts from the vendored face and the vanilla .cuf: their golden sha256s, and the fonts pack they make"""

    @classmethod
    def setUpClass(cls):
        cls.vanilla = {f['name']: FS.read('font\\' + f['name']) for f in GOLDEN['fonts']}
        cls.res = cuf_encode.render_set(sorted(cls.vanilla), cls.vanilla.__getitem__, VENDORED)

    def test_vanilla_fonts_are_the_golden_inputs(self):
        for f in GOLDEN['fonts']:
            self.assertEqual(sha(self.vanilla[f['name']]), f['vanilla_sha256'], f['name'] + ': a different vanilla font (game version?)')

    def test_each_slot_font_matches_its_golden_sha(self):
        for f in GOLDEN['fonts']:
            data = self.res[f['name']][0]
            self.assertEqual((sha(data), len(data)), (f['sha256'], f['size']), f['name'])

    def test_the_five_make_the_golden_fonts_pack(self):
        import pack                                                               # upscale/core/pack.py, as uiscale/napoleon/cli.py builds it
        names = sorted(self.res)
        ents = [('font\\' + n, len(self.res[n][0]), None, None) for n in names]
        idx = pack.index_bytes(ents)
        blob = b'PFH0' + struct.pack('<5I', pack.PTYPE_MOVIE, 0, 0, len(ents), len(idx)) + idx + b''.join(self.res[n][0] for n in names)
        self.assertEqual((sha(blob), len(blob)), (GOLDEN['pack']['sha256'], GOLDEN['pack']['size']))


if __name__ == '__main__':
    unittest.main()
