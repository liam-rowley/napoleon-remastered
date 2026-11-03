"""Host tests for the J24 run helpers moved to tools/ (review round 1, finding 2): shot_sheet.py (shot lookup, crop, missing cells),
shadow_density.py (density parsing, the per-setting row), acceptance_summary.py (failed steps, shot margins) and perf_baseline.py ladder."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAVE_PIL = importlib.util.find_spec('PIL') is not None


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sheet, dens, acc, pb = load('shot_sheet'), load('shadow_density'), load('acceptance_summary'), load('perf_baseline')


class ShotSheet(unittest.TestCase):
    def test_find_prefers_the_exact_suffix_and_skips_camera_files(self):
        with tempfile.TemporaryDirectory() as t:
            for n in ('a_p1_cam.jpg', 'a_p10.jpg', 'a_p1.jpg'):
                (Path(t) / n).write_bytes(b'x')
            self.assertEqual(sheet.find_shot(t, 'p1').name, 'a_p1.jpg')
            self.assertIsNone(sheet.find_shot(t, 'p2'))

    def test_near_crop_keeps_the_cell_aspect(self):
        x0, y0, x1, y1 = sheet.near_crop((1920, 1080))
        self.assertEqual((x0, y0, x1 - x0), (640, 540, 640))
        self.assertAlmostEqual((x1 - x0) / (y1 - y0), sheet.W / sheet.H, places=2)

    @unittest.skipUnless(HAVE_PIL, 'Pillow is not installed here (CI runners have none; shot_sheet.py imports it only to draw)')
    def test_build_marks_missing_cells(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'stock').mkdir()
            Image.new('RGB', (64, 36), (200, 0, 0)).save(Path(t) / 'stock' / 'shot_p1.png')
            im, missing = sheet.build(t, 'T', ['p1', 'p2'], ['stock:Stock', 'big'])
            self.assertEqual(im.size, (2 * sheet.W, sheet.TITLE + 2 * (sheet.H + sheet.LABEL)))
            self.assertEqual(missing, ['big/p1', 'stock/p2', 'big/p2'])
            self.assertEqual(im.getpixel((10, sheet.TITLE + sheet.LABEL + 10))[0] > 150, True)


class ShadowDensity(unittest.TestCase):
    def d(self, t20, farz=250.0):
        return {'map': 2048, 'farz': farz, 'view_to_sun_deg': 90, 'texels_per_m': {'20m': t20, '60m': 1, '140m': 0.5}}

    def test_parse_drops_null_and_junk(self):
        out = dens.parse_density(['a {"map": 1}', 'b null', 'c not json', ''])
        self.assertEqual(out, {'a': {'map': 1}})

    def test_setting_row_worst_and_ratio(self):
        dd = {'j24_s_y_0': self.d(4.0, 150), 'j24_s_y_90': self.d(10.0), 'j24_s_p1': self.d(7.0)}
        r = dens.setting_row(dd, 'j24', 's', ['0', '90', '180'], ['p1', 'p2'])
        self.assertEqual(r['yaws'], [4.0, 10.0, None])
        self.assertEqual((r['worst'], r['best_worst'], r['farz']), (4.0, 2.5, 150))
        self.assertEqual(r['poses'], [7.0, None])

    def test_tsv_is_sorted_with_a_header(self):
        lines = dens.tsv({'b': self.d(2), 'a': self.d(1)}).splitlines()
        self.assertTrue(lines[0].startswith('capture\tmap'))
        self.assertEqual([x.split('\t')[0] for x in lines[1:]], ['a', 'b'])


class AcceptanceSummary(unittest.TestCase):
    def test_failed_steps_and_shot_margins(self):
        d = {'passed': False, 'build_id': 'b1', 'steps': {
            'exe_sha1': {'ok': True},
            'hist_nile:load': {'ok': False, 'reason': 'headless relaunch'},
            'land_small:shot_match': {'ok': True, 'mean_abs_diff': 1.6, 'threshold': 4.0},
            'perf': 'not a dict'}}
        s = acc.summarize_pass(d)
        self.assertEqual((s['passed'], s['build'], s['failed']), (False, 'b1', ['hist_nile:load']))
        self.assertEqual(s['shots'], {'land_small': (1.6, 4.0)})


class Ladder(unittest.TestCase):
    def s(self, p50, va):
        return {'cells': {'dxvk|1920x1080|land_small|deploy': {'p50_ms': {'median': p50}, 'va_used_mb': {'median': va}}}}

    def test_control_first_then_deltas(self):
        out = pb.ladder(('ctl', self.s(2.0, 1800)), [('8k', self.s(2.5, 1850.4))]).splitlines()
        self.assertTrue(out[0].startswith('| run | cell | p50_ms'))
        self.assertIn('| ctl | dxvk|1920x1080|land_small|deploy | 2 | - |', out[2])
        self.assertIn('2.5 (+0.50)', out[3])
        self.assertIn('1850.4 (+50)', out[3])

    def test_run_summary_falls_back_to_cells(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'summary.json').write_text(json.dumps(self.s(1.0, 1)), encoding='utf-8')
            self.assertEqual(pb.run_summary(t), self.s(1.0, 1))


if __name__ == '__main__':
    unittest.main()
