"""Read a vanilla UI image (DDS, TGA, JPG, PNG) into RGBA and write the upscaled one in the same format family (needs numpy, Pillow).

purpose: decode DDS/TGA/JPG/PNG sources to RGBA uint8 with their container facts (vanilla DDS header, TGA bit depth) and write TGA and JPG outputs deterministically
usage: library (upscale/core)
when: batch.py loading a source or writing a non-DDS output; tests
not-a-verb: a library used by upscale/core/batch.py, not a registry operation
"""
import io
import struct

import numpy as np

import dds


class Source:
    """rgba: HxWx4 uint8; kind: dds|tga|jpg|png; fmt: DXT1|DXT3|DXT5|A8R8G8B8 for dds, 'bgr8'/'bgra8' for tga;
    header: the vanilla 128-byte DDS header; mips: vanilla mip count."""
    def __init__(self, rgba, kind, fmt='', header=None, mips=1):
        self.rgba, self.kind, self.fmt, self.header, self.mips = rgba, kind, fmt, header, mips

    @property
    def size(self):
        return self.rgba.shape[1], self.rgba.shape[0]

    def alpha_kind(self):
        """'none' (all 255), 'binary' (only 0 and 255) or 'soft'"""
        a = self.rgba[..., 3]
        if a.min() == 255:
            return 'none'
        return 'binary' if np.isin(np.unique(a), (0, 255)).all() else 'soft'


def _tga_bits(b):
    return b[16] if len(b) > 17 else 0


def load(data, ext):
    ext = ext.lower().lstrip('.')
    if ext == 'dds':
        d = dds.read_dds(data)
        fmt = 'A8R8G8B8' if d.fmt == 'X8R8G8B8' else d.fmt
        return Source(d.decode(0), 'dds', fmt, d.header, d.mips)
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    kind = 'tga' if ext == 'tga' else ('png' if ext == 'png' else 'jpg')
    bits = _tga_bits(data) if kind == 'tga' else 0
    rgba = np.asarray(im.convert('RGBA')).copy()
    if kind == 'tga' and bits == 24:
        rgba[..., 3] = 255
    return Source(rgba, kind, 'bgr8' if bits == 24 else 'bgra8')


def encode_tga(rgba, with_alpha=True):
    """Uncompressed top-left-origin TGA (bits 24 or 32). Deterministic: no id field, no footer."""
    h, w = rgba.shape[:2]
    bits = 32 if with_alpha else 24
    hd = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, w, h, bits, 0x28 if with_alpha else 0x20)
    px = rgba[..., [2, 1, 0, 3]] if with_alpha else rgba[..., [2, 1, 0]]
    return hd + np.ascontiguousarray(px).tobytes()


def encode_jpg(rgba, quality=95):
    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(rgba[..., :3]), 'RGB').save(b, 'JPEG', quality=quality, subsampling=0, optimize=False)
    return b.getvalue()


def encode_png(rgba):
    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(rgba), 'RGBA').save(b, 'PNG', compress_level=9)
    return b.getvalue()
