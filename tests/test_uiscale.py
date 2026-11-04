"""Host tests: the UI scale stop-gap's scaler (uiscale/core/scale.py, J66) on synthetic layouts of each version, and on the vanilla files when the game is here.

Checks: every layout version the game ships (V028-V033, V039 with keyframes) scales and round-trips; absolute edge snapping keeps abutting
pairs abutting (where per-value rounding opens gaps) and is exact at 2x; the 9-slice stretch flags (image-use tail) are never touched; blank
image defs stay; font names map to the context's slots; a uied.templates record's embedded TGA is scaled together with the image def that
describes it; the art target size rule. With the game installed: every vanilla layout and the templates file scale and round-trip.
"""
import json
import os
import struct
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'uiscale', 'core'))
sys.path.insert(0, os.path.join(ROOT, 'discovery', 'core'))

import scale  # noqa: E402
import tpl  # noqa: E402
import uic  # noqa: E402

VERSIONS = (28, 29, 30, 32, 33, 39)
TAIL = bytes([0, 1, 2, 3, 4, 5, 6, 1, 1]) + bytes(range(9, 25))   # bytes 7/8 = the stretch flags (set)


def state(ver, w, h, uses=(), font='Ingame 12, Normal'):
    sp = uic.spec(ver)
    return dict(id=1, name='default', w=w, h=h, text='', text2='', t_b=0, t_c=0, t_d=0, t_e=0, t_f=0, t_g=0, text_label='', text_label2='',
                pre_font=0 if sp.get('pre_font') else None, font=font, f_a=0, f_b=0, font_colour=0, f_raw=bytes(sp['f_raw']), shader='normal_t0',
                s_raw=bytes(sp['s_raw']), s_str1='', on_leave='',
                uses=[dict(img=i, x=x, y=y, w=uw, h=uh, colour=0xFFFFFFFF, tail=TAIL[:sp['iu_tail']]) for i, x, y, uw, uh in uses],
                x_a=0, x_b=0, transitions=[])


def comp(ver, name, x, y, states, children=(), images=(), anims=None):
    sp = uic.spec(ver)
    return dict(id=hash(name) & 0xFFFFFFFF, name=name, x=x, y=y, flags=bytes(sp['flags']), template='', c_a=0, tooltip='', tooltip_label='',
                c_u8=None, c_c=0, c_flag=0 if sp['c_flag'] else None, state_ref=0 if sp.get('state_ref') else None, inline_script='',
                images=[dict(id=i, path=p, w=w, h=h, colour=0) for i, p, w, h in images], i_a=0, i_b=0 if sp['i_b'] else None,
                states=states, e_a=0, e_raw=b'', events=[], e_pad=None, z_a=0,
                anims=(anims or []) if sp.get('anims') else None, children=list(children), script='')


def frame(x, y, w, h):
    return struct.pack('<ffiiI', x, y, w, h, 0xFFFFFFFF) + bytes(48 - 20)


def sample(ver):
    """root 1280x960; a frame of three abutting pieces at odd positions; a textured and a blank image def; a V039 keyframe"""
    left = comp(ver, 'left', 7, 3, [state(ver, 13, 21, [(1, 0, 0, 13, 21)])], images=[(1, 'ui\\skins\\l.tga', 13, 21)])
    mid = comp(ver, 'mid', 20, 3, [state(ver, 9, 21, [(1, 0, 0, 9, 21)])], images=[(1, 'ui\\skins\\m.tga', 9, 21)],
               anims=[dict(name='OnCreate', s2='', frames=[frame(0.0, -3.0, 9, 21)])])
    right = comp(ver, 'right', 29, 3, [state(ver, 11, 21, [(1, 0, 0, 11, 21)], font='Frontend 18, Normal')], images=[(1, '', 5, 5)])
    holder = comp(ver, 'holder', 101, 51, [state(ver, 40, 30)], children=[left, mid, right])
    root = comp(ver, 'root', 0, 0, [state(ver, 1280, 960)], children=[holder])
    return dict(version=ver, root=root)


def find(doc, name):
    return next(c for _, c in uic.walk(doc['root']) if c['name'] == name)


def abs_x(doc, name):
    """absolute x of a component (root position not counted)"""
    def rec(c, ax, path):
        for ch in c['children']:
            if ch['name'] == name:
                return ax + ch['x']
            r = rec(ch, ax + ch['x'], path)
            if r is not None:
                return r
    return rec(doc['root'], 0, [])


