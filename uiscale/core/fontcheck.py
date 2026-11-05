"""How a Warscape exe turns a font name or a fixed size into a .cuf file, the engine-text font plan per factor, and the slot check (J37, D7).

purpose: model the engine's font resolution (fixed name list -> id, unknown name -> the default id; GetFont(family, size, bold) -> even size clamped to [min, max] -> <family>_[b_]<n>.cuf), plan the engine-text fonts a factor needs (files the engine opens by itself, rendered at the factor, and aliases where the clamp sends a list name to another file), and check a fonts pack: every name a scaled layout, a template or the engine-text inventory uses resolves to a file the pack carries, no unlisted name, no vanilla font copied in, no file nothing opens
usage: library: from fontcheck import Model, plan_engine, check; Model(cfg['engine']).file_of('Frontend 38, Normal'); check(model, names, engine_plan, pack_files, vanilla_sha)   (driven by uiscale/napoleon/cli.py: `wsc uiscale check-fonts`, `wsc uiscale engine-text`)
when: building and checking a ui_scale_<f>x_fonts pack (J37 engine text, J66/J67 layout slots); host tests in tests/test_uiscale_engine_text.py
not-a-verb: a library used by uiscale/napoleon/cli.py and uiscale/napoleon/engine_text.py, not a registry operation

The model is data (uiscale/napoleon/font_slots.json `engine`, static RE run uiscale/runs/2026-11-03_j37_static): this module holds no game constants.
"""
import math
import re

NAME_RE = re.compile(r'^([A-Za-z]+) (\d+), (Normal|Bold)$')


def px(x):
    """the shared rounding rule (uiscale/core/scale.py): round half up"""
    return int(math.floor(x + 0.5))


class Model:
    """the exe's font resolution. cfg: {'name_list': [19 names], 'default_index': 2, 'getfont': {'min': 6, 'max': 32, 'even': 'down'}}"""

    def __init__(self, cfg):
        self.names = list(cfg['name_list'])
        self.default = self.names[cfg['default_index']]
        g = cfg['getfont']
        self.lo, self.hi, self.even = int(g['min']), int(g['max']), g.get('even', 'down')

    def listed(self, name):
        return name in self.names

    def effective_name(self, name):
        """the name the engine draws with: itself when listed, else the default (the lookup returns the default index)"""
        return name if name in self.names else self.default

    def size_of(self, n):
        """GetFont's size rule: odd -> one less, then clamp"""
        n = int(n)
        if self.even == 'down' and n % 2:
            n -= 1
        return max(self.lo, min(self.hi, n))

    def file_for(self, family, size, bold):
        """GetFont(family, size, bold) -> the .cuf file name it opens (lower case)"""
        return f"{family.lower()}_{'b_' if bold else ''}{self.size_of(size)}.cuf"

    def file_of(self, name):
        """layout font name -> the .cuf file the engine opens for it (through the list and GetFont)"""
        m = NAME_RE.match(self.effective_name(name))
        if not m:
            raise ValueError(f'font name {name!r} is not "<Family> <n>, Normal|Bold"')
        return self.file_for(m.group(1), int(m.group(2)), m.group(3) == 'Bold')

    def opened(self):
        """{file: [list names]} for the preload: every file the list makes the engine open"""
        out = {}
        for n in self.names:
            out.setdefault(self.file_of(n), []).append(n)
        return out


def h2_at(h2, factor):
    """target line height (h2) of an engine-text file rendered at `factor`"""
    return max(1, px(h2 * factor))


def plan_engine(rows, factor, layout_files, opened_by_list=None):
    """the engine-text fonts for one factor.
    rows: font_slots.json `engine_text` rows: {'file', 'kind': 'render'|'alias', 'alias_of'?, 'items': [...], 'max_factor'?}
    layout_files: files the scaled layouts and templates already use as slots at this factor (their own size wins: a file cannot be both).
    Returns {'render': {file: {'factor', 'items'}}, 'alias': {file: {'of', 'items'}}, 'skipped': {file: reason}}."""
    out = {'render': {}, 'alias': {}, 'skipped': {}}
    for r in sorted(rows, key=lambda r: r['file']):
        f = r['file']
        if r['kind'] == 'alias':
            src = r['alias_of']
            if src not in layout_files:
                out['skipped'][f] = f'alias of {src}, which no scaled layout uses at {factor:g}x'
            elif f in layout_files:
                out['skipped'][f] = f'{f} is itself a layout slot at {factor:g}x'
            else:
                out['alias'][f] = {'of': src, 'items': list(r['items'])}
            continue
        if factor == 1:
            out['skipped'][f] = 'factor 1: vanilla'
        elif f in layout_files:
            out['skipped'][f] = f'a layout slot at {factor:g}x (drawn at its own size)'
        elif r.get('max_factor') and factor > r['max_factor']:
            out['skipped'][f] = f'above max_factor {r["max_factor"]:g}'
        else:
            out['render'][f] = {'factor': factor, 'items': list(r['items'])}
    return out


def check(model, names, plan, pack_files, vanilla_sha=None, engine_files=()):
    """the slot check. names: {font name: uses} the scaled layouts and templates name; plan: plan_engine(); pack_files: {file: sha256}
    of the fonts pack (file names without font\\, lower case); vanilla_sha: {sha256: vanilla file} of the CA fonts; engine_files: files the
    exe opens by itself (fixed-size sites, the quote loop) that are not planned. Returns (problems [str], notes [str])."""
    problems, notes = [], []
    vanilla_sha = vanilla_sha or {}
    need = {}
    for n in sorted(names):
        if not model.listed(n):
            problems.append(f'{n!r} ({names[n]} uses) is not in the exe name list: it draws as {model.default!r}')
        need.setdefault(model.file_of(n), []).append(n)
    for f in sorted(need):
        if f not in pack_files:
            problems.append(f'{f} (for {", ".join(need[f])}) is not in the pack: the vanilla font would be drawn')
    for f, p in sorted(plan['render'].items()):
        if f not in pack_files:
            problems.append(f'{f} (engine text: {", ".join(p["items"])}) is planned at {p["factor"]:g}x but not in the pack')
    for f, a in sorted(plan['alias'].items()):
        if f not in pack_files:
            problems.append(f'{f} (alias of {a["of"]}: {", ".join(a["items"])}) is not in the pack')
        elif a['of'] in pack_files and pack_files[f] != pack_files[a['of']]:
            problems.append(f'{f} should carry the same bytes as {a["of"]} (the clamp sends {a["of"]}\'s list name to it)')
    used = set(need) | set(plan['render']) | set(plan['alias'])
    opened = set(model.opened()) | set(engine_files) | set(plan['render']) | set(plan['alias'])
    for f in sorted(pack_files):
        if pack_files[f] in vanilla_sha:
            problems.append(f'{f} is byte-identical to the vanilla {vanilla_sha[pack_files[f]]}: CA fonts never ship in a pack')
        if f not in opened:
            notes.append(f'{f} is in the pack but the engine never opens it (GetFont clamp or no caller)')
        elif f not in used:
            notes.append(f'{f} is in the pack but no scaled layout, template or engine-text item uses it')
    return problems, notes
