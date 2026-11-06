#!/usr/bin/env python3
"""The J30 host test document's art master and the crispness checks of its in-game dumps.

purpose: write the host test's 2.5x art master (deterministic PNG), check a `ctl ui dump` PNG of viewer/napoleon/hosttest (1 dp rules solid with no blended rows, box edges on whole pixels, H ink height = cap height x size x dp ratio within 1 px; writes crops for review), and compare a viewer render with an in-game dump of any document (parity: alignment, per-pixel difference, share beyond a tolerance, tiles whose content moved as distinct from edge blending, crops of the worst areas)
usage: python3 tools/ui_hosttest.py art [--out viewer/napoleon/hosttest/art_master.png] | check <dump.png> --dp <ratio> [--crops DIR] [--json OUT] | parity <viewer.png> <game.png> [--rect x,y,w,h] [--tolerance N] [--crops DIR] [--json OUT]
when: art once (committed); check on every in-game dump of the host test (J30 PC step b), the numbers go in the run README; the crispness verdict stays Liam's, from the crops; parity on every viewer and game pair (J32 S3; exit 1 when content moved)
not-a-verb: a test helper for one document's PNGs, not a registry operation

Positions mirror viewer/napoleon/hosttest/hosttest.rcss (body at 40,40 dp; keep the two in step). Standard library only: the PNG reader
handles 8-bit RGB/RGBA, non-interlaced, every filter (what stb_image_write and this script write).
"""
import argparse
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'viewer' / 'napoleon' / 'fonts' / 'IMFeENrm28P.ttf'
BG = (0x10, 0x18, 0x20)
BODY = (40, 40)
LINES = {'t14': (14, 10, 30), 't20': (20, 40, 35), 't28': (28, 75, 45), 't40': (40, 120, 60)}   # id: size, top, height (dp, in body)
RULES = (10, 190, 260, [0, 4, 9, 15, 22])    # left, top, width, offsets (dp)
BOXES = (290, 190, 40, [0, 50, 100])         # left, top, size, offsets (dp)


# ---- PNG ---------------------------------------------------------------------------------------------------------------------
def png_write(path, w, h, rows, channels=4):
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    ct = 6 if channels == 4 else 2
    data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, ct, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    Path(path).write_bytes(data)


