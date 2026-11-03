#!/usr/bin/env python3
"""J24 run helper: import a fit.sh launch's captures (shader_catalog.py import) and print the texel-density table per setting.

usage: python3 harness/runs/20261103_j24pc/dens.py [--no-import] <tag> [<tag> ...]   (writes harness/runs/20261103_j24pc/density.tsv for all tags seen)
The metric is shader_catalog.py's shadow_density (the one owner, J8 review 1 finding 4); this only tabulates its output.
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUN = '20261103_j24pc'   # shader_catalog.py import takes the run id under harness/runs/
YAWS = [0, 45, 90, 135, 180, 225, 270, 315]
POSES = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 's1']
args = [a for a in sys.argv[1:] if a != '--no-import']
for tag in args:
    names = [f'j24_{tag}_y_{y}' for y in YAWS] + [f'j24_{tag}_{p}' for p in POSES]
    if '--no-import' not in sys.argv:
        names_new = [n for n in names if not (HERE / 'captures' / f'{n}.json').exists()]
        if names_new:
            subprocess.run([sys.executable, 'discovery/core/shader_catalog.py', 'import', '--run', RUN, '--captures',
                            r'C:\napoleon_remastered_pc\captures', '--name', *names_new], cwd=REPO, capture_output=True)

rows = {}
for f in sorted((HERE / 'captures').glob('j24_*.json')):
    rows[f.stem] = f
lines = []
paths = [str(p.relative_to(REPO)) for p in rows.values()]
for i in range(0, len(paths), 40):   # the Windows command line limit
    lines += subprocess.run([sys.executable, 'discovery/core/shader_catalog.py', 'density', *paths[i:i + 40]], cwd=REPO,
                            capture_output=True, text=True).stdout.splitlines()
dens = {}
for line in lines:
    name, _, js = line.partition(' ')
    try:
        dens[name] = json.loads(js)
    except ValueError:
        pass
tsv = ['capture\tmap\tfarz\tview_to_sun\t20m\t60m\t140m']
for n, d in sorted(dens.items()):
    t = d['texels_per_m']
    tsv.append(f"{n}\t{d['map']}\t{d['farz']}\t{d['view_to_sun_deg']}\t{t['20m']}\t{t['60m']}\t{t['140m']}")
(HERE / 'density.tsv').write_text('\n'.join(tsv) + '\n', encoding='utf-8', newline='\n')
print('setting | ' + ' | '.join(f'y{y}' for y in YAWS) + ' | worst | best/worst | ' + ' | '.join(POSES) + '   (texels/m at 20 m; farz of y0)')
for tag in args:
    ys = [dens.get(f'j24_{tag}_y_{y}', {}).get('texels_per_m', {}).get('20m') for y in YAWS]
    ps = [dens.get(f'j24_{tag}_{p}', {}).get('texels_per_m', {}).get('20m') for p in POSES]
    v = [x for x in ys if x]
    w = min(v) if v else None
    r = round(max(v) / w, 2) if v and w else None
    fz = dens.get(f'j24_{tag}_y_0', {}).get('farz')
    print(f'{tag} | ' + ' | '.join(str(x) for x in ys) + f' | {w} | {r} | ' + ' | '.join(str(x) for x in ps) + f'   farz {fz}')
