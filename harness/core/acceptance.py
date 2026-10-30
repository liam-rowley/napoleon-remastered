#!/usr/bin/env python3
"""The acceptance gate: one pass proves the harness, the DLL and the control API hold; 20 in a row pass the phase 1 gate (J4, rules 28, 74, 79).

purpose: run N acceptance passes in the background against the committed baseline file (rule 74), stop at the first failure with its evidence, and append one line per pass to the committed ledger; also the pure checks the policy gate reuses (consecutive passes for a build)
usage: acceptance.py run --passes N [--owner O] [--baseline F] [--ledger F] | check-baseline [--baseline F] | streak --build ID --watcher V [--ledger F]
when: after every change to proxy/ or harness/ (rule 79: a job branch that changes them needs 20 consecutive ledger passes on its final DLL and watcher build); `check-baseline` and the helpers run in the tests gate
not-a-verb: orchestrates PC sessions through harness/core/ctl.py and job.sh (game-agnostic: the scenario list is the baseline's, the settings files and exe pin come from the adapter); a J12 core candidate

One pass: exe sha1 equals the adapter pin (rule 28); launch headless at the baseline's size; `scene` every baseline step; one `cam` pose and one
`shot` each; `perf 10` once; a warm reset; a relaunch; exit. Each step is compared with the baseline: load time within its tolerance, the shot
against the baseline shot (mean absolute pixel difference within the step's threshold), every settings file byte-identical after the exit.
A step's verb that is refused or failed fails the pass (nothing is skipped silently). Camera moves are never key or click (rule 78).
"""
import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = ROOT / 'harness' / 'acceptance' / 'baseline.json'
LEDGER = ROOT / 'harness' / 'acceptance' / 'ledger.jsonl'
NEEDED = 20   # rule 79
KINDS = ('land', 'siege', 'naval', 'historical', 'campaign')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha(path, algo='sha256'):
    h = hashlib.new(algo)
    h.update(Path(path).read_bytes())
    return h.hexdigest()


# ---- the baseline file (rule 74) -------------------------------------------------------------------------------------------
def baseline_problems(b):
    """Schema check of the baseline: what a pass is compared with. Returns a list of problems (empty = valid)."""
    errs = []
    for k in ('schema', 'date', 'build_id', 'fresh_boot', 'size', 'exe_sha1', 'steps', 'settings_files'):
        if k not in b:
            errs.append(f'baseline lacks "{k}"')
    if errs:
        return errs
    if b['schema'] != 1:
        errs.append('baseline schema must be 1')
    if not isinstance(b['fresh_boot'], bool):
        errs.append('fresh_boot is true or false (load times vary with the PC state: J3)')
    if not str(b['size']).count('x') == 1:
        errs.append('size is WxH')
    if not isinstance(b['steps'], list) or not b['steps']:
        errs.append('steps is a non-empty list')
        return errs
    seen = set()
    for i, s in enumerate(b['steps']):
        w = f'steps[{i}]'
        for k in ('scenario', 'kind', 'pose', 'load_time_s', 'load_tolerance_pct', 'shot', 'shot_threshold', 'deterministic'):
            if k not in s:
                errs.append(f'{w} lacks "{k}"')
        if s.get('kind') not in KINDS:
            errs.append(f'{w}.kind is one of {", ".join(KINDS)}')
        if s.get('scenario') in seen:
            errs.append(f'{w}: scenario {s.get("scenario")} twice')
        seen.add(s.get('scenario'))
        if s.get('deterministic') is False and not s.get('why_not'):
            errs.append(f'{w}: a non-deterministic scenario says why (never silent)')
    missing = [k for k in KINDS if k not in {s.get('kind') for s in b['steps']}]
    if missing:
        errs.append('the baseline covers every kind; missing: ' + ', '.join(missing))
    return errs


def load_baseline(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f'acceptance: no baseline file at {p}: acceptance refuses to run without one (rule 74)')
    b = json.loads(p.read_text(encoding='utf-8'))
    errs = baseline_problems(b)
    if errs:
        raise SystemExit('acceptance: the baseline is invalid:\n  ' + '\n  '.join(errs))
    return b


# ---- comparisons -------------------------------------------------------------------------------------------------------------
def load_time_ok(baseline_s, got_s, tolerance_pct):
    lim = baseline_s * (1 + tolerance_pct / 100.0)
    return got_s <= lim, {'compared': 'load time', 'baseline_s': baseline_s, 'got_s': got_s, 'limit_s': round(lim, 2)}


def mean_abs_diff(a_bytes, b_bytes):
    """Mean absolute per-channel difference (0-255) between two images, at the smaller size. Needs Pillow."""
    import io
    from PIL import Image
    a, b = Image.open(io.BytesIO(a_bytes)).convert('RGB'), Image.open(io.BytesIO(b_bytes)).convert('RGB')
    w, h = min(a.width, b.width), min(a.height, b.height)
    a, b = a.resize((w, h)), b.resize((w, h))
    pa, pb = a.tobytes(), b.tobytes()
    return sum(abs(x - y) for x, y in zip(pa, pb)) / len(pa)


def shot_ok(diff, threshold):
    return diff <= threshold, {'compared': 'shot against the baseline shot', 'mean_abs_diff': round(diff, 3), 'threshold': threshold}


