#!/usr/bin/env python3
"""Performance baseline (J23): what Napoleon costs today, per backend x size x scenario x pose, through the existing ctl verbs.

purpose: drive core/harness/ctl.py (scene, cam, perf) over a matrix of backend (proxy.backend dxvk|system), headless size, scenario, pose and repeat, one JSON per cell with the pins a number belongs to; summarize the cells into the baseline file; check a baseline; compare a later run against it and flag budget breaches
usage: perf_baseline.py measure --run RUN [--owner O] [--session S] [--backends dxvk,system] [--sizes 1920x1080,2560x1440,3840x2160] [--scenarios a,b] [--poses deploy] [--repeats 3] [--perf-s 20] [--deploy-end-s 60] [--dxvk-variants FILE] | summarize --run DIR [--out F] | check [--baseline F] | compare --run DIR [--baseline F] [--budgets F] [--feature NAME]
when: J23 measured perf/baseline.json with it; every later phase 3 job (J24 shadows, J26 cascades, J27 distances, J59 the J46 rows) re-runs `measure` on its build and reports `compare` against the committed baseline
not-a-verb: orchestrates PC sessions through core/harness/ctl.py and job.sh (a tools/ driver so it adds no harness/ file, rule 79); a warscape-core candidate once a second game has a baseline

Cells. The size is the outer loop (one temporary copy of the harness adapter per size, `ctl.launch.size` changed, passed as `--adapter`: the
committed adapter and core/ stay as they are), the backend inside it (set with `pc_deploy set proxy.backend=<b>` with the game closed), then
an optional DXVK variant (a dxvk.conf served from <state>\\_scratch\\<owner>\\dxvk_<name>\\ by pointing `proxy.dxvk_path` at a copy of the
pinned DLL there: DXVK reads its config next to its DLL, core/proxy/src/backend.cpp), then pass 0 (the warm-up after a fresh launch: every
scene loaded once, its load time kept as `cold`, no perf) and passes 1..repeats (scene, then per pose cam + perf). One `--deploy end`
land_small cell per block runs the battle at 1x for --deploy-end-s. Address space is read twice: the proxy's value at the end of perf and the
process's peak since launch (host side, read-only: Get-Process PeakVirtualMemorySize64, converted to the proxy's 32-bit view by the
offset between the two current values). The lock is taken once for the whole run and touched before every verb; the run's start values of
proxy.backend and proxy.dxvk_path are set back after the lock release and the watcher's restore.
"""
import argparse
import base64
import datetime
import hashlib
import importlib.util
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'core'
ADAPTER = ROOT / 'harness' / 'napoleon' / 'adapter.json'
SCENARIOS = ROOT / 'registries' / 'scenarios.jsonl'
BASELINE = ROOT / 'perf' / 'baseline.json'
BUDGETS = ROOT / 'perf' / 'budgets.json'
SIZES = ('1920x1080', '2560x1440', '3840x2160')
BACKENDS = ('dxvk', 'system')
# the acceptance order (J44) with the warm-reset scenes first: a historical battle and the campaign leave by a relaunch (ctl.py v_scene)
ORDER = ('land_small', 'siege_small', 'naval_small', 'naval_storm', 'hist_dresden', 'hist_nile', 'campaign_start')
PINS = ('build', 'kit', 'watcher', 'backend', 'size', 'dxvk', 'gpu', 'driver', 'dxvk_conf_sha256', 'prefs_gfx', 'frame_cap', 'date', 'run')
METRICS = ('p50_ms', 'p99_ms', 'max_ms', 'load_s', 'va_used_mb', 'va_peak_mb', 'commit_mb', 'vram_mb')
NOISY_PCT = 15.0   # brief kill criterion: a cell whose p50 spread stays above 15 % of its median is marked noisy
DXVK_DIR = 'napoleon_remastered\\dxvk'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256(path):
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# -- pure parts (host tests: tests/test_perf_baseline.py)
def load_rows(path=SCENARIOS):
    return {r['id']: r for r in (json.loads(l) for l in Path(path).read_text(encoding='utf-8').splitlines() if l.strip())}


def scenario_list(rows, wanted=None):
    """The scenarios to measure: `wanted` (in its order) or the library rows ctl.py scene can load (its launch names ctl.py scene), ORDER first."""
    if wanted:
        missing = [s for s in wanted if s not in rows]
        if missing:
            raise SystemExit(f'perf_baseline: no scenario row {", ".join(missing)} in {SCENARIOS.name}')
        return list(wanted)
    loadable = [i for i, r in rows.items() if str(r.get('launch', '')).startswith('ctl.py scene')]
    return [i for i in ORDER if i in loadable] + sorted(i for i in loadable if i not in ORDER)


