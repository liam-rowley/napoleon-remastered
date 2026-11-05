"""Classify every numeric constant of a game's compiled UI scripts that reaches a pixel: scale, set, leave (with a reason) or manual.

purpose: walk every compiled UI script (Lua 5.1, core/discovery/luachunk.py) and list each numeric constant that reaches a pixel-taking engine call (MoveTo, Resize, CreateComponentFromTemplate x/y, ...) or a position or size calculation (arithmetic or a comparison with a value read from Width, Height, Bounds, Position, Dimensions, ScreenSize, ...), with script, function, pc, the call and a class; a game adapter's overrides correct the class with a reason
usage: from lua_consts import classify; doc = classify({script id: bytes}, overrides, empire_items)   (library; `python3 core/wsc.py uiscale lua-consts` writes uiscale/napoleon/lua_consts.json and lua_patches.txt)
when: J67 Lua pass of the UI scale stop-gap: before writing or changing a patch list, and after a game update (the classes are by vanilla pc)
not-a-verb: a library behind uiscale/napoleon/cli.py lua-consts

Static and best-effort, like core/discovery/ui_walk.py: a linear symbolic walk per function (branches are not merged), with values carried
through registers, upvalues (closure captures), globals and string-keyed table fields, into Lua functions called by a unique name (their
parameters) and back out of them (their returns), across all scripts, to a fixed point. Each constant use is a row; its role is how it
met the pixel value: an offset or size (scale), a pitch (multiplied by a loop index: scale), a threshold (compared with a pixel value:
scale), a ratio (multiplied or divided with a pixel value: leave), zero (leave). Every row gets a class; nothing stays unclassified.
"""
import collections
import struct

import luachunk
from luachunk import OPS, dec

BITRK = 256
# engine calls whose arguments are pixels: name -> argument positions (1-based, self excluded) or None for all
PIXEL_SINKS = {'MoveTo': None, 'Resize': None, 'SetStateTextXOffset': None, 'ScalePosition': None,
               'CreateComponentFromTemplate': (4, 5), 'CreateFromLayout': (4, 5), 'CreateFromComponent': (4, 5),
               'SetImageMetrics': (2, 3, 4, 5)}
# engine calls whose results are pixels
PIXEL_SOURCES = {'Width', 'Height', 'Bounds', 'Position', 'Dimensions', 'WidthOfTextLine', 'RootDimensions', 'CursorPosition',
                 'ScreenSize', 'ImageMetrics', 'DistanceToBL'}
# Lua helpers that pass their arguments' values through (min, max, clamp, rounding): not followed into, so one caller's
# constants do not leak into another caller's result
TRANSPARENT = {'TruncToInt', 'RoundToInt', 'RupToInt', 'Clamp', 'Max', 'Min', 'floor', 'ceil', 'abs', 'max', 'min'}
COMPARING = {'Clamp', 'Max', 'Min', 'max', 'min'}
# string keys of a table an engine call reads as pixels (SetStateTextDetails-style option tables)
PIXEL_FIELDS = {'XOffset', 'YOffset'}

# orig: frozenset of (origin, role); origin = (script, func, k, pc) or ('param', i) inside a callee
# pix: frozenset of where the pixel-ness comes from: 'own' (a pixel getter) or ('param', i) (a caller's argument)
Val = collections.namedtuple('Val', 'orig pix idx fn')
NOPIX = frozenset()
PIX = frozenset({'own'})
EMPTY = Val(frozenset(), NOPIX, False, None)


def num(f, ki):
    t, v = f.k[ki]
    return struct.unpack('<f', v)[0] if t == 'num' else None


def kstr(f, ki):
    t, v = f.k[ki]
    return v.decode('latin1') if t == 'str' else None


def show(x):
    return int(x) if x == int(x) else round(x, 6)


