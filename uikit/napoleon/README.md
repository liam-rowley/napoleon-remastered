# uikit/napoleon: design tokens and the component library (J34)

The Napoleon design language (D43: Engraved Plate with full faction tint, `design/napoleon/LANGUAGE.md`) as tokens and an RCSS component
library, drawn by RmlUi 6.3. This README is the contract for screen authors and for J35 (the first screens and the panel host). Liam plays the
component board and locks it; `LOCK.json` is his (this job never writes it).

| File | What |
|---|---|
| `tokens.json` | the single source of every colour, length, type style and faction rule (names without spaces, hex, integer dp) |
| `tokens.py` | the token maths: derived colours, `$token` expansion, `faction_tokens(r, g, b)`, `contrast`, `faction_sheet` |
| `src/*.rcss` | the library sources (authoring format: `$token` names). `base.rcss` first, then `10_text`, `20_panel`, `30_controls`, `40_content` |
| `build.py` | expands the sources into `dist/` (committed): `base.rcss`, `library.rcss`, `factions_synthetic.rcss`; `--check` regenerates and compares |
| `lint.py`, `gate.py`, `changes.py` | the machine checks below; `test_glyphs.py` draws the three throwaway board glyphs |
| `fonts/` | Libre Baskerville 400, 700 and Public Sans 400, 600 as static TTFs, each pinned by sha256 in `SOURCES.json` with its OFL text |
| `baseline.json`, `runs/` | the render hashes of the board at the four corners, and the evidence of the J34 run |

The board is a viewer screen: `viewer/napoleon/board/` (`screen.json` with `"library": true`). Run everything with
`viewer/core/build.sh --docker all` once, then:

```sh
python3 uikit/napoleon/build.py --check              # dist is in step with src and tokens.json (the tests run it); no flag = rebuild
python3 uikit/napoleon/lint.py [screen dir]          # tokens only, library classes, dp only, text 14 dp, contrast, perf and layout, $token names
python3 uikit/napoleon/gate.py [screen dir ...]      # the four D19 corners: clipping and overflow found by the renderer
python3 uikit/napoleon/changes.py [--accept]         # which screens and corners changed against baseline.json
python3 -m unittest tests.test_uikit
python3 viewer/core/render.py viewer/napoleon/board --stage-only <dir>   # the folder a review artifact is published from
```

## Authoring a screen

A screen is a folder under `viewer/napoleon/<name>/` with `screen.json`:

```json
{"title": "...", "document": "x.rml", "library": true, "prefix": "rg-", "files": ["x.rml", "x.rcss", "x.lua"],
 "fonts": ["LibreBaskerville-Regular.ttf", "LibreBaskerville-Bold.ttf", "PublicSans-Regular.ttf", "PublicSans-SemiBold.ttf"],
 "lengths": {"rg_map_w": 320}}
```

- `library: true`: staging expands `$tokens` in the screen's `.rcss` files (the host install does the same with `build.expand_file`) and puts
  `uikit/base.rcss`, `uikit/library.rcss` and `uikit/factions_synthetic.rcss` beside the document. **That folder layout is the layout J35 installs in
  game** (`screen/uikit/*.rcss`, fonts in `fonts/`); a game install replaces `factions_synthetic.rcss` with a sheet made from the factions table.
- The document links `uikit/base.rcss`, then `uikit/library.rcss`, then a faction sheet, then its own `.rcss`:
  `<link type="text/rcss" href="uikit/base.rcss"/>`. `base.rcss` is the user-agent base RmlUi lacks (`display: block` for the usual tags, `box-sizing`, body font and colour).
- `prefix`: classes of the screen's own start with it (`rg-`); every other class must be a library class (lint rule 2). `lengths`: layout lengths the tokens
  do not have, as `<prefix with _>_name` (`rg_map_w`), used as `$rg_map_w`; no other bare length is allowed (rule 1). Percent, `0` and unitless numbers are free.
- `fonts` may name `viewer/napoleon/fonts/` or `uikit/napoleon/fonts/` files. Engine-drawn text (banners, labels: J37) is not this library's. J33 names Libre Baskerville
  Bold for it, J37's brief recommends Lora and D42 uses Lora for the stop-gap: a mismatch for Liam, not settled here.

### Tokens

