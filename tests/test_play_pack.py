"""Host tests: play packs of the UI art upscaler (J53): entries at the vanilla paths, held-back outputs, the vanilla-path guard.

Standard library only (no GPU, no game): a synthetic manifest and work folder, packs built by upscale/core/pack.py through the
`wsc upscale pack --play` code path (upscale/napoleon/cli.py play_packs), re-read by the J7 reader (core/discovery/packfs.py).
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.join(ROOT, 'upscale', 'core'), os.path.join(ROOT, 'core', 'discovery'), os.path.join(ROOT, 'upscale', 'napoleon')]

import pack  # noqa: E402
import cli  # noqa: E402

QUIET = lambda *a: None  # noqa: E731


def entry(path, role, rel, body, w, h, fmt):
    return {'status': 'done', 'role': role, 'path': path,
            'out': {'file': rel, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(), 'w': w, 'h': h, 'fmt': fmt}}


class PlayPack(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        rows = [   # (id, vanilla path, role, body, w, h, fmt)
            ('a', 'ui\\a.tga', 'icon', b'A' * 100, 160, 80, 'bgra8'),
            ('c', 'ui\\b\\c.dds', 'icon', b'C' * 40, 320, 320, 'DXT5'),
            ('odd', 'ui\\odd.dds', 'icon', b'O' * 30, 1150, 380, 'DXT3'),        # 1150 is not a multiple of 4
            ('big', 'ui\\big.tga', 'icon', b'G' * 50, 4800, 3000, 'bgr8'),      # over 4096 px on a side
            ('f', 'ui\\flag.tga', 'flag', b'F' * 20, 80, 80, 'bgra8'),
        ]
        self.man = {'entries': {}}
        for i, path, role, body, w, h, fmt in rows:
            rel = 'out/' + path.replace('\\', '/')
            os.makedirs(os.path.dirname(os.path.join(self.d, rel)), exist_ok=True)
            with open(os.path.join(self.d, rel), 'wb') as f:
                f.write(body)
            self.man['entries'][i] = entry(path, role, rel, body, w, h, fmt)
        self.man['entries']['s'] = {'status': 'skipped:under_2x', 'role': 'icon', 'path': 'ui\\s.tga'}
        self.vanilla = {r[1] for r in rows} | {'ui\\s.tga'}
        self.cfg = json.load(open(os.path.join(ROOT, 'upscale', 'napoleon', 'config.json'), encoding='utf-8'))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_entries_sit_at_the_vanilla_paths_and_unproven_outputs_are_held_back(self):
        ents, held = pack.play_plan(self.man, self.d, {'icon'}, self.vanilla)
        self.assertEqual([e[0] for e in ents], ['ui\\a.tga', 'ui\\b\\c.dds'])          # empty prefix: the vanilla path itself
        self.assertEqual({h['path']: h['reason'].split()[0] for h in held},
                         {'ui\\odd.dds': 'dxt_not_multiple_of_4', 'ui\\big.tga': 'over_4096_px'})

    def test_held_back_rules(self):
        self.assertEqual(pack.held_back_reason({'w': 1152, 'h': 382, 'fmt': 'DXT1'}), 'dxt_not_multiple_of_4 (1152x382 DXT1)')
        self.assertEqual(pack.held_back_reason({'w': 1152, 'h': 380, 'fmt': 'DXT1'}), '')
        self.assertEqual(pack.held_back_reason({'w': 1150, 'h': 380, 'fmt': 'bgra8'}), '')      # only DXT needs blocks of 4
        self.assertEqual(pack.held_back_reason({'w': 4096, 'h': 4096, 'fmt': 'DXT1'}), '')      # 4096 itself is in
        self.assertTrue(pack.held_back_reason({'w': 4097, 'h': 8, 'fmt': 'bgra8'}).startswith('over_4096_px'))

    def test_a_path_that_is_not_vanilla_is_refused(self):
        with self.assertRaises(ValueError) as c:
            pack.play_plan(self.man, self.d, {'icon'}, self.vanilla - {'ui\\a.tga'})
        self.assertIn('ui\\a.tga', str(c.exception))

    def test_cli_builds_one_pack_per_role_with_held_back_in_its_json(self):
        reg = os.path.join(self.d, 'assets.jsonl')
        with open(reg, 'w', encoding='utf-8') as f:
            f.write('\n'.join(json.dumps({'id': p, 'path': p}) for p in sorted(self.vanilla)) + '\n')
        out = os.path.join(self.d, 'packs_play')
        ok = {i for i, e in self.man['entries'].items() if e['status'] == 'done'}
        self.assertEqual(cli.play_packs(self.man, self.d, ['icon', 'flag'], ok, ['credit'], self.cfg, out, registry=reg, log=QUIET), 0)
        m = json.load(open(os.path.join(out, 'ui_art_play_icon.pack.json'), encoding='utf-8'))
        self.assertEqual((m['entries'], m['prefix'], m['role'], len(m['held_back'])), (2, '', 'icon', 2))
        self.assertTrue(os.path.exists(os.path.join(out, 'ui_art_play_flag.pack')))
        self.assertEqual(pack.check_pack(os.path.join(out, 'ui_art_play_icon.pack'), pack.play_plan(self.man, self.d, {'icon'}, self.vanilla, ok)[0]), m['sha256'])
        with open(reg, 'w', encoding='utf-8') as f:     # a registry without the icon paths: refused, exit 1
            f.write(json.dumps({'id': 'ui\\flag.tga', 'path': 'ui\\flag.tga'}) + '\n')
        self.assertEqual(cli.play_packs(self.man, self.d, ['icon'], ok, [], self.cfg, os.path.join(self.d, 'p2'), registry=reg, log=QUIET), 1)
        self.assertFalse(os.path.exists(os.path.join(self.d, 'p2', 'ui_art_play_icon.pack')))

    def test_the_j7_reader_reads_the_vanilla_paths_and_the_play_pack_wins(self):
        from packfs import PackFS, write_pack
        data = os.path.join(self.d, 'data')
        os.makedirs(data)
        write_pack(os.path.join(data, 'data.pack'), {'ui\\a.tga': b'vanilla', 'ui\\odd.dds': b'vanilla odd'})
        write_pack(os.path.join(data, 'media.pack'), {'movies\\x.bik': b'm'}, pack_type=4)
        ents, _ = pack.play_plan(self.man, self.d, {'icon'}, self.vanilla)
        pack.build(self.cfg['play_pack_name'].format(role='icon'), ents, self.d, data, log=QUIET)
        fs = PackFS(data)
        self.assertEqual(fs.packs[-1], 'ui_art_play_icon.pack')       # type 4, then name: after media.pack (napoleon.assets.pack_order)
        self.assertEqual(fs.read('ui\\a.tga'), b'A' * 100)
        self.assertEqual(fs.read('ui\\odd.dds'), b'vanilla odd')       # held back: the vanilla file stays

    def test_a_rebuild_is_byte_identical(self):
        ents, held = pack.play_plan(self.man, self.d, {'icon'}, self.vanilla)
        a = pack.build('ui_art_play_icon', ents, self.d, os.path.join(self.d, 'one'), log=QUIET, extra={'held_back': held})
        b = pack.build('ui_art_play_icon', ents, self.d, os.path.join(self.d, 'two'), log=QUIET, extra={'held_back': held})
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertEqual(open(os.path.join(self.d, 'one', 'ui_art_play_icon.pack'), 'rb').read(),
                         open(os.path.join(self.d, 'two', 'ui_art_play_icon.pack'), 'rb').read())

    def test_the_2x5_packs_keep_their_plan_signature(self):
        """the existing ui_art_2x5 packs on the PC are not rebuilt by this change: the signature without `extra` is the old one"""
        ents = pack.plan(self.man, self.d, {'icon'}, self.cfg['pack_prefix'])
        m = pack.build('t', ents, self.d, self.d, log=QUIET)
        self.assertEqual(m['plan'], hashlib.sha256(json.dumps(ents).encode()).hexdigest())
        self.assertNotIn('held_back', m)


if __name__ == '__main__':
    unittest.main()
