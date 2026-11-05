"""TTF -> Warscape bitmap font (.cuf, CUF0) encoder and the Lora 2x set recipe (game-agnostic; Empire and Napoleon share the format).

purpose: re-render a vanilla .cuf from a TrueType face (FreeType glyphs, HarfBuzz pair kerning) keeping its glyph order and header, plus the Lora 2x set recipe
usage: library: encode(face, vanilla_bytes, em, wght) -> bytes; render_set(names, reader) -> {name: (bytes, note)}   |   python uiscale/core/cuf_encode.py OUT_DIR ingame_24.cuf ... [--compare PNG] [--face TTF] [--game napoleon]
when: building the 2x UI fonts (J66: crisp text for the 2x-scaled layouts); runs in the art_build Python (freetype-py and uharfbuzz, upscale/requirements.txt; golden shas: uiscale/napoleon/font_golden.json)
not-a-verb: a build library and its one-shot CLI for the uiscale pipeline, not a registry operation

Port of empire-remastered ui_scale_mod/tools/cuf_encode.py (encoder) and build_lora_set.py (recipe, confirmed in game on Empire).
The vanilla font supplies the glyph order and cmap, the pair-table span, the header (kept: line pitch = h2 + 2, and the engine
shrinks text whose line is taller than its box) and fallback bitmaps for code points the face lacks (the U+E300.. PUA pieces).

Spacing model (Empire, verified by rendering vanilla text): a glyph's ink-cropped bitmap is drawn at (pen_x, baseline - top);
the pen then moves by pairs[L][R] when both glyphs are in the table, else by glyph.adv. So
pairs[L][R] = advance(L) + kern(L, R) - left(L) + left(R), and glyph.adv = advance - left (Empire's default `origin` mode).

Kerning comes from HarfBuzz (uharfbuzz), Empire's route (D42): encoding refuses to run without it (J79), because any other kerning
gives a different pack than the golden one (uiscale/napoleon/font_golden.json). The small GPOS reader (`Gpos`, the 'kern' and 'dist'
PairPos lookups with their variation deltas) is no longer used by encode(); it stays only as a test cross-check of HarfBuzz's pairs.
Packages: freetype-py and uharfbuzz (upscale/requirements.txt; CI: upscale/requirements-ci.txt).
"""
import argparse, hashlib, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'core', 'discovery'))
from cuf import Cuf, Glyph  # noqa: E402

DEFAULT_FACE = os.path.join(ROOT, 'uiscale', 'fonts', 'Lora-Variable.ttf')
PUA = range(0xE000, 0xF900)
# Long-form slot (Empire scale.LONGFORM_FONT = 'Frontend 24'): same glyphs as ingame_24, more line spacing (pitch = h2 + 2).
SPACED_H2 = {'frontend_24.cuf': 28}
# Sample line for the width fit of the wide-set vanilla faces (bold, tooltip, editor, console).
SAMPLE = ("Recruitment Cost Upkeep Cost Line Infantry Grand Campaign Victory Conditions Statistics Abilities "
          "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 .,:;!?()-'")
KERN_FEATURES = (b'kern', b'dist')


