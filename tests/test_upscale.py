"""Host tests of the UI art upscaler (J36): synthetic images, no GPU, no game.

The size rule, status mapping and pack writer are standard library and always run. The image tests (DDS header round trip,
alpha rules, mips, manifest and resume, determinism, verify) need numpy and Pillow (upscale/requirements.txt) and are skipped
where they are missing (the CI gate image has neither: run them with the art_build Python on the PC).
"""
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.join(ROOT, 'upscale', 'core'), os.path.join(ROOT, 'discovery', 'core')]

import pack  # noqa: E402
import rules  # noqa: E402

try:
    import numpy as np
    import PIL  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False
if HAVE:
    import batch
    import dds
    import imageio
    import resample


class SizeRule(unittest.TestCase):
    def test_target_is_two_and_a_half_rounded_half_up(self):
        self.assertEqual(rules.target_size(64, 48), (160, 120))
        self.assertEqual(rules.target_size(1, 1), (3, 3))      # round() would give 2: banker's rounding
        self.assertEqual(rules.target_size(5, 3), (13, 8))     # 12.5 -> 13, 7.5 -> 8

    def test_decide(self):
        cfg = {}
        self.assertEqual(rules.decide(64, 64, 'tga', cfg), ('run', (160, 160)))
        self.assertEqual(rules.decide(2048, 100, 'tga', cfg), ('skip', 'already_large'))
        self.assertEqual(rules.decide(2048, 100, 'tga', {'native_cap': 4096})[0], 'run')
        self.assertEqual(rules.decide(0, 0, 'tga', cfg), ('skip', 'no_header'))
        self.assertEqual(rules.decide(32, 32, 'cur', cfg), ('skip', 'not_an_image_file'))
        self.assertEqual(rules.decide(32, 32, 'tga', cfg, scale=1.5), ('skip', 'under_2x'))

    def test_parse_format(self):
        self.assertEqual(rules.parse_format('dds dxt3 128x64 m3'), ('dds', 'dxt3', 128, 64, 3))
        self.assertEqual(rules.parse_format('tga bgra8_rle 512x256'), ('tga', 'bgra8_rle', 512, 256, 0))
        self.assertEqual(rules.parse_format('cur')[0], 'cur')

    def test_registry_fields_stay_inside_the_core_schema(self):
        self.assertEqual(rules.registry_fields('done', 'm')['upscale_status'], 'done')
        self.assertEqual(rules.registry_fields('skipped:under_2x'), {'upscale_status': 'not_needed', 'upscale_method': 'skipped:under_2x'})
        self.assertEqual(rules.registry_fields('failed:boom')['upscale_status'], 'todo')
        self.assertEqual(rules.registry_fields('pending'), {'upscale_status': 'todo'})

    def test_resume_key_changes_with_input_or_settings(self):
        a = rules.input_key('aa', rules.cfg_signature({'m': 1}))
        self.assertEqual(a, rules.input_key('aa', rules.cfg_signature({'m': 1})))
        self.assertNotEqual(a, rules.input_key('ab', rules.cfg_signature({'m': 1})))
        self.assertNotEqual(a, rules.input_key('aa', rules.cfg_signature({'m': 2})))


class RoleOrder(unittest.TestCase):
    def test_items_follow_the_roles_order_not_the_registry_order(self):
        sys.path.insert(0, os.path.join(ROOT, 'upscale', 'napoleon'))
        import cli
        rows = [('f1', 'flag'), ('t1', 'technology_icon'), ('f2', 'flag'), ('t2', 'technology_icon')]
        with tempfile.TemporaryDirectory() as d:
            reg = os.path.join(d, 'assets.jsonl')
            with open(reg, 'w', encoding='utf-8') as f:
                for i, role in rows:
                    f.write(json.dumps({'id': i, 'path': i, 'role': role, 'format': 'tga bgra8 16x16'}) + '\n')
            got = [it['id'] for it in cli.items_for(['technology_icon', 'flag'], reg)]
        self.assertEqual(got, ['t1', 't2', 'f1', 'f2'])