def settings_unchanged(before, after):
    """Both are {file id: sha256 or None (absent)}. Byte-identical means the same map."""
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    return not changed, {'compared': 'settings files after the exit', 'changed': changed}


def exe_pin_ok(exe_sha1, pin):
    return exe_sha1 == pin, {'compared': 'Napoleon.exe sha1 against the pin (rule 28)', 'expected': pin, 'got': exe_sha1}


# ---- the ledger (rule 79) ----------------------------------------------------------------------------------------------------
def read_ledger(text):
    return [json.loads(line) for line in (text or '').splitlines() if line.strip()]


def ledger_line(n, build_id, watcher, kit, passed, steps, branch=''):
    return {'pass': n, 'utc': utc(), 'build_id': build_id, 'watcher': watcher, 'kit': kit, 'branch': branch,
            'result': 'pass' if passed else 'fail', 'steps': steps}


def streak(lines, build_id, watcher):
    """Passes in a row at the end of the ledger on this build and watcher: a fail, or a line of another build or watcher, ends the run."""
    n = 0
    for ln in reversed(lines):
        if ln.get('result') == 'pass' and ln.get('build_id') == build_id and ln.get('watcher') == watcher:
            n += 1
        else:
            break
    return n


# ---- one pass ----------------------------------------------------------------------------------------------------------------
def run_pass(baseline, env):
    """env supplies: exe_sha1(), settings(), launch(size), exit(), relaunch(), ctl (a harness Ctl), shot_diff(step) -> float, pin.
    Returns (passed, steps) where steps maps a step name to {ok, check or reason}; stops at the first failed step."""
    steps, passed = {}, True

    def record(name, ok, detail):
        nonlocal passed
        steps[name] = {'ok': bool(ok), **detail}
        passed = passed and bool(ok)
        return bool(ok)

    before = env['settings']()
    ok, d = exe_pin_ok(env['exe_sha1'](), baseline['exe_sha1'])
    if not record('exe_sha1', ok, d):
        return False, steps
    env['launch'](baseline['size'])
    for s in baseline['steps']:
        sid = s['scenario']
        r = env['ctl'].run('scene', sid)
        if r['status'] != 'ok':
            record(f'{sid}:scene', False, {'reason': r['reason']})
            return False, steps
        ok, d = load_time_ok(s['load_time_s'], r.get('load_s') or 0, s['load_tolerance_pct'])
        if not record(f'{sid}:load', ok, d):
            return False, steps
        r = env['ctl'].run('cam', f"{sid}:{s['pose']}")
        if not record(f'{sid}:cam', r['status'] == 'ok', {'reason': r['reason'], 'check': r['check']}):
            return False, steps
        r = env['ctl'].run('shot', f'{sid}_{s["pose"]}')
        if not record(f'{sid}:shot', r['status'] == 'ok', {'reason': r['reason'], 'check': r['check']}):
            return False, steps
        if s['deterministic']:
            ok, d = shot_ok(env['shot_diff'](s), s['shot_threshold'])
            if not record(f'{sid}:shot_match', ok, d):
                return False, steps
    r = env['ctl'].run('perf', '10')
    if not record('perf', r['status'] == 'ok', {'reason': r['reason'], 'check': r['check']}):
        return False, steps
    r = env['ctl'].run('reset', baseline['steps'][0]['scenario'])
    if not record('warm_reset', r['status'] == 'ok', {'reason': r['reason'], 'check': r['check']}):
        return False, steps
    env['exit']()
    env['relaunch'](baseline['size'])
    env['exit']()
    ok, d = settings_unchanged(before, env['settings']())
    record('settings_identical', ok, d)
    return passed, steps


def main(argv=None):
    ap = argparse.ArgumentParser(description='acceptance gate')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run'); r.add_argument('--passes', type=int, default=NEEDED); r.add_argument('--owner', default='claude-acceptance')
    r.add_argument('--baseline', default=str(BASELINE)); r.add_argument('--ledger', default=str(LEDGER))
    c = sub.add_parser('check-baseline'); c.add_argument('--baseline', default=str(BASELINE))
    s = sub.add_parser('streak'); s.add_argument('--build', required=True); s.add_argument('--watcher', required=True); s.add_argument('--ledger', default=str(LEDGER))
    a = ap.parse_args(argv)
    if a.cmd == 'check-baseline':
        load_baseline(a.baseline)
        print('baseline ok')
        return 0
    if a.cmd == 'streak':
        lp = Path(a.ledger)
        n = streak(read_ledger(lp.read_text(encoding='utf-8') if lp.exists() else ''), a.build, a.watcher)
        print(f'{n} consecutive passes on build {a.build}, watcher {a.watcher} (need {NEEDED})')
        return 0 if n >= NEEDED else 1
    load_baseline(a.baseline)   # refuses without a valid baseline (rule 74)
    raise SystemExit('acceptance run: the PC environment binding (launch, exit, shot, settings snapshot) is not wired in J4: the camera route is '
                     'unreachable (fact napoleon.battle.script_api_reachable), so a pass cannot succeed; see jobs/J4/report.md')


if __name__ == '__main__':
    sys.exit(main())