def poses_of(row, only=None):
    """The row's camera poses (sorted), or [None]: the scene's settled default view."""
    have = sorted((row.get('camera_poses') or {}))
    if only:
        have = [p for p in have if p in only]
    return have or [None]


def expand(sizes, backends, scenarios, rows, repeats, variants=(None,), only_poses=None):
    """The ordered cell plan: size outermost, backend, variant, pass (0 = warm-up, loads only), scenario, pose."""
    plan = []
    for size in sizes:
        for be in backends:
            for var in (variants if be == 'dxvk' else (None,)):
                for n in range(repeats + 1):
                    for sid in scenarios:
                        for pose in ([None] if n == 0 else poses_of(rows[sid], only_poses)):
                            plan.append({'size': size, 'backend': be, 'variant': var, 'pass': n, 'scenario': sid, 'pose': pose,
                                         'measure': n > 0})
    return plan


def cell_key(c):
    return '|'.join([c['backend'] + (f"+{c['variant']}" if c.get('variant') else ''), c['size'], c['scenario'], c.get('pose') or 'default'])


def cell_name(c):
    return '_'.join([c['backend'] + (f"-{c['variant']}" if c.get('variant') else ''), c['size'], c['scenario'], c.get('pose') or 'default',
                     f"p{c['pass']}"])


def spread(values):
    """median, spread (max - min) and spread as % of the median; None for no values."""
    v = [x for x in values if isinstance(x, (int, float))]
    if not v:
        return None
    med = statistics.median(v)
    sp = max(v) - min(v)
    return {'median': round(med, 3), 'spread': round(sp, 3), 'spread_pct': round(100.0 * sp / med, 1) if med else None, 'n': len(v)}


def va_peak(proxy_va_mb, host):
    """The process's peak address space in the proxy's 32-bit view: proxy value + (host peak - host current), all MB. None when unread."""
    try:
        return round(proxy_va_mb + (host['peak_virtual_mb'] - host['virtual_mb']), 1)
    except (TypeError, KeyError):
        return None


def metrics(cell):
    """The numbers of one measured cell, flat."""
    p = cell.get('perf') if isinstance(cell.get('perf'), dict) else {}   # run 20261101_j23pc's first sitting wrote the plan flag here
    fm, mem, vram = p.get('frame_ms') or {}, p.get('mem') or {}, p.get('vram') or {}
    return {'p50_ms': fm.get('p50'), 'p99_ms': fm.get('p99'), 'max_ms': fm.get('max'), 'load_s': (cell.get('scene') or {}).get('load_s'),
            'va_used_mb': mem.get('va_used_mb'), 'va_peak_mb': cell.get('va_peak_mb'), 'commit_mb': mem.get('commit_mb'),
            'vram_mb': vram.get('process_dedicated_mb')}


def cell_problems(cell):
    """Why a cell cannot be part of a baseline: a failed verb (first: it is the cause), a missing pin, no frames."""
    out = [f"status {cell.get('status')}: {str(cell.get('reason', '')).strip()[-300:]}"] if cell.get('status') != 'ok' else []
    out += [f'pin {k} missing' for k in PINS if (cell.get('pins') or {}).get(k) in (None, '', {})]
    read = (cell.get('pins') or {}).get('dxvk_conf_read') or {}
    if cell.get('variant') and cell.get('pins') and not read.get('found'):
        out.append("variant cell but DXVK's log has no 'Found config file': the variant was not in effect")
    if cell.get('pass', 0) > 0 and not (metrics(cell).get('p50_ms') or 0) > 0:
        out.append('no frame times')
    return out


