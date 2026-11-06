"""Host tests of the UI art upscaler (J36): synthetic images, no GPU, no game.

The size rule, status mapping and pack writer are standard library and always run. The image tests (DDS header round trip,
alpha rules, mips, manifest and resume, determinism, verify) need numpy and Pillow (upscale/requirements.txt) and are skipped
where they are missing (CI installs them from upscale/requirements-ci.txt since J79). Bootstrap: the pinned downloads of setup_env.cmd.
"""
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.join(ROOT, 'upscale', 'core'), os.path.join(ROOT, 'core', 'discovery')]

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

    def test_dxt_targets_round_up_to_a_multiple_of_4(self):
        self.assertEqual(rules.dxt_target_size(460, 152, 'dds dxt3'), (1152, 380))
        self.assertEqual(rules.dxt_target_size(232, 284, 'DXT1'), (580, 712))
        self.assertEqual(rules.dxt_target_size(64, 48, 'dds dxt5'), (160, 120))      # already aligned
        self.assertEqual(rules.dxt_target_size(460, 152, 'tga bgra8'), (1150, 380))  # not a DXT: the plain rule
        self.assertEqual(rules.dxt_target_size(460, 152, 'dds bgra8'), (1150, 380))
        self.assertEqual(rules.dxt_target_size(460, 152, ''), (1150, 380))
        self.assertEqual(rules.target_size(460, 152), (1150, 380))                   # target_size stays the plain 2.5x
        self.assertEqual(rules.decide(460, 152, 'dds dxt3', {}), ('run', (1152, 380)))
        self.assertEqual(rules.decide(460, 152, 'dds bgr8', {}), ('run', (1150, 380)))

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