# ---------------------------------------------------------------------------------------------- GPOS pair kerning
class Gpos:
    """GPOS PairPos (types 2 and 9->2) of a font file, evaluated at one set of variable-font axis values.
    pair(g1, g2) -> (x_advance_1, x_placement_1, x_placement_2) in font units, deltas applied."""

    def __init__(self, data, axis_values=None, scripts=(b'latn', b'DFLT')):
        self.d = data
        self.tables = {}
        n = struct.unpack_from('>H', data, 4)[0]
        for i in range(n):
            tag, _, off, ln = struct.unpack_from('>4sIII', data, 12 + 16 * i)
            self.tables[tag] = (off, ln)
        self.coords = self._norm_coords(axis_values or {})
        self.store = self._var_store()
        self.lookups = self._lookups(scripts) if b'GPOS' in self.tables else []

    def u16(self, o): return struct.unpack_from('>H', self.d, o)[0]
    def i16(self, o): return struct.unpack_from('>h', self.d, o)[0]
    def u32(self, o): return struct.unpack_from('>I', self.d, o)[0]

    def _norm_coords(self, values):
        if b'fvar' not in self.tables:
            return []
        if b'avar' in self.tables:
            raise ValueError('avar-mapped variable fonts are not supported by this reader')
        f = self.tables[b'fvar'][0]
        axes_off, _, count, size = struct.unpack_from('>HHHH', self.d, f + 4)
        out = []
        for i in range(count):
            tag, mn, df, mx = struct.unpack_from('>4siii', self.d, f + axes_off + i * size)
            mn, df, mx = mn / 65536, df / 65536, mx / 65536
            v = min(mx, max(mn, float(values.get(tag.decode(), df))))
            n = (v - df) / (mx - df) if v > df else (v - df) / (df - mn) if v < df else 0.0
            out.append(round(n * 16384) / 16384)        # F2Dot14, as HarfBuzz quantises it
        return out

    def _var_store(self):
        if b'GDEF' not in self.tables or not self.coords:
            return None
        g = self.tables[b'GDEF'][0]
        if (self.u16(g), self.u16(g + 2)) < (1, 3) or not self.u32(g + 14):
            return None
        s = g + self.u32(g + 14)
        rl = s + self.u32(s + 2)
        axis_count, region_count = self.u16(rl), self.u16(rl + 2)
        scalars = []
        for r in range(region_count):
            sc = 1.0
            for a in range(axis_count):
                st, pk, en = (self.i16(rl + 4 + (r * axis_count + a) * 6 + 2 * k) / 16384 for k in range(3))
                c = self.coords[a] if a < len(self.coords) else 0.0
                if st > pk or pk > en or (st < 0 < en and pk != 0) or pk == 0:
                    continue
                if c < st or c > en:
                    sc = 0.0
                    break
                if c != pk:
                    sc *= (c - st) / (pk - st) if c < pk else (en - c) / (en - pk)
            scalars.append(sc)
        datas = []
        for i in range(self.u16(s + 6)):
            o = s + self.u32(s + 8 + 4 * i)
            item_count, word_count, ri_count = self.u16(o), self.u16(o + 2), self.u16(o + 4)
            longw = bool(word_count & 0x8000)
            wc = word_count & 0x7FFF
            regions = [self.u16(o + 6 + 2 * k) for k in range(ri_count)]
            wsz, nsz = (4, 2) if longw else (2, 1)
            row = wc * wsz + (ri_count - wc) * nsz
            datas.append((o + 6 + 2 * ri_count, item_count, wc, regions, wsz, nsz, row))
        return scalars, datas

    def delta(self, outer, inner):
        if not self.store:
            return 0.0
        scalars, datas = self.store
        base, count, wc, regions, wsz, nsz, row = datas[outer]
        if inner >= count:
            return 0.0
        o, tot = base + inner * row, 0.0
        for k, r in enumerate(regions):
            if k < wc:
                v = struct.unpack_from('>i' if wsz == 4 else '>h', self.d, o)[0]
                o += wsz
            else:
                v = struct.unpack_from('>h' if nsz == 2 else '>b', self.d, o)[0]
                o += nsz
            tot += v * scalars[r]
        return tot

    def _lookups(self, scripts):
        g = self.tables[b'GPOS'][0]
        sl, fl, ll = g + self.u16(g + 4), g + self.u16(g + 6), g + self.u16(g + 8)
        script = None
        for want in scripts:
            for i in range(self.u16(sl)):
                tag = self.d[sl + 2 + 6 * i:sl + 6 + 6 * i]
                if tag == want:
                    script = sl + self.u16(sl + 6 + 6 * i)
                    break
            if script:
                break
        if not script or not self.u16(script):
            return []
        ls = script + self.u16(script)               # default LangSys
        feats = [self.u16(ls + 6 + 2 * k) for k in range(self.u16(ls + 4))]
        req = self.u16(ls + 2)
        if req != 0xFFFF:
            feats.append(req)
        idx = set()
        for f in feats:
            if self.d[fl + 2 + 6 * f:fl + 6 + 6 * f] in KERN_FEATURES:
                fo = fl + self.u16(fl + 6 + 6 * f)
                idx.update(self.u16(fo + 4 + 2 * k) for k in range(self.u16(fo + 2)))
        out = []
        for li in sorted(idx):
            lo = ll + self.u16(ll + 2 + 2 * li)
            ltype = self.u16(lo)
            subs = []
            for k in range(self.u16(lo + 4)):
                so = lo + self.u16(lo + 6 + 2 * k)
                t = ltype
                if t == 9:
                    t, so = self.u16(so + 2), so + self.u32(so + 4)
                if t == 2:
                    subs.append(self._pairpos(so))
            if subs:
                out.append(subs)
        return out

    def _coverage(self, o):
        fmt, n, cov = self.u16(o), self.u16(o + 2), {}
        if fmt == 1:
            for i in range(n):
                cov[self.u16(o + 4 + 2 * i)] = i
        else:
            for i in range(n):
                s, e, start = (self.u16(o + 4 + 6 * i + 2 * k) for k in range(3))
                for gid in range(s, e + 1):
                    cov[gid] = start + gid - s
        return cov

    def _classdef(self, o):
        fmt, cd = self.u16(o), {}
        if fmt == 1:
            start, n = self.u16(o + 2), self.u16(o + 4)
            for i in range(n):
                cd[start + i] = self.u16(o + 6 + 2 * i)
        else:
            for i in range(self.u16(o + 2)):
                s, e, c = (self.u16(o + 4 + 6 * i + 2 * k) for k in range(3))
                for gid in range(s, e + 1):
                    cd[gid] = c
        return cd

    @staticmethod
    def _vsize(fmt):
        return 2 * bin(fmt & 0xFF).count('1')

    def _value(self, sub, o, fmt):
        """(x_placement, x_advance) of a ValueRecord at o (device offsets are from the subtable start `sub`)."""
        vals = {}
        for bit in range(8):
            if fmt & (1 << bit):
                vals[bit] = self.i16(o) if bit < 4 else self.u16(o)
                o += 2
        xp, xa = float(vals.get(0, 0)), float(vals.get(2, 0))
        for bit, which in ((4, 'p'), (6, 'a')):
            if vals.get(bit):
                dv = sub + vals[bit]
                if self.u16(dv + 4) == 0x8000:                # VariationIndex device; hinting devices need a ppem (unset)
                    d = self.delta(self.u16(dv), self.u16(dv + 2))
                    if which == 'p':
                        xp += d
                    else:
                        xa += d
        return xp, xa

    def _pairpos(self, o):
        fmt, cov = self.u16(o), self._coverage(o + self.u16(o + 2))
        vf1, vf2 = self.u16(o + 4), self.u16(o + 6)
        s1, s2 = self._vsize(vf1), self._vsize(vf2)
        if fmt == 1:
            sets = {}
            for g, ci in cov.items():
                ps = o + self.u16(o + 10 + 2 * ci)
                rec = {}
                for k in range(self.u16(ps)):
                    r = ps + 2 + k * (2 + s1 + s2)
                    rec[self.u16(r)] = (r + 2, r + 2 + s1)
                sets[g] = rec
            return ('f1', o, vf1, vf2, sets)
        cd1, cd2 = self._classdef(o + self.u16(o + 8)), self._classdef(o + self.u16(o + 10))
        c1n, c2n = self.u16(o + 12), self.u16(o + 14)
        return ('f2', o, vf1, vf2, cov, cd1, cd2, c1n, c2n, s1 + s2)

    def pair(self, g1, g2):
        xa1 = xp1 = xp2 = 0.0
        for subs in self.lookups:
            for sub in subs:
                if sub[0] == 'f1':
                    _, o, vf1, vf2, sets = sub
                    rec = sets.get(g1)
                    if rec is None or g2 not in rec:
                        continue
                    r1, r2 = rec[g2]
                else:
                    _, o, vf1, vf2, cov, cd1, cd2, c1n, c2n, rs = sub
                    if g1 not in cov:
                        continue
                    k1, k2 = cd1.get(g1, 0), cd2.get(g2, 0)
                    if k1 >= c1n or k2 >= c2n:
                        continue
                    r1 = o + 16 + (k1 * c2n + k2) * rs
                    r2 = r1 + self._vsize(vf1)
                p1, a1 = self._value(o, r1, vf1)
                p2, _ = self._value(o, r2, vf2)
                xa1, xp1, xp2 = xa1 + a1, xp1 + p1, xp2 + p2
                break                                          # first applying subtable wins (per lookup)
        return xa1, xp1, xp2


