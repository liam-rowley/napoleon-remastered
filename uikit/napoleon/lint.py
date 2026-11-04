#!/usr/bin/env python3
"""Lint a Napoleon screen folder or the library's sources against the design language's mechanical rules.

purpose: check a screen folder (screen.json, RML, RCSS, Lua) or the library sources for tokens only, library classes, dp only, text size 14 dp, contrast, perf and layout rules, and unknown $tokens
usage: python3 uikit/napoleon/lint.py [screen dir | --library ...] [--json] [--factions PATH|none]   (exit 1 on any finding; default: the library sources and the board)
when: before a screen or library change is proposed and in the tests / CI's viewer job; the real 77-faction contrast check reads the git-ignored extract when present and prints counts only
not-a-verb: a file linter for one folder tree, run by the tests and CI, not a registry operation
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tokens as T  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SRC = HERE / 'src'
HEX = re.compile(r'#[0-9a-fA-F]{3,8}\b')
COLOR_FN = re.compile(r'\b(?:rgba?|hsla?)\s*\(')
LENGTH = re.compile(r'(?<![\w$.#-])(-?(?:\d+\.?\d*|\.\d+))([a-zA-Z%]*)')
OK_UNITS = {'', 'dp', '%', 'deg', 's', 'ms'}
BANNED_PROPS = {'backdrop-filter': 'backdrop filters are not drawn by the host', 'clip-path': 'clip-path is not drawn', 'outline': 'no CSS outline in RmlUi (use box-shadow)',
                'text-shadow': 'RmlUi 6.3 has no text-shadow (J34 spike)', 'mix-blend-mode': 'blend modes are not drawn'}


def strip_comments(text):
    """Comments blanked out, newlines kept so line numbers stay right."""
    return re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), text, flags=re.S)


def parse_rcss(text):
    """(selectors, declarations): selectors = [(text, line)], declarations = [(prop, value, line, selector)] from comment-stripped RCSS."""
    sels, decls, stack, buf, line, start = [], [], [], '', 1, 1
    for ch in text:
        if ch in '{};':
            if ch == '{':
                sel = buf.strip()
                stack.append(sel)
                sels.append((sel, start))
            elif ':' in buf and stack:
                prop, _, val = buf.partition(':')
                decls.append((prop.strip().lower(), val.strip(), start, stack[-1]))
            if ch == '}' and stack:
                stack.pop()
            buf, start = '', line
        else:
            if not buf.strip() and ch.strip():
                start = line
            buf += ch
        if ch == '\n':
            line += 1
    return sels, decls


def library_classes():
    out = set()
    for p in [SRC / 'base.rcss'] + sorted(SRC.glob('[0-9]*.rcss')):
        sels, _ = parse_rcss(strip_comments(p.read_text(encoding='utf-8')))
        for sel, _l in sels:
            out.update(re.findall(r'\.([A-Za-z_][\w-]*)', sel))
    return out


def find_real_factions():
    for d in [ROOT, *ROOT.parents]:
        f = d / 'extract' / 'napoleon' / 'db' / 'db__factions_tables__factions.json'
        if f.exists():
            return f
    return None


def real_factions(path):
    d = json.loads(Path(path).read_text(encoding='utf-8'))
    ix = {n: i for i, n in enumerate(d['fields'] if isinstance(d['fields'][0], str) else [f[0] for f in d['fields']])}
    cols = [ix['primary_colour_r'], ix['primary_colour_g'], ix['primary_colour_b']]
    return [tuple(int(r[c]) for c in cols) for r in d['rows']]


class Lint:
    def __init__(self, tokens=None):
        self.t = tokens or T.load_tokens()
        self.findings = []

    def add(self, rule, file, line, msg):
        self.findings.append({'rule': rule, 'file': str(file), 'line': line, 'message': msg})

    # ---- one declaration (rules 1, 3, 4, 6, 7) ----
    def declaration(self, file, line, prop, val, extra, selector=''):
        try:
            expanded = T.expand(val, self.t, f'{file}', extra)
        except ValueError as e:
            self.add('7 token names exist', file, line, str(e).split(': ', 1)[-1])
            return
        stripped = T.TOKEN_RE.sub('', re.sub(r'"[^"]*"', '', val))
        if HEX.search(stripped) or COLOR_FN.search(stripped):
            self.add('1 tokens only', file, line, f'literal colour in "{prop}: {val}": use a $color token')
        for m in LENGTH.finditer(HEX.sub('', stripped)):
            num, unit = m.group(1), m.group(2).lower()
            if unit not in OK_UNITS:
                self.add('3 dp only', file, line, f'"{num}{unit}" in "{prop}: {val}": lengths are dp (D19)')
            elif unit == 'dp' and float(num) != 0:
                self.add('1 tokens only', file, line, f'bare length {num}dp in "{prop}: {val}": use a length token')
        if prop == 'font-size':
            m = re.fullmatch(r'\s*(\d+\.?\d*)dp\s*', expanded)
            if m and float(m.group(1)) < self.t['min_text_dp']:
                self.add('4 text size', file, line, f'font-size {m.group(1)}dp is under the {self.t["min_text_dp"]} dp minimum')
        if prop == 'flex' and re.search(r'\bauto\b', val) and not val.strip().startswith('0'):
            self.add('6 perf and layout', file, line, f'"flex: {val}" with auto: nested flex 1 1 auto costs exponential relayout; use flex: 1 1 0')
        if prop == 'opacity' and re.fullmatch(r'\s*0(\.0+)?\s*', val):
            self.add('6 perf and layout', file, line, 'opacity: 0 is not hidden; use display: none')
        if prop in BANNED_PROPS:
            self.add('6 perf and layout', file, line, f'{prop}: {BANNED_PROPS[prop]}')
        if prop == 'filter' and val.strip() != 'none':
            self.add('6 perf and layout', file, line, 'filter other than none is not promised by the host')
        if prop == 'border-style' and 'dashed' in val:
            self.add('6 perf and layout', file, line, 'border-style: dashed is not drawn')
        if '!important' in val:
            self.add('6 perf and layout', file, line, '!important is not allowed')
        if prop == 'box-shadow':
            for one in re.split(r',(?![^()]*\))', expanded):
                lens = re.findall(r'(?<![\w#-])(-?\d+\.?\d*)(?:dp)?(?![\w])', HEX.sub('', one))   # x, y, blur, spread
                if len(lens) >= 3 and float(lens[2]) != 0:
                    self.add('6 perf and layout', file, line, 'box-shadow with a blur draws a black halo in the viewer (J34 spike): use blur 0')
                if re.search(r'#[0-9a-fA-F]{8}\b', one) and 'inset' not in one:
                    self.add('6 perf and layout', file, line, 'outer box-shadow with an alpha colour composites against black in the viewer (J34 spike): use an opaque colour')

    def selector(self, file, line, sel, library_ok, prefix):
        if sel.startswith('@'):
            return
        for one in sel.split(','):
            one = one.strip()
            if re.search(r'(^|[\s>+~])\*', one):
                self.add('6 perf and layout', file, line, f'"*" selector in "{one}"')
            depth = len([p for p in re.split(r'\s*[>+~]\s*|\s+', re.sub(r'\([^)]*\)', '', one)) if p])
            if depth > 3:
                self.add('6 perf and layout', file, line, f'selector "{one}" is {depth} levels deep (max 3)')
            if library_ok is not None:
                for c in re.findall(r'\.([A-Za-z_][\w-]*)', one):
                    if c not in library_ok and not (prefix and c.startswith(prefix)):
                        self.add('2 library classes', file, line, f'class ".{c}" is neither a library class nor starts with the screen prefix "{prefix}"')

    def rcss(self, path, extra, library_ok, prefix):
        text = strip_comments(Path(path).read_text(encoding='utf-8'))
        sels, decls = parse_rcss(text)
        for sel, line in sels:
            self.selector(path.name, line, sel, library_ok, prefix)
        for prop, val, line, sel in decls:
            self.declaration(path.name, line, prop, val, extra, sel)

    def rml(self, path, extra, library_ok, prefix):
        text = Path(path).read_text(encoding='utf-8')
        for m in re.finditer(r'class="([^"]*)"', text):
            line = text.count('\n', 0, m.start()) + 1
            for c in m.group(1).split():
                if '{{' in c or '}}' in c:
                    continue
                if c not in library_ok and not c.startswith(prefix):
                    self.add('2 library classes', path.name, line, f'class "{c}" is neither a library class nor starts with the screen prefix "{prefix}"')
        for m in re.finditer(r'data-class-([\w-]+)=', text):
            c = m.group(1)
            if c not in library_ok and not c.startswith(prefix):
                self.add('2 library classes', path.name, text.count('\n', 0, m.start()) + 1, f'data-class "{c}" is not a library class')
        for m in re.finditer(r'\bstyle="([^"]*)"', text):
            line = text.count('\n', 0, m.start()) + 1
            for d in m.group(1).split(';'):
                if ':' in d:
                    p, _, v = d.partition(':')
                    self.declaration(path.name, line, p.strip().lower(), v.strip(), extra)

    def lua(self, path, library_ok, prefix):
        text = Path(path).read_text(encoding='utf-8')
        for m in re.finditer(r'SetClass\(\s*["\']([\w-]+)["\']', text):
            c = m.group(1)
            if c == 'fac-':   # the faction route: SetClass("fac-" .. id)
                continue
            if c not in library_ok and not c.startswith(prefix):
                self.add('2 library classes', path.name, text.count('\n', 0, m.start()) + 1, f'SetClass("{c}") is not a library class')

    # ---- rule 5: contrast ----
    def contrast(self, factions_path='auto'):
        t = self.t
        for fg, bg, mn, ratio, ok, what in T.pair_report(t):
            if not ok:
                self.add('5 contrast', 'tokens.json', 0, f'{fg} on {bg} is {ratio}:1, needs {mn}: {what}')
        for k in t['faction_synthetic']:
            if k.startswith('_'):
                continue
            rec = T.faction_tokens(*t['faction_synthetic'][k], tokens=t)
            for name, c in (('fac_hover', rec['fac_hover']), ('fac_pressed', rec['fac_pressed']), ('fac', rec['fac'])):
                if T.contrast(c, rec['on_fac']) < t['faction']['min_ratio']:
                    self.add('5 contrast', 'tokens.json', 0, f'faction {k}: {rec["on_fac"]} on {name} {c} under 4.5')
        d = T.default_faction(t)
        for name in ('fac', 'fac_hover', 'fac_pressed'):
            if T.contrast(d[name], d['on_fac']) < t['faction']['min_ratio']:
                self.add('5 contrast', 'tokens.json', 0, f'default faction: {name} under 4.5')
        n = bad = adj = 0   # grid sweep over the RGB cube
        for r in range(0, 256, 17):
            for g in range(0, 256, 17):
                for b in range(0, 256, 17):
                    rec = T.faction_tokens(r, g, b, tokens=t)
                    n += 1
                    adj += rec['adjusted']
                    base = T.contrast(rec['fac'], rec['on_fac'])
                    if (base < t['faction']['min_ratio'] or T.contrast(rec['fac_hover'], rec['on_fac']) < base - 1e-9
                            or T.contrast(rec['fac_pressed'], rec['on_fac']) < base - 1e-9):
                        bad += 1
        self.sweep = (n, adj, bad)
        if bad:
            self.add('5 contrast', 'tokens.json', 0, f'grid sweep: {bad} of {n} colours fail the on-colour rule or hover/pressed lower the ratio')
        self.real = None
        path = find_real_factions() if factions_path == 'auto' else (None if factions_path == 'none' else Path(factions_path))
        if path:
            rows = real_factions(path)
            fails = sum(1 for rgb in rows if T.faction_tokens(*rgb, tokens=t)['ratio'] < t['faction']['min_ratio'])
            adjusted = sum(1 for rgb in rows if T.faction_tokens(*rgb, tokens=t)['adjusted'])
            self.real = (len(rows), adjusted, fails)
            if fails:
                self.add('5 contrast', 'extract', 0, f'{fails} of {len(rows)} real faction rows fail after the fix')

    def min_text_tokens(self):
        for style, s in self.t['type'].items():
            if s['size'] < self.t['min_text_dp']:
                self.add('4 text size', 'tokens.json', 0, f'type style {style} is {s["size"]} dp, under the minimum')


def lint_library(factions='auto'):
    L = Lint()
    for p in [SRC / 'base.rcss'] + sorted(SRC.glob('[0-9]*.rcss')):
        L.rcss(p, None, None, '')
    L.min_text_tokens()
    L.contrast(factions)
    return L


def lint_screen(folder, factions='none'):
    folder = Path(folder)
    L = Lint()
    manifest = json.loads((folder / 'screen.json').read_text(encoding='utf-8'))
    prefix = manifest.get('prefix', '')
    extra = manifest.get('lengths', {})
    for k in extra:
        if not prefix or not k.startswith(prefix.rstrip('-').replace('-', '_') + '_'):
            L.add('7 token names exist', 'screen.json', 0, f'screen length token "{k}" must start with the screen prefix ("{prefix}" -> "{prefix.rstrip("-")}_")')
    lib = library_classes()
    for f in manifest['files']:
        p = folder / f
        if f.endswith('.rcss'):
            L.rcss(p, extra, lib, prefix)
        elif f.endswith('.rml'):
            L.rml(p, extra, lib, prefix)
        elif f.endswith('.lua') and not f.endswith('_data.lua'):
            L.lua(p, lib, prefix)
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('paths', nargs='*', help='screen folders; default: the library and viewer/napoleon/board')
    ap.add_argument('--library', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--factions', default='auto', help='real factions extract (json) or "none"; default: find extract/napoleon/db')
    a = ap.parse_args()
    runs = []
    if a.library or not a.paths:
        runs.append(('library', lint_library(a.factions)))
    for p in a.paths or ([] if a.library else [str(ROOT / 'viewer' / 'napoleon' / 'board')]):
        runs.append((p, lint_screen(p)))
    findings = [dict(f, target=name) for name, L in runs for f in L.findings]
    if a.json:
        print(json.dumps({'findings': findings}, indent=1))
    else:
        for f in findings:
            print(f'lint: [{f["rule"]}] {f["target"]}:{f["file"]}:{f["line"]}: {f["message"]}')
        for name, L in runs:
            if hasattr(L, 'sweep'):
                n, adj, bad = L.sweep
                print(f'lint: library: grid sweep {n} colours, {adj} adjusted by the on-colour fix, {bad} failing; real factions: ' +
                      (f'{L.real[0]} rows, {L.real[1]} adjusted, {L.real[2]} failing' if L.real else 'extract not found, not checked'))
        print(f'lint: {len(findings)} finding(s)')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
