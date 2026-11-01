"""Shared: image, Lua C API map (Napoleon.exe 9aebcd21), CFG builder, call/push simulation."""
import sys, re, struct, collections, json
sys.path.insert(0, r'C:\Users\liamr\repos\napoleon-remastered\discovery\core')
import x86re
EXE = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\Napoleon.exe'
im = x86re.Image(EXE)
T0, TSZ = im.text[1], im.text[2]
CODE = bytes(im.img[T0 - im.base:T0 - im.base + TSZ])
ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_.]*$')
LAPI_RANGE = (0xfe8b00, 0xfeaf00)
# from py/lua_core.py (masked Empire signatures, unique hits; the lapi block sits at Empire + 0xe1b70) plus by-hand reads (see md)
LAPI = {
 'luaL_argerror': 0xfea0c0, 'luaL_callmeta': 0xfea1b0, 'luaL_checkany': 0xfea210, 'luaL_checkinteger': 0xfea240,
 'luaL_checklstring': 0xfea280, 'luaL_checknumber': 0xfea2c0, 'luaL_checktype': 0xfea3f0, 'luaL_error': 0xfea490,
 'luaL_getmetafield': 0xfea5b0, 'luaL_optinteger': 0xfeaa30, 'luaL_typerror': 0xfeac20, 'luaL_register': 0xfeac00,
 'lua_createtable': 0xfe8d40, 'lua_getfield': 0xfe8f90, 'lua_getmetatable': 0xfe8ff0, 'lua_gettop': 0xfe9070,
 'lua_insert': 0xfe90d0, 'lua_isnumber': 0xfe9150, 'lua_pushboolean': 0xfe9440, 'lua_pushcclosure': 0xfe9460,
 'lua_pushfstring': 0xfe94f0, 'lua_pushinteger': 0xfe9520, 'lua_pushlightuserdata': 0xfe9540, 'lua_pushlstring': 0xfe9560,
 'lua_pushnil': 0xfe95a0, 'lua_pushnumber': 0xfe95c0, 'lua_pushstring': 0xfe95e0, 'lua_pushvalue': 0xfe9640,
 'lua_rawequal': 0xfe96a0, 'lua_setfield': 0xfe9990, 'lua_setmetatable': 0xfe99f0, 'lua_settable': 0xfe9aa0,
 'lua_settop': 0xfe9ad0, 'lua_toboolean': 0xfe9ba0, 'lua_tolstring': 0xfe9c40, 'lua_tonumber': 0xfe9cc0,
 'lua_topointer': 0xfe9d00, 'lua_touserdata': 0xfe9d70, 'lua_type': 0xfe9da0, 'lua_typename': 0xfe9dc0,
 'index2adr': 0xfe8b50,
 # by shape (callee pattern) and the block's alphabetical link order, read 2026-11-01:
 'lua_atpanic': 0xfe8c00, 'lua_call': 0xfe8c20, 'lua_checkstack': 0xfe8c60, 'lua_concat': 0xfe8cc0, 'lua_equal': 0xfe8dc0,
 'lua_error': 0xfe8e20, 'lua_gc': 0xfe8e30, 'lua_getfenv': 0xfe8f20, 'lua_getupvalue': 0xfe9080, 'lua_iscfunction': 0xfe9120,
 'lua_isstring': 0xfe9190, 'lua_lessthan': 0xfe91f0, 'lua_load': 0xfe9240, 'lua_newthread': 0xfe9280, 'lua_newuserdata': 0xfe92c0,
 'lua_next': 0xfe9310, 'lua_objlen': 0xfe9350, 'lua_pcall': 0xfe93c0, 'lua_pushthread': 0xfe9620, 'lua_pushvfstring': 0xfe9670,
 'lua_rawget': 0xfe96e0, 'lua_rawgeti': 0xfe9710, 'lua_rawset': 0xfe9740, 'lua_rawseti': 0xfe97b0, 'lua_replace': 0xfe9860,
 'lua_setfenv': 0xfe9910, 'lua_setupvalue': 0xfe9b20, 'lua_tocfunction': 0xfe9bd0, 'lua_tothread': 0xfe9d50, 'lua_xmove': 0xfe9de0,
 'luaL_checkoption': 0xfea320, 'luaL_checkstack': 0xfea3c0, 'luaL_checkudata': 0xfea420, 'luaL_findtable': 0xfea4c0,
 'luaL_newmetatable': 0xfea8c0, 'luaI_openlib': 0xfea920, 'luaL_optlstring': 0xfeaa60, 'luaL_optnumber': 0xfeaac0,
 'luaL_ref': 0xfeab50, 'luaL_unref': 0xfeac60, 'lua_gettable': 0xfe9040, 'lua_isuserdata': 0xfe91c0, 'lua_tointeger': 0xfe9c00, 'lua_remove': 0xfe9820,
}
NAME = {v: k for k, v in LAPI.items()}


def s32(v):
    return v - (1 << 32) if v & 0x80000000 else v


def cs(va, n=300):
    try:
        if im.section_of(va)[0] not in ('.rdata', '.data'):
            return None
        s = im.cstr(va, n)
        return s if s and all(c.isprintable() or c in '\r\n\t' for c in s) else None
    except Exception:
        return None


def insn(pc):
    return next(im.md.disasm(im.bytes_at(pc, 16), pc), None)


