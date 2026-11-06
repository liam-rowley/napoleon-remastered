#!/usr/bin/env python3
"""J32 S3: per recipe cell, how far the game's dump is from the pinned viewer and from the viewer with the clear-order fix.

usage: python3 proxy/runs/20261106_j32pc/recipes_table.py [--game build/j32/game]   (needs Pillow; prints a table, writes recipes_table.json)
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CELLS = {'image-color': (20, 20), 'translateY': (160, 20), 'border-radius': (300, 20), 'blur shadow': (440, 20), 'alpha shadow': (580, 20), 'no-background shadow': (720, 20),
         'var() tint': (20, 160), 'focus cell': (160, 160), 'linear-gradient': (300, 160), 'repeating gradient': (440, 160), 'clip mask': (580, 160), 'layer opacity': (720, 160),
         'filter blur': (20, 300), 'hairlines': (160, 300), 'text': (300, 300)}
RUNS = [(1080, 100), (1080, 85), (1440, 100), (2160, 125)]
TOL = 8


def cell(a, b, box):
    d = ImageChops.difference(a.crop(box), b.crop(box))
    bands = d.split()
    m = ImageChops.lighter(ImageChops.lighter(bands[0], bands[1]), bands[2])
    hist = m.histogram()
    n = sum(hist)
    return round(sum(hist[TOL + 1:]) / n, 5), max(i for i, c in enumerate(hist) if c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=str(ROOT / 'build/j32/game'))
    a = ap.parse_args()
    out = {}
    for h, pct in RUNS:
        dp = h / 1080 * pct / 100
        g = Image.open(Path(a.game) / f'recipes_frontend_{h}_{pct}.png').convert('RGB')
        v = {k: Image.open(ROOT / f'build/j32/{d}/recipes_{h}_{pct}.png').convert('RGB') for k, d in (('pinned', 'viewer'), ('fixed', 'viewer_fix'))}
        for name, (x, y) in CELLS.items():
            box = tuple(round(c * dp) for c in (x - 8, y - 8, x + 128, y + 128))
            out.setdefault(name, {})[f'{h}_{pct}'] = {k: cell(v[k], g, box) for k in v}
    for name, r in out.items():
        print(f'{name:22}', ' | '.join(f"{k} p{r[k]['pinned'][0]:.3f}/{r[k]['pinned'][1]:3} f{r[k]['fixed'][0]:.3f}/{r[k]['fixed'][1]:3}" for k in r))
    (HERE / 'recipes_table.json').write_text(json.dumps(out, indent=1) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
