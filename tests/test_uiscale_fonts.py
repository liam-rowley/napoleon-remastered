"""Host tests of the 2x font builder (J66, uiscale/core/cuf_encode.py): a synthetic vanilla .cuf, no game needed.

They need freetype-py (upscale/requirements.txt) and the Lora face the build uses (the first of uiscale/napoleon/config.json font_faces), and are skipped
where either is missing (the CI gate image has no freetype-py: run them with the art_build Python on the PC).
"""
import os
import sys
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.join(ROOT, 'uiscale', 'core'), os.path.join(ROOT, 'core', 'discovery')]

from cuf import Cuf, Glyph  # noqa: E402

try:
    import freetype  # noqa: F401
    HAVE_FT = True
except ImportError:
    HAVE_FT = False
if HAVE_FT:
    import cuf_encode
import json  # noqa: E402
# the face the build uses (uiscale/napoleon/cli.py): the first of config.json font_faces that exists, so the tests run wherever a build can
with open(os.path.join(ROOT, 'uiscale', 'napoleon', 'config.json'), encoding='utf-8') as _f:
    _FACES = [os.path.join(ROOT, p) for p in json.load(_f)['font_faces']]
FACE = next((p for p in _FACES if os.path.isfile(p)), _FACES[0])
HEADER = [21, 16, 24, -1, 1, 18, -5, 7, 1, 24, 29]       # vanilla ingame_24.cuf


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


@unittest.skipUnless(HAVE_FT and os.path.isfile(FACE), 'freetype-py or the Lora face (uiscale/napoleon/config.json font_faces) missing (upscale/requirements.txt)')
class EncodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.van = synthetic_vanilla()
        cls.out = cuf_encode.encode(FACE, cls.van, 23.0, 500)

    def test_deterministic(self):
        self.assertEqual(cuf_encode.encode(FACE, self.van, 23.0, 500), self.out)

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
        face = freetype.Face(FACE)
        gid = lambda ch: face.get_char_index(ord(ch))
        with open(FACE, 'rb') as fh:
            data = fh.read()
        k400, k700 = (cuf_encode.Gpos(data, {'wght': w}).pair(gid('A'), gid('T'))[0] for w in (400, 700))
        self.assertLess(k400, 0)
        self.assertNotEqual(k400, k700)                                            # variation deltas applied
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


if __name__ == '__main__':
    unittest.main()
