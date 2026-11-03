#!/usr/bin/env python3
"""Draw the throwaway test glyphs (plus, chevron, ring) the component board tints, so the icon component can be proved without new art.

purpose: write viewer/napoleon/board/test_plus.png, test_chevron.png and test_ring.png (60 px, near-black on transparent, 2 dp stroke on a 24 dp grid at 2.5x) with plain Python
usage: python3 uikit/napoleon/test_glyphs.py [--out DIR] [--check]   (--check regenerates and compares with the committed files)
when: only to regenerate the board's test glyphs; they are named test_* and no real screen uses them (D14: no new art in J34)
not-a-verb: a one-off generator for three fixtures, not a registry operation
"""
import argparse
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'viewer' / 'napoleon' / 'board'
N, SS = 60, 4   # output px, supersampling
INK = (11, 15, 22)   # near-black
STROKE = 5.0   # 2 dp at 2.5x


def dist_seg(px, py, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def shapes():
    c = N / 2
    return {
        'test_plus': lambda x, y: min(dist_seg(x, y, (c, 12), (c, N - 12)), dist_seg(x, y, (12, c), (N - 12, c))) <= STROKE / 2,
        'test_chevron': lambda x, y: min(dist_seg(x, y, (20, 14), (40, c)), dist_seg(x, y, (40, c), (20, N - 14))) <= STROKE / 2,
        'test_ring': lambda x, y: abs(((x - c) ** 2 + (y - c) ** 2) ** 0.5 - 19) <= STROKE / 2,
    }


def png(rows):
    raw = b''.join(b'\x00' + bytes(r) for r in rows)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', N, N, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')


def render(inside):
    rows = []
    for y in range(N):
        row = []
        for x in range(N):
            hit = sum(1 for j in range(SS) for i in range(SS) if inside(x + (i + 0.5) / SS, y + (j + 0.5) / SS))
            row += [*INK, round(255 * hit / (SS * SS))]
        rows.append(row)
    return png(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    bad = 0
    for name, inside in shapes().items():
        data = render(inside)
        f = Path(a.out) / f'{name}.png'
        if a.check:
            same = f.exists() and f.read_bytes() == data
            print(f'{name}.png', 'ok' if same else 'differs')
            bad += not same
        else:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            print(f'wrote {f} ({len(data)} bytes)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