class Walker:
    def __init__(s, chunks):
        s.chunks = chunks                                    # script id -> luachunk.Chunk
        s.env = collections.defaultdict(lambda: EMPTY)       # ('g', name) | ('f', field) | ('pin', fid, i) | ('ret', fid) -> Val
        s.uses = {}                                          # (origin, role, sink) -> None (ordered set)
        s.defs = collections.defaultdict(set)                # Lua function name -> {fid}; fid = (script, func name)
        s.protos = {}                                        # fid -> Func
        for sid, ch in chunks.items():
            for name, f in ch.main.walk():
                s.protos[(sid, name)] = f
        for sid, ch in chunks.items():
            for name, f in ch.main.walk():
                s._defs(sid, name, f)

    def _defs(s, sid, name, f):
        for pc, w in enumerate(f.code):
            d = dec(w)
            if OPS[d['OP']] != 'CLOSURE':
                continue
            child = (sid, f'{name}#{d["Bx"]}')
            nup = s.protos[child].nups
            for q in range(pc + 1 + nup, min(pc + 4 + nup, len(f.code))):   # where the closure register is stored
                e = dec(f.code[q]); o = OPS[e['OP']]
                if o == 'SETGLOBAL' and e['A'] == d['A']:
                    s.defs[kstr(f, e['Bx'])].add(child); break
                if o == 'SETTABLE' and e['C'] == d['A'] and e['B'] >= BITRK and kstr(f, e['B'] - BITRK):
                    s.defs[kstr(f, e['B'] - BITRK)].add(child); break
                if o != 'MOVE' and o != 'GETUPVAL':
                    break

    def callee(s, fn):
        if not fn or fn[0] == 'engine':
            return None
        c = s.defs.get(fn[1])
        return next(iter(c)) if c and len(c) == 1 else None

    def merge(s, key, v):
        old = s.env[key]
        if key[0] in ('g', 'f', 'u'):                      # a constant stored where a pixel value is stored is a pixel too
            if old.pix and not v.pix and v.orig:
                s.use(v, 'stored with a pixel value')
            elif v.pix and not old.pix and old.orig:
                s.use(old, 'stored with a pixel value')
        new = Val(old.orig | v.orig, old.pix | v.pix, old.idx or v.idx, old.fn or v.fn)
        if new != old:
            s.env[key] = new; s.changed = True

    def use(s, v, sink, role=None):
        for o, r in v.orig:
            if o[0] != 'param':
                s.uses.setdefault((o, role or r, sink), None)

    def run(s, rounds=6):
        for _ in range(rounds):
            s.changed = False
            for (sid, name), f in s.protos.items():
                s.walk(sid, name, f)
            if not s.changed:
                break

    # ------------------------------------------------------------------------------------------------ one function
    def walk(s, sid, name, f):
        fid = (sid, name)
        R = {}
        skip = {}                                            # pcs of a closure's upvalue pseudo-instructions
        for i in range(f.nparams):
            v = s.env[('pin', fid, i)]
            mark = ('param', fid, i)                       # this parameter, for a caller to swap for its own argument
            R[i] = Val(v.orig | {(mark, 'offset')}, v.pix | ({mark} if v.pix else NOPIX), v.idx, None)
        upn = [(u or b'?').decode('latin1') for u in f.upvals] + ['?'] * f.nups

        def rk(x, pc):
            if x >= BITRK:
                v = num(f, x - BITRK)
                if v is None:
                    return EMPTY, None
                return Val(frozenset({((sid, name, x - BITRK, pc), 'offset')}), NOPIX, False, None), v
            return R.get(x, EMPTY), None

        code = f.code
        cond = conditional_pcs(code)

        def put(r, v, pc):                                   # a load inside a branch joins what the other branch loaded
            old = R.get(r)
            if cond[pc] and old is not None and old.orig and not old.pix and not v.pix:
                v = Val(old.orig | v.orig, NOPIX, old.idx and v.idx, v.fn)
            elif cond[pc] and old is not None and old.pix and not v.pix and v.orig:
                s.use(v, 'one branch of a pixel value')       # x = Width() ... else x = 1280
            R[r] = v

        loops = loop_pcs(code)
        for pc in list(range(len(code))) + loops:            # loop bodies twice: a value set at a loop's end reaches its start
            if skip.get(pc):
                continue
            d = dec(code[pc]); o = OPS[d['OP']]; a, b, c, bx = d['A'], d['B'], d['C'], d['Bx']
            if o == 'MOVE':
                put(a, R.get(b, EMPTY), pc)
            elif o == 'LOADK':
                v = num(f, bx)
                put(a, Val(frozenset({((sid, name, bx, pc), 'offset')}), NOPIX, False, None) if v is not None else EMPTY, pc)
            elif o in ('LOADBOOL', 'NEWTABLE', 'CONCAT', 'NOT', 'VARARG'):
                R[a] = EMPTY
            elif o == 'LOADNIL':
                for r in range(a, b + 1):
                    R[r] = EMPTY
            elif o == 'LEN':
                R[a] = Val(frozenset(), NOPIX, True, None)
            elif o == 'GETUPVAL':
                R[a] = s.env[('u', sid, upn[b])]
            elif o == 'SETUPVAL':
                s.merge(('u', sid, upn[b]), R.get(a, EMPTY))
            elif o == 'GETGLOBAL':
                g = kstr(f, bx)
                v = s.env[('g', g)]
                R[a] = Val(v.orig, v.pix, v.idx, ('global', g))
            elif o == 'SETGLOBAL':
                s.merge(('g', kstr(f, bx)), R.get(a, EMPTY))
            elif o in ('GETTABLE', 'SELF'):
                key = kstr(f, c - BITRK) if c >= BITRK else None
                base = R.get(b, EMPTY)
                if o == 'SELF':
                    R[a + 1] = base
                    R[a] = Val(frozenset(), NOPIX, False, ('method', key))
                elif key is not None:
                    v = s.env[('f', key)]
                    R[a] = Val(v.orig, v.pix, v.idx, ('field', key))
                else:
                    R[a] = Val(base.orig if base.pix else frozenset(), base.pix, False, None)   # t[i] of a pixel table stays pixel
            elif o == 'SETTABLE':
                key = kstr(f, b - BITRK) if b >= BITRK else None
                v, _ = rk(c, pc)
                if key is not None:
                    s.merge(('f', key), v)
                    if key in PIXEL_FIELDS:
                        s.use(v, f'field {key} of an engine option table')
            elif o in ('ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'POW'):
                x, _ = rk(b, pc); y, _ = rk(c, pc)
                put(a, s.arith(o, x, y, f'{o} with a pixel value'), pc)
            elif o == 'UNM':
                R[a] = R.get(b, EMPTY)
            elif o in ('EQ', 'LT', 'LE'):
                x, _ = rk(b, pc); y, _ = rk(c, pc)
                if x.pix and not y.pix:
                    s.use(y, f'{o} with a pixel value', 'threshold')
                elif y.pix and not x.pix:
                    s.use(x, f'{o} with a pixel value', 'threshold')
            elif o in ('CALL', 'TAILCALL'):
                s.call(f, fid, R, pc, a, b, c)
            elif o == 'RETURN':
                if b > 1:
                    for i in range(b - 1):
                        s.merge(('ret', fid, i), R.get(a + i, EMPTY))
            elif o == 'FORPREP':
                lim = R.get(a + 1, EMPTY)
                if lim.pix:                                  # a loop over pixels: its start and step are pixels too
                    s.use(R.get(a, EMPTY), 'numeric for over a pixel range', 'offset')
                    s.use(R.get(a + 2, EMPTY), 'numeric for over a pixel range', 'pitch')
                    R[a + 3] = Val(frozenset(), PIX, False, None)
                else:
                    R[a + 3] = Val(frozenset(), NOPIX, True, None)
            elif o == 'TFORLOOP':
                R[a + 3] = Val(frozenset(), NOPIX, True, None)
                for i in range(2, c + 1):
                    R[a + 2 + i] = EMPTY
            elif o == 'CLOSURE':
                child = (sid, f'{name}#{bx}')
                cf = s.protos[child]
                for i in range(cf.nups):
                    e = dec(code[pc + 1 + i])
                    if OPS[e['OP']] == 'MOVE':                 # a local captured by name (a captured upvalue is already keyed so)
                        s.merge(('u', sid, (cf.upvals[i] or b'?').decode('latin1')), R.get(e['B'], EMPTY))
                R[a] = Val(frozenset(), NOPIX, False, ('closure', child))
                for i in range(cf.nups):
                    skip[pc + 1 + i] = True

    def arith(s, o, x, y, sink):
        if o in ('ADD', 'SUB'):
            if x.idx and not (y.pix or x.pix):
                return Val(frozenset(), NOPIX, True, None)  # index arithmetic (i - 1)
            if y.idx and not (x.pix or y.pix):
                return Val(frozenset(), NOPIX, True, None)
            if x.pix and not y.pix:
                s.use(y, sink)
            elif y.pix and not x.pix:
                s.use(x, sink)
            return Val(x.orig | y.orig, x.pix | y.pix, False, None)
        # MUL DIV MOD POW
        if x.pix and y.pix:
            return Val(x.orig | y.orig, x.pix | y.pix, False, None)
        if x.pix or y.pix:
            p, q = (x, y) if x.pix else (y, x)
            s.use(q, f'{o} with a pixel value', 'ratio')
            return Val(p.orig, p.pix, False, None)
        if x.idx or y.idx:                                   # i * 66: the other operand is a pitch
            q = y if x.idx else x
            return Val(frozenset((org, 'pitch') for org, _ in q.orig), NOPIX, False, None)
        if o == 'MUL' and x.orig and y.orig:
            return Val(frozenset((org, 'product') for org, _ in x.orig | y.orig), NOPIX, False, None)
        if o in ('DIV', 'MOD', 'POW'):                        # K1 / K2: the divisor is a ratio if the result reaches a pixel
            return Val(x.orig | frozenset((org, 'ratio') for org, _ in y.orig), NOPIX, False, None)
        return Val(x.orig | y.orig, NOPIX, False, None)

    def call(s, f, fid, R, pc, a, b, c):
        fv = R.get(a, EMPTY); fn = fv.fn
        nargs = (b - 1) if b else max([0] + [r - a for r in R if r > a])
        args = [R.get(a + 1 + i, EMPTY) for i in range(nargs)]
        name = fn[1] if fn else None
        self_call = fn is not None and fn[0] == 'method'
        eargs = args[1:] if self_call else args
        if name == 'CallByAddress':                          # Component.CallByAddress(address, 'Method', args...)
            meth = loaded_string(f, pc, a + 2)
            if meth in PIXEL_SINKS or meth in PIXEL_SOURCES:
                name, eargs = meth, args[2:]
        if name in PIXEL_SINKS:
            pos = PIXEL_SINKS[name]
            for i, v in enumerate(eargs, 1):
                if pos is None or i in pos:
                    s.use(v, f'arg {i} of {name}', 'size' if name == 'Resize' else None)
        nres = (c - 1) if c else 1
        res = [EMPTY] * max(nres, 1)
        if name in PIXEL_SOURCES:
            res = [Val(frozenset(), PIX, False, None)] * len(res)
        elif name in TRANSPARENT:
            pix = frozenset().union(*[v.pix for v in eargs]) if eargs else NOPIX
            if name in COMPARING and pix:
                for v in eargs:
                    if not v.pix:
                        s.use(v, f'bound of {name} with a pixel value', 'threshold')
            orig = frozenset().union(*[v.orig for v in eargs]) if eargs else frozenset()
            res[0] = Val(orig, pix, any(v.idx for v in eargs), None)
        else:
            tgt = s.callee(fn)
            if tgt and tgt != fid:
                for i, v in enumerate(args):
                    s.merge(('pin', tgt, i), v)
                for i in range(len(res)):
                    rv = s.env[('ret', tgt, i)]
                    orig = set(); pix = set()
                    for o, role in rv.orig:                  # a returned parameter is this call's argument
                        if o[0] == 'param' and o[1] == tgt:
                            if o[2] < len(args):
                                orig |= args[o[2]].orig
                        else:
                            orig.add((o, role))
                    for q in rv.pix:
                        if isinstance(q, tuple) and q[0] == 'param' and q[1] == tgt:
                            if q[2] < len(args) and args[q[2]].pix:
                                pix.add('own')
                        else:
                            pix.add(q)
                    res[i] = Val(frozenset(orig), frozenset(pix), rv.idx, None)
        for r in [r for r in R if r >= a]:
            del R[r]
        for i, v in enumerate(res):
            R[a + i] = v


def conditional_pcs(code):
    """[bool per pc]: inside the body of a forward jump (an if, an else, the `a and K or L` idiom)"""
    cond = [False] * (len(code) + 1)
    for pc, w in enumerate(code):
        d = dec(w)
        if OPS[d['OP']] == 'JMP' and d['sBx'] > 0:
            for q in range(pc + 1, min(pc + 1 + d['sBx'], len(code))):
                cond[q] = True
            if pc + 1 + d['sBx'] < len(code):
                cond[pc + 1 + d['sBx']] = True               # the else branch's first load
    return cond


def loaded_string(f, pc, reg):
    """the string constant register reg holds at pc, if a LOADK put it there within the last few instructions"""
    for q in range(pc - 1, max(pc - 8, -1), -1):
        d = dec(f.code[q])
        if d['A'] == reg and OPS[d['OP']] not in ('EQ', 'LT', 'LE', 'TEST', 'JMP', 'SETTABLE', 'SETGLOBAL', 'SETUPVAL', 'RETURN'):
            return kstr(f, d['Bx']) if OPS[d['OP']] == 'LOADK' else None
    return None


def loop_pcs(code):
    """the pcs of every loop body (a backward JMP or FORLOOP to its target), in order, each once"""
    out = set()
    for pc, w in enumerate(code):
        d = dec(w)
        if OPS[d['OP']] in ('JMP', 'FORLOOP') and d['sBx'] < 0:
            out.update(range(pc + 1 + d['sBx'], pc + 1))
    return sorted(out)


def all_k_uses(f, ki):
    """every pc that references numeric constant ki (LOADK or an RK operand)"""
    out = []
    for pc, w in enumerate(f.code):
        d = dec(w); o = OPS[d['OP']]
        if o == 'LOADK' and d['Bx'] == ki:
            out.append(pc)
        elif o in luachunk.LAYOUT and any(p.endswith(':RK') for p in luachunk.LAYOUT[o].split()):
            if (d['B'] == ki + BITRK and 'B:RK' in luachunk.LAYOUT[o]) or (d['C'] == ki + BITRK and 'C:RK' in luachunk.LAYOUT[o]):
                out.append(pc)
    return out


def auto_class(value, role):
    if role == 'ratio':
        return 'leave', 'a ratio of a pixel value (multiplied or divided with it): the pixel value scales already'
    if value == 0:
        return 'leave', 'zero: scaling changes nothing'
    if abs(value) == 1:
        return 'leave', 'one: an index step or sentinel far more often than a pixel (a 1-px nudge left unscaled is under 1 px off at 2x)'
    if abs(value) >= 9999:
        return 'leave', 'a sentinel (an impossible size used as a start value for a min or max)'
    if abs(value) < 1:
        return 'leave', 'a fraction: a ratio, an interpolation factor or an epsilon, not a pixel'
    if role == 'product':
        return 'manual', 'one factor of a constant product reaches a pixel value: which factor is the pixel needs a look'
    return 'scale', f'a pixel {role}'


def classify(scripts, overrides=None, empire=None, rounds=6):
    """scripts: {script id: chunk bytes}; overrides: [{script, func, k, [pc], class, reason}]; empire: {script id: [item text]}"""
    chunks = {sid: luachunk.parse(b) for sid, b in sorted(scripts.items())}
    w = Walker(chunks)
    w.run(rounds)
    rows = {}
    for (o, role, sink) in w.uses:
        sid, name, ki, pc = o
        f = w.protos[(sid, name)]
        key = (sid, name, ki, pc)
        r = rows.setdefault(key, {'script': sid, 'func': name, 'k': ki, 'pc': pc, 'value': show(num(f, ki)),
                                  'instr': luachunk.fmt(f, f.code[pc], pc), 'roles': set(), 'sinks': set()})
        r['roles'].add(role); r['sinks'].add(sink)
    ov = {}
    for o in overrides or []:
        ov[(o['script'], o['func'], o['k'], o.get('pc'))] = o
    out = []
    for key in sorted(rows):
        r = rows[key]
        roles = r.pop('roles'); sinks = r.pop('sinks')
        role = 'ratio' if roles == {'ratio'} else sorted(roles - {'ratio'})[0]
        if 'ratio' in roles and roles - {'ratio'}:
            role = 'mixed'
        r['role'] = role
        r['call'] = '; '.join(sorted(sinks))
        cls, why = ('manual', 'the same load is a ratio on one path and a pixel on another') if role == 'mixed' else auto_class(r['value'], role)
        o = ov.get((r['script'], r['func'], r['k'], r['pc'])) or ov.get((r['script'], r['func'], r['k'], None))
        if o:
            cls, why = o['class'], o['reason']
            if 'value' in o:
                r['set'] = o['value']
            r['by'] = 'override'
        else:
            r['by'] = 'rule'
        r['class'] = cls; r['reason'] = why
        out.append(r)
    # Empire cross-check: which of Empire's constant items name a (func, K) that is a row here
    emp = []
    for sid, items in sorted((empire or {}).items()):
        for it in items:
            if '@' in it.split('=')[0]:
                fn, rest = it.split('@', 1); kind = 'instr'
                ref = rest.split('[')[0].split('=')[0].split('+')[0]
            else:
                fn, ki = it.split('=')[0].rsplit(':', 1); kind = 'const'; ref = ki
            hit = [r for r in out if r['script'] == sid and r['func'] == fn and (
                str(r['k']) == ref if kind == 'const' else str(r['pc']) == ref)]
            emp.append({'script': sid, 'item': it, 'napoleon_rows': len(hit),
                        'napoleon_class': sorted({r['class'] for r in hit}), 'in_napoleon': sid in scripts})
    for r in out:
        f = w.protos[(r['script'], r['func'])]
        r['k_uses'] = len(all_k_uses(f, r['k']))
    return {'rows': out, 'empire': emp}


def counts(doc):
    c = collections.Counter(r['class'] for r in doc['rows'])
    return dict(sorted(c.items()))