class Synthetic(unittest.TestCase):
    def test_each_version_scales_and_round_trips(self):
        for ver in VERSIONS:
            with self.subTest(ver=ver):
                b = uic.serialise(sample(ver))
                self.assertEqual(uic.serialise(uic.parse(b)), b)
                out = scale.layout_bytes(b, 'ui\\campaign ui\\sample', 2.0)
                doc = uic.parse(out)
                self.assertEqual(uic.serialise(doc), out)
                self.assertEqual(find(doc, 'holder')['x'], 202)
                self.assertEqual(find(doc, 'left')['states'][0]['w'], 26)
                self.assertEqual(doc['root']['states'][0]['w'], 2560)
                self.assertEqual(find(doc, 'left')['images'][0]['w'], 26)      # textured def = texture repeat period
                self.assertEqual(find(doc, 'right')['images'][0]['w'], 5)      # blank def stays
                self.assertEqual(find(doc, 'right')['states'][0]['font'], 'Frontend 38, Normal')
                self.assertEqual(find(doc, 'left')['states'][0]['font'], 'Ingame 24, Normal')
                for _, c in uic.walk(doc['root']):
                    for st in c['states']:
                        for u in st['uses']:
                            self.assertEqual(u['tail'], TAIL[:uic.spec(ver)['iu_tail']])   # stretch flags untouched

    def test_v039_keyframe_geometry(self):
        doc = uic.parse(scale.layout_bytes(uic.serialise(sample(39)), 'ui\\battle ui\\sample', 2.0))
        k = find(doc, 'mid')['anims'][0]['frames'][0]
        self.assertEqual(struct.unpack_from('<ffii', k, 0), (0.0, -6.0, 18, 42))
        self.assertEqual(k[16:], frame(0, 0, 0, 0)[16:])                    # the rest of the frame is kept

    def test_edge_snapping_keeps_abutting_pairs(self):
        """at 1.5x, per-value rounding of x and w opens a gap between left (7+13=20) and mid (20); edge snapping never does"""
        for f in (1.25, 1.5, 2.0):
            with self.subTest(f=f):
                doc = sample(33)
                scale.scale_layout(doc, f, 'campaign')
                l, m, r = find(doc, 'left'), find(doc, 'mid'), find(doc, 'right')
                self.assertEqual(l['x'] + l['states'][0]['w'], m['x'])
                self.assertEqual(m['x'] + m['states'][0]['w'], r['x'])
                u = l['states'][0]['uses'][0]
                self.assertEqual(u['x'] + u['w'], l['states'][0]['w'])
        naive = lambda v, f: scale.px(v * f)
        self.assertNotEqual(naive(7, 1.5) + naive(13, 1.5), naive(20, 1.5))   # per-value rounding: 11 + 20 overlaps mid at 30

    def test_exact_at_2x(self):
        doc = sample(33)
        scale.scale_layout(doc, 2.0, 'campaign')
        self.assertEqual([find(doc, n)['x'] for n in ('left', 'mid', 'right')], [14, 40, 58])
        self.assertEqual(scale.px(2.5), 3)
        self.assertEqual(scale.px(-2.5), -2)      # half up, also for negatives
        self.assertEqual(scale.tex_size(13, 1.25), 17)

    def test_scale_root_off_keeps_the_canvas(self):
        doc = sample(33)
        scale.scale_layout(doc, 2.0, 'campaign', scale_root=False)
        self.assertEqual((doc['root']['states'][0]['w'], doc['root']['states'][0]['h']), (1280, 960))
        self.assertEqual(find(doc, 'holder')['x'], 202)

    def test_font_slots(self):
        cases = {('Ingame 12, Normal', 'campaign'): 'Ingame 24, Normal', ('Ingame 12, Bold', 'battle'): 'Ingame 24, Bold',
                 ('Ingame 18, Normal', 'campaign'): 'Frontend 38, Normal', ('Frontend 16, Normal', 'common'): 'Frontend 24, Normal',
                 ('Frontend 18, Normal', 'templates'): 'Frontend 38, Normal', ('Frontend 18, Normal', 'frontend'): 'Frontend 38, Normal',
                 ('Frontend 22, Normal', 'frontend'): 'Frontend 38, Normal', ('Ingame 10, Normal', 'frontend'): 'Ingame 18, Normal',
                 ('Ingame 12, Normal', 'frontend'): 'Ingame 24, Normal', ('Tooltip 12, Bold', 'campaign'): 'Ingame 24, Bold',
                 ('not a font', 'campaign'): 'not a font'}
        for (name, ctx), want in cases.items():
            self.assertEqual(scale.font_slot(name, ctx), want, (name, ctx))
        self.assertEqual(scale.font_file('Ingame 24, Bold'), 'ingame_b_24.cuf')
        self.assertEqual(scale.font_file('Frontend 38, Normal'), 'frontend_38.cuf')
        self.assertEqual(scale.context_of('ui\\frontend ui\\main'), 'frontend')
        self.assertEqual(scale.context_of('ui\\campaign ui\\hud'), 'campaign')


