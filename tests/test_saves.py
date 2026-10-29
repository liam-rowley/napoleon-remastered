"""Host tests for the J14 save tools (saves/core ESF codec, diff, map walker; saves/napoleon map, recipes, staging) on synthetic files."""
import contextlib
import io
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'saves', 'core'))
sys.path.insert(0, os.path.join(ROOT, 'saves', 'napoleon'))
sys.path.insert(0, os.path.join(ROOT, 'saves', 'napoleon', 'recipes'))

import esf_diff  # noqa: E402
import esf_dump  # noqa: E402
import esf_edit as E  # noqa: E402
import esf_map  # noqa: E402
import save_map  # noqa: E402
import stage_save  # noqa: E402
from _common import SaveEdit  # noqa: E402
import agent_into_settlement  # noqa: E402
import tax_rates  # noqa: E402

# ---- an independent encoder: absolute offsets computed here, not by esf_edit
SCALARS = [(0x01, b'\x01'), (0x02, struct.pack('<b', -3)), (0x03, struct.pack('<h', -300)), (0x04, struct.pack('<i', -5)),
           (0x05, struct.pack('<q', -1 << 40)), (0x06, b'\xfe'), (0x07, struct.pack('<H', 65000)), (0x08, struct.pack('<I', 4000000000)),
           (0x09, struct.pack('<Q', 1 << 60)), (0x0a, struct.pack('<f', 1.5)), (0x0b, struct.pack('<d', -2.25)),
           (0x0c, struct.pack('<2f', 1, 2)), (0x0d, struct.pack('<3f', 1, 2, 3)), (0x10, struct.pack('<H', 1234)),
           (0x0e, struct.pack('<H', 2) + 'hi'.encode('utf-16-le')), (0x0f, struct.pack('<H', 3) + b'abc')]
ARRAYS = [(0x41, b'\x01\x00'), (0x44, struct.pack('<3i', 7, 8, 9)), (0x46, b'\x01\x02'), (0x47, struct.pack('<2H', 1, 2)),
          (0x48, struct.pack('<2I', 10, 11)), (0x4a, struct.pack('<2f', 0.5, 0.25)), (0x4c, struct.pack('<2f', 3, 4))]
NAMES = ['ROOT', 'A', 'ARR', 'ITEM']


def encode(base, magic=0xABCE, extra=b''):
    """header | ROOT{ every scalar, every packed array, A{bool}, ARR[2]{u32} , extra } | names"""
    body = b''.join(bytes([t]) + d for t, d in SCALARS)
    pos = base + 8 + len(body)
    for t, d in ARRAYS:
        body += bytes([t]) + struct.pack('<I', pos + 5 + len(d)) + d
        pos += 5 + len(d)
    a = b'\x01\x01'
    body += struct.pack('<BHBI', 0x80, 1, 0, pos + 8 + len(a)) + a
    pos += 8 + len(a)
    items, p = b'', pos + 12
    for k in range(2):
        it = b'\x08' + struct.pack('<I', 100 + k)
        p += 4 + len(it)
        items += struct.pack('<I', p) + it
    body += struct.pack('<BHBII', 0x81, 2, 1, p, 2) + items + extra
    root = struct.pack('<BHBI', 0x80, 0, 2, base + 8 + len(body)) + body
    names = struct.pack('<H', len(NAMES)) + b''.join(struct.pack('<H', len(n)) + n.encode() for n in NAMES)
    return struct.pack('<IIII', magic, 0, 1234, base + len(root)) + root + names


def write(tmp, name, data):
    p = os.path.join(tmp, name)
    with open(p, 'wb') as f:
        f.write(data)
    return p


