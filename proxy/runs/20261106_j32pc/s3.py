#!/usr/bin/env python3
"""J32 S3 in game: stage the test documents into the PC scratch folder, dump them over the front end and a battle at the four cells, and compare with the viewer.

Everything waits inside one call; the game lock is the caller's (job.sh lock j32 <session> ...). One driver at a time (pid file, J10's crash cause).
usage: python3 proxy/runs/20261106_j32pc/s3.py stage | sit [--sizes 1920x1080,...] [--scenes frontend,battle] | parity [--only name]
  stage: viewer sites (render.py --stage-only) into <state>/_scratch/j32/ui/{hosttest,board,recipes,fonts}: ui.dir points there, nothing extra goes in the game folder
  sit: per size one launch; per scene and document show, set each scale, dump; hide. results.jsonl beside this file, dumps into build/j32/game
  parity: tools/ui_hosttest.py parity for every dump against its viewer render; parity.jsonl and crops/ beside this file
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = ROOT / 'core'
OWNER = 'j32'
UI_DIR_REL = r'..\..\..\..\..\napoleon_remastered_pc\_scratch\j32\ui'
SCRATCH_UI = Path(r'C:\napoleon_remastered_pc\_scratch\j32\ui')
DOCS = {'hosttest': 'hosttest/hosttest.rml', 'board': 'board/board.rml', 'recipes': 'recipes/recipes.rml'}
SRC = {'hosttest': ROOT / 'viewer/napoleon/hosttest', 'board': ROOT / 'viewer/napoleon/board', 'recipes': HERE / 'recipes'}
SCALES = {1080: [100, 85], 1440: [100], 2160: [125]}
GAME_OUT = ROOT / 'build' / 'j32' / 'game'
VIEW_OUT = ROOT / 'build' / 'j32' / 'viewer'
PID = ROOT / 'build' / 'j32' / 'driver.pid'


def log(step, **kw):
    subprocess.run(['bash', str(CORE / 'harness' / 'job.sh'), 'touch', OWNER], capture_output=True)
    rec = {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'step': step, **kw}
    with open(HERE / 'results.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec) + '\n')
    print(json.dumps(rec)[:400], flush=True)
    return rec


def stage():
    from_site = ROOT / 'build' / 'j32' / 'site'
    for name, src in SRC.items():
        subprocess.run([sys.executable, str(ROOT / 'viewer/core/render.py'), str(src), '--stage-only', str(from_site / name)], check=True, cwd=ROOT)
        dst = SCRATCH_UI / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(from_site / name / 'screen', dst)
        # the host cannot load <script src> (fact napoleon.ui.script_src_absolute_path): the game's copy carries the scripts inline
        for rml in dst.glob('*.rml'):
            t = rml.read_text(encoding='utf-8')
            t2 = re.sub(r'<script src="([^"]+)"></script>', lambda m: '<script>\n' + (dst / m.group(1)).read_text(encoding='utf-8') + '\n</script>', t)   # RmlUi reads <script> as CDATA: a wrapper would reach Lua as text
            if t2 != t:
                rml.write_text(t2, encoding='utf-8', newline='\n')
        (SCRATCH_UI / 'fonts').mkdir(parents=True, exist_ok=True)
        for f in (from_site / name / 'fonts').iterdir():
            shutil.copy2(f, SCRATCH_UI / 'fonts' / f.name)
    print(sorted(str(p.relative_to(SCRATCH_UI)) for p in SCRATCH_UI.rglob('*') if p.is_file()))


class Run:
    def __init__(self):
        sys.path.insert(0, str(CORE / 'harness'))
        os.environ['WSP_GAME_ROOT'] = str(ROOT)
        import ctl as ctlmod
        ap = ROOT / 'harness' / 'napoleon' / 'adapter.json'
        self.pc = ctlmod.Pc(OWNER, str(ap), json.loads(ap.read_text(encoding='utf-8')))

    def ui(self, line, wait=60):
        ok, r = self.pc.ctl('ui ' + line, wait)
        return ok, (r or {})

    def scene(self, sid):
        p = subprocess.run([sys.executable, str(CORE / 'harness' / 'ctl.py'), '--owner', OWNER, 'scene', sid], capture_output=True, text=True, timeout=900,
                           env={**os.environ, 'WSP_GAME_ROOT': str(ROOT)})
        try:
            return json.loads(p.stdout[p.stdout.index('{'):p.stdout.rindex('}') + 1])
        except ValueError:
            return {'status': 'failed', 'reason': (p.stdout + p.stderr)[-400:]}


def sit(sizes, scenes, docs=None):
    GAME_OUT.mkdir(parents=True, exist_ok=True)
    r = Run()
    try:
        for size in sizes:
            h = int(size.split('x')[1])
            r.pc.exit()
            r.pc.set_keys({'ui.enabled': '1', 'ui.dir': UI_DIR_REL, 'ui.show': '', 'ui.scale': '100'})
            log('launch', size=size, res=r.pc.launch(size))
            for scene in scenes:
                if scene == 'battle':
                    g = r.scene('land_small')
                    log('scene', size=size, scene=scene, status=g.get('status'), reason=g.get('reason'))
                    if g.get('status') != 'ok':
                        continue
                for doc, path in DOCS.items():
                    if docs and doc not in docs:
                        continue
                    ok, res = r.ui(f'show {path}')
                    log('show', doc=doc, ok=ok, reason=res.get('reason'))
                    time.sleep(2)
                    for pct in SCALES[h]:
                        r.ui(f'scale {pct}')
                        time.sleep(2)
                        name = f'{doc}_{scene}_{h}_{pct}'
                        ok, res = r.ui(f'dump {name}')
                        rec = {'name': name, 'ok': ok, 'reason': res.get('reason')}
                        if ok:
                            src = Path(res['dump']['file'])
                            shutil.copy2(src, GAME_OUT / src.name)
                            rec['sha256'] = hashlib.sha256(src.read_bytes()).hexdigest()
                        log('dump', **rec)
                    r.ui('scale 100')
                    ok, st = r.ui('state 1', 70)
                    log('state', doc=doc, scene=scene, size=size, ui=st.get('ui'))
                    r.ui(f'hide {path}')
    finally:
        log('exit', how=r.pc.exit())


def rect_of(doc, h, pct):
    if doc != 'hosttest':
        return None
    dp = h / 1080 * pct / 100
    return f'{round(40 * dp)},{round(40 * dp)},{round(560 * dp)},{round(640 * dp)}'


def parity(only=None, view=VIEW_OUT, out='parity', tol=8):
    (HERE / 'crops').mkdir(exist_ok=True)
    for g in sorted(GAME_OUT.glob('*.png')):
        doc, scene, h, pct = g.stem.split('_')
        if (only and only not in g.stem) or scene != 'frontend':   # battle dumps are byte-identical to the front end's for these opaque documents
            continue
        v = Path(view) / f'{doc}_{h}_{pct}.png'
        js = ROOT / 'build' / 'j32' / f'{out}_{g.stem}.json'
        cmd = [sys.executable, str(ROOT / 'tools/ui_hosttest.py'), 'parity', str(v), str(g), '--tolerance', str(tol), '--json', str(js), '--crops', str(HERE / 'crops' / out)]
        rect = rect_of(doc, int(h), int(pct))
        if rect:
            cmd += ['--rect', rect]
        p = subprocess.run(cmd, capture_output=True, text=True)
        d = json.loads(js.read_text(encoding='utf-8'))
        row = {'name': g.stem, **{k: d.get(k) for k in ('kind', 'offset', 'pixels', 'tolerance', 'beyond', 'share_beyond', 'max_delta', 'mean_delta', 'moved_tiles', 'moved', 'worst')}}
        with open(HERE / f'{out}.jsonl', 'a', encoding='utf-8') as f:
            f.write(json.dumps(row) + '\n')
        print(p.stdout.strip()[:200], g.stem, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('phase', choices=['stage', 'sit', 'parity'])
    ap.add_argument('--sizes', default='1920x1080,2560x1440,3840x2160')
    ap.add_argument('--scenes', default='frontend,battle')
    ap.add_argument('--only')
    ap.add_argument('--view', default=str(VIEW_OUT), help='parity: the folder of viewer renders')
    ap.add_argument('--out', default='parity', help='parity: name of the .jsonl and crops folder')
    ap.add_argument('--tolerance', type=int, default=8)
    ap.add_argument('--docs', default='', help='sit: only these documents')
    a = ap.parse_args()
    if a.phase == 'stage':
        return stage()
    if a.phase == 'parity':
        return parity(a.only, a.view, a.out, a.tolerance)
    PID.parent.mkdir(parents=True, exist_ok=True)
    if PID.exists():
        sys.exit(f'driver {PID.read_text()} may be running: remove {PID} once it is gone')
    PID.write_text(str(os.getpid()))
    try:
        sit(a.sizes.split(','), a.scenes.split(','), {x for x in a.docs.split(',') if x})
    finally:
        PID.unlink()


if __name__ == '__main__':
    main()