# ---------------------------------------------------------------------------------------------- glyph rendering
def _ft():
    import freetype
    return freetype


def _flags(hinting):
    F = _ft()
    return F.FT_LOAD_NO_BITMAP | {'light': F.FT_LOAD_TARGET_LIGHT, 'normal': F.FT_LOAD_TARGET_NORMAL,
                                  'none': F.FT_LOAD_NO_HINTING, 'mono': F.FT_LOAD_TARGET_MONO}[hinting]


def _render_glyph(face, cp, flags, mono):
    F = _ft()
    face.load_char(chr(cp), flags)
    slot = face.glyph
    adv26 = slot.advance.x
    slot.render(F.FT_RENDER_MODE_MONO if mono else F.FT_RENDER_MODE_NORMAL)
    bm = slot.bitmap
    w, h, pitch = bm.width, bm.rows, bm.pitch
    buf = bm.buffer
    rows = []
    for y in range(h):
        row = buf[y * pitch:(y + 1) * pitch]
        rows.append(bytes((255 if row[x >> 3] & (0x80 >> (x & 7)) else 0) for x in range(w)) if mono else bytes(row[:w]))
    left, top = slot.bitmap_left, slot.bitmap_top
    ys = [y for y in range(h) if any(rows[y])]
    xs = [x for x in range(w) if any(r[x] for r in rows)] if ys else []
    if not ys or not xs:                                   # vanilla bitmaps are ink-cropped
        return adv26, slot.linearHoriAdvance, left, top, 0, 0, b''
    x0, x1, y0, y1 = xs[0], xs[-1] + 1, ys[0], ys[-1] + 1
    out = b''.join(rows[y][x0:x1] for y in range(y0, y1))
    return adv26, slot.linearHoriAdvance, left + x0, top - y0, x1 - x0, y1 - y0, out


