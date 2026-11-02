#!/usr/bin/env python3
"""The token maths of the Napoleon design language: load tokens.json, derive colours, expand $token references, faction tokens, contrast.

purpose: load uikit/napoleon/tokens.json, derive hover/pressed and the other computed colours, expand $token references in RCSS, compute the four faction tokens (with the on-colour fix) and WCAG contrast
usage: python3 uikit/napoleon/tokens.py [pairs | faction R G B | names]   (import it from build.py, lint.py and the tests: faction_tokens, contrast, expand, load_tokens)
when: any time a colour, a ratio or a faction record is needed; the host-side faction sheet at install time (J35, J53) calls faction_sheet; game-agnostic maths, a core candidate (J34 report)
not-a-verb: pure functions plus a tiny CLI for looking at the numbers, not a registry operation
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOKEN_RE = re.compile(r'\$([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*)')
COMMENT_OR_TOKEN = re.compile(r'/\*.*?\*/|' + TOKEN_RE.pattern, re.S)
HEX_RE = re.compile(r'^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')


def load_tokens(path=None):
    return json.loads(Path(path or HERE / 'tokens.json').read_text(encoding='utf-8'))


# ---- colour maths -------------------------------------------------------------------------------------------------

def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb, alpha=None):
    s = '#%02x%02x%02x' % tuple(int(v) for v in rgb)
    return s + ('%02x' % alpha) if alpha is not None else s


def _rgb(c):
    return hex_to_rgb(c) if isinstance(c, str) else tuple(c)


def luminance(c):
    """WCAG 2.x relative luminance of an sRGB colour (hex or (r, g, b))."""
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in _rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG contrast ratio of two colours (1..21)."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _round(x):
    return int(math.floor(x + 0.5))


def mix(a, b, t):
    """a moved t (0..1) of the way to b, per channel, rounded to integers."""
    ra, rb = _rgb(a), _rgb(b)
    return tuple(_round(x + (y - x) * t) for x, y in zip(ra, rb))


def alpha_hex(c, a):
    """#rrggbbaa for colour c at alpha a (0..1)."""
    return rgb_to_hex(_rgb(c), _round(255 * a))


def derived_colors(tokens):
    """name -> hex for the 'derived' block of tokens.json (mix of two colour tokens, or a colour with alpha)."""
    out = {}
    for name, rule in tokens['derived'].items():
        if 'mix' in rule:
            a, b, t = rule['mix']
            out[name] = rgb_to_hex(mix(tokens['color'][a], tokens['color'][b], t))
        elif 'alpha' in rule:
            c, a = rule['alpha']
            out[name] = alpha_hex(tokens['color'][c], a)
        else:
            raise ValueError(f'derived {name}: unknown rule {rule}')
    return out


def all_colors(tokens):
    return {**tokens['color'], **derived_colors(tokens)}


# ---- faction tokens -----------------------------------------------------------------------------------------------

def faction_tokens(r, g, b, tokens=None):
    """The four per-screen faction tokens from a faction's primary colour (LANGUAGE.md section 2, plus the hole fix).

    fac = the fill; on_fac = on_faction_dark or on_faction_light, whichever contrasts more; fac_hover / fac_pressed = the fill moved
    12 % / 24 % away from on_fac (towards white under dark text, towards black under white text), so the ratio only rises.
    When neither on-colour reaches min_ratio (4.5; the best of the two falls to about 4.38 over the RGB cube) the fill is moved away from
    the better on-colour in 2 % steps until it does, and `adjusted` is True (the host logs it). Returns hex strings plus `adjusted`,
    `ratio` (on_fac over fac) and `fill_in` (the colour that came in).
    """
    tokens = tokens or load_tokens()
    f = tokens['faction']
    colors = tokens['color']
    dark, light = hex_to_rgb(colors[f['dark_on']]), hex_to_rgb(colors[f['light_on']])
    fill = (int(r), int(g), int(b))
    fill_in = fill
    cd, cl = contrast(fill, dark), contrast(fill, light)
    on = dark if cd >= cl else light
    adjusted = False
    if max(cd, cl) < f['min_ratio']:
        target = (255, 255, 255) if on == dark else (0, 0, 0)
        k = 0
        while contrast(fill, on) < f['min_ratio']:
            k += 1
            fill = mix(fill_in, target, f['adjust_step'] * k)
        adjusted = True
    away = (255, 255, 255) if on == dark else (0, 0, 0)
    return {
        'fac': rgb_to_hex(fill), 'on_fac': rgb_to_hex(on),
        'fac_hover': rgb_to_hex(mix(fill, away, f['hover_step'])), 'fac_pressed': rgb_to_hex(mix(fill, away, f['pressed_step'])),
        'adjusted': adjusted, 'ratio': round(contrast(fill, on), 2), 'fill_in': rgb_to_hex(fill_in),
    }