class Codec(unittest.TestCase):
    def test_every_tag_round_trips_byte_exact(self):
        raw = encode(16)
        e = E.Esf(raw)
        self.assertEqual(e.dumps(), raw)
        self.assertEqual(e.unknown, [])
        root = e.select('ROOT')[0]
        got = [n.get() for n in E.Esf.vals(root)]
        self.assertEqual(got[:4], [True, -3, -300, -5])
        self.assertEqual(got[14:16], ['hi', 'abc'])
        self.assertEqual(got[17], [7, 8, 9])
        self.assertEqual(len(got), len(SCALARS) + len(ARRAYS))

    def test_roundtrip_cli_function_and_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, 'a.save', encode(16))
            ok, s1, s2, d, unk = E.roundtrip(p)
            self.assertTrue(ok)
            self.assertEqual((s1, d, unk), (s2, None, []))
            self.assertIn('unknown tags: none', E.info(p))

    def test_set_copy_remove_rebuild_offsets_and_counts(self):
        e = E.Esf(encode(16))
        root = e.select('ROOT')[0]
        root[15].set('a much longer string')    # 0x0f: every later offset moves
        root[3].set(42)
        arr = e.select_node('ROOT/ARR')
        e.copy_item(arr, 1)
        e.remove_item(arr, 0)
        e.name_id('NEW_NAME')
        out = e.dumps()
        e2 = E.Esf(out)
        self.assertEqual(E.Esf(e2.dumps()).dumps(), out)
        self.assertEqual([c[0].get() for c in e2.select('ROOT/ARR')], [101, 101])
        self.assertEqual(e2.select('ROOT')[0][15].get(), 'a much longer string')
        self.assertEqual(len(e2.names), len(NAMES) + 1)
        with tempfile.TemporaryDirectory() as tmp:   # the offset reader agrees on every end offset
            d = esf_dump.Esf(write(tmp, 'b.save', out))
            lines = []
            rn, o, end = esf_dump.root_span(d)
            esf_dump.tree(d, o, end, 0, 9, lines)
            self.assertIn('ARR[2] (v1)', lines)

    def test_unknown_tag_reported_with_offset(self):
        raw = bytearray(encode(16))
        off = 16 + 8   # first child of ROOT
        raw[off] = 0x3f
        with self.assertRaises(ValueError) as cm:
            E.Esf(bytes(raw))
        self.assertIn('unknown tag 0x3f at offset %d' % off, str(cm.exception))

    def test_unknown_array_element_type_fails_the_gate(self):
        raw = encode(16)
        e = E.Esf(raw)
        e.nodes[0].kids.append(E.Val(0x4e, b'\x00\x01\x02'))   # packed array of utf16: layout not known
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, 'u.save', e.dumps())
            ok, _, _, d, unk = E.roundtrip(p)
            self.assertFalse(ok)
            self.assertIsNone(d)            # still byte-exact: kept raw
            self.assertEqual(unk[0][1], 0x4e)

    def test_locate_names_path_and_tag(self):
        raw = encode(16)
        e = E.Esf(raw)
        arr_items = e.select('ROOT/ARR')
        self.assertEqual(len(arr_items), 2)
        off = raw.rindex(struct.pack('<I', 101)) - 1   # the u32 tag of ARR[1]
        path, tag = E.locate(raw, off)
        self.assertEqual((path, tag), ('ROOT/ARR[1]@value', 0x08))

    def test_cli_refuses_to_write_over_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, 'a.save', encode(16))
            sys.argv = ['esf_edit.py', 'set', p, 'ROOT', '@3', '9', '-o', p]
            with self.assertRaises(SystemExit) as cm:
                E.main()
            self.assertIn('refusing', str(cm.exception))
            out = os.path.join(tmp, 'b.save')
            sys.argv = ['esf_edit.py', 'set', p, 'ROOT', '@3', '9', '-o', out]
            with contextlib.redirect_stdout(io.StringIO()):
                E.main()
            self.assertEqual(E.Esf.load(out).select('ROOT')[0][3].get(), 9)


