#!/usr/bin/env python3
"""Build the fixed-sky dev pack (J44): the sky tables cut to one sky per season, weather and time of day (and per battle in the junction).

purpose: make a battle's lighting the same on every launch: the engine picks a battle's sky at random among its junction rows that match the
         battle's season, weather and time of day (NAP_MP_Grassy_Flatlands: two dry skies, clear and overcast, per time of day); this keeps one
         row per (battle, season, weather, time of day), the first whose sky_file has "clear" in it (empire-remastered make_fixed_sky_pack.py's
         rule), else the first; and battle_sky_types the same way per (season, weather, time of day, climate), keeping every sky the cut
         junction names (Empire's route: a junction cut alone did not pin the sky, run 20261030_j44pc); both tables go into a type-4 pack
         under their vanilla entry names, plus a listing of every choice
usage: python3 proxy/tools/build_fixed_sky_pack.py [--games discovery/napoleon/games.json] [--out FILE] [--list]
when: pc_deploy.py kit runs it when the game's packs are readable (on the PC); the launch keys switch it on through dev.file_rules
      (proxy/napoleon/lua/fixed_sky_rules.txt: `add data\\zz_napoleon_remastered_fixed_sky.pack -> ...`), so nothing is written into data\\
not-a-verb: writes a game-format binary from the game's own tables; pc_deploy.py calls it

Byte format: each table keeps the vanilla file's header bytes and is re-encoded field by field from the schema, so a table of the same rows
is byte-identical to the vanilla one (tests/test_fixed_sky.py). Whether the pack wins over data.pack and pins the sky is
the PC proof (fact napoleon.battle.fixed_sky).
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'discovery' / 'core'))
JUNCTION = 'db\\battles_to_battle_sky_types_junctions_tables\\battles_to_battle_sky_types_junctions'
SKIES = 'db\\battle_sky_types_tables\\battle_sky_types'
PACK = 'zz_napoleon_remastered_fixed_sky.pack'


def u16s(s):
    return struct.pack('<H', len(s)) + s.encode('utf-16-le')


def read_str(b, o):
    n = struct.unpack_from('<H', b, o)[0]
    return b[o + 2:o + 2 + n * 2].decode('utf-16-le'), o + 2 + n * 2


def parse_junction(b):
    """(header bytes, [(battle_key, sky_key)]) of the vanilla junction file (no guid, version 0)."""
    if b[:1] != b'\x01':
        raise SystemExit('build_fixed_sky_pack: the junction table has a guid or version header: the format this tool knows changed')
    count = struct.unpack_from('<I', b, 1)[0]
    o, rows = 5, []
    for _ in range(count):
        a, o = read_str(b, o)
        k, o = read_str(b, o)
        rows.append((a, k))
    if o != len(b):
        raise SystemExit(f'build_fixed_sky_pack: junction rows end at {o} of {len(b)} bytes')
    return b[:1], rows


def encode_junction(head, rows):
    return head + struct.pack('<I', len(rows)) + b''.join(u16s(a) + u16s(k) for a, k in rows)


def choose(junction, skies):
    """junction [(battle, sky key)], skies {key: {season, weather_type, time_of_day, sky_file}} -> (kept rows in vanilla order, choices)."""
    groups = {}
    for battle, sky in junction:
        s = skies.get(sky)
        g = (battle, s['season'], s['weather_type'], s['time_of_day']) if s else (battle, '?', sky, '?')
        groups.setdefault(g, []).append(sky)
    keep, choices = set(), []
    for g, cands in groups.items():
        pick = next((c for c in cands if 'clear' in (skies.get(c, {}).get('sky_file', '') or '').lower()), cands[0])
        keep.add((g[0], pick))
        choices.append({'battle': g[0], 'season': g[1], 'weather': g[2], 'time_of_day': g[3], 'kept': pick, 'from': cands})
    return [r for r in junction if r in keep], choices


def encode_field(t, v):
    if t == 'Boolean':
        return b'\x01' if v else b'\x00'
    if t == 'StringU16':
        return u16s(v)
    if t == 'OptionalStringU16':
        return b'\x00' if v is None else b'\x01' + u16s(v)
    raise SystemExit(f'build_fixed_sky_pack: no encoder for field type {t}')


def encode_table(head, fields, rows):
    """head = the vanilla bytes before the u32 row count; rows decoded with `fields`."""
    types = [f['type'] for f in fields]
    return head + struct.pack('<I', len(rows)) + b''.join(b''.join(encode_field(t, v) for t, v in zip(types, r)) for r in rows)


def choose_skies(rows, names, need):
    """battle_sky_types rows -> (kept rows in vanilla order): one per (season, weather, time of day, climate), "clear" first, plus `need`."""
    ix = {n: names.index(n) for n in ('key', 'season', 'weather_type', 'time_of_day', 'climate', 'sky_file')}
    groups = {}
    for r in rows:
        groups.setdefault(tuple(r[ix[n]] for n in ('season', 'weather_type', 'time_of_day', 'climate')), []).append(r)
    keep = set(need)
    for cands in groups.values():
        pick = next((r for r in cands if 'clear' in (r[ix['sky_file']] or '').lower()), cands[0])
        keep.add(pick[ix['key']])
    return [r for r in rows if r[ix['key']] in keep]


def pack_bytes(entries):
    index = b''.join(struct.pack('<I', len(d)) + p.encode('latin-1') + b'\0' for p, d in entries)
    return b'PFH0' + struct.pack('<IIIII', 4, 0, 0, len(entries), len(index)) + index + b''.join(d for _, d in entries)


def build(games_path, out=None):
    from packfs import PackFS
    import db
    fs = PackFS.from_games(json.loads(Path(games_path).read_text(encoding='utf-8')), 'napoleon')
    head, junction = parse_junction(fs.read(JUNCTION))
    _, tables = db.load_schema()
    res = db.decode_table(fs.read(SKIES), tables['battle_sky_types_tables'])
    if 'rows' not in res:
        raise SystemExit(f"build_fixed_sky_pack: battle_sky_types not decoded: {res.get('errors')}")
    names = [f['name'] for f in res['fields']]
    skies = {r[names.index('key')]: dict(zip(names, r)) for r in res['rows']}
    kept, choices = choose(junction, skies)
    sky_raw = fs.read(SKIES)
    start = db.parse_header(sky_raw)[4]
    if encode_table(sky_raw[:start - 4], res['fields'], res['rows']) != sky_raw:
        raise SystemExit('build_fixed_sky_pack: battle_sky_types does not re-encode byte for byte: the encoder is wrong for this table')
    sky_rows = choose_skies(res['rows'], names, {k for _, k in kept})
    blob = pack_bytes([(JUNCTION, encode_junction(head, kept)), (SKIES, encode_table(sky_raw[:start - 4], res['fields'], sky_rows))])
    out = Path(out or ROOT / 'build' / 'proxy' / 'napoleon' / PACK)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    out.with_suffix('.choices.json').write_text(json.dumps(choices, indent=1) + '\n', encoding='utf-8')
    print(f'build_fixed_sky_pack: {out} ({len(kept)} of {len(junction)} junction rows, {len(sky_rows)} of {len(res["rows"])} skies, sha256 {hashlib.sha256(blob).hexdigest()[:16]})')
    return out, choices


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--games', default=str(ROOT / 'discovery' / 'napoleon' / 'games.json'))
    ap.add_argument('--out')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args(argv)
    _, choices = build(a.games, a.out)
    if a.list:
        for c in choices:
            print(f"{c['battle']:40} {c['season']:7} {c['weather']:16} {c['time_of_day']:10} {c['kept']}  (of {len(c['from'])})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
