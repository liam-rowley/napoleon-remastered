#!/usr/bin/env python3
"""Re-render every library screen at the four corners and report which screens and corners changed against the committed baseline.

purpose: render the component board and every viewer/napoleon screen with "library": true at the four D19 corners; compare viewer.wasm with the baseline's wasm_sha256 first, then rgba_sha256 with uikit/napoleon/baseline.json, and judge a differing corner against its reference PNG (uikit/napoleon/baseline/) and the baseline's tolerance, writing a diff PNG when it is changed; flag a locked screen as "changed since lock"
usage: python3 uikit/napoleon/changes.py [--accept [--allow-locked]] [--json] [--wasm DIR] [--out DIR] [--screens NAME ...]   (exit 1 when viewer.wasm differs, anything is changed, new or removed, or a locked screen differs at all without --accept --allow-locked; a corner within tolerance is listed and does not fail; diff PNGs go to --out, default <wasm dir>/uikit_gate)
when: after any change to uikit/napoleon (tokens, src, fonts) or to a library screen, before the pull request; --accept rewrites baseline.json and the reference PNGs once the change is intended, and the job's reviewer accepts it with a "Baseline accepted: <sha>" line (tools/jobs_hooks.py); Liam's LOCK.json (uikit/napoleon/LOCK.json, {"locked": ["board"]}) is never written here
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
REFS = HERE / 'baseline'
LOCK = HERE / 'LOCK.json'
# Written by --accept when the baseline has no tolerance yet; from then on baseline.json owns the numbers (J80 report: the measured noise floor is zero).
DEFAULT_TOLERANCE = {'channel_tolerance': 1, 'max_changed_pixels': 0.00002, 'max_delta': 8}


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G = _load('uikit_gate', 'gate.py')
P = _load('uikit_pixeldiff', 'pixeldiff.py')


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


def lock_problems(lock=None):
    """What is wrong with a LOCK.json: it parses, has a `locked` list, and names only library screens or the board. A missing file is fine."""
    lock = Path(lock or LOCK)
    if not lock.exists():
        return []
    try:
        d = json.loads(lock.read_text(encoding='utf-8'))
    except ValueError as e:
        return [f'{lock.name}: not JSON: {e}']
    names = d.get('locked') if isinstance(d, dict) else None
    if not isinstance(names, list):
        return [f'{lock.name}: needs {{"locked": [screen, ...]}}']
    bad = sorted(set(map(str, names)) - set(library_screens()) - {'board'})
    return [f'{lock.name}: not a library screen: {", ".join(bad)}'] if bad else []


def compare(current, baseline, locked):
    """[(screen, corner, 'changed'|'new'|'removed', locked?)] between {screen: {corner: sha}} maps."""
    rows = []
    for s in sorted(set(current) | set(baseline)):
        for c in sorted(set(current.get(s, {})) | set(baseline.get(s, {}))):
            a, b = current.get(s, {}).get(c), baseline.get(s, {}).get(c)
            if a != b:
                rows.append((s, c, 'new' if b is None else 'removed' if a is None else 'changed', s in locked))
    return rows


def wasm_sha(wasm_dir=None):
    return hashlib.sha256((Path(wasm_dir or ROOT / 'build' / 'viewer' / 'out') / 'viewer.wasm').read_bytes()).hexdigest()


def wasm_finding(current, baseline):
    """The message when the viewer build is not the baseline's, else None (a baseline with no wasm hash has nothing to compare)."""
    if not baseline or current == baseline:
        return None
    return (f"changes: viewer.wasm differs from the baseline's ({current[:12]} vs {baseline[:12]}): "
            'pixel changes below may come from the viewer build; rebuild and re-accept together')


def verdict(row, details, tolerance, ref_dir, out_dir):
    """One compare() row as {screen, corner, verdict, locked, detail, diff}: a hash that differs is judged against its reference PNG; a changed corner gets a diff PNG."""
    s, c, kind, lk = row
    out = {'screen': s, 'corner': c, 'verdict': kind, 'locked': lk, 'detail': '', 'diff': None}
    if kind != 'changed':
        return out
    ref = Path(ref_dir) / f'{s}_{c}.png'
    if not ref.exists():
        return {**out, 'detail': f'no reference PNG {ref.name}'}
    r = next(x for x in details[s] if x['corner'] == c)
    cur = (r['w'], r['h'], r['rgba'])
    res = P.judge(P.decode_png(ref.read_bytes()), cur, tolerance)
    out.update(verdict='within tolerance' if res['verdict'] != 'changed' else 'changed', detail=res['reason'])
    if res['verdict'] == 'changed' and res['pixels'] and out_dir:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        out['diff'] = str(Path(out_dir) / f'{s}_{c}.diff.png')
        Path(out['diff']).write_bytes(P.diff_png(r['w'], r['h'], r['rgba'], res['pixels']))
    return out