class Diff(unittest.TestCase):
    def run_diff(self, a, b, skip=''):
        with tempfile.TemporaryDirectory() as tmp:
            pa, pb = write(tmp, 'a.save', a), write(tmp, 'b.save', b)
            A, B = esf_dump.Esf(pa), esf_dump.Esf(pb)
            ra, oa, ea = esf_dump.root_span(A)
            rb, ob, eb = esf_dump.root_span(B)
            d = esf_diff.Differ(A, B, 100, 0.0, esf_diff.skip_names(skip))
            d.seq(oa, ea, ob, eb, ra)
            return d.out

    def test_value_change_item_added_and_skip(self):
        e = E.Esf(encode(16))
        e.select('ROOT')[0][3].set(42)
        e.copy_item(e.select_node('ROOT/ARR'), 0)
        out = self.run_diff(encode(16), e.dumps())
        self.assertIn('~ ROOT@3: -5 -> 42', out)
        self.assertTrue(any(x.startswith('+ ROOT/ARR[2]') for x in out), out)
        self.assertFalse(any('ARR' in x for x in self.run_diff(encode(16), e.dumps(), skip='ARR')))

    def test_nan_is_not_a_change(self):
        a = E.Esf(encode(16))
        a.select('ROOT')[0][9].set(float('nan'))
        raw = a.dumps()
        self.assertEqual(self.run_diff(raw, raw.replace(struct.pack('<I', 1234), struct.pack('<I', 999), 1)), [])

    def test_skip_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(tmp, 'noise.txt', b'# noise\nCAI_INTERFACE\n\nQUAD_TREE_BIT_ARRAY  # fog\n')
            self.assertEqual(esf_diff.skip_names('@%s,X' % p), {'CAI_INTERFACE', 'QUAD_TREE_BIT_ARRAY', 'X'})

    def test_napoleon_noise_file_parses(self):
        names = esf_diff.skip_names('@' + os.path.join(ROOT, 'saves', 'napoleon', 'noise.txt'))
        self.assertTrue({'CAI_INTERFACE', 'CAMPAIGN_PATHFINDER', 'QUAD_TREE_BIT_ARRAY'} <= names)


# ---- a small Napoleon-shaped save built from esf_edit nodes (paths and @N positions as in saves/SAVE_FORMAT.md)
def V(tag, v):
    n = E.Val(tag, b'')
    n.set(v)
    return n


class Tree:
    def __init__(self):
        self.names = []

    def n(self, name):
        if name not in self.names:
            self.names.append(name)
        return self.names.index(name)

    def rec(self, name, kids, ver=0):
        return E.Rec(self.n(name), ver, kids)

    def arr(self, name, items):
        return E.RArr(self.n(name), 0, items)


def napoleon_save():
    """britain (player, extra CAMPAIGN_PLAYER_SETUP in front) with a gentleman in the field and governor_europe; france with London-
    like settlement owned by britain in region eur_england; returns raw bytes"""
    t = Tree()
    FIXP = 1 << 20

    def character(cid, ctype, x, y):
        loc = t.rec('LOCOMOTABLE', [V(0x04, x), V(0x04, y), V(0x04, x), V(0x04, y), V(0x0a, 3.0), V(0x0a, 3.0)])
        los = t.rec('LINE_OF_SIGHT', [V(0x01, False), V(0x0c, (-10.0, 5.0)), V(0x0c, (10.0, 25.0))])
        kids = [loc, t.rec('CHARACTER_DETAILS', [V(0x0f, 'x')]), V(0x08, cid), V(0x0e, ctype), V(0x04, 0), V(0x04, 0), V(0x04, 0),
                V(0x08, 0), V(0x04, 0), V(0x04, 0), V(0x01, False), V(0x01, False), V(0x48, []), los]
        kids += [V(0x04, 0) for _ in range(14, 25)] + [V(0x01, False), V(0x04, 0)]
        return [t.rec('CHARACTER', kids)]

    def faction(fid, key, player, chars, posts):
        kids = [t.rec('ANCILLARY_UNIQUENESS_MONITOR', [])]
        if player:
            kids.append(t.rec('CAMPAIGN_PLAYER_SETUP', [V(0x0e, key)]))
        gov = t.rec('GOVERNMENT', [V(0x08, 1), V(0x0e, 'gov_x'), V(0x04, 49), t.arr('POSTS_ARRAY', posts)])
        kids += [gov, V(0x08, fid), V(0x0e, key), V(0x0e, key.title()), t.arr('CHARACTER_ARRAY', chars), t.arr('ARMY_ARRAY', [])]
        return [t.rec('FACTION', kids)]

    taxes = t.rec('GOVERNORSHIP_TAXES', [V(0x08, 2), V(0x08, 2), V(0x08, 15), V(0x08, 15)])
    post = [t.rec('CHARACTER_POST', [V(0x08, 7), V(0x0e, 'governor_europe'), V(0x08, 0), V(0x01, True),
                                     t.rec('GOVERNORSHIP', [taxes, V(0x08, 1), V(0x48, [500])])])]
    britain = faction(1000, 'britain', True, [character(77, 'General', -5 * FIXP, 2 * FIXP), character(88, 'gentleman', -9 * FIXP, 4 * FIXP)], [post])
    france = faction(2000, 'france', False, [character(99, 'rake', 0, 0)], [])
    res = t.rec('SIEGEABLE_GARRISON_RESIDENCE', [t.rec('GARRISON_RESIDENCE', [V(0x08, 1000)]), V(0x08, 4242)] +
                [V(0x04, 0) for _ in range(2, 7)] + [V(0x01, False)] * 3 + [V(0x04, -6 * FIXP), V(0x04, 3 * FIXP), V(0x08, 0),
                                                                            V(0x48, []), V(0x48, [])])
    region = [t.rec('REGION', [V(0x0e, 'eur_england'), t.rec('POPULATION', []), t.rec('TRAITS', []), t.rec('REGION_SLOT_MANAGER', []),
                               V(0x08, 500), t.rec('SETTLEMENT', [res, t.rec('CAMPAIGN_LOCALISATION', []), V(0x04, 3),
                                                                   V(0x0f, 'settlement:eur_england:london'), V(0x08, 4242)])])]
    world = t.rec('WORLD', [t.arr('FACTION_ARRAY', [britain, france]), t.rec('REGION_MANAGER', [t.arr('REGIONS_ARRAY', [region])])])
    root = t.rec('CAMPAIGN_SAVE_GAME', [t.rec('CAMPAIGN_ENV', [t.rec('CAMPAIGN_MODEL', [world])])], ver=5)
    e = E.Esf.__new__(E.Esf)
    e.magic, e.zero, e.ts, e.names, e.tail, e.unknown, e.nodes = 0xABCE, 0, 1, t.names, b'', [], [root]
    return e.dumps()


