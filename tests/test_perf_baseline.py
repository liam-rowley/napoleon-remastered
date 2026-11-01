"""Host tests for tools/perf_baseline.py (J23): the matrix expansion and its order, median and spread, the peak address space, the baseline
shape check, the compare thresholds and the refusal of a cell without its pins."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('perf_baseline', ROOT / 'tools' / 'perf_baseline.py')
pb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pb)

ROWS = {'land_small': {'id': 'land_small', 'launch': 'ctl.py scene land_small', 'camera_poses': {'turned': {}, 'deploy': {}}},
        'campaign_start': {'id': 'campaign_start', 'launch': 'ctl.py scene campaign_start'},
        'campaign_britain_1805': {'id': 'campaign_britain_1805', 'launch': 'stage_save.py stage x'}}


def pins(backend='dxvk', size='1920x1080', run='r1'):
    return {'build': 'b', 'kit': 'k', 'watcher': '1.2.0', 'backend': backend, 'size': size, 'dxvk': {'version': '3.1.1'}, 'gpu': 'g',
            'driver': 'd', 'dxvk_conf_sha256': 'absent', 'prefs_gfx': {'gfx_vsync': 'false'}, 'frame_cap': {'gfx_vsync': 'false'},
            'date': '2026-11-01', 'run': run}


def cell(backend='dxvk', size='1920x1080', sid='land_small', pose='deploy', n=1, p50=2.0, va=1900, load=4.0):
    return {'backend': backend, 'size': size, 'variant': None, 'pass': n, 'scenario': sid, 'pose': pose, 'measure': n > 0, 'status': 'ok',
            'scene': {'load_s': load}, 'va_peak_mb': va + 50,
            'perf': {'frame_ms': {'p50': p50, 'p99': p50 * 2, 'max': p50 * 5}, 'mem': {'va_used_mb': va, 'commit_mb': 1200},
                     'vram': {'process_dedicated_mb': 600}},
            'pins': pins(backend, size)}


class Matrix(unittest.TestCase):
    def test_scenarios_from_the_registry_in_order(self):
        self.assertEqual(pb.scenario_list(ROWS), ['land_small', 'campaign_start'])   # a save-staged row is not a ctl scene
        self.assertEqual(pb.scenario_list(ROWS, ['campaign_start']), ['campaign_start'])
        with self.assertRaises(SystemExit):
            pb.scenario_list(ROWS, ['land_40'])

    def test_expand_order_and_warm_up(self):
        plan = pb.expand(['1920x1080', '3840x2160'], ['dxvk', 'system'], ['land_small', 'campaign_start'], ROWS, 3)
        # per size x backend: warm-up (2 scenes, no perf) + 3 passes x (2 land poses + campaign default)
        self.assertEqual(len(plan), 2 * 2 * (2 + 3 * 3))
        self.assertEqual([c['size'] for c in plan[:22]], ['1920x1080'] * 22)   # size outermost
        self.assertEqual({c['backend'] for c in plan[:11]}, {'dxvk'})
        self.assertFalse(any(c['measure'] for c in plan if c['pass'] == 0))
        self.assertEqual([c['pose'] for c in plan[2:5]], ['deploy', 'turned', None])
        only = pb.expand(['1920x1080'], ['dxvk'], ['land_small'], ROWS, 1, only_poses=['deploy'])
        self.assertEqual([c['pose'] for c in only], [None, 'deploy'])

    def test_variants_apply_to_dxvk_only(self):
        plan = pb.expand(['1920x1080'], ['dxvk', 'system'], ['campaign_start'], ROWS, 1, variants=['a', 'b'])
        self.assertEqual(sorted({(c['backend'], c['variant']) for c in plan}, key=str), [('dxvk', 'a'), ('dxvk', 'b'), ('system', None)])


class Numbers(unittest.TestCase):
    def test_spread(self):
        self.assertEqual(pb.spread([2.0, 2.2, 1.8]), {'median': 2.0, 'spread': 0.4, 'spread_pct': 20.0, 'n': 3})
        self.assertIsNone(pb.spread([None]))

    def test_va_peak_uses_the_host_offset(self):
        self.assertEqual(pb.va_peak(1900, {'virtual_mb': 2100.0, 'peak_virtual_mb': 2400.0}), 2200.0)
        self.assertIsNone(pb.va_peak(1900, {'error': 'x'}))

    def test_frame_cap_reads_conf_and_prefs(self):
        f = pb.frame_cap({'gfx_vsync': 'false', 'gfx_frame_rate': '60'}, 'd3d9.presentInterval = 1\n')
        self.assertEqual((f['gfx_vsync'], f['d3d9.presentInterval'], f['d3d9.maxFrameRate']), ('false', '1', 'default'))


class Summary(unittest.TestCase):
    def cells(self):
        out = [cell(n=0, pose=None, load=9.0), cell(backend='system', n=0, pose=None, load=8.0)]
        for n, p in ((1, 2.0), (2, 2.2), (3, 1.8)):
            out += [cell(n=n, p50=p), cell(backend='system', n=n, p50=p * 2)]
        return out

    def test_summary_medians_ratios_cold(self):
        s = pb.summarize(self.cells())
        row = s['cells']['dxvk|1920x1080|land_small|deploy']
        self.assertEqual(row['p50_ms']['median'], 2.0)
        self.assertEqual(row['cold_load_s'], 9.0)
        self.assertTrue(row['noisy'])   # 20 % spread
        self.assertEqual(s['dxvk_over_system']['1920x1080|land_small|deploy']['p50_ms'], 0.5)
        self.assertEqual(s['runs'], ['r1'])
        self.assertEqual(s['refused'], [])

    def test_cell_without_pins_is_refused(self):
        c = cell()
        del c['pins']['driver']
        s = pb.summarize([c])
        self.assertEqual(s['cells'], {})
        self.assertIn('pin driver missing', s['refused'][0]['problems'])
        bad = cell()
        bad['status'] = 'failed'
        self.assertTrue(pb.cell_problems(bad))

    def test_baseline_shape(self):
        b = pb.summarize(self.cells())
        b.update(date='2026-11-01', not_covered=['land_40: J46'], conditions={'headless': True})
        self.assertEqual(pb.baseline_problems(b), [])
        b2 = json.loads(json.dumps(b))
        del b2['blocks']['dxvk|1920x1080']['gpu']
        del b2['not_covered']
        probs = pb.baseline_problems(b2)
        self.assertIn('no not_covered', probs)
        self.assertIn('block dxvk|1920x1080: pin gpu missing', probs)

    def test_compare_thresholds(self):
        base = pb.summarize(self.cells())
        later = [cell(n=n, p50=p) for n, p in ((1, 2.6), (2, 2.5), (3, 2.7))]
        now = pb.summarize(later)
        rows = pb.compare(base, now, {'p50_ms': {'1920x1080': 0.5}, 'va_peak_mb': 100})
        p50 = next(r for r in rows if r['metric'] == 'p50_ms')
        self.assertEqual((p50['delta'], p50['breach']), (0.6, True))
        self.assertFalse(next(r for r in rows if r['metric'] == 'va_peak_mb')['breach'])
        self.assertFalse(any(r['breach'] for r in pb.compare(base, now)))   # no budget, no breach

    def test_sized_adapter_leaves_the_committed_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = pb.sized_adapter({'ctl': {'launch': {'size': '1920x1080', 'keys': {}}}}, '3840x2160', d)
            self.assertEqual(json.loads(p.read_text())['ctl']['launch']['size'], '3840x2160')


if __name__ == '__main__':
    unittest.main()