class LongForm(unittest.TestCase):
    """J79 (audit G9): Empire's long-form pass. Only a TextView's 'Text' child keeps the spaced Frontend 24 (line pitch 30); the rest
    move to Ingame 24, so no fixed-height box gets the spaced font. Frontend 38 and Bold stay."""

    def doc(self):
        v = 33
        tv_text = comp(v, 'Text', 2, 2, [state(v, 100, 20, font='Ingame 12, Normal')])                  # -> Ingame 24 -> Frontend 24
        tv_text_f = comp(v, 'Text', 2, 2, [state(v, 100, 20, font='Frontend 12, Normal')])              # -> Frontend 24, kept
        tv_big = comp(v, 'Text', 2, 2, [state(v, 100, 20, font='Frontend 18, Normal')])                 # -> Frontend 38, kept
        tv_bold = comp(v, 'Text', 2, 2, [state(v, 100, 20, font='Ingame 12, Bold')])                    # -> Ingame 24 Bold, kept
        tv_other = comp(v, 'title', 2, 30, [state(v, 100, 20, font='Frontend 12, Normal')])             # in a TextView, not 'Text'
        tv = comp(v, 'desc', 10, 10, [state(v, 120, 60)], children=[tv_text])
        tv['template'] = 'TextView'
        tv2 = comp(v, 'desc2', 10, 80, [state(v, 120, 60)], children=[tv_text_f, tv_big, tv_other])
        tv2['script'] = 'Template.TextView.lua'                                                          # script route, any case
        tv3 = comp(v, 'desc3', 10, 150, [state(v, 120, 60)], children=[tv_bold])
        tv3['template'] = 'TextView'
        label = comp(v, 'label', 10, 220, [state(v, 120, 20, font='Frontend 14, Normal')])              # fixed box -> Ingame 24
        plain_text = comp(v, 'Text', 10, 250, [state(v, 120, 20, font='Frontend 14, Normal')])          # 'Text' outside a TextView
        root = comp(v, 'root', 0, 0, [state(v, 1280, 960, font='Frontend 12, Normal')], children=[tv, tv2, tv3, label, plain_text])
        return dict(version=v, root=root)

    def walk(self, c, path=()):
        yield path, c
        for ch in c['children']:
            yield from self.walk(ch, path + (c,))

    def test_textview_text_takes_the_spaced_font_and_the_rest_move_off_it(self):
        stats = {}
        d = scale.scale_layout(self.doc(), 2.0, 'campaign', stats=stats)
        got = {'/'.join(x['name'] for x in p) + '/' + c['name']: c['states'][0]['font'] for p, c in self.walk(d['root'])}
        self.assertEqual(got['/root'], 'Ingame 24, Normal')                         # the root is never long-form
        self.assertEqual(got['root/desc/Text'], 'Frontend 24, Normal')              # TextView (template) Text: Ingame 24 -> Frontend 24
        d2 = [c for p, c in self.walk(d['root']) if p and p[-1]['name'] == 'desc2']    # TextView by script: Text, Text (38), title
        self.assertEqual([c['states'][0]['font'] for c in d2], ['Frontend 24, Normal', 'Frontend 38, Normal', 'Ingame 24, Normal'])
        self.assertEqual(got['root/desc3/Text'], 'Ingame 24, Bold')                 # Bold stays
        self.assertEqual(got['root/label'], 'Ingame 24, Normal')                    # fixed box: displaced
        self.assertEqual(got['root/Text'], 'Ingame 24, Normal')                     # 'Text' outside a TextView: displaced
        self.assertEqual(stats['fonts']['Frontend 24, Normal'], 2)
        self.assertEqual(sum(stats['fonts'].values()), 11)                         # every state still counted once
        self.assertEqual(stats['longform'], {'Ingame 24, Normal -> Frontend 24, Normal': 1, 'Frontend 24, Normal -> Ingame 24, Normal': 4})

    def test_off_keeps_the_slots(self):
        scale.LONGFORM = False
        try:
            d = scale.scale_layout(self.doc(), 2.0, 'campaign')
        finally:
            scale.LONGFORM = True
        self.assertEqual(find(d, 'label')['states'][0]['font'], 'Frontend 24, Normal')

    def test_template_records_get_the_pass(self):
        v = 33
        text = comp(v, 'Text', 2, 2, [state(v, 100, 20, font='Ingame 12, Normal')])
        tv = comp(v, 'tv', 0, 0, [state(v, 120, 60)], children=[text])
        tv['template'] = 'TextView'
        label = comp(v, 'label', 0, 70, [state(v, 120, 20, font='Frontend 16, Normal')])
        root = comp(v, 'rec', 0, 0, [state(v, 200, 100)], children=[tv, label])
        for _, c in uic.walk(root):
            c['textures'] = []
        d = template_file([('rec', tpl.serialise_record({'textures': [], 'root': root}, 33), 0)])
        out, rep = scale.scale_templates_file(d, 2.0)
        r = tpl.parse_record([r for r in tpl.split(out) if r['name'] == 'rec'][0])['root']
        self.assertEqual(r['children'][0]['children'][0]['states'][0]['font'], 'Frontend 24, Normal')
        self.assertEqual(r['children'][1]['states'][0]['font'], 'Ingame 24, Normal')