`$name` expands at build: colours to hex (`$panel`, `$text`, `$hover`, `$pressed`, ...), lengths to `Ndp` (`$row` 30, `$control_height` 36, `$gap` 8, ...),
type styles to `$type.<style>.family|weight|size|line` (`$type.label.size`), faction tokens to custom properties (`$fac` -> `var(--fac)`, `$on_fac`, `$fac_hover`,
`$fac_pressed`). `python3 uikit/napoleon/tokens.py names` lists them. Derived colours come from rules in `tokens.json` (`hover` and `pressed` are mixes
of `panel_raised` and `text_dim` at 8 and 14 percent; the draft's hand-typed values differed by at most a few levels). `tokens.json` counts: 15 colours,
6 derived colours, 48 lengths, 9 type styles (the seven of section 3 plus `tip_title` and `tip_body`), 109 token names.

### Classes and forced states

70 library classes (`python3 uikit/napoleon/build.py --stats`): text styles `.t-title .t-section .t-body .t-label .t-desc .t-numeral .t-big` and colours `.c-dim .c-accent
.c-pos .c-neg .c-warn`; layout `.flex-row .flex-col .grow .is-hidden`; `.panel .panel-head .panel-body .section-head .divider .stat-row .stat-label .stat-gap .stat-val`;
`.btn .btn-primary .tab-group .tab .check .check-mark .order-btn .ability-slot .manoeuvre-btn .slot-art`; `.list-hatch .list-row .tooltip .tooltip-title .bar .bar-fill
.seg .seg-cell .card .card-top .card-body .badge .icon .icon-s|m|l|xl .icon-on-fac .icon-dim .flag-slot .frame-slot`; scrollbars by tag.

Every pseudo-class rule has a twin class with the same declarations: `:hover` and `.is-hover`, `:active` and `.is-pressed`, `:focus-visible` and `.is-focus`, plus
`.is-selected`, `.is-checked`, `.is-disabled` (50 percent opacity, `pointer-events: none`), `.is-hatch`, `.is-shown` (tooltip), `.is-on`, `.is-positive|negative|warning`,
`.is-ruled`, `.is-negative` (badge). A screen drives state from its model with the twin class; the board shows them all at once. `:focus-visible` works in 6.3 (the
fallback to `:focus` was not needed); controls carry `tab-index: auto`, and a mouse click does not set it, a Tab key press does.

A control's fill is `--fill` on the element, and the frame's inner rings read it, so a state changes one property. A tooltip hides with `display: none`
(never opacity 0) and shows with `.is-shown`; where it goes and when it appears is the panel host's (J35).

### The faction route (the J33 open question)

`faction_tokens(r, g, b)` returns `fac`, `on_fac`, `fac_hover`, `fac_pressed` (hex), `adjusted` and `ratio` from a faction's primary colour: `on_fac` is `#0b0f16` or
white, whichever contrasts more; hover and pressed move the fill 12 and 24 percent away from `on_fac`, so the ratio only rises. **The hole in the rule is closed:** when neither
on-colour reaches 4.5 (the best of the two falls to about 4.38 over the RGB cube, for example 240, 0, 70) the fill is moved away from the better on-colour in 2 percent steps until it
does and `adjusted` is true (the host logs it). Checked by an 18 x 18 x 18 grid sweep in the tests (16 x 16 x 16 in lint) and, when the git-ignored extract is present, over the 77 real rows
(0 adjusted, 0 failing; counts only are printed).

How the record reaches RCSS: **custom properties on the document body** (route 1; see `engine_facts` `viewer.rcss.custom_properties` and `viewer.rcss.faction_route`).
`base.rcss` sets the default record (accent fill, white). A faction sheet from `tokens.faction_sheet(records)` (or `build.py faction-sheet <factions.json> <out.rcss>`) has one
rule per faction, `body.fac-<name> { --fac: ...; --on-fac: ...; --fac-hover: ...; --fac-pressed: ...; }`, loaded after the library; the screen picks the faction with one
class on the body (`document:SetClass("fac-france", true)`) or, with no sheet, `body.style["--fac"] = ...` from Lua (`element.style`, not `SetProperty`). Hover and pressed are ordinary pseudo-class rules reading
`var(--fac-hover)`, so nothing runs per frame. The sheet is made at install time (J35, J53 call it) and is never committed with game values; the board uses
`factions_synthetic.rcss` (France, Britain and made-up colours only).

## What the machines check

- **lint** (`lint.py`, rules numbered as in the brief; one failing fixture per rule in `tests/test_uikit.py`): 1 tokens only (no literal colour, no bare length); 2 library classes or the
  screen prefix (RML `class=`, `data-class-*`, Lua `SetClass`); 3 `dp` only; 4 text at least 14 dp after resolving tokens; 5 contrast (every pair in `tokens.json`
  `pairs`, hover/pressed, the synthetic factions, the grid sweep, the real rows when present); 6 perf and layout (no `flex: ... auto`, no `opacity: 0`, no `*`, selectors at most three
  deep, no `!important`, no `filter`/`backdrop-filter`/`clip-path`/`outline`/`text-shadow`/dashed borders, no blurred or outer-alpha box-shadow); 7 `$token` names exist.
- **gate** (`gate.py`): the board at 1080p x 85 % (dp 0.85), 4K x 125 % (2.5), 21:9 3440x1440 x 100 % (1.333), 16:10 1920x1200 x 100 % (1.111). The renderer
  (`viewer_overflow_json` in `viewer/core/src/viewer.cpp`) reports any border box outside the viewport or outside a non-scrolling parent's content box (per axis; absolute elements against the
  viewport only), and content wider or taller than its own box. A scrolling or clipping ancestor exempts what is inside it on that axis.
