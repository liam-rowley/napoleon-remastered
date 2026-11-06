"""J99: the vanilla component inventory and the layout compositor."""
import gzip
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VANILLA = ROOT / 'uikit' / 'napoleon' / 'vanilla'
sys.path.insert(0, str(VANILLA))
import inventory  # noqa: E402

HAVE_PIL = importlib.util.find_spec('PIL') is not None
if HAVE_PIL:
    import gallery
    from PIL import Image


def game_present():
    games = json.loads((ROOT / 'discovery' / 'napoleon' / 'games.json').read_text(encoding='utf-8'))
    return (Path(games['napoleon']['root']) / 'data' / 'data.pack').exists()


class Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kinds = inventory.build()
        cls.summary = json.loads((ROOT / 'discovery' / 'ui' / 'summary.json').read_text(encoding='utf-8'))['counts']

    def test_committed_file_is_current(self):
        self.assertEqual((VANILLA / 'components.json').read_text(encoding='utf-8'), inventory.dumps(self.kinds))

    def test_rebuild_is_identical(self):
        self.assertEqual(inventory.dumps(self.kinds), inventory.dumps(inventory.build()))

    def test_ids_are_unique(self):
        ids = [k['id'] for k in self.kinds]
        self.assertEqual(len(ids), len(set(ids)))

    def test_frame_groups_agree_with_the_atlas_summary(self):
        self.assertEqual(sum(k['instances'] for k in self.kinds if k['kind'] == 'frame'), self.summary['frame_groups'])

    def test_every_named_template_has_a_kind(self):
        named = set()
        for ctx in inventory.CONTEXTS:
            with gzip.open(ROOT / 'discovery' / 'ui' / f'{ctx}.json.gz') as f:
                for rec in json.load(f)['surfaces'].values():
                    named.update(t for t in rec.get('templates_used', []) if t.startswith(('script:', 'template:')))
        self.assertEqual(named, {k['id'] for k in self.kinds if k['kind'] == 'template'})

    def test_every_button_state_asset_is_in_a_family(self):
        rows = inventory.jsonl(ROOT / 'registries' / 'assets.jsonl')
        want = {r['id'] for r in rows if r.get('role') == 'button_state'}
        got = {a for k in self.kinds if k['kind'] == 'button' for s in k['states'] for a in s['assets']}
        self.assertEqual(want, got)

    def test_split_state_takes_the_whole_state(self):
        for stem, want in (('button_advice_depress', ('button_advice', 'depress')), ('button_left_down_off', ('button_left', 'down_off')),
                           ('x_unselected_roll', ('x', 'unselected_roll')), ('x_selected_depress', ('x', 'selected_depress')),
                           ('x_unselect_depress_rolloff', ('x', 'unselect_depress_rolloff')), ('textbutton_center_up_roll', ('textbutton_center', 'up_roll')),
                           ('table_head_roll_down', ('table_head', 'roll_down')), ('x_ok_down_selected', ('x_ok', 'down_selected')),
                           ('table_header_selected_off', ('table_header', 'selected_off')), ('button_shot_normal_inactive', ('button_shot_normal', 'inactive')),
                           ('button_large_ok', ('button_large_ok', 'default'))):
            self.assertEqual(inventory.split_state(stem), want)

    def test_up_and_down_on_an_arrow_are_its_direction(self):
        self.assertEqual(inventory.split_state('varrow_up_inactive'), ('varrow_up', 'inactive'))
        self.assertEqual(inventory.split_state('varrow_up'), ('varrow_up', 'default'))
        self.assertEqual(inventory.split_state('arrow_down_roll'), ('arrow_down', 'roll'))
        self.assertEqual(inventory.split_state('popularity_down'), ('popularity_down', 'default'))

    def test_no_family_is_a_sibling_plus_a_state(self):
        """One family's states stay on one card: no family's stem is another's plus a state word, or a compound state's start (J99 round 1, S1)."""
        fams = {k['id'] for k in self.kinds if k['kind'] == 'button'}
        split = []
        for f in sorted(fams):
            d, stem = f.rsplit('/', 1)
            base, state = inventory.split_state(stem)
            if state != 'default' and stem != 'button_shot_normal':    # the normal shot, beside grape and chain: a name, not a state
                split.append(f)
            words = stem.split('_')
            for i in range(1, len(words)):
                head, tail = '_'.join(words[:i]), '_'.join(words[i:])
                if f'{d}/{head}' in fams and inventory.split_state(f'x_{tail}')[1] != 'default' and not inventory.ARROW.search(head):
                    split.append(f)
        self.assertEqual(split, [])

    def test_the_states_of_a_family_share_its_card(self):
        kinds = {k['id']: k for k in self.kinds}
        names = {s['name'] for s in kinds['button:ui/campaign_ui/skins/button_advice']['states']}
        self.assertEqual(names, {'depress', 'inactive', 'normal', 'roll'})
        self.assertLessEqual({'default', 'down', 'down_off', 'roll'}, {s['name'] for s in kinds['button:ui/frontend_ui/skins/button_left']['states']})

    def test_order_is_by_use_and_the_scrollbar_leads(self):
        uses = [k['use_count'] for k in self.kinds]
        self.assertEqual(uses, sorted(uses, reverse=True))
        self.assertEqual([k['id'] for k in self.kinds[:2]], ['script:vslider_handle', 'script:vslider'])

    def test_a_kind_is_mapped_or_a_gap(self):
        self.assertTrue(all(k['library'] for k in self.kinds))
        self.assertFalse([k['id'] for k in self.kinds if k['library'] == 'gap' and k.get('uncertain')])

    def test_no_text_in_the_committed_file(self):
        """J7: ids, keys, sizes and counts only."""
        allowed = {'id', 'kind', 'source', 'sizes', 'sizes_total', 'states', 'use_count', 'instances', 'surfaces', 'ui_elements', 'sample', 'library', 'uncertain', 'insets'}
        for k in self.kinds:
            self.assertLessEqual(set(k), allowed)
            for s in k['states']:
                self.assertEqual(set(s), {'name', 'assets'})