def tga(w, h, seed=0):
    return struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, 0x28) + bytes((seed + i) & 0xFF for i in range(w * h * 4))


def template_file(records):
    """a uied.templates container: a legacy first record (passed through) then v33 records [(name, payload, ntex)]"""
    out = bytearray(struct.pack('<I', len(records) + 1))
    legacy = b'InputWindow\0'.ljust(256, b'\xfd')
    out += legacy + struct.pack('<III', 4 + 4, 4, 0) + b'\0\0\0\0'
    for name, pl, ntex in records:
        hdr = (name.encode() + b'\0').ljust(252, b'\xfd')
        out += hdr + struct.pack('<IIII', 33, len(pl) + 4, len(out), ntex) + pl
    return bytes(out)


class Templates(unittest.TestCase):
    def record(self):
        child = comp(33, 'frame', 3, 5, [state(33, 8, 8, [(7, 0, 0, 8, 8), (8, 0, 0, 30, 4)])],
                     images=[(7, 'ui\\templates\\skins\\corner.tga', 8, 8), (8, 'ui\\skins\\external.tga', 30, 4)])
        root = comp(33, 'my_tooltip', 0, 0, [state(33, 200, 100)], children=[child])
        w = uic.W()
        w.u32(1)
        w.s('ui\\templates\\skins\\corner.tga')
        w.raw(tga(8, 8))
        doc = {'textures': [], 'root': root}
        for _, c in uic.walk(root):
            c['textures'] = []
        body = tpl.serialise_record(doc, 33)
        return bytes(w.b)[4:], body

    def test_embedded_tga_is_scaled_with_its_image_def(self):
        texbytes, body = self.record()
        payload = texbytes + body
        d = template_file([('my_tooltip', payload, 1)])
        out, rep = scale.scale_templates_file(d, 2.0)
        self.assertEqual(rep['scaled'], ['my_tooltip'])
        self.assertEqual(rep['passed'], ['InputWindow (v4)'])
        r = [r for r in tpl.split(out) if r['name'] == 'my_tooltip'][0]
        doc = tpl.parse_record(r)
        t = doc['textures'][0]['tga']
        self.assertEqual(struct.unpack_from('<HH', t, 12), (16, 16))
        fr = doc['root']['children'][0]
        defs = {im['path']: (im['w'], im['h']) for im in fr['images']}
        self.assertEqual(defs['ui\\templates\\skins\\corner.tga'], (16, 16))     # embedded: def follows the pixels
        self.assertEqual(defs['ui\\skins\\external.tga'], (30, 4))               # external: def left as Empire did
        self.assertEqual((fr['x'], fr['states'][0]['w']), (6, 16))
        self.assertEqual(doc['root']['states'][0]['w'], 400)
        unchanged, _ = scale.scale_templates_file(d, 2.0, skip={'my_tooltip'})
        self.assertEqual(unchanged, d)                                           # passing through is byte-exact

    def test_nearest_neighbour_tga(self):
        t = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, 2, 1, 32, 0x28) + bytes([1, 2, 3, 4, 5, 6, 7, 8])
        up = scale.upscale_tga(t, 2.0)
        self.assertEqual(up[18:], bytes([1, 2, 3, 4, 1, 2, 3, 4, 5, 6, 7, 8, 5, 6, 7, 8]) * 2)