def default_faction(tokens=None):
    """No faction set: accent_fill with white (LANGUAGE.md section 2); hover and pressed by the same rule."""
    tokens = tokens or load_tokens()
    rec = faction_tokens(*hex_to_rgb(tokens['color'][tokens['faction']['default_fill']]), tokens=tokens)
    rec['on_fac'] = tokens['color'][tokens['faction']['default_on']]
    return rec


def faction_decls(rec, tokens=None, indent='\t'):
    """The custom-property declarations of a faction record, one per line."""
    tokens = tokens or load_tokens()
    return ''.join(f'{indent}{prop}: {rec[key]};\n' for key, prop in tokens['faction']['vars'].items())


def faction_sheet(records, tokens=None):
    """RCSS that sets the faction record per class on the document body: `body.fac-<name> { --fac: ...; }`.

    `records` = {name: (r, g, b)}. Output is plain RCSS (loaded after the library); a fill the on-colour fix adjusted is listed in a
    comment so the caller can log it. Names are lowercased and anything but [a-z0-9_-] becomes '-'. Never commit a sheet made from game data.
    """
    tokens = tokens or load_tokens()
    out = ['/* generated by uikit/napoleon/tokens.py faction_sheet: one rule per faction, selected by a class on the document body */\n']
    for name in sorted(records):
        rec = faction_tokens(*records[name], tokens=tokens)
        cls = re.sub(r'[^a-z0-9_-]', '-', name.lower())
        out.append(f'/* {cls}: on_fac ratio {rec["ratio"]}' + (f', fill adjusted from {rec["fill_in"]}' if rec['adjusted'] else '') + ' */\n')
        out.append(f'body.fac-{cls} {{\n' + faction_decls(rec, tokens) + '}\n')
    return ''.join(out)


# ---- $token expansion ---------------------------------------------------------------------------------------------

def token_values(tokens, extra=None):
    """Every $name the authoring format knows -> the text it expands to. `extra` = a screen's own length tokens ({name: dp}) from its screen.json."""
    vals = {}
    for k, v in (extra or {}).items():
        vals[k] = '0' if v == 0 else f'{v}dp'
    for k, v in all_colors(tokens).items():
        vals[k] = v
    for k, v in tokens['length'].items():
        vals[k] = '0' if v == 0 else f'{v}dp'
    for style, t in tokens['type'].items():
        vals[f'type.{style}.family'] = f'"{t["family"]}"'
        vals[f'type.{style}.weight'] = str(t['weight'])
        vals[f'type.{style}.size'] = f'{t["size"]}dp'
        vals[f'type.{style}.line'] = f'{t["line"]}dp'
    for k, prop in tokens['faction']['vars'].items():
        vals[k] = f'var({prop})'
    return vals


def expand(text, tokens=None, where='input', extra=None):
    """Replace every $name in RCSS text; an unknown name raises ValueError naming it and the line."""
    vals = token_values(tokens or load_tokens(), extra)

    def sub(m):
        if m.group(0).startswith('/*'):   # comments are left alone (they may mention $names)
            return m.group(0)
        if m.group(1) not in vals:
            line = text.count('\n', 0, m.start()) + 1
            raise ValueError(f'{where}:{line}: unknown token ${m.group(1)}')
        return vals[m.group(1)]
    return COMMENT_OR_TOKEN.sub(sub, text)


def pair_report(tokens=None):
    """[(fg, bg, min, ratio, ok, what)] for every declared text-on-fill pair."""
    tokens = tokens or load_tokens()
    colors = all_colors(tokens)
    rows = []
    for p in tokens['pairs']:
        fg, bg = colors[p['fg']], colors[p['bg']]
        ratio = contrast(fg[:7], bg[:7])
        rows.append((p['fg'], p['bg'], p['min'], round(ratio, 2), ratio >= p['min'], p['what']))
    return rows


def main(argv):
    t = load_tokens()
    cmd = argv[0] if argv else 'pairs'
    if cmd == 'pairs':
        for fg, bg, mn, ratio, ok, what in pair_report(t):
            print(f'{"ok " if ok else "FAIL"} {fg:>17} on {bg:<13} {ratio:>6.2f} (min {mn}) {what}')
    elif cmd == 'faction' and len(argv) == 4:
        print(json.dumps(faction_tokens(*(int(v) for v in argv[1:4]), tokens=t), indent=1))
    elif cmd == 'names':
        print('\n'.join(sorted(token_values(t))))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
