"""Stack-effect model for Napoleon.exe Lua bindings: per function, the lowest Lua stack level reached relative to entry
(= arguments consumed by pop-style readers), the net effect, constant positive indices read, lua_gettop use, loops.

A state is (level, low): level = stack height relative to function entry, low = lowest level seen. Lua API calls change
the level by their documented effect; engine callees are summarised recursively (depth 4, < 1500 insns) as (net, low) of
their most-consuming exit. Back edges are ignored (a loop body is walked once); consumption inside a loop of the binding
itself marks it variadic."""
import collections
from lua_common import im, LAPI, NAME, CFG, calls_with_args, imm, LAPI_RANGE

L = LAPI
PLUS1 = {'lua_pushboolean', 'lua_pushnumber', 'lua_pushinteger', 'lua_pushstring', 'lua_pushlstring', 'lua_pushnil',
         'lua_pushvalue', 'lua_pushfstring', 'lua_pushvfstring', 'lua_pushlightuserdata', 'lua_pushthread', 'lua_createtable',
         'lua_newuserdata', 'lua_newthread', 'lua_getfield', 'lua_rawgeti', 'lua_getmetatable', 'lua_getfenv',
         'luaL_newmetatable'}
ZERO = {'lua_gettable', 'lua_rawget', 'lua_insert', 'lua_objlen', 'lua_gettop', 'lua_checkstack', 'luaL_checkstack',
        'luaL_getmetafield', 'luaL_callmeta', 'lua_type', 'lua_typename', 'lua_toboolean', 'lua_tolstring', 'lua_tonumber',
        'lua_tointeger', 'lua_touserdata', 'lua_topointer', 'lua_tothread', 'lua_tocfunction', 'lua_isnumber', 'lua_isstring',
        'lua_isuserdata', 'lua_iscfunction', 'lua_rawequal', 'lua_equal', 'lua_lessthan', 'luaL_checkany', 'luaL_checkinteger',
        'luaL_checklstring', 'luaL_checknumber', 'luaL_checktype', 'luaL_optinteger', 'luaL_optlstring', 'luaL_optnumber',
        'luaL_checkudata', 'luaL_checkoption', 'luaL_unref', 'index2adr', 'lua_gc', 'lua_atpanic', 'lua_xmove'}
MINUS1 = {'lua_setfield', 'lua_rawseti', 'lua_setmetatable', 'lua_setfenv', 'lua_remove', 'lua_replace', 'luaL_ref', 'lua_next'}
MINUS2 = {'lua_settable', 'lua_rawset'}
NORETURN = {'lua_error', 'luaL_error', 'luaL_argerror', 'luaL_typerror'}
IDX_ARG2 = {'lua_toboolean', 'lua_tolstring', 'lua_tonumber', 'lua_tointeger', 'lua_touserdata', 'lua_topointer', 'lua_tothread',
            'lua_tocfunction', 'lua_type', 'lua_isnumber', 'lua_isstring', 'lua_isuserdata', 'lua_iscfunction', 'lua_getfield',
            'lua_gettable', 'lua_rawget', 'lua_rawgeti', 'lua_pushvalue', 'lua_getmetatable', 'lua_objlen', 'lua_next',
            'luaL_checkany', 'luaL_checkinteger', 'luaL_checklstring', 'luaL_checknumber', 'luaL_checktype', 'luaL_optinteger',
            'luaL_optlstring', 'luaL_optnumber', 'luaL_checkudata', 'luaL_checkoption', 'luaL_typerror', 'luaL_argerror',
            'lua_rawequal', 'lua_equal', 'lua_lessthan', 'luaL_getmetafield', 'luaL_callmeta', 'lua_remove', 'lua_insert',
            'lua_replace', 'lua_getfenv'}
READER = 0x1058750
MAXSTATES = 24

_sum = {}


def lapi_effect(name, args):
    """(delta, idx read or 0, noreturn, note)"""
    a = [imm(x) if x else None for x in args]
    a2 = a[1] if len(a) > 1 else None
    idx = a2 if (name in IDX_ARG2 and a2 is not None and 0 < a2 < 1000) else 0
    if name in ('lua_rawequal', 'lua_equal', 'lua_lessthan') and len(a) > 2 and a[2] is not None and 0 < a[2] < 1000:
        idx = max(idx, a[2])
    if name in NORETURN:
        return 0, idx, True, None
    if name in PLUS1:
        return 1, idx, False, None
    if name in ZERO:
        return 0, idx, False, None
    if name in MINUS1:
        return -1, idx, False, None
    if name in MINUS2:
        return -2, idx, False, None
    if name == 'lua_settop':
        if a2 is not None and a2 < 0:
            return a2 + 1, 0, False, None
        return 0, 0, False, 'settop_abs:%s' % a2
    if name == 'lua_pushcclosure':
        n = a[2] if len(a) > 2 and a[2] is not None else 0
        return 1 - n, 0, False, None
    if name in ('lua_call', 'lua_pcall'):
        na = a[1] if len(a) > 1 and a[1] is not None else None
        nr = a[2] if len(a) > 2 and a[2] is not None else None
        if na is None or nr is None:
            return 0, 0, False, 'call_unknown'
        return -(na + 1) + max(nr, 0), 0, False, None
    if name == 'lua_concat':
        n = a2 if a2 is not None else 1
        return -(n - 1), 0, False, None
    return 0, 0, False, 'lapi_unmodelled:%s' % name


