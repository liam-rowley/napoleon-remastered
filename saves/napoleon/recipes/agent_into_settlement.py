#!/usr/bin/env python3
"""agent_into_settlement.py: structural save recipe: move a field agent into an own settlement, both ends of the link.

purpose: put an agent (gentleman, rake, assassin...) inside an own settlement: CHARACTER@7 = the residence id, @25 = True, its LOCOMOTABLE at the residence position, and its id appended to the residence's agent list @14 (pair agent-to-settlement)
usage: python3 -I saves/napoleon/recipes/agent_into_settlement.py IN.save OUT.save --region eur_england [--agent ID] [--list]
when: a save is needed with an agent inside a settlement (load ladder C; J4 scenarios); structural (a list grows), run on a copy. Own settlements only: a foreign one is what the pair did not show
not-a-verb: a save recipe run on the PC against saves outside the repo
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (AGENT_TYPES, CHAR_ID, CHAR_IN_RESIDENCE, CHAR_RESIDENCE, CHAR_TYPE, RES_AGENTS, RES_ID, RES_X, RES_Y,  # noqa: E402
                     SaveEdit, guard_paths, report)


def field_agents(se, fk):
    return [ck for ck in se.characters(fk) if ck[CHAR_TYPE].get() in AGENT_TYPES and ck[CHAR_RESIDENCE].get() == 0]


def apply(se, region, agent=None):
    if agent is None:
        key, fk, fid = se.faction(None)
        cands = field_agents(se, fk)
        if not cands:
            raise KeyError('the player faction %s has no agent in the field' % key)
        ck = cands[0]
    else:
        key, ck = se.character(agent)
        fid = se.faction(key)[2]
        if ck[CHAR_TYPE].get() not in AGENT_TYPES:
            raise ValueError('character %d is a %s, not an agent' % (agent, ck[CHAR_TYPE].get()))
        if ck[CHAR_RESIDENCE].get() != 0:
            raise ValueError('character %d is already in residence %d' % (agent, ck[CHAR_RESIDENCE].get()))
    res, owner = se.settlement(region)
    if owner != fid:
        raise ValueError('settlement of %s belongs to faction id %d, not %s (%d)' % (region, owner, key, fid))
    cid, rid = ck[CHAR_ID].get(), res[RES_ID].get()
    who = '%s %s %d' % (key, ck[CHAR_TYPE].get(), cid)
    se.setv(ck, CHAR_RESIDENCE, rid, '%s CHARACTER@%d residence' % (who, CHAR_RESIDENCE))
    se.setv(ck, CHAR_IN_RESIDENCE, True, '%s CHARACTER@%d in residence' % (who, CHAR_IN_RESIDENCE))
    se.move_char(ck, res[RES_X].get(), res[RES_Y].get(), who)
    se.list_edit(res, RES_AGENTS, add=cid, what='%s SIEGEABLE_GARRISON_RESIDENCE@%d agents' % (region, RES_AGENTS))
    return cid, rid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--region', help='db region key of an own settlement, e.g. eur_england')
    ap.add_argument('--agent', type=int, help='character id (default: the player faction\'s first field agent)')
    ap.add_argument('--list', action='store_true', help='list the player faction\'s field agents and settlements')
    a = ap.parse_args()
    guard_paths(a.inp, a.out)
    se = SaveEdit(a.inp)
    if a.list:
        key, fk, fid = se.faction(None)
        for ck in field_agents(se, fk):
            print('agent', ck[CHAR_ID].get(), ck[CHAR_TYPE].get())
        for rk in se.regions():
            try:
                res, owner = se.settlement(rk[0].get())
            except KeyError:
                continue
            if owner == fid:
                print('settlement', rk[0].get(), res[RES_ID].get(), 'agents', res[RES_AGENTS].get())
        return
    if not a.region:
        sys.exit('--region is required')
    apply(se, a.region, a.agent)
    se.save(a.out)
    report(se, a.out)


if __name__ == '__main__':
    main()
