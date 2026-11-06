#!/usr/bin/env python3
"""J32 S4 route A sittings: per screen kind open the vanilla screen as the game does, undraw it with each Lua means, and check data, handlers, input and cost.

The game lock is the caller's. One driver at a time (s3.py's pid file rule). No click goes near a destructive popup: the only clicks are on a panel's close button and a page's button.
usage: python3 proxy/runs/20261106_j32pc/s4.py camp | battle | fe [--size 1920x1080]
Writes s4.jsonl beside this file, shots under build/j32/s4/, and keeps proxy.log as build/j32/s4_<sitting>_proxy.log (j32snap lines).
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
CORE = ROOT / 'core'
OWNER = 'j32'
PROBE = (HERE / 'probes' / 's4.lua').as_posix()
FE = (HERE / 'probes' / 'fe_s4.lua').as_posix()
J9 = (ROOT / 'harness/runs/20261101_j9fix/probes').as_posix()
MODAL = 'napoleon_remastered/lua/probes/campaign_modal_close.lua'
SHOTS = ROOT / 'build' / 'j32' / 's4'
GAME_LOG = Path(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\napoleon_remastered\logs\proxy.log')
PID = ROOT / 'build' / 'j32' / 'driver.pid'
BASE = (1280, 960)   # the root's coordinate space in the J10 trees


def log(step, **kw):
    subprocess.run(['bash', str(CORE / 'harness' / 'job.sh'), 'touch', OWNER], capture_output=True)
    rec = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'step': step, **kw}
    with open(HERE / 's4.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    print(json.dumps(rec)[:360], flush=True)
    return rec


class S:
    def __init__(self, size):
        sys.path.insert(0, str(CORE / 'harness'))
        os.environ['WSP_GAME_ROOT'] = str(ROOT)
        import ctl as ctlmod
        ap = ROOT / 'harness' / 'napoleon' / 'adapter.json'
        self.pc = ctlmod.Pc(OWNER, str(ap), json.loads(ap.read_text(encoding='utf-8')))
        self.size = size
        self.W, self.H = (int(v) for v in size.split('x'))

    def launch(self):
        self.pc.exit()
        self.pc.set_keys({'ui.enabled': '1', 'ui.show': '', 'ui.scale': '100'})
        log('launch', res=self.pc.launch(self.size))

    def ctlpy(self, *args, timeout=900):
        SHOTS.mkdir(parents=True, exist_ok=True)
        p = subprocess.run([sys.executable, str(CORE / 'harness' / 'ctl.py'), '--owner', OWNER, '--out', str(SHOTS), *args], capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, 'WSP_GAME_ROOT': str(ROOT)})
        try:
            return json.loads(p.stdout[p.stdout.index('{'):p.stdout.rindex('}') + 1])
        except ValueError:
            return {'status': 'failed', 'reason': (p.stdout + p.stderr)[-300:]}

    def lua(self, args, wait=30, path=PROBE):
        ok, r = self.pc.ctl(f'lua {path} -- {args}' if args else f'lua {path}', wait)
        r = r or {}
        return log('lua', args=args, ok=ok, result=r.get('result', r.get('reason', r)))

    def shot(self, name):
        r = self.ctlpy('shot', 'j32_' + name)
        log('shot', name=name, status=r.get('status'), file=r.get('file') or r.get('shot'), reason=r.get('reason'))

    def perf(self, tag, secs=5, runs=2):
        for i in range(runs):
            ok, p = self.pc.ctl(f'perf {secs}', secs + 40)
            p = p or {}
            log('perf', tag=tag, run=i + 1, ok=ok, frame_ms=p.get('frame_ms'), frames=p.get('frames'))

    def click_base(self, x, y, tag):
        """A click at root coordinates, through the host's window route (no document is visible, so it is the engine's)."""
        px, py = int(x * self.W / BASE[0]), int(y * self.H / BASE[1])
        ok, r = self.pc.ctl(f'ui click {px} {py}', 30)
        log('click', tag=tag, at=[px, py], ok=ok, delta=(r or {}).get('delta'))

    def finish(self, name):
        log('exit', how=self.pc.exit())
        if GAME_LOG.exists():
            shutil.copy2(GAME_LOG, ROOT / 'build' / 'j32' / f's4_{name}_proxy.log')


MEANS = [('vis', 'vis {c} 0', 'vis {c} 1'), ('pvis', 'pvis {c} 0', 'pvis {c} 1'), ('alpha', 'alpha {c} 0', 'alpha {c} 255')]


def undrawn(s, comp, tag, click=None, still=None):
    """Each Lua means on `comp`: shot; the click that would act on it; is it still there; restore."""
    for name, off, on in MEANS:
        s.lua(off.format(c=comp))
        time.sleep(1.5)
        s.shot(f'{tag}_{name}')
        s.lua(f'pos {comp}')
        if click:
            s.click_base(*click, f'{tag}_{name}')
            time.sleep(1.5)
            s.lua(f'pos {comp}')
        s.lua(on.format(c=comp))
        time.sleep(1)
        if still:
            r = still()
            if not r:
                log('gone', tag=tag, means=name)
                return name
    r = s.lua(f'pos {comp}')
    x = str(r['result']).split()
    if len(x) >= 2 and x[0] != 'absent':
        s.lua(f'move {comp} -5000 -5000')
        time.sleep(1.5)
        s.shot(f'{tag}_move')
        if click:
            s.click_base(*click, f'{tag}_move')
            time.sleep(1.5)
        s.lua(f'pos {comp}')
        s.lua(f'move {comp} {x[0]} {x[1]}')
    return None


def camp(s):
    s.launch()
    log('scene', r=s.ctlpy('scene', 'campaign_start').get('status'))
    time.sleep(20)
    s.lua('top')
    # popup: the start-up event message
    s.lua('snap popup_before event_message')
    s.shot('popup_open')
    s.lua('pos event_message')
    s.lua('vis event_message 0')
    time.sleep(1.5)
    s.shot('popup_vis')
    s.lua('pos event_message')
    s.lua('snap popup_hidden event_message')
    s.perf('popup_hidden', runs=1)
    s.lua('call event_message OnOk')   # the handler, called while it is hidden
    time.sleep(3)
    s.lua('pos event_message')
    s.lua('top')
    for i in range(4):
        s.lua('', path=MODAL)
        time.sleep(4)
    s.shot('hud')
    s.perf('hud_closed')
    s.lua('ccost 20')
    s.lua('clock 2000')
    # panel: entity lists
    s.lua('ToggleEntityLists', path=J9 + '/camp_panel.lua')
    time.sleep(5)
    s.lua('snap lists_open entity_lists')
    s.shot('lists_open')
    s.perf('lists_open')
    s.lua('vis entity_lists 0')
    time.sleep(1.5)
    s.shot('lists_vis')
    s.perf('lists_hidden')
    s.lua('snap lists_hidden entity_lists')
    s.lua('army', 20)
    ok, r = s.pc.ctl('lua napoleon_remastered/lua/probes/campaign_select.lua', 30)
    log('select', ok=ok, result=(r or {}).get('result'))
    time.sleep(6)
    s.lua('snap lists_after_select entity_lists')
    s.lua('call agents LClick')          # the tab's own handler while hidden
    time.sleep(2)
    s.lua('snap lists_after_tab entity_lists')
    s.lua('vis entity_lists 1')
    time.sleep(1.5)
    s.shot('lists_back')
    s.lua('pos button_close')
    undrawn(s, 'entity_lists', 'lists', click=(1251, 698), still=lambda: 'absent' not in str(s.lua('pos entity_lists')['result']))
    s.lua('pos entity_lists')
    s.lua('close', path=J9 + '/camp_panel.lua')
    s.finish('camp')


def battle(s):
    s.launch()
    log('scene', r=s.ctlpy('scene', 'hist_dresden').get('status'))
    time.sleep(5)
    s.lua('top')
    s.lua('snap hud_before orders')
    s.shot('hud_open')
    s.perf('hud_open')
    s.lua('vis orders 0')
    time.sleep(1.5)
    s.shot('hud_vis')
    s.perf('hud_hidden')
    s.lua('snap hud_hidden orders')
    s.lua('bsel')                        # the game changes: a selection, while the bar is hidden
    time.sleep(3)
    s.lua('snap hud_after_select orders')
    s.shot('hud_selected_hidden')
    s.lua('bhalt')                       # an order straight through the engine with the bar hidden
    time.sleep(2)
    s.lua('snap hud_after_halt orders')
    s.lua('vis orders 1')
    time.sleep(1.5)
    s.shot('hud_selected_back')
    s.lua('clock 2000')
    undrawn(s, 'orders', 'hud')
    s.finish('battle')


def fe(s):
    s.launch()
    s.lua('visible', path=FE)
    s.shot('fe_main')
    s.lua('handler vis', path=FE)
    s.shot('fe_after_handler')
    for how in ('vis', 'alpha', 'move'):
        s.launch()
        s.lua(f'hide {how}', path=FE)
        time.sleep(2)
        s.shot(f'fe_hidden_{how}')
        ok, p = s.pc.ctl('perf 5', 45)
        log('perf', tag=f'fe_hidden_{how}', frame_ms=(p or {}).get('frame_ms'))
    s.finish('fe')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sitting', choices=['camp', 'battle', 'fe'])
    ap.add_argument('--size', default='1920x1080')
    a = ap.parse_args()
    if PID.exists():
        sys.exit(f'driver {PID.read_text()} may be running: remove {PID} once it is gone')
    PID.write_text(str(os.getpid()))
    s = S(a.size)
    try:
        {'camp': camp, 'battle': battle, 'fe': fe}[a.sitting](s)
    finally:
        try:
            log('end', how=s.pc.exit())
        finally:
            PID.unlink()


if __name__ == '__main__':
    main()