def png_read(path):
    d = Path(path).read_bytes()
    assert d[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    p, idat, w = 8, b'', 0
    while p < len(d):
        n, t = struct.unpack('>I4s', d[p:p + 8])
        body = d[p + 8:p + 8 + n]
        if t == b'IHDR':
            w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', body)
            assert bd == 8 and ct in (2, 6) and il == 0, 'only 8-bit RGB/RGBA, non-interlaced'
            ch = 3 if ct == 2 else 4
        elif t == b'IDAT':
            idat += body
        p += 12 + n
    raw = zlib.decompress(idat)
    stride = w * ch
    out, prev = [], bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride if f else 0):
            a = line[i - ch] if i >= ch else 0
            b = prev[i]
            c = prev[i - ch] if i >= ch else 0
            if f == 1: line[i] = (line[i] + a) & 255
            elif f == 2: line[i] = (line[i] + b) & 255
            elif f == 3: line[i] = (line[i] + ((a + b) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out.append([tuple(line[x * ch:x * ch + 3]) for x in range(w)])
        prev = line
    return w, h, out


# ---- the art master ----------------------------------------------------------------------------------------------------------
def make_art(out):
    """160 x 160 (2.5 x 64 dp): a gold ring with 24 spokes, 1-px stripes top left (they must average out, not alias), a solid emblem."""
    n = 160
    rows = []
    for y in range(n):
        r = []
        for x in range(n):
            dx, dy = x + 0.5 - n / 2, y + 0.5 - n / 2
            rad = math.hypot(dx, dy)
            px = (0, 0, 0, 0)
            if x < 48 and y < 48:
                px = (240, 240, 240, 255) if x % 2 == 0 else (16, 24, 32, 255)
            elif 62 <= rad <= 76:
                px = (200, 160, 80, 255)
            elif rad < 62:
                ang = math.atan2(dy, dx)
                spoke = abs(((ang / (2 * math.pi) * 24) % 1) - 0.5) < 0.08
                px = (240, 216, 144, 255) if spoke or rad < 14 else (27, 36, 51, 255)
            r.extend(px)
        rows.append(r)
    png_write(out, n, n, rows, 4)
    print(f'ui_hosttest: wrote {out} ({n}x{n})')


# ---- checks ------------------------------------------------------------------------------------------------------------------
def cap_ratio():
    d = FONT.read_bytes()
    n = struct.unpack('>H', d[4:6])[0]
    t = {d[12 + 16 * i:16 + 16 * i]: struct.unpack('>II', d[20 + 16 * i:28 + 16 * i]) for i in range(n)}
    os2, head = t[b'OS/2'][0], t[b'head'][0]
    return struct.unpack('>h', d[os2 + 88:os2 + 90])[0] / struct.unpack('>H', d[head + 18:head + 20])[0]


def kind(p):
    if p == BG:
        return 'bg'
    if min(p) >= 250:
        return 'white'
    return 'blend'


def runs(seq):
    out, cur, start = [], None, 0
    for i, k in enumerate(seq + [None]):
        if k != cur:
            if cur is not None:
                out.append((cur, start, i - start))
            cur, start = k, i
    return out


def check(path, dp, crops=None):
    w, h, img = png_read(path)
    px = lambda v: v * dp
    bx, by = px(BODY[0]), px(BODY[1])
    res = {'file': str(path), 'size': [w, h], 'dp': dp, 'checks': {}}
    lo, hi = max(1, math.floor(dp)), max(1, math.ceil(dp))
    # 1 dp rules: sample 5 columns inside the rules, every row from 2 px above the first to 2 px below the last
    l, t, wd, offs = RULES
    # RmlUi rounds each nested box to whole pixels, so the rules can sit a few pixels from the naive dp x ratio: a generous window
    y0, y1 = int(by + px(t)) - 8, int(by + px(t + offs[-1] + 1)) + 10
    cols = [int(bx + px(l + f * wd)) for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
    ok, detail = True, []
    for x in cols:
        seq = [kind(img[y][x]) for y in range(y0, y1)]
        rr = [r for r in runs(seq) if r[0] != 'bg']
        whites = [r for r in rr if r[0] == 'white']
        blends = [r for r in rr if r[0] == 'blend']
        good = not blends and len(whites) == len(offs) and all(lo <= r[2] <= hi for r in whites)
        ok &= good
        detail.append({'x': x, 'white_runs': [[y0 + r[1], r[2]] for r in whites], 'blend_rows': sum(r[2] for r in blends)})
    res['checks']['rules_solid'] = {'ok': ok, 'thickness_px_allowed': [lo, hi], 'columns': detail}
    # boxes: a middle row and a middle column of each; edges white, 1 dp thick, nothing blended
    l, t, size, offs = BOXES
    ok, detail = True, []
    for o in offs:
        # content-box: the 40 dp box plus a 1 dp border each side spans 42 dp
        x0, x1 = int(bx + px(l + o)) - 3, int(bx + px(l + o + size + 2)) + 4
        ymid = int(by + px(t + size / 2))
        yr0, yr1 = int(by + px(t)) - 3, int(by + px(t + size + 2)) + 4
        xmid = int(bx + px(l + o + size / 2))
        row = runs([kind(img[ymid][x]) for x in range(x0, x1)])
        col = runs([kind(img[y][xmid]) for y in range(yr0, yr1)])
        good = True
        for rr in (row, col):
            nb = [r for r in rr if r[0] != 'bg']
            good &= len(nb) == 2 and all(r[0] == 'white' and lo <= r[2] <= hi for r in nb)
        ok &= good
        detail.append({'box_left_dp': l + o, 'row_edges': [[x0 + r[1], r[2], r[0]] for r in row if r[0] != 'bg'],
                       'col_edges': [[yr0 + r[1], r[2], r[0]] for r in col if r[0] != 'bg']})
    res['checks']['box_edges_whole_pixels'] = {'ok': ok, 'boxes': detail}
    # text: ink rows of the H line inside its box; expected = cap height / em x size x dp
    cr = cap_ratio()
    ok, detail = True, []
    for lid, (size, top, hgt) in LINES.items():
        xa, xb = int(bx + px(10)), min(w - 1, int(bx + px(10 + size * 4)))
        ya, yb = int(by + px(top)), min(h - 1, int(by + px(top + hgt)))
        # a row is ink when any pixel differs from the background by more than 64 (summed RGB, about 9 % coverage of white): faint
        # antialiased serif rows count as drawn height; `ink_rows_strict` (more than 192) is reported beside it
        diff = lambda y, x: abs(img[y][x][0] - BG[0]) + abs(img[y][x][1] - BG[1]) + abs(img[y][x][2] - BG[2])
        ink = [y for y in range(ya, yb) if any(diff(y, x) > 64 for x in range(xa, xb))]
        strict = [y for y in range(ya, yb) if any(diff(y, x) > 192 for x in range(xa, xb))]
        got = (ink[-1] - ink[0] + 1) if ink else 0
        want = cr * size * dp
        # the glyph's edge lies between the strict and the faint extent (antialiasing): within 1 px of either passes
        st = (strict[-1] - strict[0] + 1) if strict else 0
        good = min(abs(got - want), abs(st - want)) <= 1.0
        ok &= good
        detail.append({'id': lid, 'size_dp': size, 'px_size': round(size * dp, 3), 'ink_rows': got, 'ink_rows_strict': (strict[-1] - strict[0] + 1) if strict else 0, 'expected_cap_px': round(want, 2), 'ok': good})
    res['checks']['text_height'] = {'ok': ok, 'cap_height_per_em': round(cr, 4), 'lines': detail}
    res['ok'] = all(c['ok'] for c in res['checks'].values())
    if crops:
        Path(crops).mkdir(parents=True, exist_ok=True)
        stem = Path(path).stem
        for name, (cx, cy, cw, ch) in {'text': (10, 5, 330, 180), 'rules_boxes': (5, 185, 440, 50), 'art_button': (5, 245, 450, 80)}.items():
            x0, y0 = int(bx + px(cx)), int(by + px(cy))
            ww, hh = min(int(px(cw)), w - x0), min(int(px(ch)), h - y0)
            rows = [[c for p in img[y][x0:x0 + ww] for c in p] for y in range(y0, y0 + hh)]
            png_write(Path(crops) / f'{stem}_{name}.png', ww, hh, rows, 3)
        res['crops'] = str(crops)
    return res


# ---- parity: a viewer render against an in-game dump --------------------------------------------------------------------------
TILE = 32            # px: moved content is looked for tile by tile, so one moved box shows however clean the rest of the image is
SEARCH = 2           # px each way: the shifts tried for the whole image
TILE_SEARCH = 32     # px each way: the shifts tried per tile, so this bounds the moves a tile can name
SOLID_DELTA = 64     # a tile with SOLID_SHARE of its pixels this far off is no blended edge: content moved further than TILE_SEARCH, or one image lacks it
SOLID_SHARE = 0.5    # J32's 12 cells reach 0.23 at this delta, on the host test's art (0.48 at 32 levels, so a lower delta calls filtering layout). Thin or faint content moved further shows only in element boxes
TILE_SAMPLE = 48     # differing pixels of a tile tried against every shift; only the shifts they allow get a full count
MOVED_GAIN = 0.6     # a shift must remove this share of a tile's differing pixels: blending does not follow a shift, moved content does
MOVED_MIN_PX = 8     # fewer differing pixels than this in a tile say nothing
MOVED_MIN_DELTA = 32  # a tile whose worst pixel is under this is shading, not an edge; a tile of the first image with less contrast has nothing a shift could find again


def gray(img):
    return [bytes((p[0] + 2 * p[1] + p[2]) >> 2 for p in row) for row in img]


def count_off(ga, gb, x0, y0, x1, y1, dx, dy, tol):
    """-> (pixels of the box in `ga` differing beyond tol from `gb` read at (x + dx, y + dy), pixels compared). A shift drops the pixels it moves off `gb`, so compare shifts by the rate, never the count."""
    n, hb, wb = 0, len(gb), len(gb[0])
    xa, xb = max(x0, -dx), min(x1, wb - dx)
    ya, yb = max(y0, -dy), min(y1, hb - dy)
    for y in range(ya, yb):
        ra, rb = ga[y][xa:xb], gb[y + dy][xa + dx:xb + dx]
        if ra != rb:
            n += sum(1 for p, q in zip(ra, rb) if abs(p - q) > tol)
    return n, max(0, xb - xa) * max(0, yb - ya)


def shifts(reach=SEARCH):
    return sorted(((dx, dy) for dx in range(-reach, reach + 1) for dy in range(-reach, reach + 1)), key=lambda s: abs(s[0]) + abs(s[1]))


def align(ga, gb, box, tol):
    """The whole-image shift of b that fits a best (every 4th row); (0, 0) unless the shift removes MOVED_GAIN of the difference."""
    x0, y0, x1, y1 = box
    rows = list(range(y0, y1, 4))
    best, off, base = None, (0, 0), 0
    for dx, dy in shifts():
        n = c = 0
        xa, xb = max(x0, -dx), min(x1, len(gb[0]) - dx)
        for y in rows:
            if 0 <= y + dy < len(gb):
                pa, pb = ga[y][xa:xb], gb[y + dy][xa + dx:xb + dx]
                c += len(pa)
                if pa != pb:
                    n += sum(1 for p, q in zip(pa, pb) if abs(p - q) > tol)
        n = n / c if c else 1.0
        if best is None:
            base = n
        if best is None or n < best:
            best, off = n, (dx, dy)
    if off == (0, 0) or best > base * (1 - MOVED_GAIN):
        return (0, 0)
    n0, c0 = count_off(ga, gb, *box, 0, 0, tol)       # the sample can skip a rule only one image has: the shift must hold on every row
    n1, c1 = count_off(ga, gb, *box, *off, tol)
    return off if c1 and n1 / c1 <= n0 / c0 * (1 - MOVED_GAIN) else (0, 0)


def tile_shift(ga, gb, box, ox, oy, tol):
    """The shift (from the aligned position) that best explains a tile's difference as moved content, or None.
    Blending does not follow a shift and neither does a mark that only one image has: the tile must hold contrast in `ga`, and `gb` must show it again elsewhere."""
    x0, y0, x1, y1 = box
    wb, hb = len(gb[0]), len(gb)
    if max(max(ga[y][x0:x1]) for y in range(y0, y1)) - min(min(ga[y][x0:x1]) for y in range(y0, y1)) < MOVED_MIN_DELTA:
        return None
    here, area = count_off(ga, gb, x0, y0, x1, y1, ox, oy, tol)
    if not area:
        return None
    pts = [(x, y, ga[y][x]) for y in range(y0, y1) for x in range(x0, x1)
           if not (0 <= y + oy < hb and 0 <= x + ox < wb) or abs(ga[y][x] - gb[y + oy][x + ox]) > tol]
    pts = pts[::max(1, len(pts) // TILE_SAMPLE)]
    allowed = int(len(pts) * (1 - MOVED_GAIN))
    best, rate = None, here / area * (1 - MOVED_GAIN)
    for s in shifts(TILE_SEARCH):
        if s == (0, 0):
            continue
        dx, dy = ox + s[0], oy + s[1]
        miss = 0
        for x, y, v in pts:
            if not (0 <= y + dy < hb and 0 <= x + dx < wb) or abs(v - gb[y + dy][x + dx]) > tol:
                miss += 1
                if miss > allowed:
                    break
        if miss > allowed:
            continue
        n, c = count_off(ga, gb, x0, y0, x1, y1, dx, dy, tol)
        if c * 2 >= area and n / c <= rate and (best is None or n / c < rate):
            best, rate = s, n / c
    return best


def merge_tiles(tiles):
    """Tiles {(tx, ty): shift} -> boxes of touching tiles that moved the same way."""
    seen, out = set(), []
    for t, s in sorted(tiles.items()):
        if t in seen:
            continue
        stack, group = [t], []
        seen.add(t)
        while stack:
            c = stack.pop()
            group.append(c)
            for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
                if n in tiles and n not in seen and tiles[n] == s:
                    seen.add(n)
                    stack.append(n)
        xs, ys = [g[0] for g in group], [g[1] for g in group]
        out.append({'box': [min(xs) * TILE, min(ys) * TILE, (max(xs) - min(xs) + 1) * TILE, (max(ys) - min(ys) + 1) * TILE], 'shift': list(s), 'tiles': len(group)})
    return out


def parity_images(a, b, rect=None, tol=8):
    """Compare two images (rows of RGB tuples). -> the numbers, `moved` (boxes whose content a shift explains, or solid difference with shift []: layout) and `worst` (tiles by differing pixels)."""
    h, w = len(a), len(a[0])
    if (len(b), len(b[0])) != (h, w):
        return {'ok': False, 'reason': f'sizes differ: {w}x{h} and {len(b[0])}x{len(b)}'}
    x0, y0, rw, rh = rect or (0, 0, w, h)
    x1, y1 = min(w, x0 + rw), min(h, y0 + rh)
    ga, gb = gray(a), gray(b)
    ox, oy = align(ga, gb, (x0, y0, x1, y1), tol)
    hist, total, over = [0] * 256, 0, {}
    for y in range(y0, y1):
        yb = y + oy
        if not 0 <= yb < h:
            continue
        ra, rb = a[y], b[yb]
        for x in range(max(x0, -ox), min(x1, w - ox)):
            p, q = ra[x], rb[x + ox]
            if p != q:
                d = max(abs(p[0] - q[0]), abs(p[1] - q[1]), abs(p[2] - q[2]))
                hist[d] += 1
                total += d
                if d > tol:
                    t = (x // TILE, y // TILE)
                    c = over.get(t, (0, 0, 0))
                    over[t] = (c[0] + 1, max(c[1], d), c[2] + (d > SOLID_DELTA))
    px = (x1 - x0) * (y1 - y0)
    beyond = sum(hist[tol + 1:])
    moved = {}
    for (tx, ty), (n, d, far) in over.items():
        if n < MOVED_MIN_PX or d < MOVED_MIN_DELTA:
            continue
        box = (max(x0, tx * TILE), max(y0, ty * TILE), min(x1, (tx + 1) * TILE), min(y1, (ty + 1) * TILE))
        best = tile_shift(ga, gb, box, ox, oy, tol)
        if best:
            moved[(tx, ty)] = best
        elif far >= SOLID_SHARE * (box[2] - box[0]) * (box[3] - box[1]):
            moved[(tx, ty)] = ()      # shift [] in the result: no shift names it
    worst = sorted(over.items(), key=lambda kv: (-kv[1][0], kv[0]))[:6]
    return {'ok': True, 'size': [w, h], 'rect': [x0, y0, x1 - x0, y1 - y0], 'offset': [ox, oy], 'pixels': px, 'tolerance': tol, 'differing': sum(hist[1:]), 'beyond': beyond,
            'share_beyond': round(beyond / px, 7) if px else 0, 'max_delta': max((i for i, n in enumerate(hist) if n), default=0), 'mean_delta': round(total / px, 4) if px else 0,
            'moved': merge_tiles(moved), 'moved_tiles': len(moved), 'kind': 'layout' if moved or (ox, oy) != (0, 0) else ('raster' if beyond else 'same'),
            'worst': [{'box': [t[0] * TILE, t[1] * TILE, TILE, TILE], 'beyond': v[0], 'max_delta': v[1]} for t, v in worst]}


def parity_crops(a, b, res, out, stem, zoom=4):
    """Each worst tile as viewer | game | difference (x 8), a pad of 8 px round it, zoomed."""
    Path(out).mkdir(parents=True, exist_ok=True)
    h, w = len(a), len(a[0])
    ox, oy = res['offset']
    for i, t in enumerate(res['worst']):
        x, y, s, _ = t['box']
        xs = range(max(0, x - 8), min(w, x + s + 8))
        rows = []
        for yy in range(max(0, y - 8), min(h, y + s + 8)):
            yb = min(h - 1, max(0, yy + oy))
            line = []
            for panel in (0, 1, 2):
                for xx in xs:
                    p, q = a[yy][xx], b[yb][min(w - 1, max(0, xx + ox))]
                    v = p if panel == 0 else q if panel == 1 else tuple(min(255, abs(m - n) * 8) for m, n in zip(p, q))
                    line.extend(list(v) * zoom)
                line.extend([255, 0, 255] * 2)
            rows.extend([line] * zoom)
        png_write(Path(out) / f'{stem}_{i}.png', len(rows[0]) // 3, len(rows), rows, 3)


def parity(pa, pb, rect=None, tol=8, crops=None):
    _, _, a = png_read(pa)
    _, _, b = png_read(pb)
    res = {'viewer': str(pa), 'game': str(pb), **parity_images(a, b, rect, tol)}
    if crops and res['ok']:
        parity_crops(a, b, res, crops, Path(pb).stem)
        res['crops'] = str(crops)
    return res


def f32(v):
    return struct.unpack('<f', struct.pack('<f', v))[0]


def game_dp_ratio(height, percent):
    """The dp ratio the game's host really gets: D3D9 leaves the x87 in 24-bit precision, so UiDpRatio's doubles round to a float at each of its three steps (fact napoleon.ui.dp_ratio_single_precision).
    At some sizes this is one float step above height / 1080 x percent / 100, and a viewer render at the true value moves rows the game does not. Render for `verified` at this value until the core's UiDpRatio fix lands."""
    return f32(f32(f32(height / 1080.0) * percent) / 100.0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('art')
    a.add_argument('--out', default=str(ROOT / 'viewer' / 'napoleon' / 'hosttest' / 'art_master.png'))
    c = sub.add_parser('check')
    c.add_argument('png')
    c.add_argument('--dp', type=float, required=True)
    c.add_argument('--crops')
    c.add_argument('--json')
    d = sub.add_parser('dp-ratio', help="the game's dp ratio for a back-buffer height and ui.scale percent, to pass to viewer/core/render.py --dp-ratio")
    d.add_argument('height', type=int)
    d.add_argument('percent', type=int)
    q = sub.add_parser('parity')
    q.add_argument('viewer')
    q.add_argument('game')
    q.add_argument('--rect', help='x,y,w,h in pixels: compare only this box (a document that does not cover the screen)')
    q.add_argument('--tolerance', type=int, default=8, help='per-channel difference that counts (default 8)')
    q.add_argument('--crops')
    q.add_argument('--json')
    o = ap.parse_args(argv)
    if o.cmd == 'art':
        make_art(o.out)
        return 0
    if o.cmd == 'dp-ratio':
        print(repr(game_dp_ratio(o.height, o.percent)))
        return 0
    if o.cmd == 'parity':
        r = parity(o.viewer, o.game, tuple(int(v) for v in o.rect.split(',')) if o.rect else None, o.tolerance, o.crops)
        if o.json:
            Path(o.json).write_text(json.dumps(r, indent=1) + '\n', encoding='utf-8')
        print(json.dumps({k: r.get(k) for k in ('ok', 'reason', 'kind', 'offset', 'share_beyond', 'max_delta', 'mean_delta', 'moved_tiles') if k in r}))
        return 0 if r['ok'] and r['kind'] != 'layout' else 1
    r = check(o.png, o.dp, o.crops)
    text = json.dumps(r, indent=1)
    if o.json:
        Path(o.json).write_text(text + '\n', encoding='utf-8')
    print(json.dumps({'file': r['file'], 'ok': r['ok'], **{k: v['ok'] for k, v in r['checks'].items()}}))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
