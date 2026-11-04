"""Scale Warscape UI layouts and uied.templates records by a fixed factor (J66, D40 stop-gap), ported from empire-remastered ui_scale_mod.

purpose: rebuild a parsed layout (core/discovery/uic.py) or uied.templates record (tpl.py) at a factor: component x/y, state w/h, image-use rects, textured image defs, V039 keyframe geometry, the font name onto a slot the context loads, embedded TGAs with their image defs
usage: library: from scale import scale_layout, scale_templates_file, font_slot, px; scale_layout(doc, 2.0, context='campaign')   (driven by uiscale/napoleon/cli.py, `wsc uiscale build`)
when: building the ui_scale_<f>x packs and the scaled uied.templates; host tests in tests/test_uiscale.py
not-a-verb: a library used by uiscale/napoleon/cli.py, not a registry operation

Rules (empire-remastered origin/ui/multiscale ui_scale_mod/docs/multiscale.md section 4):
- absolute edge snapping: every vanilla edge e, relative to the layout or template root, lands on px(e * f) with px(x) = floor(x + 0.5);
  rel x = px(abs * f) - px(parent_abs * f), w = px((abs + w) * f) - px(abs * f). Never per-value rounding (it opened ~1,000 one-pixel
  gaps on Empire). The root's own position is not scaled.
- image defs with a path are the texture repeat period: they take tex_size = ceil(t * f) (the engine tiles at the texture's real size,
  so the art pack ships real f x textures); blank defs (containers, solid fills) stay.
- the image-use tail (9-slice stretch flags at bytes 7/8) is never touched.
- fonts: the engine loads a fixed set of font files per context; a name maps to a slot of that context (SLOTS), chosen as at 2x.
- templates: an embedded TGA is upscaled together with the image defs that describe it, never apart (a def changed alone crashed
  Empire's campaign). Records in SKIP_TEMPLATES and the undecodable v4 records pass through byte for byte.
"""
import copy
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'core', 'discovery'))
import tpl  # noqa: E402
import uic  # noqa: E402


def px(x):
    """THE rounding rule for every pixel quantity: round half up (Python's round() is half-to-even)."""
    return int(math.floor(x + 0.5))


def tex_size(t, f):
    """pixel size of a scaled texture and of the image def that describes it: ceil, so a use drawn once at native size never tiles a sliver"""
    return max(1, int(math.ceil(t * f - 1e-9)))


def span(a, n, f):
    """edge-snapped extent of the vanilla span [a, a + n) in absolute coordinates"""
    return px((a + n) * f) - px(a * f)


# ---------------------------------------------------------------------------------------------------------------- fonts
FONT_RE = re.compile(r'^(Ingame|Frontend|Tooltip) (\d+), (Normal|Bold)$')
SLOT_FACTOR = 2.0   # slot names are chosen as in the 2x build at every factor (multiscale.md section 5)
# sizes each context is proven (Empire) or assumed (Napoleon, until the J66 probe) to load
FRONTEND_LOADED = {'Frontend': [14, 16, 18, 22, 24, 38], 'Ingame': [10, 12, 14, 16, 18, 24], 'Ingame_b': [12, 14, 18, 24],
                   'Tooltip': [6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 36]}


def font_slot(name, context):
    """layout font name -> the slot name the scaled layout uses. context: 'frontend' or anything else (campaign, battle, common,
    templates), where only Ingame 24 Normal/Bold, Frontend 24 and Frontend 38 are proven to load (Empire)."""
    m = FONT_RE.match(name or '')
    if not m:
        return name
    fam, size, style = m.group(1), int(m.group(2)), m.group(3)
    want = round(size * SLOT_FACTOR)
    if context != 'frontend':
        if fam == 'Ingame':
            if style == 'Normal' and want >= 34:
                return 'Frontend 38, Normal'
            return f'Ingame 24, {style}'
        if fam == 'Frontend':
            return 'Frontend 38, Normal' if want >= 34 else 'Frontend 24, Normal'
        return f'Ingame 24, {style}'   # Tooltip
    avail = FRONTEND_LOADED['Ingame_b' if (fam == 'Ingame' and style == 'Bold') else fam]
    best = min(avail, key=lambda s: (abs(s - want), -s))   # nearest, larger on a tie
    return f'{fam} {best}, {style}'


def font_file(name):
    """'Ingame 24, Bold' -> 'ingame_b_24.cuf' (napoleon.diff.fonts.cuf: Empire's rule)"""
    m = FONT_RE.match(name or '')
    if not m:
        return None
    fam, size, style = m.group(1).lower(), m.group(2), m.group(3)
    return f'{fam}_b_{size}.cuf' if style == 'Bold' else f'{fam}_{size}.cuf'


def context_of(path):
    """layout pack path -> font context: 'frontend' for ui\\frontend ui\\..., else the folder name"""
    parts = path.lower().replace('/', '\\').split('\\')
    folder = parts[1] if len(parts) > 2 and parts[0] == 'ui' else parts[0]
    return 'frontend' if folder == 'frontend ui' else folder.replace(' ui', '')


