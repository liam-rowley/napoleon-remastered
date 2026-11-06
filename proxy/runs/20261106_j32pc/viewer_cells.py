#!/usr/bin/env python3
"""J32 S3 offline: render the host test and the J34 board in the review viewer at the four cells, at the game's back-buffer size and dp ratio.

usage: python3 proxy/runs/20261106_j32pc/viewer_cells.py [--out build/j32/viewer]
Writes <doc>_<height>_<percent>.png and .json (size, rgba_sha256, boxes, console log); prints one line per render. Needs build/viewer/out (viewer.wasm).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CELLS = [(1920, 1080, 100), (1920, 1080, 85), (2560, 1440, 100), (3840, 2160, 125)]
DOCS = {'hosttest': ROOT / 'viewer/napoleon/hosttest', 'board': ROOT / 'viewer/napoleon/board', 'recipes': Path(__file__).resolve().parent / 'recipes'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'build' / 'j32' / 'viewer'))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    bad = 0
    for doc, src in DOCS.items():
        for w, h, pct in CELLS:
            ratio = h / 1080 * pct / 100   # UiDpRatio (core/proxy/src/ui_core.h)
            tag = f'{doc}_{h}_{pct}'
            p = subprocess.run([sys.executable, str(ROOT / 'viewer' / 'core' / 'render.py'), str(src), '--size', f'{w}x{h}',
                                '--dp-ratio', repr(ratio), '--site', str(ROOT / 'build' / 'viewer' / f'site_{doc}'), '--out', str(out / f'{tag}.png'), '--json'],
                               capture_output=True, text=True, cwd=ROOT)
            if p.returncode:
                bad += 1
                print(tag, 'FAILED', (p.stdout + p.stderr)[-400:])
                continue
            (out / f'{tag}.json').write_text(p.stdout, encoding='utf-8')
            d = json.loads(p.stdout)
            noise = [x for x in d['log'] if x.startswith(('console error', 'console warning', 'pageerror'))]
            print(tag, d['w'], d['h'], d['rgba_sha256'][:12], noise[:3])
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
