#!/usr/bin/env python3
"""Render a viewer screen to PNG in headless Chromium, from the same viewer.wasm, viewer.js and host page as the review page.

purpose: stage a screen with the built viewer into a site folder, and render it to a PNG in headless Chromium (Python Playwright) at a size and dp ratio
usage: python3 viewer/core/render.py <screen dir or its .rml> --size 1920x1080 --dp-ratio 1.0 --out x.png [--wasm build/viewer/out] [--json] | --stage-only <site dir>
when: every gate render and every review page publish (--stage-only builds the folder the artifact is published from); needs `viewer/core/build.sh` output and Playwright (wsc setup check_playwright)
not-a-verb: a renderer with a browser round trip; tests/test_viewer.py and the review publish call it

One renderer for review and for gates (UI_PIPELINE section 2): the page here is viewer/core/web/index.html, served over a local http
server exactly as staged for the artifact. The PNG is the GL backbuffer read inside the wasm (viewer_read_pixels), not a page
screenshot, so browser compositing and device scale do not enter it. Chromium renders WebGL through SwiftShader (software) here,
and RmlUi's clock is frozen at 0 (viewer_set_time), so the same input gives the same pixels.
"""
import argparse
import base64
import functools
import hashlib
import http.server
import json
import shutil
import struct
import sys
import threading
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / 'viewer' / 'core' / 'web'
FONTS = ROOT / 'viewer' / 'napoleon' / 'fonts'
CHROMIUM_ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-gpu-driver-bug-workarounds',
                 '--force-color-profile=srgb']


def stage(screen_dir, site, wasm_dir):
    """Copy the host page, viewer.js/.wasm, the screen's files and fonts into `site` (the layout the artifact is published from)."""
    screen_dir, site, wasm_dir = Path(screen_dir), Path(site), Path(wasm_dir)
    manifest = json.loads((screen_dir / 'screen.json').read_text())
    if site.exists():
        shutil.rmtree(site)
    (site / 'screen').mkdir(parents=True)
    (site / 'fonts').mkdir()
    for f in ('index.html', 'viewer_host.js'):
        shutil.copy2(WEB / f, site / f)
    for f in ('viewer.js', 'viewer.wasm'):
        if not (wasm_dir / f).exists():
            sys.exit(f'render: no {wasm_dir / f}: run viewer/core/build.sh --docker build (or download the CI artifact)')
        shutil.copy2(wasm_dir / f, site / f)
    shutil.copy2(screen_dir / 'screen.json', site / 'screen' / 'screen.json')
    for f in manifest['files']:
        shutil.copy2(screen_dir / f, site / 'screen' / f)
    for f in manifest['fonts']:
        shutil.copy2(FONTS / f, site / 'fonts' / f)
    return manifest


def png_bytes(w, h, rgba):
    """RGBA, top row first -> PNG (filter 0, zlib level 9: deterministic for the same pixels)."""
    raw = b''.join(b'\x00' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.wasm': 'application/wasm', '.js': 'text/javascript'}

    def log_message(self, *a):
        pass


def serve(site):
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=str(site)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def render(site, size, ratio, boxes=(), actions=None, capture_log=None):
    """Open the staged site headless, return (w, h, rgba bytes, {id: box}). `actions(page)` may drive input before the capture."""
    from playwright.sync_api import sync_playwright
    w, h = size
    httpd = serve(site)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=CHROMIUM_ARGS)
            page = browser.new_page(viewport={'width': 1280, 'height': 900}, device_scale_factor=1)
            if capture_log is not None:
                page.on('console', lambda m: capture_log.append(f'console {m.type}: {m.text}'))
                page.on('pageerror', lambda e: capture_log.append(f'pageerror: {e}'))
                page.on('response', lambda r: capture_log.append(
                    f'response {r.status} {r.headers.get("content-type", "")} {r.url.rsplit("/", 1)[-1]}'))
            page.goto(f'http://127.0.0.1:{httpd.server_port}/index.html?headless=1&w={w}&h={h}&ratio={ratio}')
            page.wait_for_function('window.viewerReady === true || window.viewerError !== undefined', timeout=60000)
            err = page.evaluate('window.viewerError')
            if err:
                raise RuntimeError(f'viewer failed: {err}')
            if actions:
                actions(page)
            cap = page.evaluate('window.viewer.capture()')
            found = {b: page.evaluate('id => window.viewer.box(id)', b) for b in boxes}
            browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
    return cap['w'], cap['h'], base64.b64decode(cap['rgba']), found


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('screen', nargs='?', help='screen folder (with screen.json) or its .rml')
    ap.add_argument('--size', default='1920x1080')
    ap.add_argument('--dp-ratio', type=float, default=1.0, help='final dp ratio (D19: height / 1080 x slider, computed by the caller)')
    ap.add_argument('--out')
    ap.add_argument('--wasm', default=str(ROOT / 'build' / 'viewer' / 'out'))
    ap.add_argument('--site', default=str(ROOT / 'build' / 'viewer' / 'site'))
    ap.add_argument('--stage-only', metavar='SITE', help='only stage the site folder (for publishing) and exit')
    ap.add_argument('--json', action='store_true', help='print size, sha256 and the probe element boxes as JSON')
    a = ap.parse_args()
    screen = Path(a.screen) if a.screen else ROOT / 'viewer' / 'napoleon' / 'hello'
    if screen.suffix == '.rml':
        screen = screen.parent
    if a.stage_only:
        stage(screen, a.stage_only, a.wasm)
        print(f'render: staged {screen} into {a.stage_only}')
        return
    if not a.out:
        ap.error('--out is required unless --stage-only')
    manifest = stage(screen, a.site, a.wasm)
    w, h = (int(x) for x in a.size.lower().split('x'))
    log = []
    rw, rh, rgba, boxes = render(a.site, (w, h), a.dp_ratio, boxes=list(manifest.get('probe', {}).values()), capture_log=log)
    data = png_bytes(rw, rh, rgba)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()
    if a.json:
        print(json.dumps({'out': a.out, 'w': rw, 'h': rh, 'dp_ratio': a.dp_ratio, 'sha256': sha, 'boxes': boxes, 'log': log}, indent=1))
    else:
        print(f'render: {a.out} {rw}x{rh} dp {a.dp_ratio} sha256 {sha}')


if __name__ == '__main__':
    main()