def _scale_glyph(g, r):
    if r == 1:
        return g
    if not g.bitmap:
        return Glyph(g.top, max(0, round(g.adv * r)), g.w, g.h, g.bitmap)
    from PIL import Image
    im = Image.frombytes('L', (g.w, g.h), g.bitmap)
    w, h = max(1, round(g.w * r)), max(1, round(g.h * r))
    im = im.resize((w, h), Image.LANCZOS)
    return Glyph(max(-127, min(127, round(g.top * r))), min(255, round(g.adv * r)), w, h, im.tobytes())


def _hb_pairs(face_path, em, axis_values, cps):
    """{(gl, gr): 26.6 advance of gl before gr, kerning applied} by HarfBuzz (empire cuf_encode.pair_kerning).
    cps: {glyph index: codepoint} of the rendered glyphs in the pair span. Raises RuntimeError without uharfbuzz (no fallback: J79)."""
    try:
        import uharfbuzz as hb
    except ImportError as e:
        raise RuntimeError('cuf_encode: uharfbuzz is required for the pair kerning (D42); install the pins in upscale/requirements.txt '
                           '(uharfbuzz==0.56.4) into the art_build Python: upscale/pc/setup_env.cmd') from e
    font = hb.Font(hb.Face(hb.Blob.from_file_path(face_path), 0))
    font.scale = (int(round(em * 64)),) * 2
    if axis_values:
        font.set_variations(axis_values)
    feats = {'kern': True, 'liga': False, 'clig': False, 'calt': False, 'dlig': False}
    res = {}
    for gl, l in cps.items():
        for gr, r in cps.items():
            buf = hb.Buffer()
            buf.add_codepoints([l, r])
            buf.guess_segment_properties()
            hb.shape(font, buf, feats)
            pos = buf.glyph_positions
            if len(pos) == 2:
                res[(gl, gr)] = pos[0].x_advance + pos[1].x_offset - pos[0].x_offset
    return res