- **changes** (`changes.py`): re-renders the board and every library screen at the four corners and compares `rgba_sha256` with `baseline.json`; `--accept` rewrites it. When
  `LOCK.json` (`{"locked": ["board"]}`, Liam's) names a screen that changed, the tool prints `CHANGED SINCE LOCK` and exits non-zero, and `--accept` refuses without `--allow-locked`: a locked screen is never silently demoted.

## RCSS features the library uses (for J32 parity and J35 host)

J30's brief promises a D3D9 render interface with layers, filters, clip masks, gradients and box-shadow. "Not promised" marks a feature outside that list for J30 to confirm.

| Property or feature | Where | Viewer (RmlUi 6.3, `engine_facts`) | J30 |
|---|---|---|---|
| custom properties, `var()` with fallback | `--fill` on controls, the four faction tokens | works, also in shorthands and box-shadow lists | core only, no render dependency |
| `box-shadow` outer, hard edge, opaque, on a filled element | plate rings, tooltip | works | promised; **try blur before relaxing lint rule 6 (viewer draws blur and alpha outer shadows against black)** |
| `box-shadow: inset` (rings, header rule, section head) | frames, `.panel-head`, `.section-head`, focus rings | works, with or without alpha | promised |
| `decorator: repeating-linear-gradient` (135 deg, 90 deg) | hatched rows and bars, dotted stat gap, frame slot | works | promised (gradients) |
| `image-color` | `.icon`, slot art tint | works | **not promised** (a vertex colour on a textured quad: confirm) |
| `transform: translateY` | pressed button, order button, slots | works | **not promised** (needs `SetTransform`) |
| `opacity` | `.is-disabled` | works | layers promised |
| `border-radius` | `.order-btn` (28 dp) | works | **not promised** (plain geometry in core; confirm) |
| `display: flex`, `flex-wrap`, `flex: 1 1 0` | rows, tab groups, stat rows, board grid | works (layout is RmlUi's own) | core only |
| `overflow-y: auto`, scrollbar parts | list boxes, board page | works | clip masks promised |
| `:hover`, `:active`, `:focus-visible` + `tab-index: auto`, `pointer-events: none`, `cursor` | controls | works; Tab key sets focus-visible | core only |
| `display: none` for hidden | `.tooltip`, `.check-mark`, `.is-hidden` | works | core only |
| static TTF by family and weight | four faces | works | FreeType path as Empire |

Not used and not allowed: blur, backdrop filters, blend modes, clip-path, `outline`, dashed borders, `filter`, `text-shadow` (6.3 has none), percent in data expressions.

### Recipes that differ from LANGUAGE.md (nearest recipe that renders)

- **Plate drop shadow:** `0 12 36 black 45 %` becomes a hard shadow `0 6 0 5` in the opaque `shadow` token (`mix(bg_deep, text, 0.3)`): a blurred or alpha outer shadow
  composites against black in the viewer (`engine_facts` `viewer.rcss.shadow_needs_background`). A blur may come back if J30's host proves it.
- **Header band double rule:** inset shadows inside the band plus a bottom border (two 1 dp rules in `on_fac` 1 dp apart) instead of a border plus an offset shadow.
- **Section head double rule:** a bottom border and an inset ring; the head needs a `panel` background (an outer shadow on a transparent element draws black), so it sits on paper.
- **Badge text:** Public Sans 600 (the Label style) not 700: only 400 and 600 are vendored (the brief).
- **Hatched bars:** the fill is the faction colour with 1 dp lines of white at 28 percent (`hatch_bar`), because RCSS cannot mix a lighter tint of a variable colour.

## Perf and layout rules the library follows

`flex: 1 1 0` for growing items (never nested `1 1 auto`: Empire's relayout finding), hidden is `display: none`, no `*` selectors, selectors at most three levels, no
`!important`; the board's page is one scroller with `flex-wrap` rows. Long labels are not truncated (no ellipsis in RmlUi): a screen sizes its columns, and the corner gate fails it when a
label does not fit.

## Core candidates (proposed promotion rows, not moved: rule 76)

`tokens.py` contrast and tint maths (game-agnostic), `lint.py` (the rule engine; the token and class lists are Napoleon's), `gate.py` and `changes.py` (the renderer loop and baseline
compare), and the viewer's library staging in `render.py` (`library`, `lengths`, `prefix`). A `uikit/core/` promotion would be a warscape-core PR.