class CFG:
    """basic blocks of one function (recursive descent; direct jumps outside [entry, entry+0x8000) are tail calls)."""

    def __init__(s, entry, limit=6000):
        s.entry = entry; s.ins = {}; leaders = {entry}; todo = [entry]; s.tails = []; s.switch = False; s.itail = False
        edges = collections.defaultdict(set)
        while todo and len(s.ins) < limit:
            pc = todo.pop()
            while pc not in s.ins and im.in_text(pc):
                i = insn(pc)
                if i is None:
                    break
                s.ins[pc] = i; mn = i.mnemonic; nxt = pc + i.size
                if mn.startswith('ret') or mn == 'int3':
                    break
                if mn == 'jmp':
                    if i.op_str.startswith('0x'):
                        t = int(i.op_str, 16)
                        if entry <= t < entry + 0x8000:
                            todo.append(t); leaders.add(t); edges[pc].add(t)
                        else:
                            s.tails.append((pc, t))
                    else:
                        tab = im.jump_table(i.op_str, entry)
                        if tab:
                            s.switch = True; todo.extend(tab); leaders.update(tab); edges[pc].update(tab)
                        else:
                            s.itail = True
                    break
                if mn.startswith('j') or mn.startswith('loop'):
                    if i.op_str.startswith('0x'):
                        t = int(i.op_str, 16); todo.append(t); leaders.add(t); edges[pc].add(t)
                    leaders.add(nxt); edges[pc].add(nxt); todo.append(nxt)
                    break
                pc = nxt
        addrs = sorted(s.ins); s.blocks = {}; cur = None; prev_end = None
        for a in addrs:
            if a in leaders or cur is None or a != prev_end:
                cur = a; s.blocks[cur] = []
            s.blocks[cur].append(s.ins[a]); prev_end = a + s.ins[a].size
        s.succ = {}
        for b, il in s.blocks.items():
            last = il[-1]; nx = last.address + last.size; mn = last.mnemonic
            if last.address in edges:
                sc = set(edges[last.address])
            elif mn.startswith('ret') or mn == 'int3' or mn == 'jmp':
                sc = set()
            else:
                sc = {nx}
            s.succ[b] = {x for x in sc if x in s.blocks}
        s.back = set(); color = {s.entry: 1}; stack = [(s.entry, iter(sorted(s.succ.get(s.entry, ()))))]
        while stack:
            b, it = stack[-1]
            for c in it:
                if color.get(c) == 1:
                    s.back.add((b, c))
                elif c not in color:
                    color[c] = 1; stack.append((c, iter(sorted(s.succ.get(c, ()))))); break
            else:
                color[b] = 2; stack.pop()
        pred = collections.defaultdict(set)
        for x, ys in s.succ.items():
            for y in ys:
                pred[y].add(x)
        for b in s.blocks:
            ps = [x for x in pred[b]]
            if ps:
                tps = [tuple(trailing_pushes(s.blocks[x])) for x in ps]
                if all(t == tps[0] for t in tps) and tps[0]:
                    _seed[b] = list(tps[0])
        s.inloop = set()
        for (b, h) in s.back:   # loop body = blocks reachable from the header that can reach the latch
            fwd = {h}; wl = [h]
            while wl:
                x = wl.pop()
                for y in s.succ.get(x, ()):
                    if y not in fwd:
                        fwd.add(y); wl.append(y)
            bwd = {b}; wl = [b]
            while wl:
                x = wl.pop()
                if x == h:
                    continue
                for p in pred[x]:
                    if p not in bwd:
                        bwd.add(p); wl.append(p)
            s.inloop |= (fwd & bwd)

    def paths(s, weight):
        """(max, min) over acyclic paths from entry to an exit of sum(weight(block)); back edges ignored."""
        order = []; seen = {s.entry}; st = [(s.entry, iter(sorted(s.succ[s.entry])))]
        while st:
            x, it = st[-1]
            for c in it:
                if (x, c) in s.back or c in seen:
                    continue
                seen.add(c); st.append((c, iter(sorted(s.succ[c])))); break
            else:
                order.append(x); st.pop()
        order.reverse()
        mx = {b: None for b in order}; mn = {b: None for b in order}
        mx[s.entry] = mn[s.entry] = 0
        res_mx, res_mn = None, None
        for b in order:
            if mx[b] is None:
                continue
            w = weight(b); a, c = mx[b] + w, mn[b] + w
            outs = [x for x in s.succ[b] if (b, x) not in s.back]
            if not outs:
                res_mx = a if res_mx is None else max(res_mx, a); res_mn = c if res_mn is None else min(res_mn, c)
            for x in outs:
                if x not in mx:
                    continue
                mx[x] = a if mx[x] is None else max(mx[x], a)
                mn[x] = c if mn[x] is None else min(mn[x], c)
        return (res_mx or 0), (res_mn or 0)


def trailing_pushes(il):
    pushes = []
    for i in il:
        if i.mnemonic == 'push':
            pushes.append(i.op_str)
        elif i.mnemonic == 'call' or (i.mnemonic == 'add' and i.op_str.startswith('esp,')):
            pushes = []
    return pushes


_seed = {}


def calls_with_args(il, seed=None):
    """[(call insn, target or None, [arg operand strings: arg1 first])] with a per-block push simulation. MSVC hoists
    argument pushes above a conditional jump, so a block whose predecessors all end with the same pending pushes starts with them."""
    if seed is None:
        seed = _seed.get(il[0].address, [])
    out = []; pushes = list(seed)
    for i in il:
        if i.mnemonic == 'push':
            pushes.append(i.op_str)
        elif i.mnemonic == 'call':
            t = int(i.op_str, 16) if i.op_str.startswith('0x') else None
            out.append((i, t, list(reversed(pushes)))); pushes = []
        elif i.mnemonic == 'add' and i.op_str.startswith('esp,'):
            pushes = []
    return out


def imm(op):
    try:
        if op.startswith('0x'):
            return s32(int(op, 16))
        if op.startswith('-'):
            return -int(op[1:], 16) if op[1:].startswith('0x') else int(op)
        return int(op)
    except ValueError:
        return None
