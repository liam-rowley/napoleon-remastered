"""UI art at a scale factor from the J36 masters (J66): resample a 2.5x master to exactly f x the vanilla size, or Lanczos the vanilla image when there is no master (needs numpy, Pillow).

purpose: make the real f x textures the scaled layouts need (the engine tiles frame art at the texture's real size): linear-light RGB Lanczos, plain alpha (binary alpha stays binary), the vanilla container (TGA bit depth, JPG, DDS format with a full mip chain)
usage: library: from art import target_size, from_master, from_vanilla; blob, info = from_master(master_bytes, vanilla_bytes, ext, 2.0)   (driven by uiscale/napoleon/cli.py)
when: `wsc uiscale build` in the art_build Python; host tests in tests/test_uiscale.py
not-a-verb: a library used by uiscale/napoleon/cli.py, not a registry operation

The resample code is the upscaler's (upscale/core/resample.py, dds.py, imageio.py): one place for the image maths. Deterministic for a given
numpy/Pillow build (the J53 rule: build once on the PC, ship those bytes).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'upscale', 'core'))
import dds  # noqa: E402
import imageio  # noqa: E402
import resample  # noqa: E402

GAMMA = 2.2


def target_size(w, h, f):
    """the f x size of a vanilla texture: ceil, the same rule as the image defs (uiscale/core/scale.py tex_size)"""
    return max(1, int(math.ceil(w * f - 1e-9))), max(1, int(math.ceil(h * f - 1e-9)))


def _linear_lanczos(rgb_u8_or_f, w, h):
    lin = np.power(np.clip(np.asarray(rgb_u8_or_f, np.float32) / 255.0, 0, 1), GAMMA)
    out = resample.lanczos(lin, w, h)
    return np.power(np.clip(out, 0, 1), 1 / GAMMA) * 255.0


def resize_rgba(rgba, w, h, alpha_kind):
    """uint8 RGBA -> uint8 RGBA at w x h: RGB dilated under A = 0 then Lanczos in linear light; alpha by its kind (none/binary/soft)"""
    if rgba.shape[:2] == (h, w):
        return rgba
    kind = alpha_kind
    rgb = resample.dilate_rgb(rgba) if kind != 'none' and rgba[..., 3].any() else rgba[..., :3].astype(np.float32)
    rgb_t = _linear_lanczos(rgb, w, h)
    alpha = resample.resample_alpha(rgba[..., 3], w, h, kind)
    return resample.finish(rgb_t, alpha)


def resize_bgra(body, w, h, tw, th):
    """the pixels of an uncompressed 32-bit TGA (a template's embedded texture, J67) at tw x th, by resize_rgba: bytes in, bytes out, row order kept"""
    bgra = np.frombuffer(body, np.uint8).reshape(h, w, 4)
    rgba = bgra[..., [2, 1, 0, 3]]
    out = resize_rgba(rgba, tw, th, imageio.Source(rgba, 'tga').alpha_kind())
    return np.ascontiguousarray(out[..., [2, 1, 0, 3]]).tobytes()


def encode_like(out, src):
    """RGBA at the target size -> bytes in the vanilla source's container; (blob, info)"""
    th, tw = out.shape[:2]
    if src.kind == 'dds':
        n = dds.full_mips(tw, th)
        levels = resample.mip_chain(out, n)
        data = dds.encode_chain(levels, src.fmt, 'python')
        tmpl = src.header
        try:
            dds.make_header(src.fmt, tw, th, n, tmpl)
        except ValueError:
            tmpl = None
        return dds.make_header(src.fmt, tw, th, n, tmpl) + b''.join(data), {'fmt': src.fmt, 'mips': n}
    if src.kind == 'tga':
        return imageio.encode_tga(out, with_alpha=(src.fmt != 'bgr8')), {'fmt': src.fmt, 'mips': 1}
    if src.kind == 'png':
        return imageio.encode_png(out), {'fmt': 'rgba8', 'mips': 1}
    return imageio.encode_jpg(out, 95), {'fmt': 'ycc8', 'mips': 1}


def from_master(master, vanilla, ext, f):
    """J36 master bytes (2.5x, same container) + vanilla bytes -> (f x bytes, info). The alpha kind is the vanilla image's."""
    van = imageio.load(vanilla, ext)
    mas = imageio.load(master, ext)
    tw, th = target_size(van.size[0], van.size[1], f)
    out = resize_rgba(mas.rgba, tw, th, van.alpha_kind())
    blob, info = encode_like(out, van)
    info.update(w=tw, h=th, method='j36_master_resampled', master=f'{mas.size[0]}x{mas.size[1]}')
    return blob, info


def from_vanilla(vanilla, ext, f):
    """vanilla bytes -> (f x bytes, info) by Lanczos (linear-light RGB, alpha by kind): the assets with no J36 master"""
    van = imageio.load(vanilla, ext)
    tw, th = target_size(van.size[0], van.size[1], f)
    out = resize_rgba(van.rgba, tw, th, van.alpha_kind())
    blob, info = encode_like(out, van)
    info.update(w=tw, h=th, method='lanczos_from_vanilla')
    return blob, info
