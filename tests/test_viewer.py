"""J31 review viewer: pins agree with the proxy, and the built viewer renders hello-world headless, deterministically and interactively.

The render tests need the build output (viewer/core/build.sh --docker build, or CI's viewer job) and Python Playwright with Chromium
(wsc setup check_playwright); without them they skip with the reason. CI's viewer job runs them after the build.
"""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('VIEWER_OUT', ROOT / 'build' / 'viewer' / 'out'))
HELLO = ROOT / 'viewer' / 'napoleon' / 'hello'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def have_playwright():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


class Pins(unittest.TestCase):
    def test_lua_pin_matches_proxy(self):
        pins = json.loads((ROOT / 'viewer' / 'pins.json').read_text())
        proxy = load('fetch_lua', ROOT / 'proxy' / 'tools' / 'fetch_lua.py')
        self.assertEqual(pins['lua']['sha256'], proxy.PIN['sha256'])
        self.assertEqual(pins['lua']['version'], proxy.PIN['version'])

    def test_every_pin_is_exact(self):
        pins = json.loads((ROOT / 'viewer' / 'pins.json').read_text())
        for k in ('rmlui', 'freetype'):
            self.assertRegex(pins[k]['commit'], r'^[0-9a-f]{40}$', k)
        self.assertRegex(pins['emsdk_image']['digest'], r'^sha256:[0-9a-f]{64}$')

    def test_font_has_licence(self):
        for f in json.loads((HELLO / 'screen.json').read_text())['fonts']:
            self.assertTrue((ROOT / 'viewer' / 'napoleon' / 'fonts' / f).exists(), f)
        self.assertTrue((ROOT / 'viewer' / 'napoleon' / 'fonts' / 'OFL.txt').exists())


@unittest.skipUnless((OUT / 'viewer.wasm').exists(), f'no {OUT}/viewer.wasm: run viewer/core/build.sh --docker build')
@unittest.skipUnless(have_playwright(), 'no Python Playwright with Chromium (wsc setup check_playwright)')
class Render(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = load('viewer_render', ROOT / 'viewer' / 'core' / 'render.py')
        cls.tmp = tempfile.TemporaryDirectory()
        cls.site = Path(cls.tmp.name) / 'site'
        cls.manifest = cls.r.stage(HELLO, cls.site, OUT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def shot(self, size, ratio, actions=None):
        return self.r.render(self.site, size, ratio, boxes=['title', 'end_turn'], actions=actions)

    def check_layout(self, size, ratio):
        w, h, rgba, boxes = self.shot(size, ratio)
        self.assertEqual((w, h), size)
        self.assertEqual(len(rgba), w * h * 4)
        px = lambda x, y: tuple(rgba[(y * w + x) * 4:(y * w + x) * 4 + 3])
        # non-blank: the panel, text and art give many colours
        self.assertGreater(len({rgba[i:i + 3] for i in range(0, len(rgba), 4 * 97)}), 50)
        # text pixels sit where the layout puts them: bright title-coloured pixels inside the title box, none beside the panel
        x, y, bw, bh = (int(v) for v in boxes['title'])
        self.assertAlmostEqual(bh / ratio, 30 * 1.2, delta=12)   # 30 dp text scales with the ratio
        bright = sum(1 for yy in range(y, y + bh) for xx in range(x, x + bw) if px(xx, yy)[0] > 200 and px(xx, yy)[1] > 180)
        self.assertGreater(bright, bw * bh * 0.03, f'title box {boxes["title"]} has {bright} text pixels')
        right = int((40 + 520 + 2 * 16 + 2 * 2 + 20) * ratio)   # the panel's right edge in px plus a margin
        self.assertTrue(all(px(xx, yy) == (0, 0, 0) for yy in range(0, h, 7) for xx in range(right, w, 7)))
        return hashlib.sha256(rgba).hexdigest()

    def test_1080p_ratio_1(self):
        self.check_layout((1920, 1080), 1.0)

    def test_4k_slider_125(self):
        self.check_layout((3840, 2160), 2160 / 1080 * 1.25)   # D19: 4K x 125 % = dp ratio 2.5

    def test_deterministic(self):
        a = self.r.png_bytes(*self.shot((1920, 1080), 1.0)[:3])
        b = self.r.png_bytes(*self.shot((1920, 1080), 1.0)[:3])
        self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())

    def test_hover_press_click_scroll(self):
        seen = {}

        def drive(page):
            el = lambda i: page.evaluate('id => window.viewer.element(id)', i)
            b = el('end_turn')
            cx, cy = int(b['x'] + b['w'] / 2), int(b['y'] + b['h'] / 2)
            page.evaluate(f'window.viewer.mouseMove({cx}, {cy}); window.viewer.frame()')
            seen['hover'] = el('end_turn')['hover']
            page.evaluate('window.viewer.mouseDown(0); window.viewer.frame()')
            seen['active'] = el('end_turn')['active']
            page.evaluate('window.viewer.mouseUp(0); window.viewer.frame()')
            seen['turn'] = el('turn')['rml']
            seen['event'] = el('last_event')['rml']
            a = el('armies')
            page.evaluate(f'window.viewer.mouseMove({int(a["x"] + 50)}, {int(a["y"] + 50)}); window.viewer.wheel(1); window.viewer.wheel(1); window.viewer.frame()')
            seen['scroll'] = el('armies')['scroll_top']
        self.shot((1280, 720), 1.0, actions=drive)
        self.assertTrue(seen['hover'])
        self.assertTrue(seen['active'])
        self.assertEqual(seen['turn'], '2')
        self.assertIn('returned 2', seen['event'])
        self.assertGreater(seen['scroll'], 0)


if __name__ == '__main__':
    unittest.main()