@unittest.skipUnless(HAVE, 'numpy and Pillow are not installed here (upscale/requirements.txt)')
class Guards(unittest.TestCase):
    """J96: the DXT size rule through run and verify, the DXT2 invariant, the free-disk guard, the run log"""

    def _dds(self, fmt, w=10, h=12, alpha='soft', name='a'):
        img = _rgba(w, h, alpha)
        blob = dds.make_header(fmt, w, h, 1) + dds.encode_python(img, fmt)
        p = 'ui\\%s.dds' % name
        return {'id': 'ui/%s.dds' % name, 'path': p, 'role': 'icon', 'fmt': 'dds ' + fmt.lower(), 'w': w, 'h': h}, {p: blob}

    def _run(self, d, items, files, **kw):
        return batch.run(items, lambda it: files[it['path']], d, {'scale': 2.5}, {}, '', {'icon': {'model': 'lanczos'}},
                         log=lambda *a: None, model_override='lanczos', **kw)

    def _put(self, d, e, blob):
        with open(os.path.join(d, e['out']['file']), 'wb') as f:
            f.write(blob)
        e['out']['sha256'] = hashlib.sha256(blob).hexdigest()

    def test_verify_takes_a_rounded_dxt_output_and_refuses_a_plain_one(self):
        d = tempfile.mkdtemp()
        it, files = self._dds('DXT5')
        e = self._run(d, [it], files)['entries'][it['id']]
        self.assertEqual((e['out']['w'], e['out']['h']), (28, 32))                   # 10x12 -> 25x30 -> 28x32
        self.assertEqual(dds.read_dds(os.path.join(d, e['out']['file'])).dims(), (28, 32))
        self.assertEqual(batch.verify_entry(e, d), [])
        e['out']['w'], e['out']['h'] = 25, 30                                        # a J51 manifest row: the plain 2.5x
        self.assertTrue(any('size rule' in x for x in batch.verify_entry(e, d)))

    def test_a_non_dxt_output_keeps_the_plain_size(self):
        d = tempfile.mkdtemp()
        img = _rgba(10, 12, 'none')
        files = {'ui\\t.tga': imageio.encode_tga(img, with_alpha=False)}
        it = {'id': 'ui/t.tga', 'path': 'ui\\t.tga', 'role': 'icon', 'fmt': 'tga bgr8', 'w': 10, 'h': 12}
        e = self._run(d, [it], files)['entries'][it['id']]
        self.assertEqual((e['out']['w'], e['out']['h']), (25, 30))
        self.assertEqual(batch.verify_entry(e, d), [])

    def test_resume_redoes_an_output_at_the_old_plain_size(self):
        d = tempfile.mkdtemp()
        it, files = self._dds('DXT3')
        with mock.patch.object(rules, 'dxt_target_size', lambda w, h, fmt, scale=2.5: rules.target_size(w, h, scale)):
            old = self._run(d, [it], files)['entries'][it['id']]
        self.assertEqual((old['out']['w'], old['out']['h']), (25, 30))
        new = self._run(d, [it], files)['entries'][it['id']]
        self.assertEqual((new['out']['w'], new['out']['h']), (28, 32))
        self.assertEqual(batch.verify_entry(new, d), [])

    def test_verify_checks_the_premultiplied_invariant_of_dxt2_only(self):
        d = tempfile.mkdtemp()
        it, files = self._dds('DXT2', 64, 64)                                        # smooth, like the one real DXT2 (a harsh gradient in a 4x4 block can pass any tolerance)
        e = self._run(d, [it], files)['entries'][it['id']]
        self.assertEqual(e['src']['fmt'], 'DXT2')
        self.assertEqual(batch.verify_entry(e, d), [])
        w, h, n = e['out']['w'], e['out']['h'], e['out']['mips']
        white = np.full((h, w, 4), 255, np.uint8)
        white[..., 3] = 0                                                            # colour far above alpha: not premultiplied
        data = b''.join(dds.encode_python(lv, 'DXT3') for lv in [white[:max(1, h >> k), :max(1, w >> k)] for k in range(n)])
        self._put(d, e, dds.make_header('DXT2', w, h, n) + data)
        self.assertTrue(any('premultiplied' in x for x in batch.verify_entry(e, d)))
        e['src']['fmt'] = 'DXT3'                                                     # the same bytes as a DXT3: not this check's business
        self._put(d, e, dds.make_header('DXT3', w, h, n) + data)
        self.assertFalse(any('premultiplied' in x for x in batch.verify_entry(e, d)))

    def test_an_honest_alpha_ramp_stays_inside_the_tolerance(self):
        ramp = np.full((256, 256, 4), 255, np.uint8)
        ramp[..., 3] = np.arange(256, dtype=np.uint8)[None, :]
        blob = dds.encode_python(ramp, 'DXT2')
        self.assertEqual(dds.premultiplied_excess(blob, 256, 256, batch.PREMULT_TOL), 0)
        self.assertGreater(dds.premultiplied_excess(blob, 256, 256, 8), 0)           # why the tolerance is not 8

    def test_estimate_bytes(self):
        self.assertEqual(batch.estimate_bytes('dds dxt3', 8, 8), 128 + 64 + 16 + 16 + 16)
        self.assertEqual(batch.estimate_bytes('dds dxt1', 8, 8), 128 + 32 + 8 + 8 + 8)
        self.assertEqual(batch.estimate_bytes('dds bgra8', 2, 2), 128 + 16 + 4)
        self.assertEqual(batch.estimate_bytes('dds bgr8', 2, 2), 128 + 12 + 3)
        self.assertEqual(batch.estimate_bytes('dds ?', 2, 2), 128 + 16 + 4)
        self.assertEqual(batch.estimate_bytes('tga bgra8_rle', 10, 10), 18 + 400)
        self.assertEqual(batch.estimate_bytes('tga bgr8_rle', 10, 10), 18 + 300)
        self.assertEqual(batch.estimate_bytes('jpg ycc8', 1000, 1000), 259000)

    def test_estimate_matches_a_real_output_and_a_resume_needs_no_new_bytes(self):
        d = tempfile.mkdtemp()
        it, files = self._dds('DXT3')
        per, rows = batch.plan([it], {'icon': {}}, {'scale': 2.5}, d)
        self.assertEqual(per['icon']['bytes'], rows[0]['new_bytes'])
        e = self._run(d, [it], files)['entries'][it['id']]
        self.assertEqual(rows[0]['bytes'], e['out']['bytes'])
        self.assertEqual(batch.plan([it], {'icon': {}}, {'scale': 2.5}, d)[1][0]['new_bytes'], 0)

    def test_disk_floor(self):
        rows = [{'bytes': 100, 'new_bytes': 100}]
        with mock.patch.object(batch, 'disk_usage', lambda p: (1000, 0, 300)):
            disk = batch.disk_after(rows, 'w')
            self.assertEqual(disk['free_pct_after'], 20.0)
            self.assertEqual(batch.disk_refusal(disk), '')                           # exactly the floor is allowed
        with mock.patch.object(batch, 'disk_usage', lambda p: (1000, 0, 299)):
            line = batch.disk_refusal(batch.disk_after(rows, 'w'))
            self.assertIn('19.9', line)
            self.assertIn('--force-disk', line)
            self.assertNotIn('\n', line)

    def _cli(self):
        sys.path.insert(0, os.path.join(ROOT, 'upscale', 'napoleon'))
        import cli
        return cli

    def test_cli_run_refuses_below_the_floor_and_force_disk_goes_on(self):
        cli = self._cli()
        d = tempfile.mkdtemp()
        args = ['run', '--work', d, '--roles', 'icon']
        with mock.patch.object(batch, 'disk_usage', lambda p: (10 ** 12, 0, 10 ** 6)), \
                mock.patch.object(batch, 'run') as run, mock.patch.object(cli, '_packfs') as fs, mock.patch('builtins.print') as out:
            self.assertEqual(cli.main(args), 2)
            run.assert_not_called()
            fs.assert_not_called()
            self.assertEqual(out.call_count, 1)
            self.assertIn('refused', out.call_args[0][0])
            self.assertEqual(cli.main(args + ['--force-disk']), 0)
            self.assertIs(run.call_args[1]['force_disk'], True)

    def test_cli_plan_reports_bytes_and_disk(self):
        cli = self._cli()
        d = tempfile.mkdtemp()
        with mock.patch.object(batch, 'disk_usage', lambda p: (10 ** 12, 0, 5 * 10 ** 11)), mock.patch('builtins.print'):
            self.assertEqual(cli.main(['plan', '--work', d, '--roles', 'icon']), 0)
        res = json.load(open(os.path.join(d, 'plan.json')))
        self.assertGreater(res['roles']['icon']['bytes'], 0)
        self.assertEqual(res['disk']['bytes'], res['roles']['icon']['bytes'])
        self.assertEqual(res['disk']['free'], 5 * 10 ** 11)
        self.assertEqual(res['disk']['new_bytes'], res['disk']['bytes'])             # an empty work folder: every output is new

    def test_every_run_leaves_a_line_in_the_run_log(self):
        d = tempfile.mkdtemp()
        it, files = self._dds('DXT3')
        self._run(d, [it], files)
        self._run(d, [it], files, force_disk=True)
        lines = open(os.path.join(d, 'run.log'), encoding='utf-8').read().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ roles=icon done=1 fresh=1 skipped=0 failed=0 seconds=[\d.]+ force_disk=0$')
        self.assertRegex(lines[1], r' done=1 fresh=0 .* force_disk=1$')


