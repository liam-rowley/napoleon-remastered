#!/usr/bin/env python3
"""J30 PC run driver: the RmlUi host test over the front end, the campaign map and a battle, per back-buffer size (brief J30 PC test b-e).

Everything waits inside this one call (core/harness/ctl.py and job.sh do the launching and waiting; the game lock is the caller's).
usage: python3 proxy/runs/20261103_j30pc/run.py <phase> [--sizes 1920x1080,...] [--owner j30] [--core DIR]
  phases: smoke (front end at 1080p: show, state, dump), cells (b + c + e: dumps, checks, interaction per scene and size),
          perf (d: perf 10 s x 3 per scene, size and ui setting), sys (d on the system d3d9 backend at 1080p)
Writes results.jsonl beside this file (one JSON line per step) and dumps under ui.dump_dir, copied into dumps/.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GAME = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
DUMPS = Path(r'C:\napoleon_remastered_pc\ui_dumps')
DOC = 'hosttest/hosttest.rml'
ONLY = set()   # --only battle,...: run just these scenes (cells)
SCENES = [('frontend', None), ('campaign', 'campaign_start'), ('battle', 'land_small')]


def touch_lock():
    subprocess.run(['bash', str(ROOT / 'core' / 'harness' / 'job.sh'), 'touch'], capture_output=True)


def log(step, **kw):
    touch_lock()   # the run outlasts the lock's 20 min expiry; every step refreshes it
    rec = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'step': step, **kw}
    with open(HERE / 'results.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    print(json.dumps(rec)[:600], flush=True)
    return rec


class Run:
    def __init__(self, owner, core):
        self.owner, self.core = owner, Path(core)
        sys.path.insert(0, str(self.core / 'harness'))
        os.environ['WSP_GAME_ROOT'] = str(ROOT)
        import ctl as ctlmod
        self.ctlmod = ctlmod
        ap = ROOT / 'harness' / 'napoleon' / 'adapter.json'
        self.pc = ctlmod.Pc(owner, str(ap), json.loads(ap.read_text(encoding='utf-8')))

    def keys(self, **kv):
        self.pc.set_keys({k.replace('_', '.', 1): str(v) for k, v in kv.items()})

    def ctl(self, line, wait=60):
        ok, r = self.pc.ctl(line, wait)
        return ok, (r or {})

    def ctlpy(self, *args, timeout=900):
        p = subprocess.run([sys.executable, str(self.core / 'harness' / 'ctl.py'), '--owner', self.owner, *args], capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, 'WSP_GAME_ROOT': str(ROOT)})
        try:
            return json.loads(p.stdout[p.stdout.index('{'):p.stdout.rindex('}') + 1])
        except ValueError:
            return {'status': 'failed', 'reason': (p.stdout + p.stderr)[-400:]}

    def launch(self, size, **keys):
        self.pc.exit()
        self.keys(**keys)
        self.size, self.launch_keys, self.last = size, keys, None
        return self.pc.launch(size)

    def goto(self, scene):
        if scene is None:
            return {'status': 'ok'}
        if getattr(self, 'last', None) == 'campaign_start':
            # a campaign has no warm reset (fact napoleon.campaign.quit_to_menu): ctl.py would relaunch at its default size, so relaunch
            # here at this cell's size and keys first (the first cells run lost its 1440p battle to that, 19:00 UTC)
            self.launch(self.size, **self.launch_keys)
        self.last = scene
        return self.ctlpy('scene', scene)

    def ui(self, line, wait=60):
        ok, r = self.ctl('ui ' + line, wait)
        return ok, r

    def dump(self, name, dp):
        ok, r = self.ui(f'dump {name}')
        out = {'ok': ok, 'reason': r.get('reason'), 'dump': r.get('dump')}
        if ok:
            src = Path(r['dump']['file'])
            (HERE / 'dumps').mkdir(exist_ok=True)
            shutil.copy2(src, HERE / 'dumps' / src.name)
            (HERE / 'checks').mkdir(exist_ok=True)
            p = subprocess.run([sys.executable, str(ROOT / 'tools' / 'ui_hosttest.py'), 'check', str(HERE / 'dumps' / src.name), '--dp', str(dp),
                                '--crops', str(HERE / 'crops'), '--json', str(HERE / 'checks' / f'{name}.json')], capture_output=True, text=True)
            (HERE / 'checks').mkdir(exist_ok=True)
            out['check'] = p.stdout.strip()[-400:]
        return out

    def state(self, secs=0):
        ok, r = self.ui(f'state {secs}' if secs else 'state', 60 + secs)
        return r.get('ui', {}) if ok else {'error': r.get('reason')}

    def interaction(self, tag, bb):
        """c) the routing contract in this scene. Positions in back-buffer pixels from the document's dp layout."""
        W, H = bb
        dp = H / 1080 * 1.0
        P = lambda x, y: (int((40 + x) * dp), int((40 + y) * dp))
        tx, ty = P(100 + 90, 250 + 22)              # the click target's centre
        lx, ly = P(10 + 150, 360 + 100)             # the list's centre
        ex, ey = int(W * 0.62), int(H * 0.93)       # off the document: low on the screen, right of centre
        steps = {}
        s0 = self.state()
        c0 = s0.get('counters', {}).get('click_target', 0)
        def run(name, line):
            ok, r = self.ui(line)
            steps[name] = {'ok': ok, 'delta': r.get('delta'), 'counter': (r.get('ui') or {}).get('counters', {}).get('click_target', 0), 'reason': r.get('reason'),
                           'hovered': (r.get('ui') or {}).get('hovered'), 'scrolled': (r.get('ui') or {}).get('scrolled')}
        run('click_target', f'click {tx} {ty}')
        run('click_elsewhere', f'click {ex} {ey}')
        run('press_engine', f'click {ex} {ey} left down')
        run('release_over_doc', f'click {tx} {ty} left up')
        run('wheel_list', f'wheel {lx} {ly} 2')
        time.sleep(1)   # RmlUi scrolls smoothly over the next frames
        steps['wheel_list']['scrolled_after_1s'] = self.state().get('scrolled')
        run('wheel_target', f'wheel {tx} {ty} 2')
        run('wheel_game', f'wheel {ex} {ey} 1')
        d = lambda n, ev: (steps[n].get('delta') or {}).get(ev, [0, 0])
        checks = {
            'click_target_to_rml': d('click_target', 'down') == [1, 0] and d('click_target', 'up') == [1, 0] and steps['click_target']['counter'] == c0 + 1,
            'click_elsewhere_to_engine': d('click_elsewhere', 'down') == [0, 1] and d('click_elsewhere', 'up') == [0, 1] and steps['click_elsewhere']['counter'] == c0 + 1,
            'engine_press_stays_engine': d('press_engine', 'down') == [0, 1] and d('release_over_doc', 'up') == [0, 1] and steps['release_over_doc']['counter'] == c0 + 1,
            'wheel_list_to_rml': d('wheel_list', 'wheel') == [1, 0] and bool(steps['wheel_list'].get('scrolled_after_1s')),
            'wheel_target_to_engine': d('wheel_target', 'wheel') == [0, 1],
            'wheel_game_to_engine': d('wheel_game', 'wheel') == [0, 1],
        }
        # hide / show / reload: hidden, a click on the target's spot is the engine's; shown again, it is RmlUi's
        ok, _ = self.ui(f'hide {DOC}'); run('hidden_click', f'click {tx} {ty}')
        self.ui(f'show {DOC}'); run('shown_click', f'click {tx} {ty}')
        self.ui(f'reload {DOC}'); run('reloaded_click', f'click {tx} {ty}')
        checks['hidden_to_engine'] = d('hidden_click', 'down') == [0, 1]
        checks['shown_to_rml'] = d('shown_click', 'down') == [1, 0]
        checks['reloaded_to_rml'] = d('reloaded_click', 'down') == [1, 0]
        return log('interaction', tag=tag, ok=all(checks.values()), checks=checks, steps=steps, pos={'target': [tx, ty], 'list': [lx, ly], 'else': [ex, ey]})


