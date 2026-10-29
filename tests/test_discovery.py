"""Host tests for the J6 discovery readers' pure logic (discovery/core/): diff schema, pack kinds, layout V039 codec, fonts, exe masking."""
import os
import struct
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'discovery', 'core'))
sys.path.insert(0, os.path.join(ROOT, 'proxy', 'tools'))

import diffout  # noqa: E402
import exe  # noqa: E402
import fonts  # noqa: E402
import packs  # noqa: E402
import uic  # noqa: E402


class DiffSchema(unittest.TestCase):
    def test_round_trip_and_sorted(self):
        text = diffout.dumps('x', [diffout.row('b', 1, 2, 'same'), diffout.row('a', 1, 2, 'new')], {})
        import json
        doc = json.loads(text)
        self.assertEqual([r['item'] for r in doc['rows']], ['a', 'b'])
        self.assertEqual(diffout.problems(doc), [])

    def test_bad_verdict_and_duplicates(self):
        with self.assertRaises(ValueError):
            diffout.row('a', 1, 2, 'maybe')
        with self.assertRaises(ValueError):
            diffout.dumps('x', [diffout.row('a', 1, 2, 'same')] * 2, {})

    def test_committed_diff_files_pass_the_schema(self):
        import json
        d = os.path.join(ROOT, 'discovery', 'diff')
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.endswith('.json'):
                with self.subTest(f=f):
                    self.assertEqual(diffout.problems(json.load(open(os.path.join(d, f), encoding='utf-8'))), [])


class Readme(unittest.TestCase):
    def test_generated_readme_is_current(self):
        sys.path.insert(0, os.path.join(ROOT, 'tools', 'verbs'))
        import discovery
        p = os.path.join(ROOT, 'discovery', 'diff', 'README.md')
        self.assertEqual(open(p, encoding='utf-8').read(), discovery.render(ROOT), 'run `wsc discovery render`')


class PackKinds(unittest.TestCase):
    def test_kind(self):
        self.assertEqual(packs.kind('ui\\campaign ui\\x.tga'), 'ui\\campaign ui')
        self.assertEqual(packs.kind('UI\\x.tga'), 'ui')
        self.assertEqual(packs.kind('fr\\voice.wav'), 'voices (language folders)')
        self.assertEqual(packs.kind('db\\units\\t'), 'db')
        self.assertEqual(packs.kind('readme.txt'), '(root)')


def _w_state(w, sid, name, ntrans=0):
    w.u32(sid); w.s(name); w.i32(10); w.i32(20); w.ws(''); w.ws(''); w.i32(0); w.i32(0); w.i32(0); w.u32(0); w.u32(0); w.u8(0)
    w.ws(''); w.ws(''); w.s('Ingame 12, Normal'); w.u32(0); w.u32(0); w.u32(0xff); w.raw(b'\0' * 15); w.s('normal_t0')
    w.raw(b'\0' * 16); w.s(''); w.s(''); w.u32(0); w.i32(0); w.i32(0); w.u32(ntrans)


def _v039(anims):
    """A one-component Version039 layout, built field by field the way the codec documents it."""
    w = uic.W(); w.raw(b'Version039')
    w.u32(7); w.s('root'); w.i32(0); w.i32(0); w.raw(b'\1\1\0\1\0\0\0'); w.s(''); w.i32(-1); w.ws(''); w.ws(''); w.u32(0); w.u8(0)
    w.u32(99)            # state_ref: the default state's id
    w.s('')              # inline script
    w.u32(0); w.u32(0); w.u32(0)   # images, i_a, i_b
    w.u32(1); _w_state(w, 99, 'NewState')
    w.u32(0); w.s('events_end'); w.u32(0)
    w.u32(len(anims))
    for name, frames in anims:
        w.s(name); w.s(''); w.u32(frames); w.raw(b'\x11' * (uic.KEYFRAME * frames))
    w.u32(0); w.s('')    # children, script
    return bytes(w.b)


class LayoutV039(unittest.TestCase):
    def test_round_trip_without_and_with_animations(self):
        for anims in ([], [('OnCreate', 5)], [('OnCreate', 1), ('OnHide', 2)]):
            with self.subTest(anims=anims):
                b = _v039(anims)
                doc = uic.parse(b, 't')
                self.assertEqual(doc['root']['state_ref'], 99)
                self.assertEqual([a['name'] for a in doc['root']['anims']], [n for n, _ in anims])
                self.assertEqual(uic.serialise(doc), b)

    def test_v033_has_no_v039_fields(self):
        self.assertNotIn('state_ref', uic.spec(33))
        self.assertNotIn('anims', uic.spec(33))


class Fonts(unittest.TestCase):
    def test_font_file_rule(self):
        self.assertEqual(fonts.font_file('Ingame 12, Normal'), 'font\\ingame_12.cuf')
        self.assertEqual(fonts.font_file('Ingame 12, Bold'), 'font\\ingame_b_12.cuf')
        self.assertEqual(fonts.font_file('Frontend 38, Normal'), 'font\\frontend_38.cuf')
        self.assertIsNone(fonts.font_file('Comic Sans'))


class ExeSignatures(unittest.TestCase):
    def test_mask_relative_and_absolute(self):
        w = bytes([0x55, 0xE8, 1, 2, 3, 4, 0xA1]) + struct.pack('<I', 0x00412345) + bytes([0x0F, 0x84, 9, 9, 9, 9, 0xC3])
        m = exe.mask_for(w, 0x400000, 0x100000)
        self.assertEqual(m[:1] + m[1:2], [True, True])
        self.assertEqual(m[2:6], [False] * 4)       # call rel32
        self.assertEqual(m[7:11], [False] * 4)      # absolute address inside the image
        self.assertEqual(m[13:17], [False] * 4)     # jcc rel32
        self.assertTrue(m[-1])

    def test_search_masked(self):
        pat = bytes([0x55, 0x8B, 0xEC, 0x83, 0xE8, 0, 0, 0, 0, 0x5D])
        mask = [True] * 5 + [False] * 4 + [True]
        hay = b'\x90' * 7 + bytes([0x55, 0x8B, 0xEC, 0x83, 0xE8, 1, 2, 3, 4, 0x5D]) + b'\x90' * 3
        self.assertEqual(exe.search(hay, pat, mask), [7])
        self.assertEqual(exe.search(hay * 2, pat, mask), [7, 7 + len(hay)])
        self.assertIsNone(exe.search(hay, pat, [False, True, True, False, False, False, False, False, False, True]))


if __name__ == '__main__':
    unittest.main()