class Bootstrap(unittest.TestCase):
    """upscale/pc/bootstrap.json pins setup_env.cmd's downloads (J79): versioned url, sha256 and size; the script reads it and installs hash-locked"""

    def test_pins_shape(self):
        with open(os.path.join(ROOT, 'upscale', 'pc', 'bootstrap.json'), encoding='utf-8') as f:
            b = json.load(f)
        self.assertEqual(sorted(k for k in b if not k.startswith('_')), ['get_pip', 'python_embed'])
        for k in ('get_pip', 'python_embed'):
            e = b[k]
            self.assertRegex(e['sha256'], r'^[0-9a-f]{64}$', k)
            self.assertIsInstance(e['size'], int)
            self.assertTrue(e['url'].startswith('https://') and e['url'].endswith('/' + e['file']), k)
        self.assertIn('/' + b['python_embed']['version'] + '/', b['python_embed']['url'])
        self.assertRegex(b['get_pip']['url'], r'^https://raw\.githubusercontent\.com/pypa/get-pip/[0-9a-f]{40}/public/get-pip\.py$')   # commit-pinned
        self.assertNotIn('bootstrap.pypa.io/get-pip.py', b['get_pip']['url'])   # that url moves with every pip release

    def test_setup_env_uses_the_pins(self):
        with open(os.path.join(ROOT, 'upscale', 'pc', 'setup_env.cmd'), encoding='ascii') as f:
            s = f.read()
        self.assertIn('bootstrap.json', s)
        self.assertIn('call :fetch python_embed', s)
        self.assertIn('call :fetch get_pip', s)
        self.assertIn('Get-FileHash -Algorithm SHA256', s)
        self.assertIn(r'--require-hashes -r "%REPO%\upscale\requirements-ci.txt"', s)
        self.assertNotIn('https://', s.replace('https://download.pytorch.org/whl/cu130', ''))   # every other url comes from bootstrap.json

    def test_ci_requirements_are_hash_locked_and_match_the_pins(self):
        import re
        with open(os.path.join(ROOT, 'upscale', 'requirements-ci.txt'), encoding='utf-8') as f:
            text = f.read()
        reqs = re.findall(r'^([A-Za-z0-9_.-]+)==(\S+)((?:\s*\\\n\s*--hash=sha256:[0-9a-f]{64})+)', text, re.M)
        names = {n.lower(): v for n, v, _ in reqs}
        self.assertEqual(set(names), {'freetype-py', 'uharfbuzz', 'numpy', 'pillow', 'capstone', 'pefile'})
        self.assertEqual(len([l for l in text.splitlines() if l.strip() and not l.lstrip().startswith(('#', '--hash'))]), len(reqs))   # no unhashed line
        with open(os.path.join(ROOT, 'upscale', 'requirements.txt'), encoding='utf-8') as f:
            pins = dict(re.findall(r'^([A-Za-z0-9_.-]+)==([^\s#]+)', f.read(), re.M))
        for n in ('freetype-py', 'uharfbuzz', 'numpy', 'pillow'):
            self.assertEqual(names[n], pins[n], n)
        sys.path.insert(0, os.path.join(ROOT, 'core', 'discovery'))
        import re_env
        for spec in re_env.PINS:
            n, v = spec.split('==')
            self.assertEqual(names[n], v, n)


if __name__ == '__main__':
    unittest.main()
