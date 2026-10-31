"""DDS read and write with mip chains for the UI art upscaler (J36).

purpose: read and write legacy-header DDS (DXT1, DXT3, DXT5, A8R8G8B8) keeping the vanilla header; mip chains (linear-light RGB box, plain alpha box); encoders python, quicktex, texconv
usage: library (upscale/core); python3 upscale/core/dds.py info <file.dds> ...
when: reading a vanilla DDS, building an upscaled chain, or checking one (wsc upscale verify)
not-a-verb: a library used by upscale/core/batch.py, not a registry operation

Ported from empire-remastered art_mod/tools/dds.py (read-only evidence); the normal-map code is dropped and DXT3 (Napoleon: 85 UI files) is added.
The header is the vanilla file's byte for byte except height, width, pitch/linear size and mip count (dwDepth forced to 0).
"""
import hashlib, os, shutil, struct, subprocess, sys, tempfile

import numpy as np
import numpy as np

DDSD_CAPS, DDSD_HEIGHT, DDSD_WIDTH, DDSD_PITCH = 0x1, 0x2, 0x4, 0x8
DDSD_PIXELFORMAT, DDSD_MIPMAPCOUNT, DDSD_LINEARSIZE, DDSD_DEPTH = 0x1000, 0x20000, 0x80000, 0x800000
DDPF_ALPHAPIXELS, DDPF_FOURCC, DDPF_RGB = 0x1, 0x4, 0x40
DDSCAPS_COMPLEX, DDSCAPS_TEXTURE, DDSCAPS_MIPMAP = 0x8, 0x1000, 0x400000

BLOCK = {'DXT1': 8, 'DXT3': 16, 'DXT5': 16}
FORMATS = ('DXT1', 'DXT3', 'DXT5', 'A8R8G8B8', 'R8G8B8')


# ================================================================================================ geometry
def level_dims(w, h, k):
    return max(1, w >> k), max(1, h >> k)


def level_size(fmt, w, h):
    if fmt in BLOCK:
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * BLOCK[fmt]
    if fmt == 'A8R8G8B8':
        return w * h * 4
    if fmt == 'R8G8B8':
        return w * h * 3
    raise ValueError('unsupported format %s' % fmt)


def chain_size(fmt, w, h, mips):
    return sum(level_size(fmt, *level_dims(w, h, k)) for k in range(mips))


def full_mips(w, h):
    """levels down to 1x1"""
    n = 1
    while w > 1 or h > 1:
        w, h = max(1, w >> 1), max(1, h >> 1)
        n += 1
    return n


# ================================================================================================ header
def parse_header(b):
    if len(b) < 128 or b[:4] != b'DDS ':
        raise ValueError('not a DDS file')
    size, flags, h, w, pitch, depth, mips = struct.unpack_from('<7I', b, 4)
    pfsize, pfflags, fourcc, bits, rm, gm, bm, am = struct.unpack_from('<II4s5I', b, 76)
    caps = struct.unpack_from('<4I', b, 108)
    if pfflags & DDPF_FOURCC:
        fmt = fourcc.decode('latin1')
        if fmt == 'DX10':
            raise ValueError('DX10 header not supported')
    elif pfflags & DDPF_RGB and bits == 32 and (rm, gm, bm) == (0xFF0000, 0xFF00, 0xFF):
        fmt = 'A8R8G8B8' if (pfflags & DDPF_ALPHAPIXELS and am == 0xFF000000) else 'X8R8G8B8'
    elif pfflags & DDPF_RGB and bits == 24 and (rm, gm, bm) == (0xFF0000, 0xFF00, 0xFF):
        fmt = 'R8G8B8'
    else:
        fmt = 'RGB%d_%x_%x_%x_%x' % (bits, rm, gm, bm, am)
    return {'flags': flags, 'height': h, 'width': w, 'pitch': pitch, 'depth': depth,
            'mips': mips if (flags & DDSD_MIPMAPCOUNT and mips) else 1, 'mips_field': mips,
            'pf_flags': pfflags, 'fmt': fmt, 'caps': caps}


