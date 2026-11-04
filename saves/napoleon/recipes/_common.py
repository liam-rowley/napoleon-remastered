"""_common.py: shared helpers for the Napoleon save recipes: find factions, characters, settlement residences and governorships
in an esf_edit tree by meaning, not by index. Field positions and evidence: saves/SAVE_FORMAT.md.

purpose: library for the recipes in saves/napoleon/recipes/ (each one: python3 -I <recipe>.py IN OUT [options])
usage: from _common import SaveEdit, report   (imported by the recipes; not run on its own)
when: writing a new Napoleon save recipe
not-a-verb: a library imported by the recipes, which run on the PC against saves outside the repo

Ported from empire-remastered rml_mod/tools/db/save_recipes/_common.py onto the Napoleon paths (J14).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), 'core', 'saves'))   # the ESF tools (warscape-core, J12)
import esf_edit  # noqa: E402
from esf_edit import Rec, RArr, Val  # noqa: E402

FIX = 1 << 20  # map positions are 12.20 fixed point (LOCOMOTABLE, residences)
LOS_GRID = 1.25  # LINE_OF_SIGHT boxes sit on a 1.25 map-unit grid

# @N positions over all children (saves/SAVE_FORMAT.md)
CHAR_ID, CHAR_TYPE, CHAR_RESIDENCE, CHAR_IN_RESIDENCE = 2, 3, 7, 25
RES_ID, RES_X, RES_Y, RES_AGENTS = 1, 10, 11, 14
AGENT_TYPES = ('gentleman', 'rake', 'assassin', 'spy', 'Eastern_Scholar')   # characters that enter a residence on their own


class SaveEdit:
    def __init__(self, path=None, esf=None):
        self.e = esf if esf is not None else esf_edit.Esf.load(path)
        self.log = []

    # ---- generic
    def nm(self, n):
        return self.e.nm(n)

    def rec(self, kids, name, nth=0):
        hits = [n for n in kids if isinstance(n, Rec) and self.nm(n) == name]
        return hits[nth] if len(hits) > nth else None

    def arr(self, kids, name):
        return next((n for n in kids if isinstance(n, RArr) and self.nm(n) == name), None)

    def chain(self, kids, *names):
        for nmx in names:
            r = self.rec(kids, nmx)
            if r is None:
                raise KeyError('/'.join(names))
            kids = r.kids
        return kids

    def setv(self, kids, i, v, what):
        if not isinstance(kids[i], Val):
            raise TypeError('%s: @%d is a record, not a value' % (what, i))
        old = kids[i].get()
        kids[i].set(v)
        self.log.append('%s: %r -> %r' % (what, old, v))

    def model(self):
        return self.chain(self.e.nodes[0].kids, 'CAMPAIGN_ENV', 'CAMPAIGN_MODEL')

    def world(self):
        return self.chain(self.model(), 'WORLD')

    # ---- factions / characters (FACTION fields by value order: the player faction has an extra record in front)
    def factions(self):
        """[(index, key, faction kids, faction id)]"""
        out = []
        for i, it in enumerate(self.arr(self.world(), 'FACTION_ARRAY').items):
            fk = self.rec(it, 'FACTION').kids
            v = [n.get() for n in fk if isinstance(n, Val)]
            out.append((i, v[1], fk, v[0]))
        return out

    def faction(self, key=None):
        """(key, kids, id) of faction key, or of the player faction (FACTION_ARRAY[0]) when key is None"""
        for i, k, fk, fid in self.factions():
            if key is None or k == key:
                return k, fk, fid
        raise KeyError('faction %s' % key)

    def characters(self, fk):
        return [self.rec(it, 'CHARACTER').kids for it in self.arr(fk, 'CHARACTER_ARRAY').items]

    def character(self, cid):
        """(faction key, character kids) of the character with id cid"""
        for i, k, fk, fid in self.factions():
            for ck in self.characters(fk):
                if ck[CHAR_ID].get() == cid:
                    return k, ck
        raise KeyError('character %d' % cid)

    # ---- settlements (SETTLEMENT/SIEGEABLE_GARRISON_RESIDENCE)
    def regions(self):
        return [self.rec(it, 'REGION').kids for it in self.arr(self.chain(self.world(), 'REGION_MANAGER'), 'REGIONS_ARRAY').items]

    def settlement(self, region_key):
        """(residence kids, owner faction id) of the settlement of region_key"""
        for rk in self.regions():
            if rk[0].get() == region_key:
                st = self.rec(rk, 'SETTLEMENT')
                if st is None:
                    break
                res = self.rec(st.kids, 'SIEGEABLE_GARRISON_RESIDENCE').kids
                return res, self.rec(res, 'GARRISON_RESIDENCE').kids[0].get()
        raise KeyError('settlement of region %s' % region_key)

    def list_edit(self, kids, i, add=None, remove=None, what=''):
        v = list(kids[i].get())
        if remove is not None:
            v = [x for x in v if x != remove]
        if add is not None and add not in v:
            v.append(add)
        self.setv(kids, i, v, what)

    def move_char(self, ck, fx, fy, who):
        """put a character at fixed-point (fx, fy): LOCOMOTABLE @0,1 position and @2,3 destination (equal when idle); the
        LINE_OF_SIGHT box (@1, @2) shifts by the move rounded to its grid, its fog bits stay stale until the engine redraws them"""
        lk = self.rec(ck, 'LOCOMOTABLE').kids
        ox, oy = lk[0].get(), lk[1].get()
        for i, v in ((0, fx), (1, fy), (2, fx), (3, fy)):
            self.setv(lk, i, v, '%s LOCOMOTABLE@%d' % (who, i))
        los = self.rec(ck, 'LINE_OF_SIGHT')
        if los is not None and len(los.kids) > 2 and all(isinstance(n, Val) and n.tag == 0x0c for n in los.kids[1:3]):
            dx = round((fx - ox) / FIX / LOS_GRID) * LOS_GRID
            dy = round((fy - oy) / FIX / LOS_GRID) * LOS_GRID
            for i in (1, 2):
                a, b = los.kids[i].get()
                self.setv(los.kids, i, (a + dx, b + dy), '%s LINE_OF_SIGHT@%d' % (who, i))

    # ---- governorships (theatre taxes)
    def governorships(self, fk):
        """[(post key, GOVERNORSHIP kids)] of one faction"""
        out = []
        for it in self.arr(self.rec(fk, 'GOVERNMENT').kids, 'POSTS_ARRAY').items:
            pk = self.rec(it, 'CHARACTER_POST').kids
            g = self.rec(pk, 'GOVERNORSHIP')
            if g is not None:
                out.append((pk[1].get(), g.kids))
        return out

    def save(self, path):
        self.e.save(path)
        return path


def guard_paths(inp, out):
    if os.path.abspath(inp) == os.path.abspath(out):
        sys.exit('refusing to overwrite the input')


def report(se, out):
    print('\n'.join(se.log))
    print('wrote', out)
