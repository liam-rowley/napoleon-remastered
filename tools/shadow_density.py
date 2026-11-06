#!/usr/bin/env python3
"""Shadow texel-density table per setting (J24): imports a run's yaw-sweep and pose captures and tabulates shader_catalog.py's metric.

purpose: import the captures of one or more settings (named <prefix>_<tag>_y_<yaw> and <prefix>_<tag>_<pose>) into a run with core/discovery/shader_catalog.py, write <run>/density.tsv from its shadow_density metric, and print per setting the texels per metre at 20 m by yaw, the worst yaw, best/worst and the poses
usage: shadow_density.py --run RUN_ID [--prefix j24] [--yaws 0,45,...,315] [--poses p1,...,s1] [--captures DIR] [--no-import] [--cascade TAG=CONTROL ...] TAG [TAG ...]
when: a shadow fit or map-size sweep (J24; J25 and J26 cascades) needs its density figures compared across settings
not-a-verb: a run helper; the metric itself is owned by core/discovery/shader_catalog.py (J8 review 1 finding 4) and only tabulated here
"""
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = 'core/discovery/shader_catalog.py'
YAWS = '0,45,90,135,180,225,270,315'   # the J8 yaw sweep
POSES = 'p1,p2,p3,p4,p5,p6,s1'         # the J24 shot poses and the siege deploy pose
CHUNK = 40                             # paths per shader_catalog.py density call (the Windows command line limit)


def names(prefix, tag, yaws, poses):
    return [f'{prefix}_{tag}_y_{y}' for y in yaws] + [f'{prefix}_{tag}_{p}' for p in poses]


def parse_density(lines):
    """`<name> <json>` lines from `shader_catalog.py density` -> {name: result}; a null result (no software shadow registers) is dropped."""
    out = {}
    for line in lines:
        name, _, js = line.partition(' ')
        try:
            d = json.loads(js)
        except ValueError:
            continue
        if d:
            out[name] = d
    return out


def tsv(dens):
    rows = ['capture\tmap\tfarz\tview_to_sun\t20m\t60m\t140m']
    for n, d in sorted(dens.items()):
        t = d['texels_per_m']
        rows.append(f"{n}\t{d['map']}\t{d['farz']}\t{d['view_to_sun_deg']}\t{t['20m']}\t{t['60m']}\t{t['140m']}")
    return '\n'.join(rows) + '\n'


def setting_row(dens, prefix, tag, yaws, poses):
    """One setting: texels/m at 20 m per yaw, the worst yaw, best/worst, per pose, and the farz at the first yaw."""
    at20 = lambda n: dens.get(n, {}).get('texels_per_m', {}).get('20m')
    ys = [at20(f'{prefix}_{tag}_y_{y}') for y in yaws]
    ps = [at20(f'{prefix}_{tag}_{p}') for p in poses]
    v = [x for x in ys if x]
    worst = min(v) if v else None
    ratio = round(max(v) / worst, 2) if worst else None
    farz = dens.get(f'{prefix}_{tag}_y_{yaws[0]}', {}).get('farz') if yaws else None
    return {'yaws': ys, 'worst': worst, 'best_worst': ratio, 'poses': ps, 'farz': farz}


def cascade_rows(frame_txt):
    """The near cascade's receiver rows and edge from a raw frame.txt: (rows of world -> u, v, depth; size), or None. The J25 prototype keeps them in
    pixel constants c216-c218 and c220 (x = 1/size); no shader's table names them, so they are read from the capture's state dumps (`PC 0 224 ...`)."""
    pc = {}
    with open(frame_txt, encoding='latin1') as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            if p[0] == 'FRAME' and int(p[1]) > 1:
                break
            if p[0] == 'PC' and len(p) > 3:
                s, n = int(p[1]), int(p[2])
                for r in range(s, s + n):
                    if 216 <= r <= 220:
                        pc[r] = [float(x) for x in p[3 + 4 * (r - s):7 + 4 * (r - s)]]
    rows = [pc.get(r) for r in (216, 217, 218)]
    if not all(rows) or not pc.get(220) or not pc[220][0] or not any(rows[0][:3]):
        return None
    return rows, round(1 / pc[220][0])


