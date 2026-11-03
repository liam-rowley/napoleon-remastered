"""J34 spike (order of work 1): which RCSS the library relies on does RmlUi 6.3 draw in the viewer? Renders spike.rml and prints one line per probe.

usage: python3 uikit/napoleon/runs/20261102_j34/spike/run_spike.py   (needs build/viewer/out from viewer/core/build.sh --docker build and Playwright)
Probes are sampled at their box centre, corner and just outside; 'hover' is the :hover state after a mouse move; the Tab key press shows :focus-visible.
Output of the committed run: results.txt beside this file; picture: spike.png.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
spec = importlib.util.spec_from_file_location('r', ROOT / 'viewer' / 'core' / 'render.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

site = ROOT / 'build' / 'spike_site'
r.stage(HERE, site, ROOT / 'build' / 'viewer' / 'out')
ids = ['p_var', 'p_var_rt', 'p_var_cls', 'p_var_hover', 'p_var_fb', 'p_img', 'p_shadow', 'p_inset', 'p_rep', 'p_focus', 'p_focus_only', 'p_tr', 'p_ts',
       'p_none', 'p_trans', 'p_serif', 'p_serifb', 'p_sans', 'p_sansb', 'p_scroll', 'p_dev', 'q_a', 'q_b', 'q_c', 'q_d', 'q_e']
res = {}


def drive(page):
    v = page.evaluate('id => window.viewer.element(id)', 'p_var_hover')
    page.evaluate(f'window.viewer.mouseMove({int(v["x"] + 10)}, {int(v["y"] + 10)}); window.viewer.frame()')
    res['hover'] = page.evaluate('id => window.viewer.element(id)', 'p_var_hover')['hover']
    page.evaluate('window.viewer.key("Tab", true, 0); window.viewer.key("Tab", false, 0); window.viewer.frame()')
    res['focus_visible_after_tab'] = page.evaluate('id => window.viewer.element(id)', 'p_focus')['focus_visible']


log = []
w, h, rgba, boxes = r.render(site, (1000, 600), 1.0, boxes=ids, actions=drive, capture_log=log)
(HERE / 'spike.png').write_bytes(r.png_bytes(w, h, rgba))
px = lambda x, y: '#%02x%02x%02x' % tuple(rgba[(y * w + x) * 4:(y * w + x) * 4 + 3])
for k in ids:
    b = boxes[k]
    if not b:
        print(k, 'no box (display: none)')
        continue
    x, y, bw, bh = (int(v) for v in b)
    print(k, [round(v, 1) for v in b], 'centre', px(x + bw // 2, y + bh // 2), 'corner', px(x + 2, y + 2), 'outside', px(max(x - 3, 0), y + bh // 2))
print('hover', res['hover'], 'focus_visible_after_tab', res['focus_visible_after_tab'])
for line in log:
    if 'warning' in line or 'error' in line.lower():
        print(line)
sys.exit(0)