def make_header(fmt, w, h, mips, template=None):
    """128-byte header. With a template (the vanilla file's header): identical except height, width, pitch/linear size,
    mip count, and dwDepth = 0. The pitch field stays 0 when the template's is 0."""
    if template is not None:
        b = bytearray(template[:128])
        t = parse_header(bytes(b))
        if t['fmt'] != fmt:
            raise ValueError('template format %s != %s' % (t['fmt'], fmt))
        if t['pitch'] == 0:
            pitch = 0
        elif fmt in BLOCK:
            pitch = level_size(fmt, w, h)
        else:
            pitch = w * (3 if fmt == 'R8G8B8' else 4)
        struct.pack_into('<5I', b, 8, t['flags'], h, w, pitch, 0)
        if t['flags'] & DDSD_MIPMAPCOUNT or mips > 1:
            struct.pack_into('<I', b, 28, mips)
        if mips > 1 and not (t['flags'] & DDSD_MIPMAPCOUNT):
            struct.pack_into('<I', b, 8, t['flags'] | DDSD_MIPMAPCOUNT)
            struct.pack_into('<I', b, 108, t['caps'][0] | DDSCAPS_COMPLEX | DDSCAPS_MIPMAP)
        return bytes(b)
    b = bytearray(128)
    b[:4] = b'DDS '
    caps = DDSCAPS_TEXTURE | ((DDSCAPS_COMPLEX | DDSCAPS_MIPMAP) if mips > 1 else 0)
    if fmt in BLOCK:
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_LINEARSIZE | (DDSD_MIPMAPCOUNT if mips > 1 else 0)
        struct.pack_into('<7I', b, 4, 124, flags, h, w, level_size(fmt, w, h), 0, mips if mips > 1 else 0)
        struct.pack_into('<II4s5I', b, 76, 32, DDPF_FOURCC, fmt.encode('latin1'), 0, 0, 0, 0, 0)
    elif fmt == 'A8R8G8B8':
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_PITCH | (DDSD_MIPMAPCOUNT if mips > 1 else 0)
        struct.pack_into('<7I', b, 4, 124, flags, h, w, w * 4, 0, mips if mips > 1 else 0)
        struct.pack_into('<II4s5I', b, 76, 32, DDPF_RGB | DDPF_ALPHAPIXELS, b'\0\0\0\0', 32,
                         0xFF0000, 0xFF00, 0xFF, 0xFF000000)
    elif fmt == 'R8G8B8':
        flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT | DDSD_PITCH | (DDSD_MIPMAPCOUNT if mips > 1 else 0)
        struct.pack_into('<7I', b, 4, 124, flags, h, w, w * 3, 0, mips if mips > 1 else 0)
        struct.pack_into('<II4s5I', b, 76, 32, DDPF_RGB, b'\0\0\0\0', 24, 0xFF0000, 0xFF00, 0xFF, 0)
    else:
        raise ValueError('unsupported format %s' % fmt)
    struct.pack_into('<I', b, 108, caps)
    return bytes(b)


def header_diff(a, b):
    """names of the header fields (by byte range) that differ between two 128-byte headers"""
    fields = [('magic', 0, 4), ('dwSize', 4, 8), ('dwFlags', 8, 12), ('dwHeight', 12, 16), ('dwWidth', 16, 20),
              ('dwPitchOrLinearSize', 20, 24), ('dwDepth', 24, 28), ('dwMipMapCount', 28, 32), ('dwReserved1', 32, 76),
              ('ddspf', 76, 108), ('dwCaps', 108, 112), ('dwCaps2', 112, 116), ('dwCaps3_4', 116, 124),
              ('dwReserved2', 124, 128)]
    return [n for n, s, e in fields if a[s:e] != b[s:e]]


# ================================================================================================ reading / decoding
class DDS:
    def __init__(self, data):
        self.data = data
        self.header = data[:128]
        hd = parse_header(self.header)
        self.fmt, self.width, self.height, self.mips = hd['fmt'], hd['width'], hd['height'], hd['mips']
        self.hd = hd
        if self.fmt not in FORMATS and self.fmt != 'X8R8G8B8':
            raise ValueError('unsupported DDS format %s' % self.fmt)
        f = 'A8R8G8B8' if self.fmt == 'X8R8G8B8' else self.fmt
        self.levels, off = [], 128
        for k in range(self.mips):
            n = level_size(f, *level_dims(self.width, self.height, k))
            if off + n > len(data):
                raise ValueError('truncated DDS: level %d needs %d bytes at %d, file %d' % (k, n, off, len(data)))
            self.levels.append(data[off:off + n])
            off += n
        self.trailing = len(data) - off

    def dims(self, k=0):
        return level_dims(self.width, self.height, k)

    def decode(self, k=0):
        w, h = self.dims(k)
        return decode_level(self.levels[k], self.fmt, w, h)