def summarize(cells, run_ids=None, rows=None):
    """Baseline-shaped summary: per cell key the median and spread of every metric over the counted passes, cold and warm loads, and the
    DXVK / system ratios. Cells without their pins are refused (listed under `refused`, never summarized)."""
    groups, cold, refused, pins = {}, {}, [], {}
    for c in cells:
        bad = cell_problems(c)
        if bad:
            refused.append({'cell': cell_name(c), 'problems': bad})
            continue
        k = cell_key(c)
        if c['pass'] == 0:
            cold['|'.join(k.split('|')[:3])] = metrics(c)['load_s']
            continue
        if c.get('deploy_end'):
            k += '|battle'
        groups.setdefault(k, []).append(c)
        pins.setdefault('|'.join(k.split('|')[:2]), {x: c['pins'][x] for x in PINS if x not in ('run',)} | {'runs': set()})['runs'].add(c['pins']['run'])
    out = {}
    for k, cs in sorted(groups.items()):
        row = {m: spread([metrics(c)[m] for c in cs]) for m in METRICS}
        row['cold_load_s'] = cold.get('|'.join(k.split('|')[:3]))
        row['noisy'] = bool(row['p50_ms'] and row['p50_ms']['spread_pct'] is not None and row['p50_ms']['spread_pct'] > NOISY_PCT)
        row['cells'] = [cell_name(c) for c in cs]
        out[k] = row
    ratios = {}
    for k, row in out.items():
        be, rest = k.split('|', 1)
        if be == 'dxvk' and f'system|{rest}' in out:
            s = out[f'system|{rest}']
            ratios[rest] = {m: round(row[m]['median'] / s[m]['median'], 3) for m in ('p50_ms', 'p99_ms', 'load_s', 'va_peak_mb', 'commit_mb', 'vram_mb')
                            if row.get(m) and s.get(m) and s[m]['median']}
    blocks = {k: {**v, 'runs': sorted(v['runs'])} for k, v in sorted(pins.items())}
    scen = sorted({k.split('|')[2] for k in out})
    return {'schema': 1, 'date': max((v['date'] for v in blocks.values()), default=None), 'cells': out, 'dxvk_over_system': ratios,
            'blocks': blocks, 'refused': refused, 'scenarios': scen, 'not_covered': not_covered(refused, list(out), rows),
            'conditions': CONDITIONS, 'runs': sorted(run_ids or {b for v in blocks.values() for b in v['runs']})}


CONDITIONS = {
    'present': 'headless: the game runs windowed borderless on the virtual display at the cell size (the harness\'s only mode, J13); no cell is a real-monitor or fullscreen number',
    'guard_thread': 'the headless guard thread takes the Present lock while it enumerates monitors (every 25th poll; J13 review Later 4): it is in every frame time',
    'pc_use': 'Liam may have been using the PC during a run: the run README gives the time windows',
    'va_peak_mb': 'the process peak since its launch (Get-Process PeakVirtualMemorySize64, equal to the proxy\'s 32-bit value when current): a scene loaded by a warm reset inherits the peak of the scenes before it in the same process; va_used_mb is the scene\'s own value at the end of perf',
    'repeats': 'pass 0 after each fresh launch per backend x size is a warm-up (its loads are cold_load_s); medians and spreads over passes 1..n',
    'battle': 'a key ending |battle is land_small with deployment ended and the battle running at 1x (ctl scene --deploy end, speed 1)',
}
UNBUILT = [{'what': 'land_40 (20 against 20), land_large, naval_large, siege_city', 'why': 'no scenario rows: the custom-battle army setup route is J46; J59 measures them with this tool'}]


def not_covered(refused, keys, rows=None):
    """What the baseline does not cover and why: blocks whose every cell was refused (first problem named), library rows not measured, unbuilt rows."""
    out, blocks, measured = [], {}, {k.split('|')[2] for k in keys}
    for r in refused:
        be, size = r['cell'].split('_')[:2]
        if 'block skipped' not in blocks.get(f'{be}|{size}', 'block skipped'):
            continue   # keep the cause (a launch failure), not a later "block skipped"
        blocks[f'{be}|{size}'] = r['problems'][0]
    for b, why in sorted(blocks.items()):
        be = b.split('|')[0]
        if not any(k.startswith(be + '|') for k in keys):   # nothing at any size: the backend itself is not covered
            out.append({'what': f'backend {be} (every size; tried: {b})', 'why': why})
        elif not any(k.startswith(b + '|') for k in keys):
            out.append({'what': f'block {b}', 'why': why})
    for sid, row in sorted((rows or {}).items()):
        if sid not in measured:
            out.append({'what': sid, 'why': 'not a ctl scene row (' + str(row.get('launch', ''))[:60] + ')'
                        if not str(row.get('launch', '')).startswith('ctl.py scene') else 'in the library, not measured in these runs'})
    return out + UNBUILT


