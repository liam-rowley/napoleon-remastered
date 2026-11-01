"""Argument counting for Napoleon.exe Lua bindings (J9).

Reader ops (R0): functions whose own code reads a stack slot (lua_to*/lua_is*/lua_type/luaL_check*) and pops (lua_settop(L,-k),
lua_remove) without building a table (no settable/setfield/rawset/rawseti), under 400 insns; their consumption = -lowest stack
level reached (direct Lua API effects + nested reader ops). A getfield/read/pop field reader nets 0 and is not a reader op.
Any other function's count = max (and min) over acyclic CFG paths of the counts of the reader ops and functions it calls
(depth 3, callees under 3000 insns). Reader ops inside a loop of the counted function = variadic.
Direct constant positive indices (lua_to*(L, n) etc.) are reported separately (idx_max)."""
import collections
from lua_common import im, LAPI, NAME, CFG, calls_with_args, imm, LAPI_RANGE
from lua_effect import lapi_effect, IDX_ARG2

READS = {'lua_toboolean', 'lua_tolstring', 'lua_tonumber', 'lua_tointeger', 'lua_touserdata', 'lua_topointer', 'lua_tothread',
         'lua_tocfunction', 'lua_type', 'lua_isnumber', 'lua_isstring', 'lua_isuserdata', 'lua_iscfunction', 'luaL_checkany',
         'luaL_checkinteger', 'luaL_checklstring', 'luaL_checknumber', 'luaL_checktype', 'luaL_optinteger', 'luaL_optlstring',
         'luaL_optnumber', 'luaL_checkudata', 'lua_next', 'lua_objlen'}
BUILD = {'lua_settable', 'lua_setfield', 'lua_rawset', 'lua_rawseti'}
_cls = {}
TABLE_OPEN = set()
_cnt = {}


def direct_lapi(g):
    return [(NAME[t], args) for b in g.blocks.values() for (i, t, args) in calls_with_args(b) if t in NAME]


def reader_cons(f, depth=3):
    """consumption (int > 0) if f is a reader op, else 0"""
    if f in _cls:
        return _cls[f]
    _cls[f] = 0
    if not im.in_text(f) or LAPI_RANGE[0] <= f < LAPI_RANGE[1]:
        return 0
    g = CFG(f, limit=400)
    if len(g.ins) >= 400:
        return 0
    lap = direct_lapi(g)
    names = {n for n, a in lap}
    pops = any(n == 'lua_remove' or (n == 'lua_settop' and len(a) > 1 and (imm(a[1]) or 0) < 0) for n, a in lap)
    reads_top = any(n in READS and len(a) > 1 and imm(a[1]) == -1 for n, a in lap)
    if reads_top and not pops and not (names & BUILD) and 'lua_gettop' in names and len(g.ins) < 60             and any(n == 'lua_type' and len(a) > 1 and imm(a[1]) == -1 for n, a in lap)             and any(i.mnemonic == 'cmp' and i.op_str.endswith(', 5') for i in g.ins.values()):
        _cls[f] = 1          # table reader open: checks type(-1) == table and records gettop as the table's index
        TABLE_OPEN.add(f)
        return 1
    if not (names & READS) or not pops or (names & BUILD) or not reads_top:
        return 0
    # effect walk: lapi effects + nested reader ops
    low = walk_low(g, depth)
    _cls[f] = low
    return low


def walk_low(g, depth):
    order = topo(g)
    states = collections.defaultdict(set); states[g.entry].add((0, 0)); exits = []
    steps = {}
    for b, il in g.blocks.items():
        st = []; noret = False
        for (i, t, args) in calls_with_args(il):
            if t is None:
                continue
            if t in NAME:
                d, idx, nr, note = lapi_effect(NAME[t], args)
                if nr:
                    noret = True; break
                st.append((min(d, 0), d))
            elif depth > 0:
                c = reader_cons(t, depth - 1)
                if c:
                    st.append((-c, -c))
        steps[b] = (st, noret)
    for b in order:
        S = states[b]
        if not S:
            continue
        st, noret = steps[b]
        out = set()
        for (lv, lo) in S:
            for (sl, sd) in st:
                lo = min(lo, lv + sl); lv += sd
            out.add((lv, lo))
        out = set(sorted(out, key=lambda x: x[1])[:16])
        if noret:
            continue
        succ = [c for c in g.succ[b] if (b, c) not in g.back]
        if not succ:
            exits.extend(out)
        for c in succ:
            states[c] |= out
    return max([-lo for (lv, lo) in exits] + [0])


