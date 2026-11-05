"""Check a UI scale factor against a screen: each layout's scaled extent, abutting pairs, and the fonts its scaled layouts name.

purpose: for each vanilla layout (core/discovery/uic.py), scale it at a factor (scale.py) and report its scaled root, the extent of its components against the screen (a layout taller or wider than the screen loses content), abutting sibling pairs that gap or overlap after scaling, and every font name of the scaled layouts against the slot table for that factor
usage: from check import check_layouts; rep = check_layouts([(path, bytes)], 1.5, 2560, 1440, slots)   (library; `python3 core/wsc.py uiscale check --factor F --height H` prints it)
when: choosing the 1440p factor (J67: 1.25 or 1.5) and before shipping any factor; ported from the idea of empire-remastered origin/ui/multiscale multiscale_check.py
not-a-verb: a library behind uiscale/napoleon/cli.py check

Positions are parent-relative, so a component's absolute rect is the sum of its parents' x/y plus its own and its first state's w/h.
Docking is not applied (the extent is the layout's own coordinate box), the same approximation Empire's check made.
"""
import copy

PARKED = 4000          # a component placed this far out is parked off screen by design (the tooltips park theirs near x = 10000)
BLEED = 1              # vanilla pixels: a full-canvas page drawn 1 px past the 1280x960 root (credits, load pages: 1280x961) loses no content
BASELINE = (1.0, 1920, 1080)   # what a layout is measured against: vanilla at 1080p (the 2x build at 3840x2160 is the same box)

import scale
import uic


def rects(c, ox=0, oy=0, out=None, depth=0):
    """[(abs x, abs y, w, h, name, depth)] of a component tree, vanilla pixels"""
    out = [] if out is None else out
    ax, ay = ox + c['x'], oy + c['y']
    st = c['states'][0] if c['states'] else {'w': 0, 'h': 0}
    out.append((ax, ay, st['w'], st['h'], c.get('name', ''), depth))
    for ch in c['children']:
        rects(ch, ax, ay, out, depth + 1)
    return out


def extent(doc):
    """(x0, y0, x1, y1) of every component below the root, vanilla pixels; None for an empty layout"""
    rs = [r for r in rects(doc['root']) if r[5] > 0 and (r[2] or r[3]) and abs(r[0]) < PARKED and abs(r[1]) < PARKED]
    if not rs:
        return None
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[0] + r[2] for r in rs), max(r[1] + r[3] for r in rs))


def abutting(van, sc):
    """sibling pairs that touch in vanilla (a.x + a.w == b.x or a.y + a.h == b.y) and gap or overlap after scaling"""
    bad = []

    def walk(cv, cs):
        kids = list(zip(cv['children'], cs['children']))
        for i, (a, a2) in enumerate(kids):
            if not a['states'] or not a2['states']:
                continue
            for b, b2 in kids[i + 1:]:
                if not b['states'] or not b2['states']:
                    continue
                for ax, aw, bx, ax2, aw2, bx2, axis in (
                        (a['x'], a['states'][0]['w'], b['x'], a2['x'], a2['states'][0]['w'], b2['x'], 'x'),
                        (b['x'], b['states'][0]['w'], a['x'], b2['x'], b2['states'][0]['w'], a2['x'], 'x'),
                        (a['y'], a['states'][0]['h'], b['y'], a2['y'], a2['states'][0]['h'], b2['y'], 'y'),
                        (b['y'], b['states'][0]['h'], a['y'], b2['y'], b2['states'][0]['h'], a2['y'], 'y')):
                    if aw and ax + aw == bx and ax2 + aw2 != bx2:
                        bad.append((a.get('name'), b.get('name'), axis, ax2 + aw2 - bx2))
        for a, a2 in kids:
            walk(a, a2)

    walk(van['root'], sc['root'])
    return bad


def fonts_of(doc):
    out = set()

    def walk(c):
        for st in c['states']:
            if st.get('font'):
                out.add(st['font'])
        for ch in c['children']:
            walk(ch)
    walk(doc['root'])
    return out


def check_layouts(layouts, f, width, height, slot_files=None, scale_root=True):
    """layouts: [(pack path, bytes)]; slot_files: the .cuf names the fonts pack holds at this factor (None: not checked).
    -> {'factor', 'screen', 'layouts': n, 'overflow': [...], 'abutting': [...], 'fonts_missing': [...], 'worst': ...}"""
    over, abut, missing, n = [], [], {}, 0
    for path, data in layouts:
        try:
            van = uic.parse(data, path)
        except Exception:
            continue
        n += 1
        ctx = scale.context_of(path)
        sc = scale.scale_layout(copy.deepcopy(van), f, ctx, scale_root)
        e = extent(van)
        if e:
            w, h = e[2] - e[0], e[3] - e[1]
            sw, sh = scale.px(w * f), scale.px(h * f)
            if sw > width or sh > height:
                bf, bw, bh = BASELINE
                base = scale.px(w * bf) > bw or scale.px(h * bf) > bh
                over.append({'layout': path, 'vanilla': [w, h], 'scaled': [sw, sh], 'over': [max(0, sw - width), max(0, sh - height)],
                             'over_vanilla': round(max(w - width / f, h - height / f), 2), 'also_at_1080p': base})
        for a, b, axis, d in abutting(van, sc):
            abut.append({'layout': path, 'pair': [a, b], 'axis': axis, 'gap': d})
        if slot_files is not None:
            for name in fonts_of(sc):
                ff = scale.font_file(name)
                if ff and ff not in slot_files:
                    missing.setdefault(ff, []).append(path)
    over.sort(key=lambda r: (-max(r['over']), r['layout']))
    return {'factor': f, 'screen': [width, height], 'layouts': n, 'overflow': over, 'abutting': abut,
            'loses_content': [o['layout'] for o in over if not o['also_at_1080p'] and o['over_vanilla'] > BLEED],
            'bleed': [o['layout'] for o in over if not o['also_at_1080p'] and o['over_vanilla'] <= BLEED],
            'fonts_missing': {k: sorted(set(v))[:5] for k, v in sorted(missing.items())}}
