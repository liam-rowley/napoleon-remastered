"""Host tests: this mod's own packs in data\\ are never indexed as game packs (J50, J36 open question 6).

Every role pack the UI art upscaler can build (upscale/napoleon/config.json pack_name over its roles) must be in
discovery/napoleon/games.json napoleon.mod_packs, and a PackFS built from that file must leave such a pack out.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'discovery', 'core'))

from packfs import PackFS, write_pack  # noqa: E402


def load(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return json.load(f)


class ModPacks(unittest.TestCase):
    def setUp(self):
        self.games = load('discovery/napoleon/games.json')
        self.cfg = load('upscale/napoleon/config.json')

    def role_packs(self):
        return [self.cfg['pack_name'].format(role=r) + '.pack' for r in self.cfg['roles']]

    def test_every_upscaler_pack_is_skipped(self):
        skip = set(self.games['napoleon'].get('mod_packs', ()))
        missing = [p for p in self.role_packs() if p not in skip]
        self.assertEqual(missing, [], 'add these to discovery/napoleon/games.json napoleon.mod_packs')

    def test_packfs_leaves_a_mod_pack_out(self):
        with tempfile.TemporaryDirectory() as d:
            data = os.path.join(d, 'data')
            os.makedirs(data)
            write_pack(os.path.join(data, 'data.pack'), {'ui\\a.tga': b'vanilla'})
            mod = self.role_packs()[0]
            write_pack(os.path.join(data, mod), {self.cfg['pack_prefix'] + 'ui\\a.tga': b'upscaled', 'ui\\a.tga': b'override'}, pack_type=4)
            games = {'napoleon': dict(self.games['napoleon'], root=d)}
            fs = PackFS.from_games(games, 'napoleon')
            self.assertNotIn(mod, fs.packs)
            self.assertEqual(fs.read('ui\\a.tga'), b'vanilla')


if __name__ == '__main__':
    unittest.main()