def smoke(r, size):
    log('launch', size=size, res=r.launch(size, ui_enabled=1, ui_show=DOC, ui_scale=100))
    st = r.state(2)
    log('state', size=size, ui=st)
    W, H = map(int, size.split('x'))
    log('dump', size=size, res=r.dump(f'smoke_fe_{H}', H / 1080))


def cells(r, sizes):
    for size in sizes:
        W, H = map(int, size.split('x'))
        log('launch', size=size, res=r.launch(size, ui_enabled=1, ui_show=DOC, ui_scale=100))
        for tag, scene in [s for s in SCENES if not ONLY or s[0] in ONLY]:
            g = r.goto(scene)
            log('scene', size=size, scene=tag, status=g.get('status'), reason=g.get('reason'))
            ok, _ = r.ui(f'show {DOC}')
            st = r.state(3)
            log('state', size=size, scene=tag, ui=st)
            log('dump', size=size, scene=tag, scale=100, res=r.dump(f'{tag}_{H}_100', H / 1080))
            if H == 1080 or H == 2160:
                pct = 85 if H == 1080 else 125
                r.ui(f'scale {pct}')
                time.sleep(1)
                log('dump', size=size, scene=tag, scale=pct, res=r.dump(f'{tag}_{H}_{pct}', H / 1080 * pct / 100))
                r.ui('scale 100')
            r.interaction(f'{tag}_{H}', (W, H))
        # e) back to the front end with the document open (warm reset from the battle), then into a battle again and back
        g = r.ctlpy('reset')
        st = r.state(2)
        log('warm_reset', size=size, status=g.get('status'), reason=g.get('reason'), ui=st)
        r.interaction(f'after_reset_{H}', (W, H))
        log('dump', size=size, scene='after_reset', res=r.dump(f'after_reset_{H}', H / 1080))


