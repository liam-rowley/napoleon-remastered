"""Resample and alpha rules of the UI art upscaler (J36): dilate RGB under A = 0, per-channel Lanczos, binary alpha, mip chain (needs numpy, Pillow).

purpose: the image maths between the vanilla RGBA and the output chain: fringe-free RGB for the model, exact-size Lanczos, alpha that never meets the model, mips
usage: library (upscale/core)
when: batch.py processing an asset; tests of the alpha and mip rules
not-a-verb: a library used by upscale/core/batch.py, not a registry operation
"""
import numpy as np
from PIL import Image

import dds


def dilate_rgb(rgba, max_iter=64):
    """Fill the RGB of A == 0 texels from their valid neighbours (8-neighbour mean, repeated), so the model sees no black or white halo.
    Texels still unreached after max_iter get the mean colour of the valid ones. Returns float32 HxWx3."""
    rgb = rgba[..., :3].astype(np.float32).copy()
    valid = rgba[..., 3] > 0
    if valid.all():
        return rgb
    if not valid.any():
        return np.full_like(rgb, 128.0)
    h, w = valid.shape
    for _ in range(max_iter):
        if valid.all():
            break
        pv = np.pad(valid.astype(np.float32), 1)
        pr = np.pad(rgb * valid[..., None], ((1, 1), (1, 1), (0, 0)))
        cnt = np.zeros((h, w), np.float32)
        acc = np.zeros((h, w, 3), np.float32)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                if dy == 1 and dx == 1:
                    continue
                cnt += pv[dy:dy + h, dx:dx + w]
                acc += pr[dy:dy + h, dx:dx + w]
        fill = (~valid) & (cnt > 0)
        rgb[fill] = acc[fill] / cnt[fill][:, None]
        valid = valid | fill
    if not valid.all():
        rgb[~valid] = rgb[valid].mean(0)
    return rgb


def lanczos(ch, w, h):
    """float32 HxW (or HxWxC, per channel) -> hxw with PIL Lanczos in float mode"""
    if ch.ndim == 3:
        return np.stack([lanczos(ch[..., c], w, h) for c in range(ch.shape[2])], -1)
    if ch.shape == (h, w):
        return ch.astype(np.float32)
    return np.asarray(Image.fromarray(np.ascontiguousarray(ch, np.float32), 'F').resize((w, h), Image.LANCZOS), np.float32)


def resample_alpha(alpha, w, h, kind):
    """alpha uint8 HxW -> uint8 hxw. 'none' stays 255, 'binary' is Lanczos then cut at 128 (stays 0/255), 'soft' is Lanczos clipped."""
    if kind == 'none':
        return np.full((h, w), 255, np.uint8)
    a = lanczos(alpha.astype(np.float32), w, h)
    if kind == 'binary':
        return np.where(a >= 127.5, 255, 0).astype(np.uint8)
    return np.clip(np.round(a), 0, 255).astype(np.uint8)


def finish(rgb_f, alpha_u8):
    """float RGB (after the model and Lanczos) + final alpha -> RGBA uint8; RGB under A = 0 is kept (dilated colour compresses well)."""
    rgb = np.clip(np.round(rgb_f), 0, 255).astype(np.uint8)
    return np.dstack([rgb, alpha_u8])


def mip_chain(rgba, n):
    """n uint8 RGBA levels: RGB box-filtered in linear light (gamma 2.2), alpha plain box (no coverage remap)."""
    return dds.mips_diffuse(rgba, n, linear=True, coverage_targets=None)


def alpha_mean(alpha):
    """mean alpha 0..1: equals the covered fraction for a binary cut-out and, unlike a threshold count, is stable for soft alpha sitting near 128"""
    a = np.asarray(alpha, np.float32)
    return float(a.mean() / 255.0) if a.size else 0.0


def alpha_coverage(alpha, ref=128):
    a = np.asarray(alpha)
    return float((a >= ref).mean()) if a.size else 0.0
