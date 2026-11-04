"""J50 scratch probe packs (never committed): marker, real J36 outputs, DDS at a TGA path. Run from the repo root.
usage: build_probes.py marker|real|dds [dds_target_path]"""
import hashlib, json, os, re, shutil, sys
ROOT = os.getcwd()
sys.path[:0] = [os.path.join(ROOT, 'upscale', 'core'), os.path.join(ROOT, 'discovery', 'core')]
import numpy as np  # noqa
import imageio, dds, pack  # noqa
from packfs import PackFS  # noqa

SCR = r'C:\napoleon_remastered_pc\_scratch\j50'
WORK = r'C:\napoleon_remastered_pc\upscale\work'
games = json.load(open(os.path.join(ROOT, 'discovery', 'napoleon', 'games.json'), encoding='utf-8'))
rows = [json.loads(l) for l in open(os.path.join(ROOT, 'registries', 'assets.jsonl'), encoding='utf-8')]
paths = [r['path'] for r in rows]

MAGENTA, GREEN, CYAN, ORANGE = (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 128, 0)
FRONT = [r'ui\frontend ui\skins\simple_button_center_up.tga', r'ui\common ui\skins\simple_button_center_up.tga']
END_TURN = [p for p in paths if re.search(r'^ui\\campaign ui\\skins\\button_end_turn_', p, re.I)]
BATTLE = [p for p in paths if re.search(r'^ui\\battle ui\\skins\\button_.*_unselected\.tga$', p, re.I)]


def tint(rgba, col):
    out = rgba.copy()
    out[..., 0], out[..., 1], out[..., 2] = col
    return out


def build(name, files):
    """files: {entry path: bytes}"""
    work = os.path.join(SCR, name + '_work')
    shutil.rmtree(work, ignore_errors=True)
    entries = []
    for p, b in files.items():
        rel = p.replace('\\', os.sep)
        os.makedirs(os.path.dirname(os.path.join(work, rel)), exist_ok=True)
        open(os.path.join(work, rel), 'wb').write(b)
        entries.append((p, len(b), rel, hashlib.sha256(b).hexdigest()))
    m = pack.build(name, entries, work, os.path.join(SCR, 'packs'), force=True)
    print(json.dumps({'pack': name, 'entries': len(entries), 'sha256': m.get('sha256'), 'paths': sorted(files)}, indent=1))


def main():
    what = sys.argv[1]
    fs = PackFS.from_games(games, 'napoleon')
    assert not any(n.startswith(('ui_art_2x5', 'zz_j50')) for n in fs.packs), fs.packs
    if what == 'marker':
        files = {}
        for group, col in ((FRONT, MAGENTA), (END_TURN, GREEN), (BATTLE, CYAN)):
            for p in group:
                src = imageio.load(fs.read(p), 'tga')
                files[p] = imageio.encode_tga(tint(src.rgba, col), with_alpha=True)
        build('zz_j50_marker', files)
    elif what == 'marker2':
        files = {}
        dirs = ((r'ui\frontend ui\skins', MAGENTA), (r'ui\battle ui\buttons', CYAN)) if sys.argv[2:] != ['battle'] else ((r'ui\battle ui\skins', CYAN),)
        for d, col in dirs:
            for p in paths:
                if p.lower().rsplit('\\', 1)[0] == d and p.lower().endswith('.tga'):
                    try:
                        src = imageio.load(fs.read(p), 'tga')
                    except Exception as e:  # noqa
                        print('skip', p, e)
                        continue
                    files[p] = imageio.encode_tga(tint(src.rgba, col), with_alpha=True)
        build('zz_j50_marker3' if sys.argv[2:] == ['battle'] else 'zz_j50_marker2', files)
    elif what == 'real':
        man = json.load(open(os.path.join(WORK, 'manifest.json'), encoding='utf-8'))['entries']
        pick = [r'ui\frontend ui\skins\logo.tga', r'ui\frontend ui\skins\button_steam_store.tga',
                r'ui\campaign ui\skins\button_end_turn_active.tga', r'ui\campaign ui\skins\button_end_turn_unselect.tga']
        files = {}
        for p in pick:
            e = man[next(r['id'] for r in rows if r['path'] == p)]
            assert e['status'] == 'done', e
            b = open(os.path.join(WORK, e['out']['file']), 'rb').read()
            assert hashlib.sha256(b).hexdigest() == e['out']['sha256']
            files[p] = b
            print(p, e['src']['w'], 'x', e['src']['h'], '->', e['out']['w'], 'x', e['out']['h'])
        build('zz_j50_real', files)
    elif what == 'dds':
        targets = sys.argv[2:] or [r'ui\frontend ui\skins\logo.tga', r'ui\frontend ui\skins\button_steam_store.tga']
        files = {}
        for p in targets:
            src = imageio.load(fs.read(p), 'tga')
            img = tint(src.rgba, ORANGE)
            h, w = img.shape[:2]
            levels = dds.mips_box(img, dds.full_mips(w, h))
            data = dds.encode_chain(levels, 'DXT5')
            tmp = os.path.join(SCR, 'probe.dds')
            dds.write_dds(tmp, 'DXT5', w, h, data)
            b = open(tmp, 'rb').read()
            d = dds.read_dds(b)
            print(p, w, 'x', h, 'DXT5 mips', d.mips, len(b), 'bytes')
            files[p] = b
        build('zz_j50_dds', files)


main()
