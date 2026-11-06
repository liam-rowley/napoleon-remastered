"""J96 scratch probe packs (never committed; kept as evidence). Run from the repo root in the art_build Python.
usage: build_probes.py art|load <unaligned file stem>|pics|tpl|tpl2x|fonts|all
tpl2x: probe 4, second marker (the renamed paths of tpl stayed invisible even by route 2): J67's 2x templates file on vanilla layouts, so template-built elements change size;
       zz_j96_tpl2x_r1 delivers it by a pack entry, rules_tpl2x_r2.txt by dev.file_rules (the control)
pics:  probe 2, the file class that is on screen: every DXT loading picture in its own colour at 4802x3002 (the plain 2.5x of 1921x1200 is 4803x3000: neither is on the 4 grid)
load:  probe 2 again: every DXT file of the loading screen in its own colour at the rounded-up size, so the shot shows which are on screen, except the named one at a size off the 4 grid
art:   probes 1 to 3 in one pack: DXT5 at 4-aligned TGA paths; DXT files at sizes not a multiple of 4; the 4800 px loading pictures with a marker band;
       and the in-pack control: TGA markers on paths J50 proved drawn, so a shot tells "this pack was read" apart from "the DDS was not drawn"
tpl:   probe 4: a templates file whose image paths are renamed (same length) to files only the probe pack holds, so a template-built element goes magenta
       only if the engine read this templates file; zz_j96_tpl_r1 delivers it by a pack entry, the rules file by dev.file_rules (the control)
fonts: probe 5: the five slot fonts, each at its own multiple of the J66 size, slot table read-only
"""
import json
import os
import re
import struct
import sys

ROOT = os.getcwd()
sys.path[:0] = [os.path.join(ROOT, 'upscale', 'core'), os.path.join(ROOT, 'core', 'discovery'), os.path.join(ROOT, 'uiscale', 'core')]
import numpy as np  # noqa: E402
import dds  # noqa: E402
import imageio  # noqa: E402
import rules  # noqa: E402
from packfs import PackFS, write_pack  # noqa: E402

SCR = r'C:\napoleon_remastered_pc\_scratch\j96'
WORK = r'C:\napoleon_remastered_pc\upscale\work'
GAME = r'C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War'
PACKS = os.path.join(SCR, 'packs')
ORANGE, GREEN, CYAN, YELLOW, MAGENTA = 0xFC00, 0x07E0, 0x07FF, 0xFFE0, 0xF81F    # 5:6:5
FONT_PROBE = {'frontend_24.cuf': 0.6, 'frontend_38.cuf': 0.8, 'ingame_18.cuf': 1.3, 'ingame_24.cuf': 0.7, 'ingame_b_24.cuf': 1.5}

rows = [json.loads(ln) for ln in open(os.path.join(ROOT, 'registries', 'assets.jsonl'), encoding='utf-8')]
games = json.load(open(os.path.join(ROOT, 'discovery', 'napoleon', 'games.json'), encoding='utf-8'))


def block(fmt, c565):
    col = struct.pack('<HHI', c565, c565, 0)
    if fmt == 'DXT1':
        return col
    if fmt in ('DXT2', 'DXT3'):
        return b'\xff' * 8 + col
    return b'\xff\xff' + b'\0' * 6 + col       # DXT5: alpha endpoints 255


