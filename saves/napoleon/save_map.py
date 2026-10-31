#!/usr/bin/env python3
"""save_map.py: semantic summary of a Napoleon save on the record paths mapped in saves/SAVE_FORMAT.md.

purpose: list a Napoleon save's factions, characters (type, position, residence), forces, settlement residences (agents inside) and governorship taxes, resolve an id, and find own field characters near foreign ones
usage: python3 -I saves/napoleon/save_map.py SAVE [factions|characters|forces|settlements|taxes|near|all] [--faction KEY] [--radius R] [--json]   (id lookups: core/saves/esf_map.py SAVE id ID)
when: before writing or running a recipe (which agent, which residence id, which theatre), and to read back a value after a QuickSave (load ladder B); field meanings in saves/SAVE_FORMAT.md
not-a-verb: reads saves on the PC that are never in the repo; a library for the recipes as well as a CLI

Ported from empire-remastered rml_mod/tools/db/esf_map.py onto the Napoleon paths of J14 (pairs agent-to-settlement, taxes-changed).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'core', 'saves'))   # the ESF tools (warscape-core, J12)
from esf_map import FIX, Save  # noqa: E402

MODEL = ('CAMPAIGN_ENV', 'CAMPAIGN_MODEL')
# field positions (@N over all children), from saves/SAVE_FORMAT.md. FACTION is the exception: the player faction has an extra
# CAMPAIGN_PLAYER_SETUP record in front, so its fields are read by value order (0 id, 1 key, 2 name), not by @N.
FACTION_ID, FACTION_KEY, FACTION_NAME = 0, 1, 2
CHAR_ID, CHAR_TYPE, CHAR_RESIDENCE, CHAR_IN_RESIDENCE = 2, 3, 7, 25
RES_ID, RES_X, RES_Y, RES_FORCE, RES_AGENTS = 1, 10, 11, 12, 14
ARMY_RESIDENCE = 5


def world(s):
    return s.chain(s.root(), *MODEL, 'WORLD')


def factions(s):
    """yield (index, key, faction span, faction values)"""
    for i, it in enumerate(s.items(world(s), 'FACTION_ARRAY')):
        _, fs = s.item_rec(it)
        v = dict(enumerate(x for _, x in sorted(s.vals(fs).items())))   # value order, see FACTION_ID
        yield i, v.get(FACTION_KEY), fs, v


def faction_rows(s):
    out = []
    for i, key, fs, v in factions(s):
        gov = s.sub(fs, 'GOVERNMENT')
        gv = s.vals(gov) if gov else {}
        out.append({'index': i, 'id': v.get(FACTION_ID), 'key': key, 'name': v.get(FACTION_NAME), 'government': gv.get(1),
                    'characters': len(s.items(fs, 'CHARACTER_ARRAY')), 'forces': len(s.items(fs, 'ARMY_ARRAY'))})
    return out


def characters(s, fkey=None):
    for fi, key, fs, _ in factions(s):
        if fkey and key != fkey:
            continue
        for ci, it in enumerate(s.items(fs, 'CHARACTER_ARRAY')):
            _, cs = s.item_rec(it)
            v = s.vals(cs)
            loc = s.sub(cs, 'LOCOMOTABLE')
            lv = s.vals(loc) if loc else {}
            yield {'path': 'FACTION_ARRAY[%d]/CHARACTER_ARRAY[%d]' % (fi, ci), 'fkey': key, 'id': v.get(CHAR_ID),
                   'type': v.get(CHAR_TYPE), 'residence': v.get(CHAR_RESIDENCE), 'in_residence': v.get(CHAR_IN_RESIDENCE),
                   'pos': (round(lv[0] / FIX, 3), round(lv[1] / FIX, 3)) if loc else None}


def forces(s, fkey=None):
    for fi, key, fs, _ in factions(s):
        if fkey and key != fkey:
            continue
        for ai, it in enumerate(s.items(fs, 'ARMY_ARRAY')):
            name, rs = s.item_rec(it)
            mf = s.sub(rs, 'MILITARY_FORCE')
            mv = s.vals(mf) if mf else {}
            yield {'path': 'FACTION_ARRAY[%d]/ARMY_ARRAY[%d]/%s' % (fi, ai, name), 'fkey': key, 'kind': name,
                   'force_id': mv.get(0), 'commander': mv.get(1), 'residence': s.vals(rs).get(ARMY_RESIDENCE),
                   'units': len(s.items(rs, 'UNITS_ARRAY'))}


def settlements(s):
    for ri, it in enumerate(s.items(s.sub(world(s), 'REGION_MANAGER'), 'REGIONS_ARRAY')):
        _, reg = s.item_rec(it)
        rv = s.vals(reg)
        st = s.sub(reg, 'SETTLEMENT')
        if not st:
            continue
        sg = s.sub(st, 'SIEGEABLE_GARRISON_RESIDENCE')
        gv = s.vals(sg)
        gr = s.sub(sg, 'GARRISON_RESIDENCE')
        yield {'path': 'REGIONS_ARRAY[%d]/REGION/SETTLEMENT' % ri, 'region': rv.get(0), 'region_id': rv.get(4),
               'owner': s.vals(gr).get(0) if gr else None, 'residence_id': gv.get(RES_ID),
               'pos': (round(gv[RES_X] / FIX, 3), round(gv[RES_Y] / FIX, 3)), 'force': gv.get(RES_FORCE),
               'agents': gv.get(RES_AGENTS)}


def taxes(s, fkey=None):
    """governorship (theatre) taxes: [lower level, upper level, lower rate %, upper rate %] and the region ids it governs"""
    for fi, key, fs, _ in factions(s):
        if fkey and key != fkey:
            continue
        for pi, it in enumerate(s.items(s.sub(fs, 'GOVERNMENT'), 'POSTS_ARRAY')):
            _, ps = s.item_rec(it)
            gs = s.sub(ps, 'GOVERNORSHIP')
            if gs:
                tv = s.vals(s.sub(gs, 'GOVERNORSHIP_TAXES'))
                yield {'path': 'FACTION_ARRAY[%d]/FACTION/GOVERNMENT/POSTS_ARRAY[%d]' % (fi, pi), 'fkey': key,
                       'post': s.vals(ps).get(1), 'taxes': [tv[i] for i in sorted(tv)], 'regions': s.vals(gs).get(2)}


def near(s, fkey, radius):
    """own field characters of fkey with a foreign field character within radius map units"""
    chars = [c for c in characters(s) if c['pos'] and c['pos'] != (0.0, 0.0) and not c['residence']]
    for c in (c for c in chars if c['fkey'] == fkey):
        for f in (f for f in chars if f['fkey'] != fkey):
            d = ((c['pos'][0] - f['pos'][0]) ** 2 + (c['pos'][1] - f['pos'][1]) ** 2) ** 0.5
            if d <= radius:
                yield {'own': c['id'], 'own_type': c['type'], 'foreign': f['id'], 'foreign_fkey': f['fkey'],
                       'foreign_type': f['type'], 'dist': round(d, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('save')
    ap.add_argument('what', nargs='?', default='all',
                    choices=['factions', 'characters', 'forces', 'settlements', 'taxes', 'near', 'all'])
    ap.add_argument('--faction')
    ap.add_argument('--radius', type=float, default=6.0, help='near: distance in map units (LOCOMOTABLE / 2^20)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    s = Save(a.save)
    out = {}
    if a.what in ('factions', 'all'):
        out['factions'] = faction_rows(s)
    if a.what in ('characters', 'all'):
        out['characters'] = list(characters(s, a.faction))
    if a.what in ('forces', 'all'):
        out['forces'] = list(forces(s, a.faction))
    if a.what in ('settlements', 'all'):
        out['settlements'] = list(settlements(s))
    if a.what in ('taxes', 'all'):
        out['taxes'] = list(taxes(s, a.faction))
    if a.what == 'near':
        own = a.faction or next(factions(s))[1]
        out['near'] = sorted(near(s, own, a.radius), key=lambda r: r['dist'])
    if a.json:
        json.dump(out, sys.stdout, default=str, indent=1)
        return
    for sec, rows in out.items():
        print('## %s (%d)' % (sec, len(rows)))
        for r in rows:
            print(json.dumps(r, default=str))


if __name__ == '__main__':
    main()
