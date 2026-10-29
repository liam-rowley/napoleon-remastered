#!/usr/bin/env python3
"""tax_rates.py: scalar save recipe: set one theatre governorship's tax levels (lower and upper class) and their rates.

purpose: set GOVERNORSHIP_TAXES of one governorship: @0 lower-class level, @1 upper-class level, @2 and @3 their rates (rate = 5 + 5 x level, pair taxes-changed)
usage: python3 -I saves/napoleon/recipes/tax_rates.py IN.save OUT.save [--faction KEY] [--post governor_europe] [--lower 0-4] [--upper 0-4] [--list]
when: a save is needed with other tax settings (load ladder B; J4 scenarios); scalar edit only, run on a copy. The REGION@15 values the game moves with taxes (public order, by the look of it) are left for the engine to recompute
not-a-verb: a save recipe run on the PC against saves outside the repo
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import SaveEdit, guard_paths, report  # noqa: E402

LEVELS = range(0, 5)


def rate(level):
    return 5 + 5 * level   # 0 -> 5, 2 -> 15, 4 -> 25 (taxes-changed pair: both classes, both saves)


def apply(se, faction=None, post=None, lower=4, upper=4):
    key, fk, fid = se.faction(faction)
    govs = se.governorships(fk)
    if not govs:
        raise KeyError('faction %s has no governorship' % key)
    name, gk = next(((p, g) for p, g in govs if post in (None, p)), (None, None))
    if gk is None:
        raise KeyError('no governorship %s in %s (has %s)' % (post, key, [p for p, _ in govs]))
    tk = se.rec(gk, 'GOVERNORSHIP_TAXES').kids
    for i, v in ((0, lower), (1, upper), (2, rate(lower)), (3, rate(upper))):
        se.setv(tk, i, v, '%s %s GOVERNORSHIP_TAXES@%d' % (key, name, i))
    return key, name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--faction', help='faction key (default: the player faction, FACTION_ARRAY[0])')
    ap.add_argument('--post', help='governorship post key (default: the faction\'s first, e.g. governor_europe)')
    ap.add_argument('--lower', type=int, choices=LEVELS, default=4)
    ap.add_argument('--upper', type=int, choices=LEVELS, default=4)
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    guard_paths(a.inp, a.out)
    se = SaveEdit(a.inp)
    if a.list:
        key, fk, _ = se.faction(a.faction)
        for p, gk in se.governorships(fk):
            print(key, p, [n.get() for n in se.rec(gk, 'GOVERNORSHIP_TAXES').kids])
        return
    apply(se, a.faction, a.post, a.lower, a.upper)
    se.save(a.out)
    report(se, a.out)


if __name__ == '__main__':
    main()