class PackWriter(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.blobs = {'out/a.tga': b'A' * 100, 'out/b/c.dds': b'C' * 33}
        for rel, b in self.blobs.items():
            os.makedirs(os.path.dirname(os.path.join(self.d, rel)), exist_ok=True)
            open(os.path.join(self.d, rel), 'wb').write(b)
        self.man = {'entries': {
            'x/a': {'status': 'done', 'role': 'icon', 'path': 'ui\\a.tga', 'out': {'file': 'out/a.tga', 'bytes': 100, 'sha256': hashlib.sha256(b'A' * 100).hexdigest()}},
            'x/c': {'status': 'done', 'role': 'icon', 'path': 'ui\\b\\c.dds', 'out': {'file': 'out/b/c.dds', 'bytes': 33, 'sha256': hashlib.sha256(b'C' * 33).hexdigest()}},
            'x/s': {'status': 'skipped:under_2x', 'role': 'icon', 'path': 'ui\\s.tga'}}}

    def test_build_reread_and_prefix(self):
        ents = pack.plan(self.man, self.d, {'icon'}, 'ui_art_2x5\\')
        self.assertEqual([e[0] for e in ents], ['ui_art_2x5\\ui\\a.tga', 'ui_art_2x5\\ui\\b\\c.dds'])
        m = pack.build('ui_art_2x5_icon', ents, self.d, self.d, ['credit'], log=lambda *a: None)
        p = os.path.join(self.d, 'ui_art_2x5_icon.pack')
        t, idx = pack.read_pack(p)
        self.assertEqual(t, 4)                                  # movie type: never replaces a vanilla pack (D2)
        self.assertEqual([(n, s) for n, s, _ in idx], [(e[0], e[1]) for e in ents])
        self.assertEqual(pack.check_pack(p, ents), m['sha256'])
        self.assertFalse(os.path.exists(p + '.building'))
        self.assertEqual(pack.build('ui_art_2x5_icon', ents, self.d, self.d, log=lambda *a: None)['sha256'], m['sha256'])   # kept, not rebuilt

    def test_the_discovery_reader_reads_it(self):
        from packfs import PackFS
        ents = pack.plan(self.man, self.d, {'icon'}, 'ui_art_2x5\\')
        pack.build('ui_art_2x5_icon', ents, self.d, os.path.join(self.d, 'data'), log=lambda *a: None)
        fs = PackFS(os.path.join(self.d, 'data'))
        self.assertEqual(fs.read('ui_art_2x5\\ui\\a.tga'), b'A' * 100)

    def test_changed_input_stops_the_build_and_leaves_no_pack(self):
        ents = pack.plan(self.man, self.d, {'icon'}, 'p\\')
        open(os.path.join(self.d, 'out/a.tga'), 'wb').write(b'B' * 100)
        with self.assertRaises(RuntimeError):
            pack.build('t', ents, self.d, self.d, log=lambda *a: None)
        self.assertFalse(os.path.exists(os.path.join(self.d, 't.pack')))

    def test_a_flipped_byte_in_a_finished_pack_is_found(self):
        ents = pack.plan(self.man, self.d, {'icon'}, 'p\\')
        pack.build('t', ents, self.d, self.d, log=lambda *a: None)
        p = os.path.join(self.d, 't.pack')
        b = bytearray(open(p, 'rb').read())
        b[-1] ^= 1
        open(p, 'wb').write(bytes(b))
        with self.assertRaises(ValueError):
            pack.check_pack(p, ents)


def _rgba(w, h, alpha):
    y, x = np.mgrid[0:h, 0:w]
    img = np.dstack([x * 255 // max(1, w - 1), y * 255 // max(1, h - 1), (x + y) % 256, np.full((h, w), 255)]).astype(np.uint8)
    if alpha == 'binary':
        img[..., 3] = np.where((x - w / 2) ** 2 + (y - h / 2) ** 2 < (w / 3) ** 2, 255, 0)
    elif alpha == 'soft':
        img[..., 3] = np.clip(255 - np.hypot(x - w / 2, y - h / 2) * 255 / (w / 2), 0, 255)
    return img


@unittest.skipUnless(HAVE, 'numpy and Pillow are not installed here (upscale/requirements.txt)')
class Images(unittest.TestCase):
    def test_dds_header_round_trip_keeps_the_vanilla_header(self):
        for fmt in ('DXT1', 'DXT2', 'DXT3', 'DXT5', 'A8R8G8B8', 'R8G8B8'):
            img = _rgba(32, 16, 'soft')
            lv = resample.mip_chain(img, 3)
            van = dds.make_header(fmt, 32, 16, 3)
            data = [dds.encode_python(l, fmt) for l in lv]
            blob = dds.make_header(fmt, 80, 40, 7, van) + b''.join(dds.encode_python(l, fmt) for l in resample.mip_chain(_rgba(80, 40, 'soft'), 7))
            d = dds.read_dds(blob)
            self.assertEqual((d.fmt, d.width, d.height, d.mips), (fmt, 80, 40, 7))
            diff = dds.header_diff(van, blob[:128])
            self.assertTrue(set(diff) <= {'dwHeight', 'dwWidth', 'dwPitchOrLinearSize', 'dwMipMapCount'}, (fmt, diff))
            self.assertEqual(len(data), 3)

    def test_alpha_rules(self):
        a = _rgba(20, 20, 'binary')[..., 3]
        self.assertTrue(np.isin(np.unique(resample.resample_alpha(a, 50, 50, 'binary')), (0, 255)).all())
        self.assertTrue((resample.resample_alpha(np.full((8, 8), 255, np.uint8), 20, 20, 'none') == 255).all())
        s = _rgba(20, 20, 'soft')[..., 3]
        r = resample.resample_alpha(s, 50, 50, 'soft')
        self.assertGreater(len(np.unique(r)), 20)
        self.assertAlmostEqual(r.mean(), s.mean(), delta=2.0)

    def test_dilate_fills_transparent_texels_from_their_neighbours(self):
        img = np.zeros((8, 8, 4), np.uint8)
        img[..., :3] = 0
        img[2:6, 2:6] = (200, 100, 50, 255)
        out = resample.dilate_rgb(img)
        self.assertTrue((out[0, 0] == (200, 100, 50)).all())          # no black fringe
        self.assertTrue((out[3, 3] == (200, 100, 50)).all())          # valid texels untouched

    def test_mip_chain_counts_and_linear_light(self):
        self.assertEqual(dds.full_mips(160, 120), 8)
        img = np.zeros((4, 4, 4), np.uint8)
        img[..., 3] = 255
        img[::2, :, :3] = 255                                          # white and black rows
        lv = resample.mip_chain(img, 3)
        self.assertEqual([l.shape[:2] for l in lv], [(4, 4), (2, 2), (1, 1)])
        self.assertAlmostEqual(float(lv[1][0, 0, 0]), 255 * 0.5 ** (1 / 2.2), delta=1.5)      # linear-light average, brighter than 128
        self.assertGreater(lv[1][0, 0, 0], 128)

    def test_alpha_mip_is_a_plain_box(self):
        img = np.zeros((4, 4, 4), np.uint8)
        img[:, :2, 3] = 255
        lv = resample.mip_chain(img, 2)
        self.assertEqual(sorted(set(lv[1][..., 3].ravel().tolist())), [0, 255])

    def _items(self, d):
        items, files = [], {}
        for i, (kind, fmt, alpha, w, h) in enumerate([('tga', 'bgra8', 'binary', 20, 20), ('dds', 'DXT5', 'soft', 24, 16), ('dds', 'DXT1', 'none', 16, 16), ('tga', 'bgr8', 'none', 12, 10)]):
            img = _rgba(w, h, alpha)
            if kind == 'dds':
                n = dds.full_mips(w, h) if i == 1 else 1
                blob = dds.make_header(fmt, w, h, n) + b''.join(dds.encode_python(l, fmt) for l in resample.mip_chain(img, n))
            else:
                blob = imageio.encode_tga(img, with_alpha=(fmt == 'bgra8'))
            p = 'ui\\t%d.%s' % (i, kind)
            files[p] = blob
            items.append({'id': 'ui/t%d.%s' % (i, kind), 'path': p, 'role': 'icon', 'fmt': kind, 'w': w, 'h': h})
        items.append({'id': 'ui/big.tga', 'path': 'ui\\big.tga', 'role': 'icon', 'fmt': 'tga', 'w': 4000, 'h': 10})
        items.append({'id': 'ui/c.cur', 'path': 'ui\\c.cur', 'role': 'icon', 'fmt': 'cur', 'w': 0, 'h': 0})
        return items, files

    def _run(self, d, items, files, **kw):
        return batch.run(items, lambda it: files[it['path']], d, {'scale': 2.5}, {}, '', {'icon': {'model': 'lanczos'}},
                         log=lambda *a: None, model_override='lanczos', **kw)

    def test_run_resume_determinism_and_verify(self):
        d1, d2 = tempfile.mkdtemp(), tempfile.mkdtemp()
        items, files = self._items(d1)
        m1 = self._run(d1, items, files)
        st = {i: e['status'] for i, e in m1['entries'].items()}
        self.assertEqual(st['ui/big.tga'], 'skipped:already_large')
        self.assertEqual(st['ui/c.cur'], 'skipped:not_an_image_file')
        self.assertEqual([i for i, s in st.items() if s == 'done'], ['ui/t0.tga', 'ui/t1.dds', 'ui/t2.dds', 'ui/t3.tga'])
        e = m1['entries']['ui/t1.dds']
        self.assertEqual((e['out']['w'], e['out']['h'], e['out']['mips']), (60, 40, dds.full_mips(60, 40)))
        self.assertEqual(batch.verify(d1, log=lambda *a: None)['failed'], {})
        # resume: a second run changes nothing (same manifest bytes, no fresh work)
        before = open(os.path.join(d1, 'manifest.json'), 'rb').read()
        t_before = {i: os.path.getmtime(os.path.join(d1, e['out']['file'])) for i, e in m1['entries'].items() if e['status'] == 'done'}
        self._run(d1, items, files)
        self.assertEqual(open(os.path.join(d1, 'manifest.json'), 'rb').read(), before)
        self.assertEqual(t_before, {i: os.path.getmtime(os.path.join(d1, e['out']['file'])) for i, e in m1['entries'].items() if e['status'] == 'done'})
        # determinism: a second work folder gets byte-identical outputs
        m2 = self._run(d2, items, files)
        for i, e in m1['entries'].items():
            if e['status'] == 'done':
                self.assertEqual(e['out']['sha256'], m2['entries'][i]['out']['sha256'], i)

    def test_verify_lists_a_tampered_asset(self):
        d = tempfile.mkdtemp()
        items, files = self._items(d)
        m = self._run(d, items, files)
        p = os.path.join(d, m['entries']['ui/t0.tga']['out']['file'])
        b = bytearray(open(p, 'rb').read())
        b[-3] ^= 0xFF
        open(p, 'wb').write(bytes(b))
        bad = batch.verify(d, log=lambda *a: None)['failed']
        self.assertIn('ui/t0.tga', bad)
        self.assertTrue(any('sha256' in x for x in bad['ui/t0.tga']))

    def test_verify_catches_a_wrong_size_and_a_flat_output(self):
        d = tempfile.mkdtemp()
        items, files = self._items(d)
        m = self._run(d, items, files)
        e = m['entries']['ui/t3.tga']
        flat = imageio.encode_tga(np.full((25, 30, 4), 90, np.uint8), with_alpha=False)
        p = os.path.join(d, e['out']['file'])
        open(p, 'wb').write(flat)
        e['out']['sha256'] = hashlib.sha256(flat).hexdigest()
        self.assertTrue(any('flat' in x for x in batch.verify_entry(e, d)))
        wrong = imageio.encode_tga(_rgba(20, 20, 'none'), with_alpha=False)
        open(p, 'wb').write(wrong)
        e['out']['sha256'] = hashlib.sha256(wrong).hexdigest()
        self.assertTrue(any('size' in x for x in batch.verify_entry(e, d)))

    def test_dxt3_decode_matches_what_was_encoded(self):
        img = _rgba(16, 16, 'soft')
        d = dds.decode_level(dds.encode_python(img, 'DXT3'), 'DXT3', 16, 16)
        self.assertLess(np.abs(d[..., 3].astype(int) - img[..., 3]).max(), 9)     # 4-bit alpha: steps of 17

    def test_dxt2_is_premultiplied_dxt3(self):
        img = _rgba(16, 16, 'soft')
        blob = dds.encode_python(img, 'DXT2')
        raw = dds.decode_level(blob, 'DXT3', 16, 16).astype(int)             # the stored colour is premultiplied
        pre = np.round(img[..., :3].astype(float) * img[..., 3:4] / 255.0)
        self.assertLess(np.abs(raw[..., :3] - pre).mean(), 6)
        d = dds.decode_level(blob, 'DXT2', 16, 16).astype(int)               # decoded back to straight alpha
        vis = img[..., 3] >= 128
        self.assertLess(np.abs(d[..., :3] - img[..., :3])[vis].mean(), 8)
        self.assertLess(np.abs(d[..., 3] - img[..., 3]).max(), 9)


if __name__ == '__main__':
    unittest.main()
