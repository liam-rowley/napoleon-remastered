#!/usr/bin/env python3
"""Build the fixed-sky dev pack (J44): the battles-to-sky junction cut to one sky per battle, season, weather and time of day.

purpose: make a battle's lighting the same on every launch: the engine picks a battle's sky at random among its junction rows that match the
         battle's season, weather and time of day (NAP_MP_Grassy_Flatlands: two dry skies, clear and overcast, per time of day); this keeps one
         row per (battle, season, weather, time of day), the first whose sky_file has "clear" in it (empire-remastered make_fixed_sky_pack.py's
         rule), else the first, and writes the table as a type-4 pack under the vanilla entry name, plus a listing of every choice
usage: python3 proxy/tools/build_fixed_sky_pack.py [--games discovery/napoleon/games.json] [--out FILE] [--list]
when: pc_deploy.py kit runs it when the game's packs are readable (on the PC); the launch keys switch it on through dev.file_rules
      (proxy/napoleon/lua/fixed_sky_rules.txt: `add data\\zz_napoleon_remastered_fixed_sky.pack -> ...`), so nothing is written into data\\
not-a-verb: writes a game-format binary from the game's own tables; pc_deploy.py calls it

Byte format: the vanilla file's header (no guid, version 0: u8 1, u32 rows) and rows of two StringU16 (u16 length, UTF-16LE), so a table of
the same rows would be byte-identical to the vanilla one (tests/test_fixed_sky.py). Whether the pack wins over data.pack and pins the sky is
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
    blob = pack_bytes([(JUNCTION, encode_junction(head, kept))])
    out = Path(out or ROOT / 'build' / 'proxy' / 'napoleon' / PACK)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    out.with_suffix('.choices.json').write_text(json.dumps(choices, indent=1) + '\n', encoding='utf-8')
    print(f'build_fixed_sky_pack: {out} ({len(kept)} of {len(junction)} junction rows, {len(choices)} groups, sha256 {hashlib.sha256(blob).hexdigest()[:16]})')
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
