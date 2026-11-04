"""Before and after contact sheets of the UI art upscaler (J36; needs numpy, Pillow).

purpose: draw per-role before/after sheets at one display scale and 1:1 crops of a fixed set of hard cases (thin frames, glyph-like icons, flag cloth, portraits, cursors, soft alpha edges); 'before' is the vanilla art resampled to the same size with plain Lanczos
usage: library (upscale/core), driven by `python3 core/wsc.py upscale sheets`
when: after a run, for Liam to judge the look (nothing here claims approval)
not-a-verb: a library used by tools/verbs/upscale.py, not a registry operation
"""
import hashlib
import os

import numpy as np
from PIL import Image, ImageDraw

import dds
import imageio
import resample

CELL, LABEL, GAP = 176, 14, 6
HARD = [   # name, role, test on the manifest entry
    ('thin_frame', 'panel_frame', lambda e: min(e['src']['w'], e['src']['h']) <= 12),
    ('glyph_icon', 'icon', lambda e: e['src']['alpha'] == 'binary' and max(e['src']['w'], e['src']['h']) <= 64),
    ('flag_cloth', 'flag', lambda e: True),
    ('portrait', 'portrait', lambda e: True),
    ('cursor', 'cursor', lambda e: True),
    ('soft_alpha_edge', None, lambda e: e['src']['alpha'] == 'soft'),
]


def pick(entries, n, tag=''):
    """a fixed sample: the n entries with the smallest sha256(tag + id), so it never changes between runs"""
    return sorted(entries, key=lambda e: hashlib.sha256((tag + e['id']).encode()).hexdigest())[:n]