def encode(face_path, vanilla_cuf_bytes, em, wght, keep_header=True, set_h2=None, hinting='light', adv_mode='origin',
           tracking=0):
    """Re-render one vanilla .cuf from `face_path` at `em` px (variable axis wght = `wght`, None for a static face).
    keep_header: header copied from vanilla except h1 (= measured cap height); set_h2 overrides h2 (line pitch = h2 + 2).
    Deterministic: same inputs, same bytes."""
    F = _ft()
    tpl = Cuf.parse(vanilla_cuf_bytes)
    inv = tpl.chars()
    face = F.Face(face_path)
    axis_values = {}
    if wght is not None:
        axes = face.get_variation_info().axes
        axis_values = {'wght': float(wght)}
        face.set_var_design_coords([axis_values.get(ax.tag, ax.default) for ax in axes])
    flags = _flags(hinting)
    face.set_char_size(int(round(em * 64)), 0, 72, 72)
    ratio = em / tpl.header[2]
    fb_ratio = 1.0 if keep_header else ratio      # fallback (vanilla) glyphs stay native size when the header is kept

    out = Cuf()
    out.cmap = list(tpl.cmap)
    out.pair_first = tpl.pair_first
    out.header = list(tpl.header)
    lefts, adv26s, gids, missing = {}, {}, {}, []
    for gi, tg in enumerate(tpl.glyphs):
        cp = inv.get(gi)
        if cp is None or cp < 32:
            out.glyphs.append(Glyph(tg.top, 0 if cp is None or cp < 32 else tg.adv, 0, 0, b''))
            lefts[gi] = 0
            continue
        gid = face.get_char_index(cp)
        if gid and cp not in PUA:
            adv26, lin, left, top, w, h, bm = _render_glyph(face, cp, flags, hinting == 'mono')
            adv26s[gi], gids[gi] = adv26, gid
            if w == 0:
                top = tg.top if tg.w == 0 else -128
            if not (-128 <= top <= 127 and w <= 255 and h <= 255):
                raise ValueError(f'glyph U+{cp:04X} out of range: top={top} {w}x{h}')
            lefts[gi] = left if w else 0
            adv = round(adv26 / 64)
            if adv_mode == 'origin' and w:
                adv -= left
            out.glyphs.append(Glyph(top, max(0, min(255, adv)), w, h, bm))
        else:
            missing.append(cp)
            out.glyphs.append(_scale_glyph(tg, fb_ratio))
            lefts[gi] = 0

    # pair table: step = round(kerned advance) - left(L) + left(R). Kerned advance in 26.6 comes from HarfBuzz shaping the pair
    # (Empire's route, D42); uharfbuzz is required (no GPOS fallback: J79).
    N, base = len(tpl.pairs), tpl.pair_base
    span = range(base, base + N)
    hbk = _hb_pairs(face_path, em, axis_values, {gi: inv[gi] for gi in span if gi in gids})
    out.pairs = []
    for gl in span:
        row = bytearray(N)
        for j, gr in enumerate(span):
            if gl in gids and gr in gids and (gl, gr) in hbk:
                d26 = hbk[(gl, gr)]
            elif gl in adv26s:
                d26 = adv26s[gl]
            else:
                d26 = out.glyphs[gl].adv * 64
            row[j] = max(0, min(255, round(d26 / 64) - lefts[gl] + lefts[gr] + tracking))
        out.pairs.append(row)

    H = out.header
    if ratio != 1 and not keep_header:
        for k in (0, 5, 6, 7, 10):
            H[k] = round(H[k] * ratio)
    H[1] = out.glyphs[out.cmap[ord('H')]].top
    if set_h2 is not None:
        H[2] = set_h2
    data = out.serialise()
    Cuf.parse(data)                                           # refuse to hand back anything the codec cannot read
    return data


# ---------------------------------------------------------------------------------------------- the Lora 2x recipe
def sample_width(c, text=SAMPLE):
    gis = [g for g in (c.glyph_index(ch) for ch in text) if g != 0xFFFF]
    return sum(c.step(g, gis[i + 1] if i + 1 < len(gis) else None) for i, g in enumerate(gis))


def recipe(name):
    """(wght, fit_width) for a vanilla font file name (Empire build_lora_set.py)."""
    regular = (name.startswith('ingame_') and not name.startswith('ingame_b_')) or name.startswith('frontend_')
    return (700 if name.startswith(('ingame_b_', 'tooltip_')) else 500), not regular


def render_set(names, vanilla_reader, face_path=DEFAULT_FACE):
    """Render each vanilla font `name` (e.g. 'ingame_24.cuf') as Lora. vanilla_reader(name) -> vanilla .cuf bytes.
    Regular ingame_/frontend_: wght 500, em = 23/24 x vanilla h2. ingame_b_/tooltip_: wght 700, others 500, em reduced until
    the sample line is <= 99% of the vanilla width. Header kept; SPACED_H2 names get their h2. Returns {name: (bytes, note)}."""
    res = {}
    for name in names:
        van_bytes = vanilla_reader(name)
        van = Cuf.parse(van_bytes)
        wght, fit = recipe(name)
        em = van.header[2] * 23.0 / 24
        h2 = SPACED_H2.get(name)

        def enc(e):
            return encode(face_path, van_bytes, float(f'{e:.2f}'), wght, keep_header=True, set_h2=h2)
        data = enc(em)
        note = f'wght {wght} em {float(f"{em:.2f}"):.2f}'
        if fit:
            wv = sample_width(van)
            for _ in range(12):
                w = sample_width(Cuf.parse(data))
                if w <= 0.99 * wv:
                    break
                em *= 0.99 * wv / w
                data = enc(em)
            note = f'wght {wght} em {float(f"{em:.2f}"):.2f} width {sample_width(Cuf.parse(data))}/{wv} vanilla'
        else:
            note += f' width {sample_width(Cuf.parse(data))}/{sample_width(van)} vanilla'
        if h2 is not None:
            note += f' line pitch {h2 + 2} (spaced long-form slot)'
        res[name] = (data, note)
    return res


