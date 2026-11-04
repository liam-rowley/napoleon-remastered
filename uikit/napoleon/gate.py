#!/usr/bin/env python3
"""The corner gate: render a library screen at the four D19 corners and fail on clipping or overflow found by the renderer.

purpose: stage a screen with the built viewer, render it at 1080p x 85 %, 4K x 125 %, 21:9 and 16:10, and report every element box outside the viewport or its parent, and every text wider than its box (viewer_overflow_json); also gives the PNG and rgba_sha256 per corner
usage: python3 uikit/napoleon/gate.py [screen dir ...] [--out DIR] [--json] [--wasm build/viewer/out]   (default: the component board; exit 1 on any finding)
when: before every library or screen change is proposed and in CI's viewer job (needs the viewer build and Playwright); changes.py reuses render_corners
not-a-verb: a renderer round trip with a browser, not a registry operation
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('viewer_render', ROOT / 'viewer' / 'core' / 'render.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

# D19: dp ratio = height / 1080 x slider. name, width, height, slider
CORNERS = [('1080p_85', 1920, 1080, 0.85), ('4k_125', 3840, 2160, 1.25), ('21x9_100', 3440, 1440, 1.0), ('16x10_100', 1920, 1200, 1.0)]


def ratio(h, slider):
    return round(h / 1080 * slider, 6)


def render_corners(screen_dir, wasm=None, site=None, out_dir=None, corners=CORNERS):
    """[{corner, w, h, dp_ratio, rgba_sha256, findings, timings}] for one screen folder; PNGs go to out_dir/<screen>_<corner>.png when given."""
    import hashlib
    import tempfile
    screen_dir = Path(screen_dir)
    wasm = Path(wasm or ROOT / 'build' / 'viewer' / 'out')
    tmp = None
    if site is None:
        tmp = tempfile.TemporaryDirectory()
        site = Path(tmp.name) / 'site'
    R.stage(screen_dir, site, wasm)
    results = []
    for name, w, h, slider in corners:
        seen = {}

        def probe(page):
            seen['findings'] = page.evaluate('window.viewer.overflow()')
            seen['timings'] = page.evaluate('window.viewerTimings')
        rw, rh, rgba, _ = R.render(site, (w, h), ratio(h, slider), actions=probe)
        res = {'corner': name, 'w': rw, 'h': rh, 'dp_ratio': ratio(h, slider), 'rgba_sha256': hashlib.sha256(rgba).hexdigest(),
               'findings': seen['findings'], 'timings': seen['timings']}
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            (Path(out_dir) / f'{screen_dir.name}_{name}.png').write_bytes(R.png_bytes(rw, rh, rgba))
        results.append(res)
    if tmp:
        tmp.cleanup()
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('screens', nargs='*', default=[str(ROOT / 'viewer' / 'napoleon' / 'board')])
    ap.add_argument('--out')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--wasm')
    a = ap.parse_args()
    report, bad = {}, 0
    for s in a.screens:
        res = render_corners(s, a.wasm, out_dir=a.out)
        report[Path(s).name] = res
        for r in res:
            bad += len(r['findings'])
            if not a.json:
                print(f'gate: {Path(s).name} {r["corner"]} {r["w"]}x{r["h"]} dp {r["dp_ratio"]}: {len(r["findings"])} finding(s), rgba_sha256 {r["rgba_sha256"][:16]}')
                for f in r['findings'][:20]:
                    print(f'  {f["kind"]}: {f["element"]} box {f["box"]} {f["detail"]}')
    if a.json:
        print(json.dumps(report, indent=1))
    elif not bad:
        print('gate: no clipping or overflow at the four corners')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