def baseline_problems(b):
    """A baseline file every later job reports against: its shape and its pins."""
    out = []
    for k in ('schema', 'date', 'cells', 'blocks', 'scenarios', 'runs', 'not_covered', 'conditions'):
        if k not in b:
            out.append(f'no {k}')
    for k, row in (b.get('cells') or {}).items():
        if len(k.split('|')) < 4:
            out.append(f'cell key {k}: want backend|size|scenario|pose')
        blk = '|'.join(k.split('|')[:2])
        if blk not in (b.get('blocks') or {}):
            out.append(f'cell {k}: no pins for block {blk}')
        for m in ('p50_ms', 'p99_ms', 'va_peak_mb', 'commit_mb', 'vram_mb'):
            if not (row.get(m) or {}).get('median'):
                out.append(f'cell {k}: no {m}')
    for blk, p in (b.get('blocks') or {}).items():
        out += [f'block {blk}: pin {x} missing' for x in PINS if x != 'run' and p.get(x) in (None, '', {})]
        if not p.get('runs'):
            out.append(f'block {blk}: no run ids')
    return out


def compare(base, now, budget=None):
    """Rows of (key, metric, baseline median, now median, delta, limit, breach) for every cell key in both. `budget` maps metric -> {size: limit}
    (a delta limit, ms or MB) or metric -> number (every size)."""
    rows = []
    for k, b in sorted(base.get('cells', {}).items()):
        n = now.get('cells', {}).get(k)
        if not n:
            continue
        size = k.split('|')[1]
        for m in ('p50_ms', 'p99_ms', 'va_peak_mb', 'commit_mb', 'vram_mb'):
            if not (b.get(m) and n.get(m)):
                continue
            d = round(n[m]['median'] - b[m]['median'], 3)
            lim = (budget or {}).get(m)
            lim = lim.get(size) if isinstance(lim, dict) else lim
            rows.append({'cell': k, 'metric': m, 'baseline': b[m]['median'], 'now': n[m]['median'], 'delta': d, 'limit': lim,
                         'breach': lim is not None and d > lim})
    return rows


def frame_cap(prefs, conf_text):
    """What could cap the frame rate: the game's vsync and frame-rate prefs, DXVK's present interval and frame-rate options (default when unset)."""
    conf = dict(re.findall(r'^\s*([\w.]+)\s*=\s*(\S+)', conf_text or '', re.M))
    return {'gfx_vsync': prefs.get('gfx_vsync'), 'gfx_frame_rate': prefs.get('gfx_frame_rate'),
            'd3d9.presentInterval': conf.get('d3d9.presentInterval', 'default'), 'd3d9.maxFrameRate': conf.get('d3d9.maxFrameRate', 'default'),
            'dxvk.maxFrameRate': conf.get('dxvk.maxFrameRate', 'default'), 'present': 'headless: windowed borderless on the virtual display'}


def prefs_values(text):
    return dict(re.findall(r'^\s*(gfx_\w+|x_res|y_res)\s+([^;]*);', text, re.M))