class NapoleonMap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = write(self.tmp.name, 's.save', napoleon_save())
        self.s = esf_map.Save(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_factions_by_value_order(self):
        rows = save_map.faction_rows(self.s)
        self.assertEqual([(r['id'], r['key']) for r in rows], [(1000, 'britain'), (2000, 'france')])

    def test_characters_settlements_taxes(self):
        ch = list(save_map.characters(self.s, 'britain'))
        self.assertEqual([(c['id'], c['type'], c['residence']) for c in ch], [(77, 'General', 0), (88, 'gentleman', 0)])
        self.assertEqual(ch[1]['pos'], (-9.0, 4.0))
        st = list(save_map.settlements(self.s))
        self.assertEqual((st[0]['region'], st[0]['residence_id'], st[0]['owner'], st[0]['agents']), ('eur_england', 4242, 1000, []))
        self.assertEqual(list(save_map.taxes(self.s))[0]['taxes'], [2, 2, 15, 15])

    def test_grep_id_finds_both_ends(self):
        self.assertEqual(len(esf_map.grep_id(self.s, 4242)), 2)


class Recipes(unittest.TestCase):
    def setUp(self):
        self.raw = napoleon_save()

    def diff(self, out):
        with tempfile.TemporaryDirectory() as tmp:
            A, B = esf_dump.Esf(write(tmp, 'a.save', self.raw)), esf_dump.Esf(write(tmp, 'b.save', out))
            ra, oa, ea = esf_dump.root_span(A)
            _, ob, eb = esf_dump.root_span(B)
            d = esf_diff.Differ(A, B, 100, 0.0, set())
            d.seq(oa, ea, ob, eb, ra)
            return d.out

    def test_tax_rates_scalar(self):
        se = SaveEdit(esf=E.Esf(self.raw))
        self.assertEqual(tax_rates.apply(se, lower=4, upper=0), ('britain', 'governor_europe'))
        out = se.e.dumps()
        d = self.diff(out)
        self.assertEqual(len(d), 4, d)
        self.assertTrue(all('GOVERNORSHIP_TAXES@' in x for x in d))
        self.assertTrue(any(x.endswith('GOVERNORSHIP_TAXES@2: 15 -> 25') for x in d))
        self.assertTrue(any(x.endswith('GOVERNORSHIP_TAXES@3: 15 -> 5') for x in d))
        with self.assertRaises(KeyError):
            tax_rates.apply(SaveEdit(esf=E.Esf(self.raw)), post='governor_nowhere')

    def test_agent_into_settlement_both_ends(self):
        se = SaveEdit(esf=E.Esf(self.raw))
        self.assertEqual(agent_into_settlement.apply(se, 'eur_england'), (88, 4242))   # first field agent, not the General
        out = se.e.dumps()
        d = self.diff(out)
        self.assertIn('CHARACTER_ARRAY[1]/CHARACTER@7: 0 -> 4242', '\n'.join(d))
        self.assertIn('CHARACTER_ARRAY[1]/CHARACTER@25: False -> True', '\n'.join(d))
        self.assertIn('SIEGEABLE_GARRISON_RESIDENCE@14: [] -> [88]', '\n'.join(d))
        self.assertIn('LOCOMOTABLE@0: -9437184 -> -6291456', '\n'.join(d))
        self.assertIn('LINE_OF_SIGHT@1: (-10.0, 5.0) -> (-7.5, 3.75)', '\n'.join(d))   # moved (+3, -1) -> grid (+2.5, -1.25)
        self.assertEqual(len(d), 9, d)   # @7, @25, LOCOMOTABLE@0-3, two LINE_OF_SIGHT corners, the residence list

    def test_agent_refusals(self):
        with self.assertRaises(ValueError):   # a General is not an agent
            agent_into_settlement.apply(SaveEdit(esf=E.Esf(self.raw)), 'eur_england', agent=77)
        with self.assertRaises(ValueError):   # france's rake: the settlement is britain's
            agent_into_settlement.apply(SaveEdit(esf=E.Esf(self.raw)), 'eur_england', agent=99)
        se = SaveEdit(esf=E.Esf(self.raw))
        agent_into_settlement.apply(se, 'eur_england', agent=88)
        with self.assertRaises(ValueError):   # already inside
            agent_into_settlement.apply(se, 'eur_england', agent=88)


class Staging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.saves, self.state = base / 'save_games', base / 'state'
        self.saves.mkdir()
        self.state.mkdir()
        self.src = base / 'edited.save'
        self.src.write_bytes(b'ESF' * 1000)
        (self.saves / 'liam_campaign.save').write_bytes(b'mine')

    def tearDown(self):
        self.tmp.cleanup()

    def quiet(self, fn, *a, **k):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a, **k)

    def test_stage_zz_only(self):
        self.assertEqual(self.quiet(stage_save.stage, self.src, 'zz_j14_a', self.saves), 'zz_j14_a')
        self.assertEqual((self.saves / 'zz_j14_a.save').read_bytes(), self.src.read_bytes())
        for bad in ('j14_a', 'zz_', '../zz_x', 'zz_a/b', 'liam_campaign'):
            with self.assertRaises(SystemExit):
                stage_save.stage(self.src, bad, self.saves)
        self.assertEqual((self.saves / 'liam_campaign.save').read_bytes(), b'mine')

    def test_stage_refuses_other_content_then_clear_moves(self):
        self.quiet(stage_save.stage, self.src, 'zz_j14_a.save', self.saves)
        self.quiet(stage_save.stage, self.src, 'zz_j14_a', self.saves)   # same sha: fine
        other = Path(self.tmp.name) / 'other.save'
        other.write_bytes(b'other')
        with self.assertRaises(SystemExit):
            stage_save.stage(other, 'zz_j14_a', self.saves)
        moved = self.quiet(stage_save.clear, self.saves, self.state)
        self.assertEqual([p.name for p in moved], ['zz_j14_a.save'])
        self.assertTrue(moved[0].is_file() and '_to_delete' in str(moved[0]))
        self.assertEqual(sorted(p.name for p in self.saves.iterdir()), ['liam_campaign.save'])   # Liam's save untouched

    def test_keep_copies_read_only_and_refuses_conflicts(self):
        dest = self.quiet(stage_save.keep, 'liam_campaign', self.saves, self.state)
        self.assertEqual(dest, self.state / 'saves' / 'liam_campaign.save')
        self.assertEqual(dest.read_bytes(), b'mine')
        with self.assertRaises(PermissionError):
            dest.write_bytes(b'edited in place')
        for bad in ('../x.save', 'a/b.save', 'c:x.save'):
            with self.assertRaises(SystemExit):
                stage_save.keep('liam_campaign', self.saves, self.state, bad)
        self.quiet(stage_save.keep, 'liam_campaign.save', self.saves, self.state)   # same sha again: fine
        (self.saves / 'liam_campaign.save').write_bytes(b'changed')
        with self.assertRaises(SystemExit):
            stage_save.keep('liam_campaign', self.saves, self.state)
        self.assertEqual(dest.read_bytes(), b'mine')


if __name__ == '__main__':
    unittest.main()