def read_dds(src):
    if isinstance(src, (bytes, bytearray)):
        return DDS(bytes(src))
    with open(src, 'rb') as f:
        return DDS(f.read())
def _rgb565(c):
    c = c.astype(np.uint32)
    r = (c >> 11) & 31
    g = (c >> 5) & 63
    b = c & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.int32)


def _colour_palette(blk8, four_always):
    """blk8: (N, 8) uint8 colour blocks -> palette (N, 4, 4) int RGBA, indices (N, 16)"""
    c0 = blk8[:, 0].astype(np.uint32) | (blk8[:, 1].astype(np.uint32) << 8)
    c1 = blk8[:, 2].astype(np.uint32) | (blk8[:, 3].astype(np.uint32) << 8)
    idx = (blk8[:, 4].astype(np.uint32) | (blk8[:, 5].astype(np.uint32) << 8) |
           (blk8[:, 6].astype(np.uint32) << 16) | (blk8[:, 7].astype(np.uint32) << 24))
    p0, p1 = _rgb565(c0), _rgb565(c1)
    n = blk8.shape[0]
    pal = np.zeros((n, 4, 4), np.int32)
    pal[:, 0, :3], pal[:, 1, :3] = p0, p1
    pal[:, :, 3] = 255
    four = np.ones(n, bool) if four_always else (c0 > c1)
    p2_4 = (2 * p0 + p1 + 1) // 3
    p3_4 = (p0 + 2 * p1 + 1) // 3
    p2_3 = (p0 + p1 + 1) // 2
    pal[:, 2, :3] = np.where(four[:, None], p2_4, p2_3)
    pal[:, 3, :3] = np.where(four[:, None], p3_4, 0)
    pal[:, 3, 3] = np.where(four, 255, 0)
    sh = (2 * np.arange(16, dtype=np.uint32))[None, :]
    ind = (idx[:, None] >> sh) & 3
    return pal, ind


