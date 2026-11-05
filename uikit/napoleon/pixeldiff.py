#!/usr/bin/env python3
"""The pixel comparison behind the UI baseline: decode the renderer's PNGs, count the pixels that moved, judge them against a tolerance, draw a diff image.

purpose: pure functions for uikit/napoleon/changes.py: decode_png (the fixed format of viewer/core/render.py png_bytes, stdlib only), judge (unchanged, within tolerance or changed against the baseline's channel_tolerance, max_changed_pixels and max_delta) and diff_png (changed pixels in red over the render dimmed 30 %)
usage: import it (changes.py and tests/test_uikit.py do); it has no command line
when: changes.py calls it for a corner whose rgba_sha256 differs from the baseline; equal hashes never reach it
not-a-verb: a library module of changes.py, with no command line of its own
"""
import importlib.util
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('viewer_render', ROOT / 'viewer' / 'core' / 'render.py')
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
DIM = bytes(v * 7 // 10 for v in range(256))   # 30 % dimmed: never reaches 255, so a red mark cannot be a render pixel


def decode_png(data):
    """(w, h, rgba) of a PNG written by render.py png_bytes: 8-bit RGBA, not interlaced, filter 0 on every row. ValueError for anything else."""
    if data[:8] != PNG_SIGNATURE:
        raise ValueError('not a PNG')
    pos, head, idat = 8, None, []
    while pos < len(data):
        size, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + size]
        pos += 12 + size
        if kind == b'IHDR':
            head = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat.append(body)
    if head is None or head[2:] != (8, 6, 0, 0, 0):
        raise ValueError(f'PNG format is not the renderer\'s 8-bit RGBA: {head}')
    w, h = head[:2]
    raw = zlib.decompress(b''.join(idat))
    stride = w * 4 + 1
    if len(raw) != stride * h or any(raw[y * stride] for y in range(h)):
        raise ValueError('PNG rows are not the renderer\'s filter 0 rows')
    return w, h, b''.join(raw[y * stride + 1:(y + 1) * stride] for y in range(h))


def judge(ref, cur, tol):
    """Compare two (w, h, rgba) images: {verdict, changed, budget, max_delta, pixels, reason}. `pixels` are the indexes whose largest channel difference exceeds
    channel_tolerance; the verdict is `within tolerance` when their count is at most max_changed_pixels (a fraction of the image) and no pixel differs by more than max_delta."""
    (rw, rh, rpx), (w, h, px) = ref, cur
    if (rw, rh) != (w, h):
        return {'verdict': 'changed', 'changed': 0, 'budget': 0, 'max_delta': 0, 'pixels': [], 'reason': f'dimensions differ: {rw}x{rh} vs {w}x{h}'}
    stride, pixels, top = w * 4, [], 0
    for y in range(h):
        a, b = rpx[y * stride:(y + 1) * stride], px[y * stride:(y + 1) * stride]
        if a == b:
            continue
        for x in range(w):
            i = x * 4
            d = max(abs(a[i] - b[i]), abs(a[i + 1] - b[i + 1]), abs(a[i + 2] - b[i + 2]), abs(a[i + 3] - b[i + 3]))
            top = max(top, d)
            if d > tol['channel_tolerance']:
                pixels.append(y * w + x)
    budget = int(w * h * tol['max_changed_pixels'])
    verdict = 'unchanged' if not top else 'changed' if len(pixels) > budget or top > tol['max_delta'] else 'within tolerance'
    return {'verdict': verdict, 'changed': len(pixels), 'budget': budget, 'max_delta': top, 'pixels': pixels,
            'reason': f'{len(pixels)} pixels over {tol["channel_tolerance"]} levels, budget {budget}; largest difference {top}, limit {tol["max_delta"]}'}


def diff_png(w, h, rgba, pixels):
    """PNG bytes: the render dimmed 30 % and opaque, with each index of `pixels` in pure red."""
    out = bytearray(rgba.translate(DIM))
    out[3::4] = b'\xff' * (w * h)
    for i in pixels:
        out[i * 4:i * 4 + 4] = b'\xff\x00\x00\xff'
    return R.png_bytes(w, h, bytes(out))