# -- the PC
def load_ctl():
    spec = importlib.util.spec_from_file_location('ctl', CORE / 'harness' / 'ctl.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sized_adapter(adapter, size, folder):
    """A temporary copy of the harness adapter whose ctl launches at `size` (the committed file is not edited)."""
    a = json.loads(json.dumps(adapter))
    a.setdefault('ctl', {}).setdefault('launch', {})['size'] = size
    p = Path(folder) / f'adapter_{size}.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(a, indent=1), encoding='utf-8')
    return p


class Rig:
    """One game on the PC under one lock: ctl's Pc and Ctl rebuilt per size, host reads for pins and peak memory."""
    def __init__(self, owner, session, adapter_path, work, log):
        self.ctlmod = load_ctl()
        self.owner, self.session, self.log = owner, session, log
        self.base_adapter = json.loads(Path(adapter_path).read_text(encoding='utf-8'))
        self.a, self.work, self.locked = self.base_adapter, Path(work), False
        self.adapter_path = str(adapter_path)
        self.game = Path(self.a['game_dir'])
        self.rows = self.ctlmod.load_scenarios(SCENARIOS)
        self.use_size(self.a.get('ctl', {}).get('launch', {}).get('size', SIZES[0]))

    def use_size(self, size):
        self.adapter_path = str(sized_adapter(self.base_adapter, size, self.work))
        self.pc = self.ctlmod.Pc(self.owner, self.adapter_path, self.a)
        self.pc.launch_cfg = dict(self.pc.launch_cfg, size=size)
        state = Path(self.a['state_dir'])
        self.ctl = self.ctlmod.Ctl(self.ctlmod.job_sh_transport(self.owner, self.adapter_path), self.rows, self.a, pc=self.pc,
                                   session=self.ctlmod.Session(state / 'ctl' / '_ctl_session.json'))

    def sh(self, *args, timeout=120):
        p = subprocess.run([self.ctlmod.bash(), str(CORE / 'harness' / 'job.sh'), '--adapter', self.adapter_path, *args],
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr

    def lock(self):
        rc, out = self.sh('lock', self.owner, self.session, 'J23 perf baseline')
        if rc != 0:
            raise RuntimeError(f'cannot take the game lock: {out.strip()[-300:]}')
        self.locked = True

    def release(self):
        if not self.locked:
            return
        self.sh('unlock', self.owner)
        self.locked = False
        for _ in range(180):
            st = self.pc.status()
            if st.get('profile_active') is None and st.get('lock') is None:
                return
            time.sleep(1)
        raise RuntimeError('the watcher did not restore the profile within 180 s of the lock release')

    def run(self, verb, *args):
        self.sh('touch')
        return self.ctl.run(verb, *args)

    def ini(self):
        p = self.pc.ini_path()
        return self.ctlmod.ini_values(p.read_text(encoding='utf-8')) if p.exists() else {}

    def set_keys(self, keys):
        if self.pc.pid() is not None:
            self.log(f'exit before setting {sorted(keys)}: {self.pc.exit()}')
        self.pc.set_keys(keys)

    def prefs(self):
        import os
        c = next(c for c in self.a['config_files'] if c['id'] == 'prefs')
        p = Path(os.path.expandvars(self.a['appdata_dir'])) / c['path']
        return prefs_values(p.read_bytes().decode('utf-16-le', errors='replace')) if p.exists() else {}

    def host_mem(self, pid):
        ps = (f"$p = Get-Process -Id {int(pid)} -ErrorAction Stop; '{{0}} {{1}} {{2}} {{3}}' -f [math]::Round($p.VirtualMemorySize64/1MB,1),"
              " [math]::Round($p.PeakVirtualMemorySize64/1MB,1), [math]::Round($p.PagedMemorySize64/1MB,1), [math]::Round($p.PeakPagedMemorySize64/1MB,1)")
        p = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps], capture_output=True, text=True, timeout=60)
        try:
            v, pv, c, pc = [float(x) for x in p.stdout.strip().splitlines()[-1].split()]
            return {'virtual_mb': v, 'peak_virtual_mb': pv, 'private_mb': c, 'peak_private_mb': pc,
                    'source': 'Get-Process VirtualMemorySize64/PeakVirtualMemorySize64/PagedMemorySize64/PeakPagedMemorySize64'}
        except (ValueError, IndexError):
            return {'error': (p.stdout + p.stderr).strip()[-200:]}

    def gpu(self):
        p = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'], capture_output=True, text=True, timeout=30)
        try:
            name, drv = [x.strip() for x in p.stdout.strip().splitlines()[0].split(',')]
            return name, drv
        except (ValueError, IndexError):
            return None, None

    def dxvk_pin(self):
        sys.path.insert(0, str(CORE / 'proxy' / 'tools'))
        import fetch_dxvk
        pin = getattr(fetch_dxvk, 'PIN', None) or {}
        dll = self.dxvk_dll()
        m = re.search(r'dxvk-(\d+(?:\.\d+)*)', json.dumps(pin))
        return {'version': m.group(1) if m else None, 'sha256': sha256(dll), 'pinned_sha256': pin.get('d3d9_sha256'), 'path': str(dll)}

    def dxvk_dll(self):
        p = self.ini().get('proxy.dxvk_path') or (DXVK_DIR + '\\d3d9_dxvk.dll')
        return Path(p) if re.match(r'^[A-Za-z]:', p) else self.game / p

    def conf_path(self):
        # where the proxy points DXVK_CONFIG_FILE: always <mod>/dxvk/, whatever proxy.dxvk_path says (core/proxy/src/backend.cpp; run 20261101_j23sweep
        # staged its confs next to a copied DLL and DXVK read none of them)
        return self.game / DXVK_DIR / 'dxvk.conf'

    def conf_read(self):
        """What DXVK says it read, from its own log (<mod>/dxvk/<exe>_d3d9.log): 'Found config file' and the 'Effective configuration' lines."""
        logs = sorted((self.game / DXVK_DIR).glob('*_d3d9.log'), key=lambda q: q.stat().st_mtime)
        text = logs[-1].read_text(encoding='utf-8', errors='replace') if logs else ''
        eff = text.split('Effective configuration:', 1)[1].split('info:  DXVK', 1)[0] if 'Effective configuration:' in text else ''
        return {'found': 'Found config file:' in text, 'effective': dict(re.findall(r'info:\s+([\w.]+) = (\S+)', eff)),
                'log': logs[-1].name if logs else None}

    def pins(self, run):
        b = self.pc.build_info()
        st = self.pc.status()
        conf = self.conf_path()
        text = conf.read_text(encoding='utf-8', errors='replace') if conf.is_file() else ''
        prefs = self.prefs()
        name, drv = self.gpu()
        return {'build': b.get('build'), 'kit': b.get('kit'), 'watcher': st.get('version'), 'backend': b.get('backend'), 'size': b.get('size'),
                'dxvk': self.dxvk_pin() if b.get('backend') == 'dxvk' else {'version': 'n/a (system d3d9)'},
                'gpu': name, 'driver': drv, 'dxvk_conf_sha256': sha256(conf) or 'absent', 'dxvk_conf': text.strip(),
                'dxvk_conf_read': self.conf_read() if b.get('backend') == 'dxvk' else None,
                'prefs_gfx': prefs, 'frame_cap': frame_cap(prefs, text), 'date': utc()[:10], 'run': run}


