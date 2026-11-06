"""tools/ui_hosttest.py parity on synthetic pairs: moved content is told apart from edge blending (J32 S3)."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ui_hosttest', ROOT / 'tools' / 'ui_hosttest.py')
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

BG, FG, MID = (16, 24, 32), (240, 240, 240), (128, 132, 136)


def canvas(w=128, h=96):
    return [[BG] * w for _ in range(h)]


def box(img, x, y, w, h, c=FG):
    for yy in range(y, y + h):
        img[yy] = img[yy][:x] + [c] * w + img[yy][x + w:]
    return img


def scene(dx=0, dy=0):
    return box(box(canvas(), 20 + dx, 20 + dy, 40, 30), 80, 60, 30, 1)


class Parity(unittest.TestCase):
    def test_identical_images_are_the_same(self):
        r = H.parity_images(scene(), scene())
        self.assertEqual((r['kind'], r['beyond'], r['max_delta'], r['moved']), ('same', 0, 0, []))

    def test_small_differences_stay_under_the_tolerance(self):
        b = box(scene(), 20, 20, 40, 30, (236, 236, 236))
        r = H.parity_images(scene(), b, tol=8)
        self.assertEqual((r['kind'], r['beyond']), ('same', 0))
        self.assertEqual(r['max_delta'], 4)
        self.assertEqual(r['differing'], 40 * 30)

    def test_a_blended_edge_is_rasterising_not_layout(self):
        b = box(scene(), 60, 20, 1, 30, MID)        # the box's right edge half covered one pixel further out
        r = H.parity_images(scene(), b)
        self.assertEqual(r['kind'], 'raster')
        self.assertEqual(r['moved'], [])
        self.assertEqual(r['beyond'], 30)

    def test_a_rule_spread_over_two_rows_is_rasterising(self):
        a = box(canvas(), 10, 40, 100, 1)
        b = box(box(canvas(), 10, 40, 100, 1, MID), 10, 41, 100, 1, MID)
        self.assertEqual(H.parity_images(a, b)['kind'], 'raster')

    def test_one_moved_box_is_layout_and_is_found_where_it_is(self):
        a = box(box(canvas(), 8, 8, 50, 80), 70, 40, 40, 30)
        b = box(box(canvas(), 8, 8, 50, 80), 71, 40, 40, 30)
        r = H.parity_images(a, b)
        self.assertEqual(r['kind'], 'layout')
        self.assertEqual(r['offset'], [0, 0])
        self.assertTrue(r['moved'])
        self.assertTrue(all(m['shift'] == [1, 0] for m in r['moved']))
        self.assertTrue(all(m['box'][0] >= 64 for m in r['moved']))

    def test_a_whole_image_shift_is_aligned_and_reported(self):
        r = H.parity_images(scene(), box(box(canvas(), 21, 22, 40, 30), 81, 62, 30, 1))
        self.assertEqual(r['offset'], [1, 2])
        self.assertEqual(r['kind'], 'layout')
        self.assertEqual(r['beyond'], 0)

    def test_a_box_moved_further_than_the_whole_image_search_is_still_layout(self):
        for n in (3, 4, 8, 20):
            a = box(canvas(320, 200), 60, 60, 120, 40)
            b = box(canvas(320, 200), 60 + n, 60 + n, 120, 40)
            r = H.parity_images(a, b)
            self.assertEqual(r['kind'], 'layout', n)
            self.assertIn([n, n], [m['shift'] for m in r['moved']], n)

    def test_a_box_moved_beyond_the_tile_search_shows_as_solid_difference(self):
        r = H.parity_images(box(canvas(400, 240), 40, 60, 200, 60), box(canvas(400, 240), 140, 160, 200, 60))
        self.assertEqual(r['kind'], 'layout')
        self.assertIn([], [m['shift'] for m in r['moved']])

    def test_a_box_only_one_image_has_is_layout_not_blending(self):
        self.assertEqual(H.parity_images(canvas(320, 200), box(canvas(320, 200), 60, 60, 120, 40))['kind'], 'layout')

    def test_a_move_along_one_axis_is_layout(self):
        r = H.parity_images(box(canvas(320, 200), 60, 60, 120, 40), box(canvas(320, 200), 80, 60, 120, 40))
        self.assertEqual(r['kind'], 'layout')

    def test_a_box_moved_at_the_image_edge_is_layout(self):
        for x, y, n in ((280, 150, -8), (0, 0, 8), (200, 170, 8)):   # the last one is clipped by the bottom of the image
            a = box(canvas(320, 200), x, y, 40, 30)
            b = canvas(320, 200)
            box(b, max(0, x + n), max(0, y + n), 40, min(30, 200 - y - n))
            self.assertEqual(H.parity_images(a, b)['kind'], 'layout', (x, y, n))

    def test_a_column_differing_to_the_bottom_edge_is_not_explained_by_rows_falling_off(self):
        a, b = canvas(128, 80), canvas(128, 80)
        box(a, 40, 64, 30, 16, MID)
        box(b, 40, 64, 30, 16, MID)
        box(b, 50, 64, 1, 16, FG)     # J32 review: the 4K tile at 1504,2144, a pixel column differing in all 16 rows of a cut tile
        self.assertEqual(H.parity_images(a, b)['kind'], 'raster')

    def test_a_mark_only_one_image_has_is_not_moved_by_shifting_it_away(self):
        b = box(canvas(), 20, 40, 60, 1)
        self.assertEqual(H.parity_images(canvas(), b)['kind'], 'raster')

    def test_a_soft_edge_on_a_wide_search_stays_rasterising(self):
        a = box(canvas(320, 200), 60, 60, 120, 40)
        b = box(box(canvas(320, 200), 60, 60, 120, 40), 59, 59, 122, 1, MID)
        self.assertEqual(H.parity_images(a, b)['kind'], 'raster')

    def test_rect_limits_the_comparison(self):
        b = box(scene(), 100, 5, 10, 10, (200, 0, 0))
        self.assertEqual(H.parity_images(scene(), b, rect=(0, 0, 90, 96))['kind'], 'same')
        self.assertEqual(H.parity_images(scene(), b)['beyond'], 100)

    def test_share_is_of_the_compared_pixels(self):
        b = box(scene(), 0, 0, 4, 4, (200, 0, 0))
        r = H.parity_images(scene(), b, rect=(0, 0, 8, 8))
        self.assertEqual((r['pixels'], r['beyond'], r['share_beyond']), (64, 16, 0.25))

    def test_sizes_that_differ_are_refused(self):
        r = H.parity_images(canvas(10, 10), canvas(12, 10))
        self.assertFalse(r['ok'])
        self.assertIn('sizes differ', r['reason'])

    def test_the_command_line_reads_pngs_writes_crops_and_exits_1_on_layout(self):
        def save(img, path):
            H.png_write(path, len(img[0]), len(img), [[c for p in row for c in p] for row in img], 3)
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            still = lambda: box(box(box(canvas(), 4, 4, 60, 30), 4, 50, 60, 30), 70, 4, 50, 30)
            save(box(still(), 70, 50, 40, 30), t / 'a.png')
            save(box(still(), 71, 50, 40, 30), t / 'moved.png')
            save(box(box(still(), 70, 50, 40, 30), 110, 50, 1, 30, MID), t / 'blend.png')
            self.assertEqual(H.main(['parity', str(t / 'a.png'), str(t / 'moved.png'), '--json', str(t / 'r.json'), '--crops', str(t / 'c')]), 1)
            self.assertEqual(json.loads((t / 'r.json').read_text())['kind'], 'layout')
            self.assertTrue(list((t / 'c').glob('moved_*.png')))
            self.assertEqual(H.main(['parity', str(t / 'a.png'), str(t / 'blend.png')]), 0)


if __name__ == '__main__':
    unittest.main()