def cascade_summary(control, rows, size):
    """The control capture's summary (same pose: its camera, view and light) with the cascade's matrix and size first, so the catalogue's one metric reads
    them. That metric uses (M0.Q / M3.Q, M1.Q / M3.Q) * size / 2 and only its derivatives: clip rows are twice the receiver's uv rows, w is 1."""
    m = [[2 * x for x in rows[0]], [2 * x for x in rows[1]], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    near = {'consts': {'shadow_map_projection_matrix': m, 'shadow_map_texture_size': [[float(size), 0.0, 0.0, 0.0]]}}
    return {**control, 'shaders': {'cascade0': near, **control['shaders']}}


def catalog():
    spec = importlib.util.spec_from_file_location('shader_catalog', ROOT / CATALOG)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str((ROOT / CATALOG).parent))
    spec.loader.exec_module(m)
    return m


def cascade_table(here, captures, prefix, yaws, pairs):
    """Per `TAG=CONTROL`: the near cascade's density at each yaw, by the catalogue's metric. Prints the same columns as a setting."""
    metric = catalog().shadow_density
    lines = []
    for pair in pairs:
        tag, control = pair.split('=')
        vals = []
        for y in yaws:
            got = cascade_rows(Path(captures) / f'{prefix}_{tag}_y_{y}' / 'frame.txt')
            ctl = here / 'captures' / f'{prefix}_{control}_y_{y}.json'
            if not got or not ctl.exists():
                vals.append(None)
                continue
            d = metric(cascade_summary(json.loads(ctl.read_text(encoding='utf-8')), *got))
            vals.append(d['texels_per_m'] if d else None)
        at20 = [v['20m'] if v else None for v in vals]
        ok = [x for x in at20 if x]
        lines.append(f"{tag} cascade 0 | " + ' | '.join(str(x) for x in at20)
                     + f" | {min(ok) if ok else None} | {round(max(ok) / min(ok), 2) if ok else None}")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True, help='run id under harness/runs/ (shader_catalog.py import takes the id, not a path)')
    ap.add_argument('--prefix', default='j24')
    ap.add_argument('--yaws', default=YAWS)
    ap.add_argument('--poses', default=POSES)
    ap.add_argument('--captures', default=r'C:\napoleon_remastered_pc\captures')
    ap.add_argument('--no-import', action='store_true', help='tabulate the captures already imported')
    ap.add_argument('--cascade', action='append', default=[], metavar='TAG=CONTROL', help="the near cascade of TAG's yaw captures, with CONTROL's imported summaries for the pose (J25)")
    ap.add_argument('tags', nargs='+')
    a = ap.parse_args(argv)
    yaws, poses = a.yaws.split(','), [p for p in a.poses.split(',') if p]
    here = ROOT / 'harness' / 'runs' / a.run
    if not a.no_import:
        for tag in a.tags:   # a shots-only launch has no yaw captures: import only what exists and is not yet imported
            new = [n for n in names(a.prefix, tag, yaws, poses)
                   if not (here / 'captures' / f'{n}.json').exists() and (Path(a.captures) / n).is_dir()]
            if new:
                subprocess.run([sys.executable, CATALOG, 'import', '--run', a.run, '--captures', a.captures, '--name', *new],
                               cwd=ROOT, capture_output=True)
    paths = [str(p.relative_to(ROOT)) for p in sorted((here / 'captures').glob(f'{a.prefix}_*.json'))]
    lines = []
    for i in range(0, len(paths), CHUNK):
        lines += subprocess.run([sys.executable, CATALOG, 'density', *paths[i:i + CHUNK]], cwd=ROOT,
                                capture_output=True, text=True).stdout.splitlines()
    dens = parse_density(lines)
    (here / 'density.tsv').write_text(tsv(dens), encoding='utf-8', newline='\n')
    print('setting | ' + ' | '.join(f'y{y}' for y in yaws) + ' | worst | best/worst | ' + ' | '.join(poses) + '   (texels/m at 20 m; farz of the first yaw)')
    for tag in a.tags:
        r = setting_row(dens, a.prefix, tag, yaws, poses)
        print(f'{tag} | ' + ' | '.join(str(x) for x in r['yaws']) + f" | {r['worst']} | {r['best_worst']} | "
              + ' | '.join(str(x) for x in r['poses']) + f"   farz {r['farz']}")
    for line in cascade_table(here, a.captures, a.prefix, yaws, a.cascade):
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
