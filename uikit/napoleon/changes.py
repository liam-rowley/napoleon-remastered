#!/usr/bin/env python3
"""Re-render every library screen at the four corners and report which screens and corners changed against the committed baseline.

purpose: render the component board and every viewer/napoleon screen with "library": true at the four D19 corners, compare rgba_sha256 with uikit/napoleon/baseline.json, print what changed; flag a locked screen as "changed since lock"
usage: python3 uikit/napoleon/changes.py [--accept [--allow-locked]] [--json] [--wasm DIR] [--screens NAME ...]   (exit 1 when anything changed, or a locked screen changed without --accept --allow-locked)
when: after any change to uikit/napoleon (tokens, src, fonts) or to a library screen, before the pull request; --accept rewrites the baseline once the change is intended; Liam's LOCK.json (uikit/napoleon/LOCK.json, {"locked": ["board"]}) is never written here
not-a-verb: a renderer round trip with a browser and a baseline file, not a registry operation
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = HERE / 'baseline.json'
LOCK = HERE / 'LOCK.json'
spec = importlib.util.spec_from_file_location('uikit_gate', HERE / 'gate.py')
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def library_screens():
    out = {}
    for f in sorted((ROOT / 'viewer' / 'napoleon').glob('*/screen.json')):
        if json.loads(f.read_text(encoding='utf-8')).get('library'):
            out[f.parent.name] = f.parent
    return out


def locked_screens():
    """Names Liam has locked (LOCK.json is written by whoever records his lock, never by this tool); a missing file means none."""
    if not LOCK.exists():
        return set()
    d = json.loads(LOCK.read_text(encoding='utf-8'))
    return set(d['locked'] if isinstance(d, dict) else d)


def compare(current, baseline, locked):
    """[(screen, corner, 'changed'|'new'|'removed', locked?)] between {screen: {corner: sha}} maps."""
    rows = []
    for s in sorted(set(current) | set(baseline)):
        for c in sorted(set(current.get(s, {})) | set(baseline.get(s, {}))):
            a, b = current.get(s, {}).get(c), baseline.get(s, {}).get(c)
            if a != b:
                rows.append((s, c, 'new' if b is None else 'removed' if a is None else 'changed', s in locked))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--accept', action='store_true', help='rewrite baseline.json with what was just rendered')
    ap.add_argument('--allow-locked', action='store_true', help='with --accept: also accept a change to a locked screen (it stays flagged for Liam to play again)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--wasm')
    ap.add_argument('--screens', nargs='*')
    a = ap.parse_args()
    screens = library_screens()
    if a.screens:
        screens = {k: v for k, v in screens.items() if k in a.screens}
    current, details = {}, {}
    for name, folder in screens.items():
        res = G.render_corners(folder, a.wasm)
        current[name] = {r['corner']: r['rgba_sha256'] for r in res}
        details[name] = res
    base = json.loads(BASELINE.read_text(encoding='utf-8')) if BASELINE.exists() else {'screens': {}}
    baseline = base['screens']
    if a.screens:   # compare only the screens asked for
        baseline = {k: v for k, v in baseline.items() if k in screens}
    locked = locked_screens()
    rows = compare(current, baseline, locked)
    hard = [r for r in rows if r[3] and r[2] != 'new']
    if a.json:
        print(json.dumps({'changes': rows, 'locked': sorted(locked)}, indent=1))
    else:
        for s, c, kind, lk in rows:
            print(f'changes: {s} {c}: {kind}' + (' (CHANGED SINCE LOCK: Liam plays it again)' if lk and kind != 'new' else ''))
        if not rows:
            print(f'changes: {sum(len(v) for v in current.values())} renders in {len(current)} screen(s), none changed since the baseline')
    if a.accept:
        if hard and not a.allow_locked:
            print('changes: a locked screen changed: refusing --accept without --allow-locked (the change stays flagged until Liam plays it again)')
            return 1
        merged = {**base['screens'], **current}
        wasm_sha = hashlib.sha256((Path(a.wasm or ROOT / 'build' / 'viewer' / 'out') / 'viewer.wasm').read_bytes()).hexdigest()
        BASELINE.write_text(json.dumps({'_doc': 'rgba_sha256 of each library screen at the four D19 corners; rewritten by uikit/napoleon/changes.py --accept',
                                        'wasm_sha256': wasm_sha, 'screens': merged}, indent=1) + '\n', encoding='utf-8', newline='\n')
        print(f'changes: baseline.json written ({len(merged)} screen(s))')
        return 0
    return 1 if rows or hard else 0


if __name__ == '__main__':
    sys.exit(main())