def topo(g):
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
    return order


def count(f, depth=3, limit=3000, top=False):
    """dict(max, min, loop, gettop, idx, ops, notes)"""
    key = (f, depth, top)
    if key in _cnt:
        return _cnt[key]
    _cnt[key] = dict(max=0, min=0, loop=False, gettop=False, idx=0, ops=[], notes=['recursion'], noret=False)
    g = CFG(f, limit=limit)
    notes = set()
    if len(g.ins) >= limit:
        notes.add('truncated')
    w = {}; gettop = False; idx = 0; ops = []; loop = False; noretb = set()
    for b, il in g.blocks.items():
        mx = mn = 0
        for (i, t, args) in calls_with_args(il):
            if t is None:
                notes.add('icall'); continue
            if t in NAME:
                n = NAME[t]
                if n == 'lua_gettop':
                    gettop = True
                if n in ('lua_error', 'luaL_error', 'luaL_argerror', 'luaL_typerror'):
                    noretb.add(b)
                a2 = imm(args[1]) if len(args) > 1 and args[1] else None
                if n in IDX_ARG2 and a2 is not None and 0 < a2 < 1000:
                    idx = max(idx, a2)
                continue
            if LAPI_RANGE[0] <= t < LAPI_RANGE[1]:
                continue
            c = reader_cons(t)
            if c:
                mx += c; mn += c; ops.append('%x' % t)
                if b in g.inloop:
                    loop = True
                # does the reader op check the top (lua_gettop) itself?
                continue
            if depth > 0 and im.in_text(t):
                s = count(t, depth - 1, limit=3000)
                gettop |= s['gettop']
                if s['max']:
                    mx += s['max']; mn += s['min']; ops.append('via:%x' % t)
                    if b in g.inloop:
                        loop = True
                    notes.add('reads_in_callee:%x' % t)
                if s['loop']:
                    loop = True; notes.add('loop_in_callee:%x' % t)
        for (pc, t) in g.tails:
            if pc == il[-1].address:
                c = reader_cons(t)
                if c:
                    mx += c; mn += c; ops.append('%x' % t)
                elif depth > 0:
                    s = count(t, depth - 1)
                    mx += s['max']; mn += s['min']; gettop |= s['gettop']
                    if s['max']:
                        notes.add('reads_in_tail:%x' % t)
        w[b] = (mx, mn)
    # paths
    order = topo(g)
    best = {g.entry: (0, 0)}; exits = []
    for b in order:
        if b not in best:
            continue
        a, c = best[b]; a += w[b][0]; c += w[b][1]
        if b in noretb:
            continue
        succ = [x for x in g.succ[b] if (b, x) not in g.back]
        if not succ:
            exits.append((a, c))
        for x in succ:
            if x in best:
                best[x] = (max(best[x][0], a), min(best[x][1], c))
            else:
                best[x] = (a, c)
    r = dict(max=max([e[0] for e in exits] + [0]), min=min([e[1] for e in exits]) if exits else 0, loop=loop, gettop=gettop,
             idx=idx, ops=ops, notes=sorted(notes), noret=not exits, n=len(g.ins))
    _cnt[key] = r
    return r


# ---------------------------------------------------------------- clamped effect walk (used for the deliverable)
_w2 = {}


def summary2(f, depth, strict=False):
    """(low, net, flags) of a non-reader callee under the clamped model."""
    key = (f, depth, strict)
    if key in _w2:
        return _w2[key]
    _w2[key] = (0, 0, dict(gettop=False, loop=False, idx=0, notes={'recursion'}))
    if not im.in_text(f) or LAPI_RANGE[0] <= f < LAPI_RANGE[1]:
        r = (0, 0, dict(gettop=False, loop=False, idx=0, notes=set()))
    else:
        g = CFG(f, limit=3000)
        if len(g.ins) >= 3000 or depth < 0:
            r = (0, 0, dict(gettop=False, loop=False, idx=0, notes={'big_callee:%x' % f}))
        else:
            res = walk2(g, depth, top=False, strict=strict)
            r = (res['low'], res['net'], res)
    _w2[key] = r
    return r