def measure(a):
    run = a.run
    out = ROOT / 'harness' / 'runs' / run
    cells_dir = out / 'cells'
    cells_dir.mkdir(parents=True, exist_ok=True)
    def log(msg):
        line = f'{utc()} {msg}'
        print(line, flush=True)
        with open(out / 'events.log', 'a', encoding='utf-8') as f:
            f.write(line + '\n')

    work = ROOT / '_scratch' / 'perf_baseline' / run
    rig = Rig(a.owner, a.session, a.adapter, work, log)
    rows = load_rows()
    scen = scenario_list(rows, a.scenarios.split(',') if a.scenarios else None)
    variants = json.loads(Path(a.dxvk_variants).read_text(encoding='utf-8')) if a.dxvk_variants else None
    plan = expand(a.sizes.split(','), a.backends.split(','), scen, rows, a.repeats, list(variants) if variants else (None,),
                  a.poses.split(',') if a.poses else None)
    start_ini = rig.ini()
    restore = {k: start_ini.get(k) for k in ('proxy.backend', 'proxy.dxvk_path') if start_ini.get(k) is not None}
    log(f'plan: {len(plan)} cells, scenarios {scen}, sizes {a.sizes}, backends {a.backends}, variants {list(variants or [])}; start keys {restore}')
    run_meta = {'run': run, 'start_utc': utc(), 'plan_cells': len(plan), 'scenarios': scen, 'blocks': [], 'restore_keys': restore}
    block, launch_fail, pins, last_scene = None, {}, None, None
    try:
        rig.lock()
        for c in plan:
            b = (c['size'], c['backend'], c['variant'])
            if b != block:
                if block is not None:
                    run_meta['blocks'][-1]['end_utc'] = utc()
                    if a.deploy_end_s and pins:
                        deploy_end_cell(rig, block, pins, a, cells_dir, log)
                block = b
                run_meta['blocks'].append({'size': b[0], 'backend': b[1], 'variant': b[2], 'start_utc': utc()})
                log(f'block {b}: exit, set keys, relaunch')
                rig.use_size(b[0])
                keys = {'proxy.backend': b[1]}
                if 'proxy.dxvk_path' in restore:
                    keys['proxy.dxvk_path'] = restore['proxy.dxvk_path']
                rig.set_keys(keys)   # exits the game first
                if variants:
                    log(stage_variant(rig, variants[b[2]] if b[2] else None))
                pins = None
            if launch_fail.get(b, 0) >= 2:   # brief kill criterion: not launched headless twice in a row, the block is recorded failed
                write_cell(cells_dir, dict(c, status='failed', reason='block skipped: two launch failures in a row', pins=pins or {}), log)
                continue
            c = dict(c, start_utc=utc())
            if c['pose'] is None or c['pose'] == poses_of(rows[c['scenario']], a.poses.split(',') if a.poses else None)[0]:
                r = rig.run('scene', c['scenario'])
                c['scene'] = {k: r.get(k) for k in ('status', 'reason', 'load_s', 'path', 'settle')}
                last_scene = c['scene'] if r.get('status') == 'ok' else None
                if r.get('status') != 'ok':
                    launching = re.search(r'step (launch|frontend)|HEADLESS', str(r.get('reason')))
                    launch_fail[b] = launch_fail.get(b, 0) + 1 if launching else 0
                    write_cell(cells_dir, dict(c, status=r.get('status'), reason=r.get('reason'), pins=pins or {}), log)
                    continue
                launch_fail[b] = 0
            elif last_scene is None:
                write_cell(cells_dir, dict(c, status='failed', reason='its scene did not load', pins=pins or {}), log)
                continue
            else:
                c['scene'] = dict(last_scene, reused=True)
            if pins is None:
                pins = rig.pins(run)
            if not c['measure']:
                write_cell(cells_dir, dict(c, status='ok', pins=pins), log)
                continue
            if c['pose']:
                r = rig.run('cam', f"{c['scenario']}:{c['pose']}")
                if r.get('status') != 'ok':
                    write_cell(cells_dir, dict(c, status=r.get('status'), reason='cam: ' + str(r.get('reason')), pins=pins), log)
                    continue
            write_cell(cells_dir, perf_cell(rig, c, pins, a.perf_s), log)
        run_meta['blocks'][-1]['end_utc'] = utc()
        if a.deploy_end_s and pins and block:
            deploy_end_cell(rig, block, pins, a, cells_dir, log)
    except Exception as e:   # the run stops; what was measured stays, and the end state is put back below
        log(f'RUN STOPPED: {type(e).__name__}: {e}')
        run_meta['stopped'] = f'{type(e).__name__}: {e}'
    finally:
        try:
            if rig.pc.pid() is not None:
                log(f'exit: {rig.pc.exit()}')
            if variants and rig.locked:
                log(stage_variant(rig, None))
        finally:
            rig.release()
            if restore and {k: rig.ini().get(k) for k in restore} != restore:
                rig.pc.set_keys(restore)
            log(f'released; keys now {({k: rig.ini().get(k) for k in restore})}')
            run_meta['end_utc'] = utc()
            # a run folder can be measured in several sittings (a resume after a stop): run.json lists each, events.log appends
            rj = out / 'run.json'
            prev = json.loads(rj.read_text(encoding='utf-8')) if rj.exists() else {'run': run, 'sittings': []}
            prev.setdefault('sittings', []).append(run_meta)
            rj.write_text(json.dumps(prev, indent=1), encoding='utf-8')
    cells = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(cells_dir.glob('*.json'))]
    s = summarize(cells, [run])
    (out / 'summary.json').write_text(json.dumps(s, indent=1), encoding='utf-8')
    log(f'summary: {len(s["cells"])} cell keys, {len(s["refused"])} refused cells -> {out / "summary.json"}')
    return 0 if not run_meta.get('stopped') else 1