def game_root():
    try:
        with open(os.path.join(ROOT, 'discovery', 'napoleon', 'games.json'), encoding='utf-8') as f:
            g = json.load(f)
    except OSError:
        return None, None
    data = os.path.join(g['napoleon']['root'], g['napoleon']['data'])
    return (g, data) if os.path.isdir(data) else (None, None)


class Vanilla(unittest.TestCase):
    @unittest.skipUnless(game_root()[0], 'Napoleon is not installed here')
    def test_every_vanilla_layout_and_the_templates_scale_and_round_trip(self):
        import packfs
        g, data = game_root()
        fs = packfs.PackFS.from_games(g, 'napoleon')
        n = 0
        for c in fs.list(under='ui\\'):
            if '.' in c.path.rsplit('\\', 1)[-1]:
                continue
            b = fs.read(c)
            if b.startswith(b'Version'):
                scale.layout_bytes(b, c.path, 2.0)   # raises unless the input and the output round-trip
                n += 1
        self.assertEqual(n, 174)                    # napoleon.diff.layouts.versions
        with open(os.path.join(data, 'ui', 'templates', 'uied.templates'), 'rb') as f:
            d = f.read()
        out, rep = scale.scale_templates_file(d, 2.0)
        self.assertEqual(len(rep['scaled']) + len(rep['passed']), 126)
        self.assertEqual(sorted(p.split(' ')[0] for p in rep['passed']), ['BattleEditor', 'Cursor', 'InputWindow', 'slider'])
        self.assertEqual(len(tpl.split(out)), 126)


    @unittest.skipUnless(game_root()[0], 'Napoleon is not installed here')
    def test_long_form_rule_holds_on_every_template_state(self):
        """J79: 12 template states use Frontend 24 after the slots alone (audit G9), none in a TextView's Text; after the pass only
        TextView Text states use it (1 in the shipped uied.templates, measured 2026-11-04)"""
        g, data = game_root()
        with open(os.path.join(data, 'ui', 'templates', 'uied.templates'), 'rb') as f:
            d = f.read()

        def counts(on):
            scale.LONGFORM = on
            try:
                out, rep = scale.scale_templates_file(d, 2.0)
            finally:
                scale.LONGFORM = True
            tv_text = other = 0
            for r in tpl.split(out):
                if r['name'] not in rep['scaled']:
                    continue
                root = tpl.parse_record(r)['root']

                def rec(c, in_tv, top=False):
                    nonlocal tv_text, other
                    if any(st.get('font') == scale.LONGFORM_FONT for st in c['states']):
                        n = sum(st.get('font') == scale.LONGFORM_FONT for st in c['states'])
                        if in_tv and not top and c['name'] == 'Text':
                            tv_text += n
                        else:
                            other += n
                    for ch in c['children']:
                        rec(ch, scale.is_textview(c))
                rec(root, False, True)
            return tv_text, other
        self.assertEqual(counts(False), (0, 12))
        after = counts(True)
        self.assertEqual(after[1], 0)                                               # no fixed box keeps the spaced font
        self.assertEqual(after, (1, 0))


class ArtSize(unittest.TestCase):
    def test_target_size_matches_the_image_def_rule(self):
        try:
            import art
        except ImportError as e:
            self.skipTest(f'numpy/Pillow not here: {e}')
        self.assertEqual(art.target_size(13, 7, 2.0), (26, 14))
        self.assertEqual(art.target_size(13, 7, 1.25), (scale.tex_size(13, 1.25), scale.tex_size(7, 1.25)))


if __name__ == '__main__':
    unittest.main()
