#!/usr/bin/env python3
"""The J30 host test document's art master and the crispness checks of its in-game dumps.

purpose: write the host test's 2.5x art master (deterministic PNG), and check a `ctl ui dump` PNG of viewer/napoleon/hosttest: 1 dp rules solid with no blended rows, box edges on whole pixels, H ink height = cap height x size x dp ratio within 1 px; writes crops for review
usage: python3 tools/ui_hosttest.py art [--out viewer/napoleon/hosttest/art_master.png] | check <dump.png> --dp <ratio> [--crops DIR] [--json OUT]
when: art once (committed); check on every in-game dump of the host test (J30 PC step b), the numbers go in the run README; the crispness verdict stays Liam's, from the crops
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
        for i in range(stride):
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
    o = ap.parse_args(argv)
    if o.cmd == 'art':
        make_art(o.out)
        return 0
    r = check(o.png, o.dp, o.crops)
    text = json.dumps(r, indent=1)
    if o.json:
        Path(o.json).write_text(text + '\n', encoding='utf-8')
    print(json.dumps({'file': r['file'], 'ok': r['ok'], **{k: v['ok'] for k, v in r['checks'].items()}}))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