def perf_cell(rig, c, pins, secs):
    r = rig.run('perf', secs)
    pid = rig.pc.pid()
    host = rig.host_mem(pid) if pid else {'error': 'no game'}
    p = {k: r.get(k) for k in ('frame_ms', 'frames', 'mem', 'vram', 'build', 'backend', 'size')}
    va = va_peak((r.get('mem') or {}).get('va_used_mb'), host)
    return dict(c, status=r.get('status'), reason=r.get('reason', ''), perf=p, host_mem=host, va_peak_mb=va, pins=pins, end_utc=utc())


def deploy_end_cell(rig, block, pins, a, cells_dir, log):
    """land_small with deployment ended, the battle running at 1x: a battle in progress, not a deployment view."""
    c = {'size': block[0], 'backend': block[1], 'variant': block[2], 'pass': 1, 'scenario': 'land_small', 'pose': 'battle1x', 'measure': True,
         'deploy_end': True, 'start_utc': utc()}
    r = rig.run('scene', 'land_small', '--deploy', 'end')
    c['scene'] = {k: r.get(k) for k in ('status', 'reason', 'load_s', 'path', 'check')}
    if r.get('status') == 'ok':
        rig.run('speed', '1')
        write_cell(cells_dir, perf_cell(rig, c, pins, a.deploy_end_s), log)
    else:
        write_cell(cells_dir, dict(c, status=r.get('status'), reason=r.get('reason'), pins=pins), log)


def stage_variant(rig, conf_text):
    """Write (or with None remove) <mod>/dxvk/dxvk.conf, the file the proxy points DXVK_CONFIG_FILE at, through an owner-locked watcher job
    with the game closed (agents never write into the game folder themselves). The folder is the kit's own (uninstall removes it).
    Checked by sha256 afterwards; returns a log line."""
    target = rig.conf_path()
    if conf_text is None:
        body = f"Remove-Item -LiteralPath '{target}' -Force -ErrorAction SilentlyContinue"
    else:
        b64 = base64.b64encode(conf_text.encode('utf-8')).decode('ascii')
        body = f"[IO.File]::WriteAllBytes('{target}', [Convert]::FromBase64String('{b64}'))"
    rc, out = rig.pc.job(f'#job owner={rig.owner} timeout=60 type=ps1\n{body}\n', 60)
    want = hashlib.sha256(conf_text.encode('utf-8')).hexdigest() if conf_text is not None else None
    if rc != 0 or sha256(target) != want:
        raise RuntimeError(f'dxvk.conf staging failed (exit {rc}, sha {sha256(target)}, want {want}): {out.strip()[-200:]}')
    return f"dxvk.conf {'removed' if conf_text is None else 'staged sha ' + want[:12]} at {target}"