def scaled_h2(van_h2, factor):
    """h2 (line height) of an engine-text font rendered at `factor` (J37): the same round-half-up rule as the scaler"""
    return max(1, int(van_h2 * factor + 0.5))


def render_scaled(names, vanilla_reader, factor, face_path=DEFAULT_FACE):
    """Engine-text fonts (J37): render each vanilla `name` as Lora at `factor` x its own size, under its own file name, because the exe opens
    that file itself (a fixed GetFont size or the loading-quote loop) and no layout can point it at a bigger slot. The recipe is render_set's
    (wght by family, em = 23/24 x h2, bold and wide faces fitted to 99 % of the vanilla width scaled by the factor); the header is scaled with
    the glyphs and h2 = scaled_h2(h2, factor), so line pitch = h2 + 2 keeps its meaning. Returns {name: (bytes, note)}."""
    res = {}
    for name in names:
        van_bytes = vanilla_reader(name)
        van = Cuf.parse(van_bytes)
        wght, fit = recipe(name)
        h2 = scaled_h2(van.header[2], factor)
        em = h2 * 23.0 / 24

        def enc(e):
            return encode(face_path, van_bytes, float(f'{e:.2f}'), wght, keep_header=False, set_h2=h2)
        data = enc(em)
        if fit:
            wv = sample_width(van) * factor
            for _ in range(12):
                w = sample_width(Cuf.parse(data))
                if w <= 0.99 * wv:
                    break
                em *= 0.99 * wv / w
                data = enc(em)
        res[name] = (data, f'engine text at {factor:g}x: wght {wght} em {float(f"{em:.2f}"):.2f} h2 {van.header[2]} -> {h2} '
                           f'width {sample_width(Cuf.parse(data))}/{sample_width(van)} vanilla')
    return res


def compare_png(pairs, path, text='Line Infantry - Grand Campaign: Victory Conditions 0123'):
    """Stack vanilla over re-rendered sample lines for each (name, vanilla_bytes, new_bytes); writes a PNG."""
    from PIL import Image, ImageDraw
    rows = []
    for name, vb, nb in pairs:
        for tag, b in (('vanilla', vb), ('lora', nb)):
            im = Cuf.parse(b).render(text)
            lab = Image.new('L', (im.width + 160, im.height), 0)
            ImageDraw.Draw(lab).text((4, 4), f'{name[:-4]} {tag}', fill=160)
            lab.paste(im, (160, 0))
            rows.append(lab)
    W, Ht = max(r.width for r in rows), sum(r.height + 4 for r in rows)
    sheet = Image.new('L', (W, Ht), 0)
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 4
    sheet.save(path)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('out_dir')
    p.add_argument('names', nargs='+', help="vanilla font file names, e.g. ingame_24.cuf (read as pack entry font\\<name>)")
    p.add_argument('--face', default=DEFAULT_FACE)
    p.add_argument('--game', default='napoleon', help='games.json key the vanilla fonts are read from')
    p.add_argument('--compare', help='also write a vanilla-vs-new sample PNG here')
    a = p.parse_args(argv)
    from packfs import PackFS
    with open(os.path.join(ROOT, 'discovery', a.game, 'games.json')) as fh:
        fs = PackFS.from_games(json.load(fh), a.game)

    def reader(n):
        return fs.read('font\\' + n)
    os.makedirs(a.out_dir, exist_ok=True)
    res = render_set(a.names, reader, a.face)
    for n, (data, note) in res.items():
        with open(os.path.join(a.out_dir, n), 'wb') as fh:
            fh.write(data)
        print(f'{n:18} {hashlib.sha256(data).hexdigest()}  {note}')
    if a.compare:
        compare_png([(n, reader(n), d) for n, (d, _) in res.items()], a.compare)
        print('compare:', a.compare)


if __name__ == '__main__':
    main()