def perf(r, sizes, backend='dxvk', runs=3, secs=10):
    for size in sizes:
        for setting in ('off', 'idle', 'doc'):
            keys = {'ui_enabled': 0 if setting == 'off' else 1, 'ui_show': DOC if setting == 'doc' else '', 'ui_scale': 100, 'proxy_backend': backend}
            log('launch', size=size, setting=setting, backend=backend, res=r.launch(size, **keys))
            for tag, scene in SCENES:
                g = r.goto(scene)
                if setting == 'doc':
                    r.ui(f'show {DOC}')
                time.sleep(3)
                for i in range(runs):
                    ok, p = r.ctl(f'perf {secs}', secs + 40)
                    ui = r.state(0) if setting != 'off' else {}
                    log('perf', size=size, scene=tag, setting=setting, backend=backend, run=i + 1, status=g.get('status'),
                        frame_ms=p.get('frame_ms'), frames=p.get('frames'), mem=p.get('mem'),
                        ui_cost=(ui.get('cost_ms') if isinstance(ui, dict) else None), draws=(ui.get('draws_last_frame') if isinstance(ui, dict) else None))


def battle(r, size, keyspec):
    """One launch with the given ui keys, then land_small: does the battle load? (the hang bisection, results.jsonl `battle`)"""
    keys = dict(kv.split('=', 1) for kv in keyspec.split(',')) if keyspec else {}
    keys = {k.replace('.', '_', 1): v for k, v in keys.items()}
    log('launch', size=size, keys=keys, res=r.launch(size, **keys))
    t0 = time.time()
    g = r.goto('land_small')
    st = r.state(2) if keys.get('ui_enabled') == '1' else {}
    log('battle', size=size, keys=keys, status=g.get('status'), reason=g.get('reason'), load_s=round(time.time() - t0, 1), ui=st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['smoke', 'cells', 'perf', 'sys', 'battle'])
    ap.add_argument('--keys', default='', help='battle: ui keys as k=v,k=v')
    ap.add_argument('--only', default='', help='cells: only these scenes (frontend,campaign,battle)')
    ap.add_argument('--sizes', default='1920x1080,2560x1440,3840x2160')
    ap.add_argument('--owner', default='j30')
    ap.add_argument('--core', default=str(ROOT / 'core'))
    a = ap.parse_args()
    ONLY.update(x for x in a.only.split(',') if x)
    r = Run(a.owner, a.core)
    sizes = a.sizes.split(',')
    try:
        if a.phase == 'smoke':
            smoke(r, sizes[0])
        elif a.phase == 'cells':
            cells(r, sizes)
        elif a.phase == 'battle':
            battle(r, sizes[0], a.keys)
        elif a.phase == 'perf':
            perf(r, sizes)
        else:
            perf(r, ['1920x1080'], backend='system')
    finally:
        log('exit', how=r.pc.exit())


if __name__ == '__main__':
    main()
