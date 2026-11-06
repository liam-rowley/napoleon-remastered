#!/usr/bin/env python3
"""J32 S3: the layout boxes of the board in the viewer and in game, to name the first element that differs at a fractional dp ratio.

usage: python3 proxy/runs/20261106_j32pc/boxes.py run [--size 2560x1440 --pct 100]  (the lock is the caller's; a launch, one pointer move, then exit) | diff
A variant of the staged board lists every div's absolute box once, on a key in the viewer and on hide in game (a body onmouseover never fired in either), by print: it reaches the proxy log in game and the console log in the viewer (the host's Lua has no io).
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / 'build' / 'j32' / 'boxes'
GAME_LOG = Path(r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War\napoleon_remastered\logs\proxy.log')
SNIPPET = """
J32Done = false
function J32Dump(document)
	if J32Done then return end
	J32Done = true
	local list = document:GetElementsByTagName("div")
	for i, e in ipairs(list) do
		local line = "J32BOX " .. i .. " " .. tostring(e.id) .. " " .. tostring(e.class_name) .. " " .. tostring(e.absolute_left) .. " " .. tostring(e.absolute_top) .. " " .. tostring(e.offset_left) .. " " .. tostring(e.offset_top) .. " " .. tostring(e.offset_width) .. " " .. tostring(e.offset_height)
		print(line)
	end
end
"""


def variant(src, dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    rml = dst / 'board.rml'
    t = rml.read_text(encoding='utf-8')
    t = t.replace('<body id="root" data-model="board">', '<body id="root" data-model="board" onkeydown="J32Dump(document)" onhide="J32Dump(document)">')
    return rml, t


def run(a):
    sys.path.insert(0, str(ROOT / 'viewer/core'))
    import render as R
    w, h = (int(v) for v in a.size.split('x'))
    ratio = a.ratio or h / 1080 * a.pct / 100
    OUT.mkdir(parents=True, exist_ok=True)
    # viewer
    site = ROOT / 'build' / 'j32' / 'site_boxes'
    R.stage(ROOT / 'viewer/napoleon/board', site, ROOT / 'build/viewer/out')
    rml, t = variant(site / 'screen', ROOT / 'build' / 'j32' / 'tmp_boxes')
    shutil.rmtree(ROOT / 'build' / 'j32' / 'tmp_boxes')
    p = site / 'screen' / 'board.rml'
    t = p.read_text(encoding='utf-8').replace('<body id="root" data-model="board">', '<body id="root" data-model="board" onkeydown="J32Dump(document)" onhide="J32Dump(document)">')
    p.write_text(t, encoding='utf-8', newline='\n')
    lua = site / 'screen' / 'board.lua'
    lua.write_text(lua.read_text(encoding='utf-8') + SNIPPET, encoding='utf-8', newline='\n')
    log = []

    def act(page):
        page.wait_for_timeout(500)
        page.evaluate("window.viewer.key('Tab', true, 0)")
        page.wait_for_timeout(500)
    R.render(site, (w, h), ratio, actions=act, capture_log=log)
    lines = [re.sub(r'^.*?J32BOX', 'J32BOX', x) for x in log if 'J32BOX' in x]
    (OUT / f'viewer_{h}_{a.pct}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('viewer boxes', len(lines), [x for x in log if 'rml' in x and ('warn' in x or 'error' in x)][:4])
    if a.viewer_only:
        return
    # game
    import s3
    ui = s3.SCRATCH_UI / 'boardbox'
    if ui.exists():
        shutil.rmtree(ui)
    shutil.copytree(s3.SCRATCH_UI / 'board', ui)
    p = ui / 'board.rml'
    t = p.read_text(encoding='utf-8').replace('<body id="root" data-model="board">', '<body id="root" data-model="board" onkeydown="J32Dump(document)" onhide="J32Dump(document)">')
    t = t.replace('</head>', '<script>\n' + SNIPPET + '\n</script>\n</head>')
    p.write_text(t, encoding='utf-8', newline='\n')
    r = s3.Run()
    r.pc.exit()
    r.pc.set_keys({'ui.enabled': '1', 'ui.dir': s3.UI_DIR_REL, 'ui.show': '', 'ui.scale': str(a.pct)})
    print(r.pc.launch(a.size))
    print(r.ui('show boardbox/board.rml'))
    time.sleep(2)
    print(r.ui('hide boardbox/board.rml')[0])
    time.sleep(2)
    print(r.pc.exit())
    lines = [re.sub(r'^.*?J32BOX', 'J32BOX', x) for x in GAME_LOG.read_text(encoding='utf-8', errors='replace').splitlines() if 'J32BOX' in x]
    (OUT / f'game_{h}_{a.pct}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('game boxes', len(lines))


def diff(a):
    h = a.size.split('x')[1]
    v = (OUT / f'viewer_{h}_{a.pct}.txt').read_text(encoding='utf-8').splitlines()
    g = (OUT / f'game_{h}_{a.pct}.txt').read_text(encoding='utf-8').splitlines()
    print(len(v), len(g))
    n = 0
    for x, y in zip(v, g):
        if x != y:
            n += 1
            if n <= 14:
                print('V', x[:110])
                print('G', y[:110])
    print('differing', n)


if __name__ == '__main__':
    sys.path.insert(0, str(HERE))
    ap = argparse.ArgumentParser()
    ap.add_argument('verb', choices=['run', 'diff'])
    ap.add_argument('--size', default='2560x1440')
    ap.add_argument('--pct', type=int, default=100)
    ap.add_argument('--viewer-only', action='store_true')
    ap.add_argument('--ratio', type=float, help='the viewer ratio instead of height / 1080 x percent')
    a = ap.parse_args()
    {'run': run, 'diff': diff}[a.verb](a)