def _alpha_palette(blk8):
    a0 = blk8[:, 0].astype(np.int32)
    a1 = blk8[:, 1].astype(np.int32)
    bits = np.zeros(blk8.shape[0], np.uint64)
    for i in range(6):
        bits |= blk8[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    sh = (3 * np.arange(16, dtype=np.uint64))[None, :]
    ind = ((bits[:, None] >> sh) & np.uint64(7)).astype(np.int64)
    n = blk8.shape[0]
    pal = np.zeros((n, 8), np.int32)
    pal[:, 0], pal[:, 1] = a0, a1
    eight = a0 > a1
    for i in range(1, 7):   # 8-value mode: (7-i)*a0 + i*a1 over 7 at palette slot i+1
        pal[:, i + 1] = np.where(eight, ((7 - i) * a0 + i * a1 + 3) // 7, pal[:, i + 1])
    for i in range(1, 5):   # 6-value mode
        pal[:, i + 1] = np.where(eight, pal[:, i + 1], ((5 - i) * a0 + i * a1 + 2) // 5)
    pal[:, 6] = np.where(eight, pal[:, 6], 0)
    pal[:, 7] = np.where(eight, pal[:, 7], 255)
    return pal, ind


def _blocks_to_image(px, w, h):
    """px (N, 16, C) in block-row-major order -> (h, w, C)"""
    bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    c = px.shape[-1]
    img = px.reshape(bh, bw, 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(bh * 4, bw * 4, c)
    return img[:h, :w]


def decode_level(data, fmt, w, h):
    if fmt == 'R8G8B8':
        a = np.frombuffer(data, np.uint8, w * h * 3).reshape(h, w, 3)
        return np.dstack([a[..., [2, 1, 0]], np.full((h, w), 255, np.uint8)])
    if fmt in ('A8R8G8B8', 'X8R8G8B8'):
        a = np.frombuffer(data, np.uint8, w * h * 4).reshape(h, w, 4)
        out = a[..., [2, 1, 0, 3]].copy()
        if fmt == 'X8R8G8B8':
            out[..., 3] = 255
        return out
    if fmt == 'DXT1':
        blk = np.frombuffer(data, np.uint8).reshape(-1, 8)
        pal, ind = _colour_palette(blk, False)
        px = np.take_along_axis(pal, ind[:, :, None].astype(np.int64).repeat(4, 2), 1)
        return _blocks_to_image(px.astype(np.uint8), w, h)
    if fmt == 'DXT3':
        blk = np.frombuffer(data, np.uint8).reshape(-1, 16)
        pal, ind = _colour_palette(blk[:, 8:], True)
        px = np.take_along_axis(pal, ind[:, :, None].astype(np.int64).repeat(4, 2), 1)
        al = np.stack([blk[:, :8] & 15, blk[:, :8] >> 4], 2).reshape(-1, 16).astype(np.int32)
        px[:, :, 3] = al * 17
        return _blocks_to_image(px.astype(np.uint8), w, h)
    if fmt == 'DXT5':
        blk = np.frombuffer(data, np.uint8).reshape(-1, 16)
        apal, aind = _alpha_palette(blk[:, :8])
        pal, ind = _colour_palette(blk[:, 8:], True)
        px = np.take_along_axis(pal, ind[:, :, None].astype(np.int64).repeat(4, 2), 1)
        px[:, :, 3] = np.take_along_axis(apal, aind, 1)
        return _blocks_to_image(px.astype(np.uint8), w, h)
    raise ValueError('cannot decode %s' % fmt)


# ================================================================================================ python encoder
def _image_to_blocks(a):
    """(h, w, C) -> (N, 16, C) in block-row-major order; edges replicated to a multiple of 4"""
    h, w, c = a.shape
    H, W = max(4, (h + 3) // 4 * 4), max(4, (w + 3) // 4 * 4)
    if (H, W) != (h, w):
        a = np.pad(a, ((0, H - h), (0, W - w), (0, 0)), mode='edge')
    return a.reshape(H // 4, 4, W // 4, 4, c).transpose(0, 2, 1, 3, 4).reshape(-1, 16, c)


def _q565(rgb):
    """float RGB 0..255 (N,3) -> (packed u16 (N,), dequantised int RGB (N,3))"""
    r = np.clip(np.round(rgb[:, 0] * 31 / 255), 0, 31).astype(np.uint32)
    g = np.clip(np.round(rgb[:, 1] * 63 / 255), 0, 63).astype(np.uint32)
    b = np.clip(np.round(rgb[:, 2] * 31 / 255), 0, 31).astype(np.uint32)
    c = (r << 11) | (g << 5) | b
    return c, _rgb565(c)


def _encode_colour(px, opaque, punch):
    """px (N,16,3) float, opaque (N,16) bool. punch: BC1 with transparency -> 3-colour mode where a block has a
    transparent texel. Returns (N, 8) uint8 colour blocks."""
    n = px.shape[0]
    w = opaque.astype(np.float32)
    cnt = np.maximum(w.sum(1), 1)[:, None]
    mean = (px * w[..., None]).sum(1) / cnt
    d = (px - mean[:, None]) * w[..., None]
    cov = np.einsum('nki,nkj->nij', d, d)
    v = np.ones((n, 3), np.float32) / np.sqrt(3)
    for _ in range(8):
        v = np.einsum('nij,nj->ni', cov, v)
        v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-12)
    t = ((px - mean[:, None]) * v[:, None]).sum(-1)
    big = 1e9
    tmin = np.where(opaque, t, big).min(1)
    tmax = np.where(opaque, t, -big).max(1)
    tmin = np.where(tmin > tmax, 0, tmin)
    tmax = np.where(tmin > tmax, 0, tmax)
    e0 = mean + v * tmax[:, None]
    e1 = mean + v * tmin[:, None]
    three = np.zeros(n, bool) if not punch else (~opaque).any(1)

    def fit(e0, e1):
        c0, p0 = _q565(np.clip(e0, 0, 255))
        c1, p1 = _q565(np.clip(e1, 0, 255))
        # 4-colour blocks need c0 > c1, 3-colour blocks c0 <= c1: order the endpoints, palette follows the order
        swap4 = ~three & (c0 < c1)
        swap3 = three & (c0 > c1)
        sw = swap4 | swap3
        c0, c1 = np.where(sw, c1, c0), np.where(sw, c0, c1)
        p0, p1 = np.where(sw[:, None], p1, p0), np.where(sw[:, None], p0, p1)
        pal = np.zeros((n, 4, 3), np.float32)
        pal[:, 0], pal[:, 1] = p0, p1
        pal[:, 2] = np.where(three[:, None], (p0 + p1 + 1) // 2, (2 * p0 + p1 + 1) // 3)
        pal[:, 3] = np.where(three[:, None], 0, (p0 + 2 * p1 + 1) // 3)
        err = ((px[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)       # (N,16,4)
        err[:, :, 3] = np.where(three[:, None], big, err[:, :, 3])       # slot 3 = transparent in 3-colour mode
        ind = err.argmin(-1)
        ind = np.where(three[:, None] & ~opaque, 3, ind)
        # c0 == c1 in a "4-colour" block decodes as 3-colour: only index 0/1 are safe then
        same = (c0 == c1) & ~three
        ind = np.where(same[:, None], 0, ind)
        return c0, c1, ind, (err.min(-1) * opaque).sum(1)

    c0, c1, ind, e = fit(e0, e1)
    # one least-squares pass on the endpoints given the indices (4-colour weights; 3-colour: 0, 1, 1/2)
    wt4 = np.array([1.0, 0.0, 2 / 3, 1 / 3], np.float32)
    wt3 = np.array([1.0, 0.0, 0.5, 0.0], np.float32)
    # indices refer to the (possibly swapped) endpoint order; recover which endpoint is c0
    a = np.where(three[:, None], wt3[ind], wt4[ind]) * w
    b = (np.where(three[:, None], np.array([0, 1, 0.5, 0], np.float32)[ind], 1 - wt4[ind])) * w
    aa, bb, ab = (a * a).sum(1), (b * b).sum(1), (a * b).sum(1)
    det = aa * bb - ab * ab
    ok = np.abs(det) > 1e-6
    ax = (a[..., None] * px).sum(1)
    bx = (b[..., None] * px).sum(1)
    det_s = np.where(ok, det, 1)[:, None]
    n0 = (bb[:, None] * ax - ab[:, None] * bx) / det_s
    n1 = (aa[:, None] * bx - ab[:, None] * ax) / det_s
    c0b, c1b, indb, eb = fit(np.where(ok[:, None], n0, e0), np.where(ok[:, None], n1, e1))
    better = eb < e
    c0, c1 = np.where(better, c0b, c0), np.where(better, c1b, c1)
    ind = np.where(better[:, None], indb, ind)
    out = np.zeros((n, 8), np.uint8)
    out[:, 0], out[:, 1] = c0 & 255, c0 >> 8
    out[:, 2], out[:, 3] = c1 & 255, c1 >> 8
    bits = (ind.astype(np.uint32) << (2 * np.arange(16, dtype=np.uint32))[None, :]).sum(1, dtype=np.uint64)
    for i in range(4):
        out[:, 4 + i] = (bits >> np.uint64(8 * i)) & np.uint64(255)
    return out


def _encode_alpha(al):
    """al (N,16) float 0..255 -> (N, 8) uint8 BC3 alpha blocks; 8-value mode with exact min/max endpoints, so 0 and
    255 survive wherever they are a block's extremes (masks)."""
    a = np.clip(np.round(al), 0, 255).astype(np.int32)
    a0, a1 = a.max(1), a.min(1)
    n = a.shape[0]
    pal = np.zeros((n, 8), np.int32)
    pal[:, 0], pal[:, 1] = a0, a1
    for i in range(1, 7):
        pal[:, i + 1] = ((7 - i) * a0 + i * a1 + 3) // 7
    ind = np.abs(a[:, :, None] - pal[:, None, :]).argmin(-1).astype(np.uint64)
    ind = np.where((a0 == a1)[:, None], 0, ind).astype(np.uint64)
    bits = (ind << (3 * np.arange(16, dtype=np.uint64))[None, :]).sum(1, dtype=np.uint64)
    out = np.zeros((n, 8), np.uint8)
    out[:, 0], out[:, 1] = a0, a1
    for i in range(6):
        out[:, 2 + i] = (bits >> np.uint64(8 * i)) & np.uint64(255)
    return out


def encode_python(rgba, fmt, alpha_threshold=128):
    rgba = np.asarray(rgba)
    if fmt == 'A8R8G8B8':
        return np.ascontiguousarray(rgba[..., [2, 1, 0, 3]]).astype(np.uint8).tobytes()
    if fmt == 'R8G8B8':
        return np.ascontiguousarray(rgba[..., [2, 1, 0]]).astype(np.uint8).tobytes()
    blk = _image_to_blocks(rgba.astype(np.float32))
    if fmt == 'DXT1':
        opaque = blk[:, :, 3] >= alpha_threshold
        punch = bool((~opaque).any())
        return _encode_colour(blk[:, :, :3], opaque, punch).tobytes()
    if fmt == 'DXT3':
        c = _encode_colour(blk[:, :, :3], np.ones(blk.shape[:2], bool), False)
        q = np.clip(np.round(blk[:, :, 3] / 17.0), 0, 15).astype(np.uint8)
        a = (q[:, 0::2] | (q[:, 1::2] << 4)).astype(np.uint8)
        return np.concatenate([a, c], 1).tobytes()
    if fmt == 'DXT5':
        c = _encode_colour(blk[:, :, :3], np.ones(blk.shape[:2], bool), False)
        a = _encode_alpha(blk[:, :, 3])
        return np.concatenate([a, c], 1).tobytes()
    raise ValueError(fmt)


# ================================================================================================ quicktex / texconv
def encode_quicktex(rgba, fmt, level=10):
    from quicktex import RawTexture
    rgba = np.ascontiguousarray(np.asarray(rgba, np.uint8))
    h, w = rgba.shape[:2]
    H, W = max(4, (h + 3) // 4 * 4), max(4, (w + 3) // 4 * 4)
    if (H, W) != (h, w):
        rgba = np.ascontiguousarray(np.pad(rgba, ((0, H - h), (0, W - w), (0, 0)), mode='edge'))
    raw = RawTexture.frombytes(rgba.tobytes(), W, H)
    if fmt == 'DXT5':
        import quicktex.s3tc.bc3 as bc3
        return bytes(bc3.BC3Encoder(level).encode(raw).tobytes())
    if fmt == 'DXT3':
        raise ValueError('quicktex has no BC2 encoder; use texconv or python')
    if fmt == 'DXT1':
        if (rgba[..., 3] < 128).any():
            raise ValueError('quicktex BC1 path does not handle punch-through alpha; use texconv or python')
        import quicktex.s3tc.bc1 as bc1
        return bytes(bc1.BC1Encoder(level).encode(raw).tobytes())
    raise ValueError(fmt)


def _wine_prefix():
    if sys.platform.startswith('win'):
        return []
    w = shutil.which('wine') or shutil.which('wine64')
    if not w:
        raise RuntimeError('texconv needs Windows or wine')
    return [w]


def encode_texconv(levels, fmt, exe, uniform=False, workdir=None, extra=()):
    """Compress our own mip chain with texconv. levels: list of HxWx4 RGBA uint8 (level 0 first). Returns bytes per level.
    The chain is handed over as an A8R8G8B8 DDS; texconv keeps supplied mips (verified in step 4)."""
    if fmt in ('A8R8G8B8', 'R8G8B8'):
        return [encode_python(l, fmt) for l in levels]
    h, w = levels[0].shape[:2]
    tf = {'DXT1': 'BC1_UNORM', 'DXT3': 'BC2_UNORM', 'DXT5': 'BC3_UNORM'}[fmt]
    own = workdir is None
    d = tempfile.mkdtemp(prefix='tcv_') if own else workdir
    os.makedirs(os.path.join(d, 'o'), exist_ok=True)
    try:
        src = os.path.join(d, 'in.dds')
        with open(src, 'wb') as f:
            f.write(make_header('A8R8G8B8', w, h, len(levels)))
            for l in levels:
                f.write(encode_python(l, 'A8R8G8B8'))
        # -m n: with a 1-level input texconv would otherwise generate a chain; with n supplied levels it keeps ours
        cmd = _wine_prefix() + [os.path.abspath(exe), '-nologo', '-y', '-f', tf, '-m', str(len(levels)), '-o', 'o']
        if uniform:
            cmd += ['-bc', 'u']
        cmd += list(extra) + ['in.dds']
        env = dict(os.environ, WINEDEBUG='-all')
        # cwd + relative names: wine's texconv reads a leading '/' as a switch (step 3 finding)
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=d, env=env, timeout=1800)
        out = os.path.join(d, 'o', 'in.dds')
        if r.returncode != 0 or not os.path.exists(out):
            raise RuntimeError('texconv failed (%s): %s %s' % (' '.join(cmd), r.stdout[-800:], r.stderr[-800:]))
        dd = read_dds(out)
        if dd.fmt != fmt or (dd.width, dd.height) != (w, h) or dd.mips != len(levels):
            raise RuntimeError('texconv output %s %dx%d mips %d, expected %s %dx%d mips %d' % (
                dd.fmt, dd.width, dd.height, dd.mips, fmt, w, h, len(levels)))
        return list(dd.levels)
    finally:
        if own:
            shutil.rmtree(d, ignore_errors=True)
        else:
            for p in (os.path.join(d, 'in.dds'), os.path.join(d, 'o', 'in.dds')):
                try:
                    os.remove(p)
                except OSError:
                    pass


def encode_chain(levels, fmt, encoder='python', texconv=None, uniform=False, quicktex_level=10, workdir=None):
    """levels: list of RGBA uint8 arrays -> list of bytes. encoder: python | quicktex | texconv"""
    if fmt in ('A8R8G8B8', 'R8G8B8'):
        return [encode_python(l, fmt) for l in levels]
    if encoder == 'texconv':
        if not texconv:
            raise ValueError('texconv encoder needs the texconv.exe path')
        return encode_texconv(levels, fmt, texconv, uniform=uniform, workdir=workdir)
    if encoder == 'quicktex':
        return [encode_quicktex(l, fmt, quicktex_level) for l in levels]
    if encoder == 'python':
        return [encode_python(l, fmt) for l in levels]
    raise ValueError('unknown encoder %s' % encoder)


# ================================================================================================ writing
def write_dds(path, fmt, w, h, level_data, template=None):
    """Write header + levels atomically (path.tmp, then rename). Returns (sha256, bytes)."""
    mips = len(level_data)
    for k, d in enumerate(level_data):
        need = level_size(fmt, *level_dims(w, h, k))
        if len(d) != need:
            raise ValueError('level %d: %d bytes, expected %d' % (k, len(d), need))
    blob = make_header(fmt, w, h, mips, template) + b''.join(level_data)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(blob)
    os.replace(tmp, path)
    return hashlib.sha256(blob).hexdigest(), len(blob)


# ================================================================================================ mips (guide 3.6)
def resize_box(ch, w, h):
    """float32 HxW -> hxw, area-weighted (exact 2x2 mean for even sizes)"""
    from PIL import Image
    return np.asarray(Image.fromarray(np.ascontiguousarray(ch, np.float32), 'F').resize((w, h), Image.BOX))


def _down(a, w, h):
    if a.ndim == 2:
        return resize_box(a, w, h)
    return np.stack([resize_box(a[..., c], w, h) for c in range(a.shape[2])], -1)


def to_u8(a):
    return np.clip(np.round(a), 0, 255).astype(np.uint8)


def coverage(alpha, ref):
    """fraction of texels that pass an alpha test 'alpha >= ref' (ref in 0..255 levels)"""
    a = np.asarray(alpha)
    return float((a >= ref).mean()) if a.size else 0.0


def _value_for_coverage(a, cov):
    """the alpha value v such that fraction(a >= v) ~= cov"""
    flat = a.reshape(-1)
    n = flat.size
    k = int(round(cov * n))
    if k <= 0:
        return float(flat.max()) + 1e-3
    if k >= n:
        return float(flat.min())
    return float(np.partition(flat, n - k)[n - k])


def coverage_remap(a, targets):
    """Monotone piecewise-linear remap of a float alpha level (0..255) so that coverage(a', ref) == target for each
    (ref, target) in targets (refs ascending). Knots (0,0) .. (v_i, ref_i) .. (255,255)."""
    # knots from the highest ref down: a lower ref whose value is not below the higher one's (equal coverage at both,
    # e.g. 1.0) is dropped, so the higher (stricter) ref keeps its exact coverage
    knots = []
    for ref, cov in sorted(targets, reverse=True):
        if not 0 < ref < 255:
            continue
        v = min(max(_value_for_coverage(a, cov), 1e-3), 255.0 - 1e-3)
        if knots and v >= knots[-1][0] - 1e-3:
            continue
        knots.append((v, float(ref)))
    xs, ys = [0.0], [0.0]
    for v, ref in reversed(knots):
        xs.append(v)
        ys.append(ref)
    xs.append(255.0)
    ys.append(255.0)
    if len(xs) == 2:
        return a
    return np.interp(a, xs, ys).astype(np.float32)


def mips_diffuse(rgba, n, linear=True, coverage_targets=None, gamma=2.2, alpha_floor=0):
    """rgba float32 or uint8 HxWx4 (level 0) -> list of n uint8 RGBA levels.
    RGB averaged in linear light; alpha box-filtered, then for level k >= 1 remapped to coverage_targets[k] (a list of
    (ref, coverage) pairs per level, or None for no correction). alpha_floor: on remapped levels, texels that pass the
    lowest ref but sit below alpha_floor are lifted to it (BC3's 8-step alpha palette would round them to 0)."""
    a = np.asarray(rgba, np.float32)
    h, w = a.shape[:2]
    out = [to_u8(a)]
    lin = (np.clip(a[..., :3], 0, 255) / 255.0) ** gamma if linear else a[..., :3]
    al = a[..., 3]
    for k in range(1, n):
        lw, lh = level_dims(w, h, k)
        lin = _down(lin, lw, lh)
        al = _down(al, lw, lh)
        rgb = (np.clip(lin, 0, 1) ** (1.0 / gamma)) * 255.0 if linear else lin
        al_k = al
        if coverage_targets is not None and coverage_targets[k]:
            al_k = coverage_remap(al, coverage_targets[k])
            if alpha_floor:
                lo = min(r for r, _ in coverage_targets[k])
                al_k = np.where((al_k >= lo - 0.5) & (al_k < alpha_floor), alpha_floor, al_k)
        out.append(to_u8(np.dstack([rgb, al_k])))
    return out


def alpha_chain(alpha0, n):
    """the box-filtered float alpha of every level, exactly as mips_diffuse computes it before any remap (ranking input
    for coverage_place)"""
    al = np.asarray(alpha0, np.float32)
    h, w = al.shape
    out = [al]
    for k in range(1, n):
        al = _down(al, *level_dims(w, h, k))
        out.append(al)
    return out


def coverage_place(alpha, rank_by, targets, margin, floor=0):
    """Exact alpha-test coverage on one level, with a guard band against encoder error (tiny levels, where one texel is
    1.5-6 % and a statistical re-aim cannot land). For each (ref, cov), the round(cov * n) texels with the highest
    rank_by value (the pre-remap box-filtered alpha; ties broken by position) pass: they are lifted to >= ref + margin
    (and >= floor), every other texel is held <= ref - margin (>= 0). Texels already outside the band keep their value.
    alpha: the level's current alpha (uint8 or float), returns float32 of the same shape."""
    a = np.asarray(alpha, np.float32).ravel().copy()
    n = a.size
    order = np.argsort(-np.asarray(rank_by, np.float32).ravel(), kind='stable')
    rank = np.empty(n, np.int64)
    rank[order] = np.arange(n)
    start, upper = 0, 255.0
    for ref, cov in sorted(targets, reverse=True):          # highest ref first; counts must not shrink downwards
        cnt = max(start, min(n, int(round(cov * n))))
        sel = (rank >= start) & (rank < cnt)
        lo = min(max(ref + margin, floor), upper)
        a[sel] = np.clip(a[sel], lo, upper)
        upper = max(0.0, ref - margin)
        start = cnt
    rest = rank >= start
    a[rest] = np.minimum(a[rest], upper)
    return a.reshape(np.shape(alpha))


def mips_box(rgba, n):
    a = np.asarray(rgba, np.float32)
    h, w = a.shape[:2]
    out = [to_u8(a)]
    for k in range(1, n):
        a = _down(a, *level_dims(w, h, k))
        out.append(to_u8(a))
    return out


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


if __name__ == '__main__':
    # tiny CLI: python dds.py info <file.dds> [...]
    if len(sys.argv) >= 3 and sys.argv[1] == 'info':
        for p in sys.argv[2:]:
            d = read_dds(p)
            print('%s %s %dx%d mips %d bytes %d trailing %d flags %#x caps %#x' % (
                p, d.fmt, d.width, d.height, d.mips, len(d.data), d.trailing, d.hd['flags'], d.hd['caps'][0]))
    else:
        print(__doc__)