def write_cell(folder, c, log):
    p = Path(folder) / (cell_name(c) + '.json')
    p.write_text(json.dumps(c, indent=1), encoding='utf-8')
    m = metrics(c)
    log(f"cell {cell_name(c)} {c.get('status')}: load {m['load_s']} p50 {m['p50_ms']} p99 {m['p99_ms']} VA {m['va_used_mb']}/{m['va_peak_mb']} "
        f"commit {m['commit_mb']} vram {m['vram_mb']} {c.get('reason') or ''}")


def read_cells(run_dir):
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((Path(run_dir) / 'cells').glob('*.json'))]


def cmd_summarize(a):
    dirs = [Path(d) for d in a.run]
    s = summarize([c for d in dirs for c in read_cells(d)], [d.name for d in dirs], load_rows())
    text = json.dumps(s, indent=1)
    if a.out:
        Path(a.out).write_text(text + '\n', encoding='utf-8')
    else:
        print(text)
    print(f"{len(s['cells'])} cell keys, {len(s['refused'])} refused", file=sys.stderr)
    return 0


def cmd_check(a):
    b = json.loads(Path(a.baseline).read_text(encoding='utf-8'))
    bad = baseline_problems(b)
    for x in bad:
        print('perf_baseline check:', x)
    print(f'perf_baseline check: {"ok" if not bad else "FAILED"} ({len(b.get("cells", {}))} cell keys, {len(b.get("runs", []))} runs)')
    return 1 if bad else 0


def cmd_compare(a):
    base = json.loads(Path(a.baseline).read_text(encoding='utf-8'))
    now = summarize(read_cells(a.run), [Path(a.run).name])
    budget = None
    if a.feature:
        budget = json.loads(Path(a.budgets).read_text(encoding='utf-8'))['features'][a.feature]['delta']
    rows = compare(base, now, budget)
    print(f"{'cell':52} {'metric':10} {'base':>9} {'now':>9} {'delta':>9} {'limit':>7}")
    for r in rows:
        print(f"{r['cell']:52} {r['metric']:10} {r['baseline']:9} {r['now']:9} {r['delta']:9} {str(r['limit'] if r['limit'] is not None else '-'):>7}"
              f"{'  BREACH' if r['breach'] else ''}")
    n = sum(r['breach'] for r in rows)
    print(f'{len(rows)} comparisons, {n} breach(es)' + ('' if a.feature else ' (no --feature: no budget applied)'))
    return 1 if n else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('measure')
    m.add_argument('--run', required=True)
    m.add_argument('--owner', default='claude-j23')
    m.add_argument('--session', default='perf_baseline')
    m.add_argument('--adapter', default=str(ADAPTER))
    m.add_argument('--backends', default=','.join(BACKENDS))
    m.add_argument('--sizes', default=','.join(SIZES))
    m.add_argument('--scenarios')
    m.add_argument('--poses', help='only these poses (default: every pose of each row)')
    m.add_argument('--repeats', type=int, default=3)
    m.add_argument('--perf-s', type=int, default=20)
    m.add_argument('--deploy-end-s', type=int, default=60, help='the land_small --deploy end cell per block (0: none)')
    m.add_argument('--dxvk-variants', help='JSON {name: dxvk.conf text}: DXVK blocks run once per variant (the dxvk.conf sweep)')
    s = sub.add_parser('summarize')
    s.add_argument('--run', required=True, action='append')
    s.add_argument('--out')
    c = sub.add_parser('check')
    c.add_argument('--baseline', default=str(BASELINE))
    k = sub.add_parser('compare')
    k.add_argument('--run', required=True)
    k.add_argument('--baseline', default=str(BASELINE))
    k.add_argument('--budgets', default=str(BUDGETS))
    k.add_argument('--feature')
    a = ap.parse_args(argv)
    return {'measure': measure, 'summarize': cmd_summarize, 'check': cmd_check, 'compare': cmd_compare}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
