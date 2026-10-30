#!/usr/bin/env python3
"""The control API: one call per verb, blocks until a checked result, always one JSON object (J4).

purpose: (untested on the PC until J44: scene, shot, reset, perf and state are tested against fakes only; cam, order, pause and speed are refused until J43) name a scenario and a camera pose and get a settled, checked answer back (scene, cam, shot, order, pause, speed, reset, perf, state), over the proxy's ctl channel (job.sh ctl) and the watcher's shot job; game-agnostic, everything game-specific comes from the adapter's `ctl` block and the scenarios registry
usage: ctl.py [--owner O] [--adapter A] [--registry R] <verb> [args]   verbs: scene <id> | cam <scenario:pose | x y z yaw pitch [fov]> | shot <name> | order <unit> move x z [facing] | halt | formation <f> | pause on|off | speed <x> | reset [<id>] | perf <seconds> | state | key|click|wait (probe only)
when: every time an agent needs a known game state or a frame (never type key taps or sleeps for it); the acceptance runner (acceptance.py) calls the same functions
not-a-verb: a host-side client over harness/core/job.sh and the proxy's ctl verbs, not a registry operation; a J12 core candidate

Result contract (every verb, tests/test_ctl.py): `status` ok | failed | refused, `reason`, the verb's fields, `settle` (what it waited for and how
long), `check` (what was compared: expected against got; ok is never returned without one), `evidence` (paths: shot, state, log) and
`start_utc` / `end_utc`. A failure names the step and keeps its evidence. Exit code 0 only for ok (failed 1, refused 2).
Settle (defined once, `Settle`): scene ready + N presented frames + the scene unchanged for T ms (the proxy has no shader-creation hook
yet: frame and scene stability stand in, fact napoleon.ctl.settle_signal). N and T are adapter fields, never sleeps in callers.
Routes the adapter marks unreachable (fact napoleon.battle.script_api_reachable) make cam, order, pause and speed answer `refused` with that reason.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROBE_ONLY = ('key', 'click', 'wait')   # rule 78: never part of a scenario row, a generated file or the acceptance script
VERBS = ('scene', 'cam', 'shot', 'order', 'pause', 'speed', 'reset', 'perf', 'state')
POSE_FIELDS = ('x', 'y', 'z', 'yaw', 'pitch', 'fov')


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


class Refused(Exception):
    pass


def make_result(verb, status, reason='', start=None, check=None, settle=None, evidence=None, **fields):
    """The one result shape. `ok` without a `check` is a bug (rule 77): it is turned into `failed` here, so no verb can return it."""
    r = {'verb': verb, 'status': status, 'reason': reason}
    r.update(fields)
    r['settle'] = settle or {}
    r['check'] = check or {}
    r['evidence'] = evidence or {}
    r['start_utc'] = start or utc()
    r['end_utc'] = utc()
    if status == 'ok' and not r['check']:
        r['status'], r['reason'] = 'failed', 'verb returned ok without a check (rule 77)'
    return r


def exit_code(result):
    return {'ok': 0, 'failed': 1, 'refused': 2}.get(result['status'], 1)


# ---- scenarios and poses ------------------------------------------------------------------------------------------------
def load_scenarios(path):
    rows = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r['id']] = r
    return rows


def resolve_scenario(rows, sid):
    if sid not in rows:
        raise Refused(f'unknown scenario {sid!r} (known: {", ".join(sorted(rows))})')
    return rows[sid]


def scenario_target(row, battles_dir):
    """The autostart target a scenario row loads through: a battle preset of the same id (generated from the row), else refused with why."""
    if row['kind'] in ('land', 'siege', 'naval') and (Path(battles_dir) / f"{row['id']}.txt").exists():
        return f"battle:{row['id']}"
    if row['kind'] == 'historical':
        raise Refused('no autostart route for historical battles yet (open fact napoleon.autostart.historical)')
    if row['kind'] == 'campaign':
        raise Refused('campaign scenarios load through saves/napoleon/load_save.sh until the recipe generation is wired into scene (J4 report, open)')
    raise Refused(f"scenario {row['id']} has no battle preset file {row['id']}.txt: generate it from the row")


def parse_pose(text):
    """'x y z yaw pitch [fov]' -> dict. Raises Refused on a wrong count or a non-number."""
    parts = text.replace(',', ' ').split()
    if len(parts) not in (5, 6):
        raise Refused(f'a pose is x y z yaw pitch [fov]: got {len(parts)} values')
    try:
        vals = [float(p) for p in parts]
    except ValueError as e:
        raise Refused(f'a pose has only numbers: {e}')
    return dict(zip(POSE_FIELDS, vals))


def resolve_pose(rows, ref):
    """`<scenario>:<pose>` from the row's camera_poses, or literal numbers."""
    if re.match(r'^[a-z0-9][a-z0-9_.-]*:[a-z0-9][a-z0-9_.-]*$', ref):
        sid, pid = ref.split(':', 1)
        poses = resolve_scenario(rows, sid).get('camera_poses', {})
        if pid not in poses:
            raise Refused(f'scenario {sid} has no pose {pid!r} (has: {", ".join(sorted(poses)) or "none"})')
        return dict(poses[pid])
    return parse_pose(ref)


