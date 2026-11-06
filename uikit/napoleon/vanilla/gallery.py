#!/usr/bin/env python3
"""Composite every vanilla UI surface from its layout and the game's art, and build the private reference page (J99).

purpose: draw static composites of all atlas surfaces (art, 9-slice uses, tiling, .cuf text) and the component state strips, and stage the "Vanilla UI reference" page
usage: python3 uikit/napoleon/vanilla/gallery.py compose [--only WORD ...] [--out DIR]
when: after the atlas, the inventory or the library changes, before publishing the page (README.md beside this file); reads the game's packs in place, so it runs on the PC
not-a-verb: a one-page generator beside its inventory, like uikit/napoleon/build.py; composites and shots go to the page, never to git (J7)

The atlas keeps art ids per state but not where each image use sits, so this reads the layouts themselves through uic and tpl. Per image use: x, y, w, h,
colour and the tail, where tail[0] tiles the art, tail[1] and tail[2] mirror it on x and y, tail[3] is the 9-slice slot, tail[7] and tail[8] say it stretches
with the component. Component flag byte 3 is the default visibility. Component x and y are relative to the parent. Text: t_b 2 left, 3 right, 4 centre;
t_c 4 centred vertically, 0 top (read from samples, not from the engine). These are references: the live shots are the truth where they exist.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'core' / 'discovery'))
import cuf  # noqa: E402
import fonts  # noqa: E402
import loc  # noqa: E402
import tpl  # noqa: E402
import uic  # noqa: E402
from packfs import PackFS  # noqa: E402

CONTEXTS = ('battle', 'campaign', 'common', 'frontend', 'template')
GAME = 'napoleon'
BG = (38, 38, 43, 255)
DYNAMIC = (255, 92, 214, 255)        # a field the game fills at run time: its key, in this colour
HATCH = (255, 196, 0, 255)           # art the game does not ship under that path (UI-editor paths)
DEFAULT_FONT = 'Ingame 12, Normal'
TAGS = re.compile(r'\[\[.*?\]\]')
JPEG_QUALITY = 80
SHEET_W, SHEET_H = 2048, 4096        # sprite sheet size
MAX_STATES = 14                      # states drawn per kind (the most any template has is 13 distinct ones)
BIG_CELL = 256                       # above this a kind shows its default state only
BIG_LIMIT = 1024                     # a cell is cut to this: a 10000-wide strip is a stretched rule
MAX_MASTERS = 12                     # art pieces per kind shown from their masters
MASTER_MAX = 256                     # art larger than this at 1x stays out of the 2x sheets: fills and pictures, not components
MASTERS = 'C:/napoleon_remastered_pc/upscale/work/packs'


def surfaces():
    out = {}
    for ctx in CONTEXTS:
        with gzip.open(ROOT / 'discovery' / 'ui' / f'{ctx}.json.gz') as f:
            out.update(json.load(f)['surfaces'])
    return out


def art_key(path):
    """A layout image path -> pack key, or None for a UI-editor path (the atlas's art_id rule)."""
    k = path.replace('\\', '/').lower()
    i = k.find('ui/')
    if k.startswith('data/'):
        k = k[5:]
    elif i > 0 and k[i - 1] == '/':
        k = k[i:]
    if re.match(r'^[a-z]:', k) or k.startswith('//'):
        return None
    return k.replace('/', '\\')


def tail_flags(tail):
    """(tile, mirror x, mirror y) of an image use; older records have a shorter tail."""
    t = bytes(tail or b'') + bytes(3)
    return bool(t[0]), bool(t[1]), bool(t[2])


def visible(comp):
    f = comp['flags']
    return len(f) < 4 or bool(f[3])


def default_state(comp):
    """The state a component starts in: V039's state_ref, else the named default, else the first."""
    states = comp['states']
    ref, name = comp.get('state_ref'), comp.get('default_state')
    for st in states:
        if (ref and st['id'] == ref) or (name and st['name'] == name):
            return st
    return states[0] if states else None


def tint(img, colour):
    """Multiply by an image use's ARGB colour."""
    if colour in (0xffffffff, 0):
        return img
    a, r, g, b = (colour >> 24) & 255, (colour >> 16) & 255, (colour >> 8) & 255, colour & 255
    ch = img.split()
    return Image.merge('RGBA', [c.point(lambda v, m=m: v * m // 255) for c, m in zip(ch, (r, g, b, a))])


def fit(img, w, h, tile):
    """The art for a w x h use: tiled from the top left, or stretched."""
    if img.size == (w, h):
        return img
    if not tile:
        return img.resize((w, h), Image.BILINEAR)
    out = Image.new('RGBA', (w, h))
    for y in range(0, h, img.height):
        for x in range(0, w, img.width):
            out.paste(img, (x, y))
    return out


def wrap(text, width, measure):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for word in para.split(' '):
            nxt = f'{cur} {word}' if cur else word
            if cur and measure(nxt) > width:
                lines.append(cur)
                cur = word
            else:
                cur = nxt
        lines.append(cur)
    return lines


class Game:
    """Read-only view of the art, fonts and loc text, cached."""

    def __init__(self):
        games = json.load(open(ROOT / 'discovery' / 'napoleon' / 'games.json', encoding='utf-8'))
        self.fs = PackFS.from_games(games, GAME)
        self._art, self._fonts, self._loc, self._tpl = {}, {}, None, None

    def art(self, path):
        k = art_key(path)
        if k is None:
            return None
        if k not in self._art:
            img = None
            if self.fs.stat(k):
                import io
                try:
                    img = Image.open(io.BytesIO(self.fs.read(k))).convert('RGBA')
                except OSError:
                    img = None
            self._art[k] = img
        return self._art[k]

    def font(self, name):
        name = name or DEFAULT_FONT
        if name not in self._fonts:
            f = fonts.font_file(name)
            self._fonts[name] = cuf.Cuf.parse(self.fs.read(f)) if f and self.fs.stat(f) else None
            if self._fonts[name] is None and name != DEFAULT_FONT:
                self._fonts[name] = self.font(DEFAULT_FONT)
        return self._fonts[name]

    @property
    def text(self):
        if self._loc is None:
            self._loc = {}
            for c in self.fs.copies():
                if c.path.lower().endswith('.loc') and c.effective:
                    for k, t, _ in loc.decode(self.fs.read(c))[1]:
                        self._loc[k] = t
        return self._loc

    def doc(self, path, rec):
        """The root component of a surface."""
        if path.startswith('uied.templates/'):
            if self._tpl is None:
                self._tpl = {r['name']: r for r in tpl.split(self.fs.read('ui\\templates\\uied.templates'))}
            return tpl.parse_record(self._tpl[path.split('/', 1)[1]])['root']
        p = 'ui\\' + rec['path']
        return uic.parse(self.fs.read(p), p)['root']


class Canvas:
    def __init__(self, game, w, h, bg=BG):
        self.game, self.img, self.d = game, Image.new('RGBA', (max(w, 1), max(h, 1)), bg), None
        self.d = ImageDraw.Draw(self.img)
        self.stats = {'components': 0, 'drawn': 0, 'hatched': 0, 'standin': 0, 'dynamic': 0}
        self.hidden = []

    def put(self, art, x, y):
        cw, ch = self.img.size
        l, t, r, b = max(x, 0), max(y, 0), min(x + art.width, cw), min(y + art.height, ch)
        if l < r and t < b:
            self.img.alpha_composite(art, (l, t), (l - x, t - y, r - x, b - y))

    def hatch(self, x, y, w, h, label):
        self.stats['hatched'] += 1
        self.d.rectangle((x, y, x + w - 1, y + h - 1), outline=HATCH)
        for i in range(0, w + h, 8):
            self.d.line((x + min(i, w), y + max(0, i - w), x + max(0, i - h), y + min(i, h)), fill=HATCH)
        self.d.text((x + 2, y + 1), re.split(r'[\\/]', label)[-1][:40], fill=(255, 255, 255, 255), font=ImageFont.load_default())

    def use(self, u, by_id, x, y, root=False):
        im = by_id.get(u['img'])
        w, h = u['w'], u['h']
        if im is None or w <= 0 or h <= 0:
            return
        if not im['path']:                       # no art: a flat rule or fill in the use's colour (the column dividers of a list header)
            c = u.get('colour', 0)
            if not root and c >> 24:
                self.put(Image.new('RGBA', (w, h), ((c >> 16) & 255, (c >> 8) & 255, c & 255, c >> 24)), x + u['x'], y + u['y'])
            return
        art = self.game.art(im['path'])
        if art is None:
            self.hatch(x + u['x'], y + u['y'], w, h, im['path'])
            return
        tile, mx, my = tail_flags(u.get('tail'))
        if mx:
            art = art.transpose(Image.FLIP_LEFT_RIGHT)
        if my:
            art = art.transpose(Image.FLIP_TOP_BOTTOM)
        self.put(tint(fit(art, w, h, tile), u.get('colour', 0xffffffff)), x + u['x'], y + u['y'])

    def measure(self, f, s):
        pen, prev = 0, None
        for ch in s:
            g = f.cmap[ord(ch)] if ord(ch) < 65536 else 0xffff
            if g == 0xffff:
                pen += 6
                prev = None
                continue
            pen += self.step(f, prev, g)
            prev = g
        return pen + (f.glyphs[prev].adv if prev is not None else 0)

    @staticmethod
    def step(f, prev, g):
        """The pen step from glyph prev to glyph g: the pair table where it covers them, else prev's advance."""
        if prev is None:
            return 0
        first = f.cmap[f.pair_first]
        i, j = prev - first, g - first
        if 0 <= i < len(f.pairs) and 0 <= j < len(f.pairs) and f.pairs[i][j]:
            return f.pairs[i][j]
        return f.glyphs[prev].adv

    def line(self, f, s, x, base, colour):
        pen, prev = x, None
        for ch in s:
            g = f.cmap[ord(ch)] if ord(ch) < 65536 else 0xffff
            if g == 0xffff:
                self.stats['standin'] += 1
                self.d.text((pen, base - 10), ch, fill=colour, font=ImageFont.load_default())
                pen += 6
                prev = None
                continue
            pen += self.step(f, prev, g)
            prev = g
            gl = f.glyphs[g]
            if gl.w and gl.h and gl.top != -128:
                self.img.paste(colour[:3] + (255,), (pen, base - gl.top, pen + gl.w, base - gl.top + gl.h), Image.frombytes('L', (gl.w, gl.h), gl.bitmap))

    def text(self, comp, st, x, y):
        key = st.get('text_label') or ''
        known = self.game.text.get(key) if key else None
        dynamic = comp['name'].lower().startswith('dy_') or (key and known is None)
        s = (key or comp['name']) if dynamic else (known or st.get('text') or '')
        s = TAGS.sub('', s).replace('\r', '').strip()
        if not s:
            return
        f = self.game.font(st.get('font'))
        if f is None:
            return
        c = st.get('font_colour', 0xffffffff)
        colour = DYNAMIC if dynamic else ((c >> 16) & 255, (c >> 8) & 255, c & 255, 255)
        self.stats['dynamic'] += bool(dynamic)
        if dynamic:                                  # a key is a label, not copy: one line, cut to the component's width
            while len(s) > 4 and self.measure(f, s) > st['w']:
                s = s[:-1]
        lines = [s] if dynamic else wrap(s, max(st['w'], 1), lambda v: self.measure(f, v))
        lh = f.header[10] or f.header[2]
        total = lh * len(lines)
        top = y + ((st['h'] - total) // 2 if st.get('t_c') == 4 else 0)
        for i, ln in enumerate(lines):
            wd = self.measure(f, ln)
            left = x + {3: st['w'] - wd, 4: (st['w'] - wd) // 2}.get(st.get('t_b'), 0)
            self.line(f, ln, left, top + i * lh + f.header[0], colour)

    def component(self, c, ox, oy, state=None, root=False):
        self.stats['components'] += 1
        x, y = (ox, oy) if root else (ox + c['x'], oy + c['y'])
        st = state or default_state(c)
        if not root and not visible(c):
            self.hidden.append([x, y, st['w'] if st else 0, st['h'] if st else 0, c['name']])
            return
        if st:
            self.stats['drawn'] += 1
            by_id = {im['id']: im for im in c['images']}
            for u in st['uses']:
                self.use(u, by_id, x, y, root)
            self.text(c, st, x, y)
        for k in c['children']:
            self.component(k, x, y)


def compose(game, path, rec):
    """(RGB image, stats, hidden rects) of one surface, at its layout base size."""
    if rec.get('layout_unread'):
        return None, {'unread': True}, []
    root = game.doc(path, rec)
    st = default_state(root)
    w, h = rec.get('base') or (0, 0)
    if not w or not h:
        w, h = (st['w'], st['h']) if st else (256, 256)
    cv = Canvas(game, w, h)
    cv.component(root, 0, 0, root=True)
    return cv.img.convert('RGB'), cv.stats, cv.hidden


def slug(path):
    return re.sub(r'[^a-z0-9]+', '_', path.lower()).strip('_')


def cmd_compose(a):
    game = Game()
    out = Path(a.out)
    (out / 'composites').mkdir(parents=True, exist_ok=True)
    table = {}
    for path, rec in sorted(surfaces().items()):
        if a.only and not any(w.lower() in path.lower() for w in a.only):
            continue
        img, stats, hidden = compose(game, path, rec)
        if img is not None:
            stats['sha256'] = hashlib.sha256(img.tobytes()).hexdigest()
            stats['size'] = list(img.size)
            img.save(out / 'composites' / f'{slug(path)}.jpg', quality=JPEG_QUALITY, optimize=True)
        table[path] = {**stats, 'hidden': hidden}
        print(path, {k: v for k, v in stats.items() if k != 'sha256'}, flush=True)
    if not a.only:
        (out / 'composites.json').write_text(json.dumps(table, sort_keys=True, indent=0), encoding='utf-8')
    return 0


class Sheets:
    """Shelf-packs small images into PNG sprite sheets: an artifact holds at most 511 files, the page shows thousands of cells."""

    def __init__(self, out, prefix, width=SHEET_W, height=SHEET_H):
        self.out, self.prefix, self.w, self.h = Path(out), prefix, width, height
        self.names, self.sizes = [], {}
        self.cur = None

    def _new(self):
        self._flush()
        self.cur = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        self.x = self.y = self.row = 0

    def _flush(self):
        if self.cur is not None:
            used = self.y + self.row
            name = f'{self.prefix}_{len(self.names):02d}.png'
            img = self.cur.crop((0, 0, self.w, max(used, 1)))
            img.save(self.out / name, optimize=True)
            self.names.append(name)
            self.sizes[name] = list(img.size)
            self.cur = None

    def add(self, img):
        """Place img; returns [sheet index, x, y, w, h]."""
        if img.width > self.w:
            img = img.crop((0, 0, self.w, img.height))
        if img.height > self.h:
            img = img.crop((0, 0, img.width, self.h))
        if self.cur is None:
            self._new()
        if self.x + img.width > self.w:
            self.x, self.y, self.row = 0, self.y + self.row + 1, 0
        if self.y + img.height > self.h:
            self._new()
        self.cur.paste(img, (self.x, self.y))
        at = [len(self.names), self.x, self.y, img.width, img.height]
        self.x += img.width + 1
        self.row = max(self.row, img.height)
        return at

    def close(self):
        self._flush()
        return [{'file': n, 'size': self.sizes[n]} for n in self.names]


def find(comp, path):
    """The component at an atlas path ('root/a/b') under a root."""
    for name in path.split('/')[1:]:
        comp = next((k for k in comp['children'] if k['name'] == name), None)
        if comp is None:
            return None
    return comp


def asset_path(game, asset, rows):
    return rows.get(asset, {}).get('path') or asset


def state_cells(game, kind, docs):
    """[(label, RGBA image)] for a kind's vanilla states at 1x."""
    s = kind.get('sample')
    rows = game.rows
    if kind['kind'] == 'button':
        out = []
        for st in kind['states']:
            art = game.art(asset_path(game, st['assets'][0], rows))
            if art is not None:
                out.append((st['name'], art))
        return out
    if not s:
        return []
    if s['surface'] not in docs:
        docs[s['surface']] = game.doc(s['surface'], game.surf[s['surface']])
    comp = find(docs[s['surface']], s['path'])
    if comp is None or not comp['states']:
        return []
    default = default_state(comp)
    want = [st for st in comp['states'] if st['name'] == s['state']] if s.get('state') else list(comp['states'])
    big = max(default['w'], default['h']) > BIG_CELL
    if big:                                       # a whole list or panel: its other states differ little and the sheets are what the publish pays for
        want = [default] if not s.get('state') else want[:1]
    out, seen = [], set()
    for st in want[:MAX_STATES]:
        if not st['w'] or not st['h']:
            continue
        cv = Canvas(game, min(st['w'], BIG_LIMIT), min(st['h'], BIG_LIMIT), bg=(0, 0, 0, 0))
        cv.component(comp, 0, 0, state=st, root=True)
        sig = cv.img.tobytes()
        if sig in seen:                           # states that draw the same pixels (click down mouse off and the like) keep one cell, named by the first
            continue
        seen.add(sig)
        out.append((st['name'], cv.img))
    return out


def master(game, asset, rows):
    """The 2x image of an art id from its 2.5x master, or None."""
    p = rows.get(asset, {}).get('path')
    if not p:
        return None
    c = game.masters.stat('ui_art_2x5\\' + p)
    if c is None:
        return None
    src = game.art(p)
    if src is None or max(src.size) > MASTER_MAX:
        return None
    import io
    img = Image.open(io.BytesIO(game.masters.read(c))).convert('RGBA')
    return img.resize((src.width * 2, src.height * 2), Image.LANCZOS)


def cmd_strips(a):
    game = Game()
    game.surf = surfaces()
    game.rows = {}
    with open(ROOT / 'registries' / 'assets.jsonl', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            game.rows[r['id']] = r
    game.masters = PackFS(a.masters)
    out = Path(a.out)
    (out / 'sheets').mkdir(parents=True, exist_ok=True)
    one, two = Sheets(out / 'sheets', 's1'), Sheets(out / 'sheets', 's2')
    kinds = json.load(open(HERE / 'components.json', encoding='utf-8'))
    table, docs = {}, {}
    for k in kinds:
        cells = [[label] + one.add(img) for label, img in state_cells(game, k, docs)]
        arts = []
        for st in k['states']:
            arts.extend(x for x in st['assets'] if x not in arts)
        ms = []
        for art in arts[:MAX_MASTERS]:
            img = master(game, art, game.rows)
            if img is not None:
                ms.append([art.rsplit('/', 1)[-1]] + two.add(img))
        table[k['id']] = {'cells': cells, 'masters': ms}
    data = {'kinds': table, 'one': one.close(), 'two': two.close()}
    (out / 'strips.json').write_text(json.dumps(data, sort_keys=True), encoding='utf-8')
    mb = sum((out / 'sheets' / s['file']).stat().st_size for s in data['one'] + data['two']) / 1e6
    print(f"{len(table)} kinds, {sum(bool(v['cells']) for v in table.values())} with a strip, {sum(bool(v['masters']) for v in table.values())} with masters, "
          f"{len(data['one'])}+{len(data['two'])} sheets, {mb:.1f} MB")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('compose', help='draw the composites')
    c.add_argument('--only', nargs='*', help='surfaces whose path holds one of these words')
    c.add_argument('--out', default=str(ROOT / '_scratch' / 'j99'))
    s = sub.add_parser('strips', help='draw every kind\'s state strip and 2x masters into sprite sheets')
    s.add_argument('--out', default=str(ROOT / '_scratch' / 'j99'))
    s.add_argument('--masters', default=MASTERS)
    a = ap.parse_args(argv)
    return {'compose': cmd_compose, 'strips': cmd_strips}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