def _checker(w, h):
    y, x = np.mgrid[0:h, 0:w]
    c = np.where(((x // 8) + (y // 8)) % 2, 200, 160).astype(np.uint8)
    return Image.fromarray(np.dstack([c, c, c]), 'RGB').convert('RGBA')


def _after(e, work):
    data = open(os.path.join(work, e['out']['file']), 'rb').read()
    return imageio.load(data, os.path.splitext(e['path'])[1]).rgba


def _before(e, read, item):
    src = imageio.load(read(item), os.path.splitext(e['path'])[1])
    return resample.finish(resample.lanczos(src.rgba[..., :3].astype(np.float32), e['out']['w'], e['out']['h']),
                           resample.resample_alpha(src.rgba[..., 3], e['out']['w'], e['out']['h'], src.alpha_kind()))


def _paste(sheet, rgba, x, y, w, h):
    im = Image.fromarray(rgba, 'RGBA')
    bg = _checker(w, h)
    bg.alpha_composite(im, (0, 0))
    sheet.paste(bg.convert('RGB'), (x, y))


def role_sheet(role, entries, work, read, items, out_png, per_sheet=24, cols=3):
    """pairs [before | after] on a checker, the same scale in both; returns the png path (or None when nothing is done)"""
    es = pick([e for e in entries if e['role'] == role and e['status'] == 'done'], per_sheet, role)
    if not es:
        return None
    rows = (len(es) + cols - 1) // cols
    cw = 2 * CELL + GAP
    sheet = Image.new('RGB', (cols * (cw + GAP) + GAP, rows * (CELL + LABEL + GAP) + GAP), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for i, e in enumerate(es):
        x0, y0 = GAP + (i % cols) * (cw + GAP), GAP + (i // cols) * (CELL + LABEL + GAP)
        a, b = _after(e, work), _before(e, read, items[e['id']])
        s = min(1.0, CELL / a.shape[1], CELL / a.shape[0])
        w, h = max(1, int(a.shape[1] * s)), max(1, int(a.shape[0] * s))
        for k, img in enumerate((b, a)):
            small = np.asarray(Image.fromarray(img, 'RGBA').resize((w, h), Image.LANCZOS))
            _paste(sheet, small, x0 + k * (CELL + GAP), y0 + LABEL, w, h)
        d.text((x0, y0), '%s  %dx%d -> %dx%d  display x%.2f' % (e['id'].rsplit('/', 1)[-1][:34], e['src']['w'], e['src']['h'], a.shape[1], a.shape[0], s), fill=(230, 230, 230))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sheet.save(out_png)
    return out_png


def hard_case_sheet(entries, work, read, items, out_png, per_case=3, crop=128):
    """1:1 crops (crop x crop texels of the 2.5x output, taken where the art is) of the fixed hard cases: before | after"""
    cells = []
    for name, role, test in HARD:
        es = pick([e for e in entries if e['status'] == 'done' and (role is None or e['role'] == role) and test(e)], per_case, name)
        cells += [(name, e) for e in es]
    if not cells:
        return None
    cw = 2 * crop + GAP
    cols = 3
    rows = (len(cells) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (cw + GAP) + GAP, rows * (crop + LABEL + GAP) + GAP), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for i, (name, e) in enumerate(cells):
        x0, y0 = GAP + (i % cols) * (cw + GAP), GAP + (i // cols) * (crop + LABEL + GAP)
        a, b = _after(e, work), _before(e, read, items[e['id']])
        h, w = a.shape[:2]
        ys, xs = np.nonzero(a[..., 3] > 0)
        cy, cx = (int(ys.mean()), int(xs.mean())) if len(ys) else (h // 2, w // 2)
        top, left = min(max(0, cy - crop // 2), max(0, h - crop)), min(max(0, cx - crop // 2), max(0, w - crop))
        for k, img in enumerate((b, a)):
            c = np.ascontiguousarray(img[top:top + crop, left:left + crop])
            _paste(sheet, c, x0 + k * (crop + GAP), y0 + LABEL, c.shape[1], c.shape[0])
        d.text((x0, y0), '%s: %s' % (name, e['id'].rsplit('/', 1)[-1][:30]), fill=(230, 230, 230))
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sheet.save(out_png)
    return out_png


def compare_sheet(role, works, entries_by_label, read, items, out_png, n=8, crop=160):
    """side by side for the model choice: [Lanczos baseline | model A | model B ...] on the same fixed sample, 1:1 crops of the 2.5x size.
    works: {label: work dir}; entries_by_label: {label: [manifest entries]}"""
    labels = list(works)
    common = None
    for lb in labels:
        ids = {e['id'] for e in entries_by_label[lb] if e['role'] == role and e['status'] == 'done'}
        common = ids if common is None else common & ids
    es = pick([e for e in entries_by_label[labels[0]] if e['id'] in (common or ())], n, 'cmp' + role)
    if not es:
        return None
    cols = 1 + len(labels)
    sheet = Image.new('RGB', (cols * (crop + GAP) + GAP, len(es) * (crop + LABEL + GAP) + GAP), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for r, e in enumerate(es):
        y0 = GAP + r * (crop + LABEL + GAP)
        imgs = [_before(e, read, items[e['id']])] + [_after(next(x for x in entries_by_label[lb] if x['id'] == e['id']), works[lb]) for lb in labels]
        h, w = imgs[0].shape[:2]
        ys, xs = np.nonzero(imgs[0][..., 3] > 0)
        cy, cx = (int(ys.mean()), int(xs.mean())) if len(ys) else (h // 2, w // 2)
        top, left = min(max(0, cy - crop // 2), max(0, h - crop)), min(max(0, cx - crop // 2), max(0, w - crop))
        d.text((GAP, y0), '%s   lanczos | %s' % (e['id'].rsplit('/', 1)[-1][:30], ' | '.join(labels)), fill=(230, 230, 230))
        for k, img in enumerate(imgs):
            c = np.ascontiguousarray(img[top:top + crop, left:left + crop])
            _paste(sheet, c, GAP + k * (crop + GAP), y0 + LABEL, c.shape[1], c.shape[0])
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    sheet.save(out_png)
    return out_png