def pose_check(expected, got, tol):
    """Compare a pose with the one read back. Each field within tol[field] (default tol['default']). Returns (ok, check dict)."""
    detail, ok = {}, True
    for f in POSE_FIELDS:
        if f not in expected:
            continue
        t = tol.get(f, tol.get('default', 0.5))
        g = got.get(f)
        d = None if g is None else abs(g - expected[f])
        if f in ('yaw', 'pitch') and d is not None:
            d = min(d, 360 - d) if d <= 360 else d
        within = d is not None and d <= t
        ok = ok and within
        detail[f] = {'expected': expected[f], 'got': g, 'tolerance': t, 'within': within}
    return ok, detail


# ---- settle ---------------------------------------------------------------------------------------------------------------
class Settle:
    """scene ready + N presented frames + the scene unchanged for T ms. `state` is a callable returning the proxy's state dict; `clock`
    and `sleep` are injectable so the tests need no game."""
    def __init__(self, frames, quiet_ms, timeout_s, ready_scenes, state, clock=time.monotonic, sleep=time.sleep, poll_s=0.5):
        self.frames, self.quiet_ms, self.timeout_s, self.ready = frames, quiet_ms, timeout_s, set(ready_scenes)
        self.state, self.clock, self.sleep, self.poll_s = state, clock, sleep, poll_s

    def wait(self):
        t0 = self.clock()
        first_frame = None
        last = None
        while True:
            s = self.state()
            last = s
            if s.get('scene') in self.ready:
                f = s.get('frame', 0)
                first_frame = f if first_frame is None else first_frame
                if f - first_frame >= self.frames and s.get('scene_s', 0) * 1000 >= self.quiet_ms:
                    return {'waited_for': f'scene in {sorted(self.ready)} + {self.frames} frames + {self.quiet_ms} ms stable',
                            'waited_s': round(self.clock() - t0, 2), 'frames': f - first_frame, 'scene': s['scene'], 'settled': True}
            else:
                first_frame = None
            if self.clock() - t0 > self.timeout_s:
                return {'waited_for': f'scene in {sorted(self.ready)} + {self.frames} frames + {self.quiet_ms} ms stable',
                        'waited_s': round(self.clock() - t0, 2), 'scene': (last or {}).get('scene'), 'settled': False}
            self.sleep(self.poll_s)