def solid_dds(fmt, w, h, c565):
    """a one-colour DXT file with a full mip chain, built from constant blocks"""
    n = dds.full_mips(w, h)
    b = block(fmt, c565)
    data = b''.join(b * (dds.level_size(fmt, *dds.level_dims(w, h, k)) // len(b)) for k in range(n))
    blob = dds.make_header(fmt, w, h, n) + data
    d = dds.read_dds(blob)
    assert (d.width, d.height, d.mips, d.fmt) == (w, h, n, fmt), (d.width, d.height, d.mips, d.fmt)
    return blob


def band_dds(blob, c565):
    """the middle fifth of every level of a DXT file overwritten with a marker colour"""
    d = dds.read_dds(blob)
    b = block(d.fmt, c565)
    out = bytearray(blob)
    off = 128
    for k in range(d.mips):
        w, h = d.dims(k)
        bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
        r0, r1 = bh * 2 // 5, max(bh * 2 // 5 + 1, bh * 3 // 5)
        for r in range(r0, r1):
            s = off + r * bw * len(b)
            out[s:s + bw * len(b)] = b * bw
        off += len(d.levels[k])
    return bytes(out)


def band_rgba(img):
    out = img.copy()
    h = out.shape[0]
    out[h * 2 // 5:h * 3 // 5, :, :3] = (255, 0, 255)
    return out


def tint_tga(fs, path, rgb):
    src = imageio.load(fs.read(path), '.tga')
    img = src.rgba.copy()
    img[..., 0], img[..., 1], img[..., 2] = rgb
    return imageio.encode_tga(img, with_alpha=True)


def art():
    files, log = {}, {}
    fs = PackFS.from_games(games, 'napoleon')
    assert not any('zz_j96' in n for n in fs.packs), fs.packs
    # control: TGA at paths J50 saw drawn (s2m, s2m2, s2r3): logo magenta, the 73x71 end-turn files green, every unaligned battle skin cyan
    ctrl = re.compile(r'^ui\\campaign ui\\skins\\button_end_turn_(active|down|down_off|hover)\.tga$|^ui\\frontend ui\\skins\\logo\.tga$|^ui\\battle ui\\skins\\', re.I)
    for r in rows:
        k, s, w, h, m = rules.parse_format(r['format'])
        if k == 'tga' and w and h and (w % 4 or h % 4) and ctrl.search(r['path']):
            low = r['path'].lower()
            try:
                files[r['path']] = tint_tga(fs, r['path'], (255, 0, 255) if 'logo' in low else (0, 255, 0) if 'end_turn' in low else (0, 255, 255))
            except Exception as e:  # noqa: BLE001: a control the reader refuses is only one control less
                print('control skipped', r['path'], e)
                continue
            log.setdefault('control_tga', []).append(r['path'])
    # probe 1: DXT5, vanilla size, both sides multiples of 4, full mips, at TGA paths on screen
    p1 = re.compile(r'^ui\\frontend ui\\skins\\button_steam_store|^ui\\campaign ui\\skins\\button_end_turn_(inactive|unselect)|^ui\\battle ui\\skins\\', re.I)
    for r in rows:
        k, s, w, h, m = rules.parse_format(r['format'])
        if k == 'tga' and w and h and w % 4 == 0 and h % 4 == 0 and p1.search(r['path']):
            files[r['path']] = solid_dds('DXT5', w, h, ORANGE)
            log.setdefault('p1_dxt5_at_tga', []).append('%s %dx%d' % (r['path'], w, h))
    # probe 2: the affected loading-screen files at the plain 2.5x, and every flag (the only other UI DXT) at a size off the 4 grid
    for r in rows:
        k, s, w, h, m = rules.parse_format(r['format'])
        if k != 'dds' or not rules.is_dxt(s):
            continue
        fmt = s.upper()
        if r['role'] == 'loading_screen' and 'loadingscreen' in r['path'].lower():
            tw, th = rules.target_size(w, h)
            if (tw, th) != rules.dxt_target_size(w, h, s):
                files[r['path']] = solid_dds(fmt, tw, th, GREEN if 'heading' in r['path'] else CYAN)
                log.setdefault('p2_plain', []).append('%s %dx%d %s' % (r['path'], tw, th, fmt))
        elif r['path'].lower().endswith('large.dds') and 'flags' in r['path'].lower():
            tw, th = rules.target_size(w, h)
            files[r['path']] = solid_dds(fmt, tw + 2, th + 2, YELLOW)
            log.setdefault('p2_flags', []).append('%s %dx%d %s' % (r['path'], tw + 2, th + 2, fmt))
    # probe 3: every J51 loading picture output 4800 px wide, with a magenta band at every level
    man = json.load(open(os.path.join(WORK, 'manifest.json'), encoding='utf-8'))['entries']
    for e in man.values():
        if e['status'] != 'done' or e['out']['w'] < 4800:
            continue
        data = open(os.path.join(WORK, e['out']['file']), 'rb').read()
        ext = os.path.splitext(e['path'])[1].lower()
        if ext == '.dds':
            files[e['path']] = band_dds(data, MAGENTA)
        else:
            src = imageio.load(data, ext)
            img = band_rgba(src.rgba)
            files[e['path']] = imageio.encode_tga(img, with_alpha=False) if ext == '.tga' else imageio.encode_jpg(img, 95)
        log.setdefault('p3_4800', []).append('%s %dx%d %s' % (e['path'], e['out']['w'], e['out']['h'], e['out']['fmt']))
    write_pack(os.path.join(PACKS, 'zz_j96_art.pack'), files, pack_type=4)
    print(json.dumps({k: len(v) for k, v in log.items()}), len(files), sum(map(len, files.values())))
    json.dump(log, open(os.path.join(SCR, 'art_entries.json'), 'w'), indent=1)


def load(unaligned):
    cols = [ORANGE, GREEN, CYAN, YELLOW, MAGENTA, 0x001F, 0xFFFF, 0xF800, 0x8010, 0x0410]
    files, log = {}, []
    for r in rows:
        k, s, w, h, m = rules.parse_format(r['format'])
        if k == 'dds' and rules.is_dxt(s) and 'loadingscreen' in r['path'].lower():
            tw, th = rules.dxt_target_size(w, h, s)
            if unaligned in r['path'].lower():
                tw, th = tw + 2, th + 2
            c = cols[len(files) % len(cols)]
            files[r['path']] = solid_dds(s.upper(), tw, th, c)
            log.append('%s %s vanilla %dx%d probe %dx%d colour %04x' % (r['path'], s, w, h, tw, th, c))
    write_pack(os.path.join(PACKS, 'zz_j96_load.pack'), files, pack_type=4)
    print('\n'.join(log))


def pics():
    cols = [ORANGE, GREEN, CYAN, YELLOW, MAGENTA, 0x001F, 0xFFFF, 0xF800, 0x8010, 0x0410, 0x8400, 0x4208, 0xFD20, 0x07F0, 0xF81A, 0x2C4A]
    files, log = {}, []
    for r in rows:
        k, s, w, h, m = rules.parse_format(r['format'])
        if k == 'dds' and rules.is_dxt(s) and 'loading_screen_pictures' in r['path'].lower():
            c = cols[len(files) % len(cols)]
            files[r['path']] = solid_dds(s.upper(), 4802, 3002, c)
            log.append('%s %s %dx%d colour %04x' % (r['path'], s, w, h, c))
    write_pack(os.path.join(PACKS, 'zz_j96_pics.pack'), files, pack_type=4)
    print('\n'.join(log))
    open(os.path.join(SCR, 'pics_colours.txt'), 'w').write('\n'.join(log))


def rename(path):
    """same length, a name no vanilla file has: the last stem letter becomes '9' (or '8')"""
    stem, ext = path[:-4], path[-4:]
    return stem[:-1] + (b'8' if stem[-1:] == b'9' else b'9') + ext


def tpl():
    fs = PackFS.from_games(games, 'napoleon')
    src = os.path.join(GAME, 'data', 'ui', 'templates', 'uied.templates')
    b = open(src, 'rb').read()
    paths = sorted(set(re.findall(rb'data\\UI\\[A-Za-z0-9_ \\\-\.]{1,}\.tga', b, re.I)))
    tex, skipped = {}, []
    out = b
    for p in paths:
        name = p.decode()[5:]
        try:
            img = imageio.load(fs.read(name), '.tga')
        except Exception as e:  # noqa: BLE001: a named file the game does not hold stays as it is
            skipped.append('%s: %s' % (name, e))
            continue
        new = rename(p)
        m = img.rgba.copy()
        m[..., 0], m[..., 1], m[..., 2] = 255, 0, 255
        m[..., 3] = np.maximum(m[..., 3], 200)
        tex[new.decode()[5:]] = imageio.encode_tga(m, with_alpha=True)
        out = out.replace(p, new)
    assert len(out) == len(b)
    marked = os.path.join(SCR, 'uied.templates.marked')
    open(marked, 'wb').write(out)
    write_pack(os.path.join(PACKS, 'zz_j96_tpl_tex.pack'), tex, pack_type=4)
    write_pack(os.path.join(PACKS, 'zz_j96_tpl_r1.pack'), dict(tex, **{'ui\\templates\\uied.templates': out}), pack_type=4)
    sky = open(os.path.join(ROOT, 'proxy', 'napoleon', 'lua', 'fixed_sky_rules.txt'), encoding='utf-8').read()
    open(os.path.join(SCR, 'rules_tpl_r2.txt'), 'w', encoding='utf-8', newline='\n').write(
        sky + '\n# J96 control: the marked templates by route 2\nredirect data\\ui\\templates\\uied.templates -> %s\n' % marked)
    print('templates', len(paths), 'paths,', len(tex), 'marked,', len(skipped), 'skipped', skipped[:4])


def tpl2x():
    built = r'C:\napoleon_remastered_pc\uiscale\work\uied.templates.ui_scale_2x'
    write_pack(os.path.join(PACKS, 'zz_j96_tpl2x_r1.pack'), {'ui\\templates\\uied.templates': open(built, 'rb').read()}, pack_type=4)
    sky = open(os.path.join(ROOT, 'proxy', 'napoleon', 'lua', 'fixed_sky_rules.txt'), encoding='utf-8').read()
    open(os.path.join(SCR, 'rules_tpl2x_r2.txt'), 'w', encoding='utf-8', newline='\n').write(
        sky + '\n# J96 control: the 2x templates by route 2\nredirect data\\ui\\templates\\uied.templates -> %s\n' % built)
    print('tpl2x built')


def fonts():
    import cuf_encode
    fs = PackFS.from_games(games, 'napoleon')
    face = os.path.join(ROOT, 'uiscale', 'fonts', 'Lora-Variable.ttf')
    spaced = {'frontend_24.cuf': int(28 * FONT_PROBE['frontend_24.cuf'])}
    out = cuf_encode.render_set(sorted(FONT_PROBE), lambda n: fs.read('font\\' + n), face, scale=FONT_PROBE, spaced=spaced)
    write_pack(os.path.join(PACKS, 'zz_j96_fonts.pack'), {'font\\' + n: v[0] for n, v in out.items()}, pack_type=4)
    print({n: v[1][:50] for n, v in out.items()})


if __name__ == '__main__':
    os.makedirs(PACKS, exist_ok=True)
    what = sys.argv[1]
    if what == 'load':
        load(sys.argv[2])
    if what == 'pics':
        pics()
    if what == 'tpl2x':
        tpl2x()
    for name, fn in (('art', art), ('tpl', tpl), ('fonts', fonts)):
        if what in (name, 'all'):
            fn()