def walk2(g, depth, top=True, strict=False):
    steps = {}; gettop = False; idx = 0; notes = set(); ops = []
    for b, il in g.blocks.items():
        st = []; noret = False
        calls = calls_with_args(il)
        for (i, t, args) in calls:
            if t is None:
                notes.add('icall'); continue
            if t in NAME:
                n = NAME[t]
                if n == 'lua_gettop':
                    gettop = True
                if n == 'lua_type' and len(args) > 1 and imm(args[1]) == -1:
                    notes.add('peeks_top_type')
                if (n.startswith('lua_to') or n.startswith('lua_is') or n.startswith('luaL_check') or n.startswith('luaL_opt')) \
                        and len(args) > 1 and args[1] and imm(args[1]) is None and b in g.inloop and top:
                    notes.add('var_index_read_in_loop')
                if n in ('lua_call', 'lua_pcall') and len(args) > 1 and args[1] and imm(args[1]) is None:
                    notes.add('forwards_args' if top else 'callee_forwards_args')
                d, ix, nr, note = lapi_effect(n, args)
                if n in IDX_ARG2:
                    idx = max(idx, ix)
                if nr:
                    noret = True; break
                if n == 'lua_settop' and d < 0 and b not in g.inloop:
                    st.append(('read', d))       # discarding an argument (pop after a type peek) counts as consuming it
                else:
                    st.append(('clamp' if d < 0 else 'push', d))
                continue
            if LAPI_RANGE[0] <= t < LAPI_RANGE[1]:
                continue
            if t == 0x1058ed0:
                notes.add('peeks_top_type')
            if t == 0x1058750:
                st.append(('fetch', 0))
            c = reader_cons(t)
            if c:
                st.append(('read', -c)); ops.append('%x' % t); continue
            lo, net, fl = summary2(t, depth - 1, strict)
            if strict and lo < 0 and fl.get('n', 99999) > 80 and not fl.get('reader'):
                notes.add('via_skipped:%x(%d)' % (t, -lo)); gettop |= fl['gettop']
                st.append(('callee', (0, 0))); continue
            if strict and lo < 0 and fl.get('n', 99999) > 80:
                notes.add('reader_fetching_callee:%x(%d)' % (t, -lo))
            gettop |= fl['gettop']; notes |= {x for x in fl['notes'] if x != 'recursion'}
            if fl.get('loop'):
                notes.add('loop_in_callee:%x' % t)
            if lo < 0:
                ops.append('via:%x(%d)' % (t, -lo))
            st.append(('callee', (lo, net)))
        for (pc, t) in g.tails:
            if pc == il[-1].address:
                c = reader_cons(t)
                if c:
                    st.append(('read', -c)); ops.append('%x' % t)
                else:
                    lo, net, fl = summary2(t, depth - 1)
                    gettop |= fl['gettop']
                    st.append(('callee', (lo, net)))
        steps[b] = (st, noret)
    order = topo(g)
    states = collections.defaultdict(set); states[g.entry].add((0, 0, False)); exits = []; loop = False
    for b in order:
        S = states[b]
        if not S:
            continue
        st, noret = steps[b]
        out = set()
        for (lv, lo, fe) in S:
            for kind, v in st:
                if kind == 'fetch':
                    fe = True
                elif kind == 'read':
                    if lv + v < lo:
                        lo = lv + v
                        if b in g.inloop:
                            loop = True
                    lv += v
                elif kind == 'push':
                    lv += v
                elif kind == 'clamp':
                    lv = max(lv + v, lo)
                else:
                    clo, cnet = v
                    if lv + clo < lo:
                        lo = lv + clo
                        if b in g.inloop:
                            loop = True
                    lv = max(lv + cnet, lo)
            out.add((lv, lo, fe))
        if len(out) > 16:
            out = set(sorted(out, key=lambda x: (x[1], x[0]))[:8] + sorted(out, key=lambda x: (-x[1], -x[0]))[:8])
        if noret:
            continue
        succ = [c for c in g.succ[b] if (b, c) not in g.back]
        if not succ:
            exits.extend(out)
        for c in succ:
            states[c] |= out
    reader = any(k == 'fetch' for b in steps for k, v in steps[b][0])
    if not exits:
        return dict(low=0, net=0, max=0, min=0, gettop=gettop, idx=idx, loop=loop, notes=notes, ops=ops, noret=True, n=len(g.ins), reader=reader)
    worst = min(exits, key=lambda x: (x[1], x[0]))
    fetched = [e for e in exits if e[2]]
    mins = [-e[1] for e in (fetched or exits)]
    return dict(low=worst[1], net=worst[0], max=-worst[1], min=min(mins), gettop=gettop, idx=idx, loop=loop,
                notes=notes, ops=ops, noret=False, n=len(g.ins), reader=reader, pushed=sorted({e[0] - e[1] for e in exits}))