@unittest.skipUnless(HAVE_PIL, 'needs Pillow')
class Compositor(unittest.TestCase):
    def test_tail_flags(self):
        self.assertEqual(gallery.tail_flags(bytes.fromhex('010000050000000101')), (True, False, False))
        self.assertEqual(gallery.tail_flags(bytes.fromhex('000101090000000000')), (False, True, True))
        self.assertEqual(gallery.tail_flags(b''), (False, False, False))

    def test_art_key(self):
        self.assertEqual(gallery.art_key('data\\UI\\Campaign UI\\Skins\\x.tga'), 'ui\\campaign ui\\skins\\x.tga')
        self.assertEqual(gallery.art_key('C:\\Empire\\data\\UI\\Skins\\x.tga'), 'ui\\skins\\x.tga')
        self.assertIsNone(gallery.art_key('X:\\Art - Empire\\scroll\\x.tga'))

    def test_visible_is_flag_byte_three(self):
        self.assertTrue(gallery.visible({'flags': bytes.fromhex('00000001000000')}))
        self.assertFalse(gallery.visible({'flags': bytes.fromhex('01010000000000')}))

    def test_default_state(self):
        a, b = {'id': 1, 'name': 'a'}, {'id': 2, 'name': 'b'}
        self.assertIs(gallery.default_state({'states': [a, b], 'state_ref': 2}), b)
        self.assertIs(gallery.default_state({'states': [a, b], 'default_state': 'b'}), b)
        self.assertIs(gallery.default_state({'states': [a, b]}), a)
        self.assertIsNone(gallery.default_state({'states': []}))

    def test_fit_tiles_or_stretches(self):
        src = Image.new('RGBA', (2, 2), (255, 0, 0, 255))
        src.putpixel((0, 0), (0, 0, 255, 255))
        tiled = gallery.fit(src, 4, 4, True)
        self.assertEqual(tiled.getpixel((2, 2)), (0, 0, 255, 255))
        self.assertEqual(gallery.fit(src, 4, 4, False).size, (4, 4))

    def test_tint_multiplies_argb(self):
        px = gallery.tint(Image.new('RGBA', (1, 1), (255, 255, 255, 255)), 0x80ff0000).getpixel((0, 0))
        self.assertEqual(px, (255, 0, 0, 128))

    def test_wrap(self):
        self.assertEqual(gallery.wrap('aa bb cc', 5, len), ['aa bb', 'cc'])

    def test_sheets_never_overlap(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            s = gallery.Sheets(d, 't', 32, 32)
            rects = [s.add(Image.new('RGBA', (10, 10))) for _ in range(12)]
            sheets = s.close()
        self.assertGreater(len(sheets), 1)
        seen = {(r[0], r[1], r[2]) for r in rects}
        self.assertEqual(len(seen), len(rects))

    def test_twin_screen_is_current(self):
        self.assertEqual((ROOT / 'viewer' / 'napoleon' / 'vanilla_ref' / 'vanilla_ref.rml').read_text(encoding='utf-8'), gallery.twin_rml())

    def test_every_mapped_class_has_a_twin(self):
        kinds = json.loads((VANILLA / 'components.json').read_text(encoding='utf-8'))
        twins = {c for c, _, _ in gallery.twin_cells()}
        self.assertEqual({k['library'] for k in kinds} - {'gap'} - twins, set())

    @unittest.skipUnless(HAVE_PIL and game_present(), 'needs the game folder')
    def test_composites_are_deterministic(self):
        surf = gallery.surfaces()
        for path in ('campaign ui/entity_lists', 'frontend ui/single_player'):
            shas = [hashlib.sha256(gallery.compose(gallery.Game(), path, surf[path])[0].tobytes()).hexdigest() for _ in range(2)]
            self.assertEqual(shas[0], shas[1], path)


if __name__ == '__main__':
    unittest.main()