def judge(details, base, locked, wasm, ref_dir=REFS, out_dir=None):
    """(lines, exit status, rows) for {screen: render_corners rows} against a baseline: the viewer build first, then each corner whose hash differs (equal hashes read no PNG)."""
    current = {s: {r['corner']: r['rgba_sha256'] for r in res} for s, res in details.items()}
    tolerance = base.get('tolerance', DEFAULT_TOLERANCE)
    finding = wasm_finding(wasm, base.get('wasm_sha256'))
    rows = [verdict(r, details, tolerance, ref_dir, out_dir) for r in compare(current, base['screens'], locked)]
    lines = [finding] if finding else []
    for r in rows:
        lines.append(f'changes: {r["screen"]} {r["corner"]}: {r["verdict"]}' + (f' ({r["detail"]})' if r['detail'] else '') + (' (wasm differs)' if finding else '')
                     + (' (CHANGED SINCE LOCK: Liam plays it again)' if r['locked'] and r['verdict'] != 'new' else '') + (f' diff: {r["diff"]}' if r['diff'] else ''))
    if not rows:
        lines.append(f'changes: {sum(len(v) for v in current.values())} renders in {len(current)} screen(s), none changed since the baseline')
    bad = finding or any(r['verdict'] != 'within tolerance' or (r['locked'] and r['verdict'] != 'new') for r in rows)
    return lines, 1 if bad else 0, rows


def accept(details, base, wasm, baseline=BASELINE, ref_dir=REFS):
    """Write baseline.json and one reference PNG per rendered corner; returns the line naming what the reviewer must write (the blob sha git gives the file)."""
    ref_dir = Path(ref_dir)
    ref_dir.mkdir(parents=True, exist_ok=True)
    for s, res in details.items():
        for r in res:
            (ref_dir / f'{s}_{r["corner"]}.png').write_bytes(G.R.png_bytes(r['w'], r['h'], r['rgba']))
    current = {s: {r['corner']: r['rgba_sha256'] for r in res} for s, res in details.items()}
    text = json.dumps({'_doc': 'rgba_sha256 of each library screen at the four D19 corners; rewritten by uikit/napoleon/changes.py --accept', 'wasm_sha256': wasm,
                       'tolerance': base.get('tolerance', DEFAULT_TOLERANCE), 'screens': {**base['screens'], **current}}, indent=1) + '\n'
    Path(baseline).write_text(text, encoding='utf-8', newline='\n')
    data = text.encode('utf-8')
    blob = hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()
    return f'baseline written; it is not accepted until the reviewer adds "Baseline accepted: {blob}" to jobs/<id>/review.md'


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--accept', action='store_true', help='rewrite baseline.json and the reference PNGs with what was just rendered')
    ap.add_argument('--allow-locked', action='store_true', help='with --accept: also accept a change to a locked screen (it stays flagged for Liam to play again)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--wasm')
    ap.add_argument('--out', help='where diff PNGs go (default: <wasm dir>/uikit_gate, which CI keeps as an artifact)')
    ap.add_argument('--screens', nargs='*')
    a = ap.parse_args()
    screens = library_screens()
    if a.screens:
        screens = {k: v for k, v in screens.items() if k in a.screens}
    wasm_dir = Path(a.wasm or ROOT / 'build' / 'viewer' / 'out')
    wasm = wasm_sha(wasm_dir)
    details = {name: G.render_corners(folder, wasm_dir, keep_rgba=True) for name, folder in screens.items()}
    base = json.loads(BASELINE.read_text(encoding='utf-8')) if BASELINE.exists() else {'screens': {}}
    baseline = base['screens']
    if a.screens:   # compare only the screens asked for
        baseline = {k: v for k, v in baseline.items() if k in screens}
    locked = locked_screens()
    lines, status, rows = judge(details, {**base, 'screens': baseline}, locked, wasm, out_dir=a.out or wasm_dir / 'uikit_gate')
    hard = [r for r in rows if r['locked'] and r['verdict'] != 'new']
    if a.json:
        print(json.dumps({'wasm': wasm_finding(wasm, base.get('wasm_sha256')), 'changes': rows, 'locked': sorted(locked)}, indent=1))
    else:
        print('\n'.join(lines))
    if a.accept:
        if hard and not a.allow_locked:
            print('changes: a locked screen changed: refusing --accept without --allow-locked (the change stays flagged until Liam plays it again)')
            return 1
        print(accept(details, base, wasm))
        return 0
    return status


if __name__ == '__main__':
    sys.exit(main())