def summary(f, depth):
    if f in _sum:
        return _sum[f]
    _sum[f] = dict(net=0, low=0, gettop=False, idx=0, big=False, loop=False, notes=[], noret=False)   # recursion guard
    if not im.in_text(f):
        r = dict(net=0, low=0, gettop=False, idx=0, big=False, loop=False, notes=[], noret=False)
    else:
        g = CFG(f, limit=1500)
        if len(g.ins) >= 1500 or depth <= 0:
            r = dict(net=0, low=0, gettop=False, idx=0, big=True, loop=False, notes=[], noret=False, n=len(g.ins))
        else:
            r = run(g, depth - 1)
    _sum[f] = r
    return r


def block_ops(g, b, depth):
    """list of (low_rel, delta) steps for the block, plus flags"""
    steps = []; fl = dict(gettop=False, idx=0, notes=set(), noret=False, reader=False, topconsume=False)
    il = g.blocks[b]
    for (i, t, args) in calls_with_args(il):
        if t is None:
            fl['notes'].add('icall'); continue
        if t in NAME:
            d, idx, nr, note = lapi_effect(NAME[t], args)
            fl['idx'] = max(fl['idx'], idx)
            if note:
                fl['notes'].add(note)
            if NAME[t] == 'lua_gettop':
                fl['gettop'] = True
            if nr:
                fl['noret'] = True; break
            steps.append((min(d, 0), d))
            continue
        if LAPI_RANGE[0] <= t < LAPI_RANGE[1]:
            fl['notes'].add('lapi_unknown:%x' % t); continue
        if t == READER:
            fl['reader'] = True
        s = summary(t, depth)
        fl['gettop'] |= s['gettop']
        if s['big']:
            fl['notes'].add('big_callee:%x' % t)
        if s.get('noret'):
            fl['noret'] = True; break
        steps.append((s['low'], s['net']))
    last = il[-1]
    for (pc, t) in g.tails:
        if pc == last.address:
            s = summary(t, depth)
            fl['gettop'] |= s['gettop']
            if s['big']:
                fl['notes'].add('big_callee:%x' % t)
            steps.append((s['low'], s['net']))
    return steps, fl


def run(g, depth, top=False):
    ops = {b: block_ops(g, b, depth) for b in g.blocks}
    # topological order ignoring back edges
    order = []; seen = {g.entry}; st = [(g.entry, iter(sorted(g.succ[g.entry])))]
    while st:
        x, it = st[-1]
        for c in it:
            if (x, c) in g.back or c in seen:
                continue
            seen.add(c); st.append((c, iter(sorted(g.succ[c])))); break
        else:
            order.append(x); st.pop()
    order.reverse()
    states = collections.defaultdict(set); states[g.entry].add((0, 0))
    exits = []
    loop_consume = False
    for b in order:
        S = states[b]
        if not S:
            continue
        steps, fl = ops[b]
        out = set()
        for (lv, lo) in S:
            for (sl, sd) in steps:
                if lv + sl < lo:
                    lo = lv + sl
                    if b in g.inloop and top:
                        loop_consume = True
                lv += sd
            out.add((lv, lo))
        if len(out) > MAXSTATES:
            out = set(sorted(out, key=lambda x: (x[1], -x[0]))[:MAXSTATES // 2] + sorted(out, key=lambda x: (-x[1], x[0]))[:MAXSTATES // 2])
        if fl['noret']:
            continue        # error path: does not return to the caller
        succ = [c for c in g.succ[b] if (b, c) not in g.back]
        if not succ:
            exits.extend(out)
        for c in succ:
            states[c] |= out
    gettop = any(ops[b][1]['gettop'] for b in g.blocks)
    idx = max([ops[b][1]['idx'] for b in g.blocks] + [0])
    notes = sorted({n for b in g.blocks for n in ops[b][1]['notes']})
    reader = any(ops[b][1]['reader'] for b in g.blocks)
    if not exits:
        return dict(net=0, low=0, gettop=gettop, idx=idx, big=False, loop=False, notes=notes, noret=True, reader=reader)
    worst = min(exits, key=lambda x: (x[1], x[0]))
    lows = sorted({-lo for (lv, lo) in exits})
    pushed = sorted({lv - lo for (lv, lo) in exits})
    return dict(net=worst[0], low=worst[1], gettop=gettop, idx=idx, big=False, loop=loop_consume, notes=notes, noret=False,
                reader=reader, consumed_set=lows, pushed_set=pushed, n=len(g.ins), switch=g.switch)


def analyse(f):
    g = CFG(f, limit=8000)
    r = run(g, 4, top=True)
    if len(g.ins) >= 8000:
        r['notes'].append('truncated')
    return r