# ----------------------------------------------------------------------------------------------------------- components
KF_X, KF_Y, KF_W, KF_H = 0, 4, 8, 12   # V039 keyframe: f32 x, f32 y, i32 w, i32 h (napoleon.diff.layouts.v039)


def scale_frame(k, ax, ay, f):
    """a V039 keyframe at the component's absolute origin (ax, ay): x/y snapped as offsets from it, w/h as spans"""
    kb = bytearray(uic.frame_bytes(k))
    x, y, w, h = struct.unpack_from('<ffii', kb, 0)
    kx, ky = ax + x, ay + y
    nx = px(kx * f) - px(ax * f)
    ny = px(ky * f) - px(ay * f)
    struct.pack_into('<ffii', kb, 0, float(nx), float(ny), span(kx, w, f), span(ky, h, f))
    return bytes(kb) if isinstance(k, bytes) else (bytes(kb),) + tuple(k[1:])


def scale_component(c, f, context, is_root=False, image_defs=True, org=(0, 0), stats=None):
    """scale a component tree in place; org = the parent's vanilla absolute origin"""
    if is_root:
        ax, ay = 0, 0
    else:
        ox, oy = org
        ax, ay = ox + c['x'], oy + c['y']
        c['x'] = px(ax * f) - px(ox * f)
        c['y'] = px(ay * f) - px(oy * f)
    if image_defs:
        for im in c['images']:
            if im['path']:
                im['w'] = tex_size(im['w'], f)
                im['h'] = tex_size(im['h'], f)
    for st in c['states']:
        st['w'] = span(ax, st['w'], f)
        st['h'] = span(ay, st['h'], f)
        if st.get('font'):
            new = font_slot(st['font'], context)
            if stats is not None:
                stats.setdefault('fonts', {}).setdefault(new, 0)
                stats['fonts'][new] += 1
            st['font'] = new
        for u in st['uses']:
            ux, uy = ax + u['x'], ay + u['y']
            u['x'] = px(ux * f) - px(ax * f)
            u['y'] = px(uy * f) - px(ay * f)
            u['w'] = span(ux, u['w'], f)
            u['h'] = span(uy, u['h'], f)
    for a in c.get('anims') or []:
        a['frames'] = [scale_frame(k, ax, ay, f) for k in a['frames']]
        if stats is not None:
            stats['keyframes'] = stats.get('keyframes', 0) + len(a['frames'])
    for ch in c['children']:
        scale_component(ch, f, context, image_defs=image_defs, org=(ax, ay), stats=stats)


def scale_layout(doc, f, context, scale_root=True, stats=None):
    """scale a parsed layout in place. scale_root=False keeps the root's own state size (the canvas) vanilla."""
    root = doc['root']
    keep = [(st['w'], st['h']) for st in root['states']]
    scale_component(root, f, context, is_root=True, stats=stats)
    if not scale_root:
        for st, (w, h) in zip(root['states'], keep):
            st['w'], st['h'] = w, h
    return doc


def layout_bytes(data, path, f, scale_root=True, stats=None):
    """vanilla layout bytes -> scaled bytes; refuses a file that does not round-trip, and re-parses the output"""
    doc = uic.parse(data, path)
    if uic.serialise(doc) != data:
        raise ValueError(f'{path}: does not round-trip through uic.py, refusing to scale')
    scale_layout(doc, f, context_of(path), scale_root, stats)
    out = uic.serialise(doc)
    if uic.serialise(uic.parse(out, path)) != out:
        raise ValueError(f'{path}: scaled output does not round-trip')
    return out


# -------------------------------------------------------------------------------------------------------------- templates
SKIP_TEMPLATES = {'slider', 'Cursor', 'InputWindow', 'BattleEditor'}   # Empire left these vanilla (slider: field boundaries unverified)
# pre-v27 records keep a numeric font id (0 = tiny engine default), so their text cannot take a slot name in place; Empire rewrote
# the text-bearing ones as Version033 (proven in game there). Only names that exist in the file below v33 are touched.
UPGRADE_TO_33 = {'minister_effect_cartouche', 'minister_details', 'turns', 'numerical_input', 'diplomacy_allies_list_item',
                 'sortable_list', 'character_info_list_entry'}


def upgrade_component(c, is_root):
    """a parsed v20-v28 component tree -> Version033 field layout, in place (empire scale_templates.upgrade_component)"""
    c['flags'] = (c['flags'] + b'\0' * 7)[:7]
    c['template'] = c.get('template') or (c['name'] if is_root else '')
    c['c_a'] = c['c_a'] if c.get('c_a') is not None else (0 if is_root else -1)
    c['tooltip'] = c.get('tooltip') or ''
    c['tooltip_label'] = c.get('tooltip_label') or ''
    c['c_c'] = c.get('c_c') or 0
    c['c_flag'] = 0
    c['inline_script'] = c.get('inline_script') or ''
    c['i_a'] = c.get('i_a') or 0
    c['i_b'] = c.get('i_b') or 0
    c['e_a'] = c.get('e_a') or 0
    c['z_a'] = c.get('z_a') or 0
    c['e_pad'] = None
    for st in c['states']:
        st['pre_font'] = None
        if not st['font']:
            st['font'] = 'Ingame 12, Normal'
        fr = st['f_raw']
        st['f_raw'] = (bytes(12) + fr[16:18] + b'\0') if len(fr) == 18 else (fr + b'\0' * 15)[:15]
        if st['shader'] in ('', 'Regular'):
            st['shader'] = 'normal_t0'
        st['s_raw'] = (st['s_raw'] + bytes(16))[:16]
        for u in st['uses']:
            u['tail'] = (u['tail'] + bytes(21))[:21]
    for ch in c['children']:
        upgrade_component(ch, False)