# ---- the client -------------------------------------------------------------------------------------------------------------
def job_sh_transport(owner, adapter=None):
    """(line, wait_s) -> (exit code, parsed result or None) over `job.sh ctl`."""
    def send(line, wait_s=170):
        cmd = ['bash', str(HERE / 'job.sh')] + (['--adapter', str(adapter)] if adapter else []) + ['ctl', owner, line, str(wait_s)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        try:
            return p.returncode, json.loads(p.stdout)
        except ValueError:
            return p.returncode, None
    return send


class Ctl:
    def __init__(self, transport, scenarios, adapter, battles_dir=None, shotter=None, clock=time.monotonic, sleep=time.sleep):
        self.t, self.rows, self.cfg = transport, scenarios, adapter.get('ctl', {})
        self.battles_dir = battles_dir or ROOT / 'proxy' / adapter.get('game', 'napoleon') / 'lua' / 'battles'
        self.shotter, self.clock, self.sleep = shotter, clock, sleep
        self.scene_id = None

    # -- plumbing
    def state(self):
        rc, r = self.t('state', 20)
        if rc != 0 or not r:
            raise RuntimeError(f'ctl state failed (exit {rc}): is the game running with dev.ctl=1?')
        return r['state']

    def settle(self):
        s = self.cfg.get('settle', {})
        return Settle(s.get('frames', 30), s.get('quiet_ms', 2000), s.get('timeout_s', 120), s.get('ready_scenes', ['battle_deploy', 'battle', 'campaign']),
                      self.state, self.clock, self.sleep).wait()

    def route(self, name):
        rt = self.cfg.get('routes', {}).get(name, {})
        if rt.get('status', 'unknown') != 'reachable':
            raise Refused(f"route {name} is {rt.get('status', 'unknown')}: {rt.get('why', 'not probed')} (fact {rt.get('fact', '?')})")

    def run(self, verb, *args):
        start = utc()
        try:
            fn = getattr(self, 'v_' + verb)
            return fn(start, *args)
        except Refused as e:
            return make_result(verb, 'refused', str(e), start)
        except Exception as e:   # a failure names its step and keeps going to the caller as data, never a traceback
            return make_result(verb, 'failed', f'{type(e).__name__}: {e}', start)

    # -- verbs
    def v_state(self, start):
        s = self.state()
        return make_result('state', 'ok', start=start, state=s, check={'compared': 'state.json readable', 'expected': 'a scene and a frame', 'got': {'scene': s.get('scene'), 'frame': s.get('frame')}})

    def v_scene(self, start, sid):
        row = resolve_scenario(self.rows, sid)
        target = scenario_target(row, self.battles_dir)
        rc, r = self.t(f'autostart {target} 240', 260)
        if rc != 0 or not r:
            return make_result('scene', 'failed', f"step autostart {target}: {(r or {}).get('reason', 'no result')}", start, scenario=sid, evidence={'ctl': r})
        settle = self.settle()
        if not settle['settled']:
            return make_result('scene', 'failed', 'step settle: ' + json.dumps(settle), start, scenario=sid, settle=settle, evidence={'ctl': r})
        self.scene_id = sid
        got = {'map': r.get('map'), 'scene': settle['scene']}
        want = {'map': row['map'].split(' ')[0] if row['kind'] == 'campaign' else row['map']}
        ok = row['kind'] == 'campaign' or got['map'] == want['map']
        check = {'compared': 'preset map against the row', 'expected': want, 'got': got, 'ok': ok}
        return make_result('scene', 'ok' if ok else 'failed', '' if ok else 'WRONG MAP', start, scenario=sid, target=target, load_s=r.get('load_s'), settle=settle, check=check, evidence={'ctl': r})

    def v_cam(self, start, *ref):
        self.route('camera')
        pose = resolve_pose(self.rows, ' '.join(ref))
        raise Refused('camera route is reachable but the pose conversion is not implemented: ' + json.dumps(pose))

    def v_order(self, start, *args):
        self.route('orders')
        raise Refused('order route is reachable but not implemented (J28)')

    def v_pause(self, start, mode):
        if mode not in ('on', 'off'):
            raise Refused('pause takes on or off')
        self.route('speed')
        raise Refused('pause route is reachable but not implemented')

    def v_speed(self, start, x):
        try:
            float(x)
        except ValueError:
            raise Refused('speed takes a number')
        self.route('speed')
        raise Refused('speed route is reachable but not implemented')

    def v_shot(self, start, name):
        if not re.match(r'^[A-Za-z0-9_.-]+$', name):
            raise Refused('a shot name is letters, digits, . _ -')
        if self.shotter is None:
            raise Refused('no shot helper configured')
        settle = self.settle()
        if not settle['settled']:
            return make_result('shot', 'failed', 'step settle: ' + json.dumps(settle), start, settle=settle)
        path, size = self.shotter(name)
        ok = bool(path) and size > 0
        return make_result('shot', 'ok' if ok else 'failed', '' if ok else 'empty shot', start, settle=settle, shot=path,
                           check={'compared': 'shot file written', 'expected': 'size > 0', 'got': size, 'ok': ok}, evidence={'shot': path})

    def v_reset(self, start, sid=None):
        row = resolve_scenario(self.rows, sid) if sid else None
        target = scenario_target(row, self.battles_dir) if row else 'frontend'
        rc, r = self.t(f'reset {target} 240', 260)
        if rc != 0 or not r:
            return make_result('reset', 'failed', f"step reset {target}: {(r or {}).get('reason', 'no result')}", start, evidence={'ctl': r})
        settle = self.settle() if row else {'waited_for': 'frontend', 'settled': True}
        ok = settle['settled']
        return make_result('reset', 'ok' if ok else 'failed', '' if ok else 'step settle', start, path='warm', settle=settle,
                           check={'compared': 'scene after reset', 'expected': target, 'got': settle.get('scene', 'frontend'), 'ok': ok}, evidence={'ctl': r})

    def v_perf(self, start, secs):
        rc, r = self.t(f'perf {int(secs)}', int(secs) + 30)
        if rc != 0 or not r:
            return make_result('perf', 'failed', f"step perf: {(r or {}).get('reason', 'no result (dev.perf off?)')}", start, evidence={'ctl': r})
        cfg = self.cfg.get('perf', {})
        sane = r.get('frames', 0) > 0 and r.get('frame_ms', {}).get('p50', 0) > 0
        check = {'compared': 'frames recorded and a positive median', 'expected': 'frames > 0, p50 > 0', 'got': {'frames': r.get('frames'), 'p50': r.get('frame_ms', {}).get('p50')}, 'ok': sane}
        return make_result('perf', 'ok' if sane else 'failed', '' if sane else 'no usable frames', start, check=check,
                           frame_ms=r.get('frame_ms'), frames=r.get('frames'), mem=r.get('mem'), vram={'source': cfg.get('vram_source', 'nvidia-smi from a watcher job (not read by this verb yet)')},
                           evidence={'ctl': r})


def main(argv=None):
    ap = argparse.ArgumentParser(description='control API: one checked JSON result per verb')
    ap.add_argument('--owner', default='claude-ctl')
    ap.add_argument('--adapter', default=str(ROOT / 'harness' / 'napoleon' / 'adapter.json'))
    ap.add_argument('--registry', default=str(ROOT / 'registries' / 'scenarios.jsonl'))
    ap.add_argument('verb')
    ap.add_argument('args', nargs='*')
    a = ap.parse_args(argv)
    if a.verb in PROBE_ONLY:
        print(json.dumps(make_result(a.verb, 'refused', f'{a.verb} is a probe verb: use job.sh ctl directly; scenarios and scripts never use it (rule 78)')))
        return 2
    if a.verb not in VERBS:
        print(json.dumps(make_result(a.verb, 'refused', f'unknown verb; verbs: {", ".join(VERBS)}')))
        return 2
    adapter = json.loads(Path(a.adapter).read_text(encoding='utf-8'))
    ctl = Ctl(job_sh_transport(a.owner, a.adapter), load_scenarios(a.registry), adapter)
    res = ctl.run(a.verb, *a.args)
    print(json.dumps(res, indent=2))
    return exit_code(res)


if __name__ == '__main__':
    sys.exit(main())