def upscale_tga(tga, f):
    """uncompressed TGA (type 2/3) -> tex_size(dim, f) by nearest neighbour (integer factors; the 2x build)"""
    if f != int(f):
        raise ValueError('embedded template textures: only integer factors (J66 builds 2.0; fractional needs the wrap-aware Lanczos, J67)')
    h = bytearray(tga[:18])
    idlen = h[0]
    w, hh = struct.unpack_from('<HH', h, 12)
    bpp = h[16] // 8
    body = tga[18 + idlen:18 + idlen + w * hh * bpp]
    nw, nh = tex_size(w, f), tex_size(hh, f)
    rows = []
    for y in range(nh):
        sy = min(int(y / f), hh - 1)
        row = body[sy * w * bpp:(sy + 1) * w * bpp]
        rows.append(b''.join(row[min(int(x / f), w - 1) * bpp:(min(int(x / f), w - 1) + 1) * bpp] for x in range(nw)))
    struct.pack_into('<HH', h, 12, nw, nh)
    return bytes(h) + tga[18:18 + idlen] + b''.join(rows) + tga[18 + idlen + w * hh * bpp:]


def _scale_embedded(c, f, record_texs):
    """upscale a component's own embedded textures and every image def (here or on the record) that names an embedded texture"""
    texs = c.get('textures', [])
    for t in texs:
        t['tga'] = upscale_tga(t['tga'], f)
    names = {t['path'] for t in texs} | record_texs
    for im in c['images']:
        if im['path'] and im['path'] in names:
            im['w'] = tex_size(im['w'], f)
            im['h'] = tex_size(im['h'], f)
    for ch in c['children']:
        _scale_embedded(ch, f, record_texs)


def rebuild(d, recs, payloads):
    """the container with new payloads (sizes and self-offsets rewritten); identity when the payloads are unchanged"""
    out = bytearray(d[:4])
    for r, pl in zip(recs, payloads):
        if r['legacy']:
            out += d[r['hdr']:r['hdr'] + 256] + struct.pack('<III', len(pl) + 4, r['ver'], r['ntex']) + pl
            continue
        self_off = len(out)
        out += d[r['hdr']:r['hdr'] + 252] + struct.pack('<IIII', r['ver'], len(pl) + 4, self_off, r['ntex']) + pl
    return bytes(out)


def scale_record(r, f, stats=None):
    """one tpl.split record -> (new version, new payload); raises on a record that does not round-trip"""
    doc = tpl.parse_record(r)
    if tpl.serialise_record(doc, r['ver']) != r['payload']:
        raise ValueError(f"{r['name']}: record does not round-trip")
    ver = r['ver']
    if r['name'] in UPGRADE_TO_33 and ver < 33:
        upgrade_component(doc['root'], True)
        ver = 33
    scale_component(doc['root'], f, 'templates', is_root=True, image_defs=False, stats=stats)
    for t in doc['textures']:
        t['tga'] = upscale_tga(t['tga'], f)
    rec_names = {t['path'] for t in doc['textures']}
    _scale_embedded(doc['root'], f, rec_names)
    return ver, tpl.serialise_record(doc, ver)


def scale_templates_file(d, f, skip=SKIP_TEMPLATES, stats=None):
    """uied.templates bytes -> (scaled bytes, report {scaled, passed, upgraded})"""
    recs = tpl.split(d)
    if rebuild(d, recs, [r['payload'] for r in recs]) != d:
        raise ValueError('uied.templates: container rebuild is not the identity')
    payloads, rep = [], {'scaled': [], 'passed': [], 'upgraded': []}
    for r in recs:
        r = dict(r)
        if r['name'] in skip or r['legacy']:
            payloads.append(r['payload'])
            rep['passed'].append(f"{r['name']} (v{r['ver']})")
            continue
        try:
            ver, pl = scale_record(r, f, stats)
        except Exception as e:  # noqa: BLE001 (an undecodable record passes through; it is listed)
            payloads.append(r['payload'])
            rep['passed'].append(f"{r['name']} (v{r['ver']}: {type(e).__name__})")
            continue
        if ver != r['ver']:
            rep['upgraded'].append(r['name'])
        r['ver'] = ver
        recs[recs.index(next(x for x in recs if x['hdr'] == r['hdr']))] = r
        payloads.append(pl)
        rep['scaled'].append(r['name'])
    out = rebuild(d, recs, payloads)
    for r in tpl.split(out):   # every scaled record must parse again
        if r['name'] in rep['scaled']:
            tpl.parse_record(r)
    return out, rep


def deep(doc):
    return copy.deepcopy(doc)
