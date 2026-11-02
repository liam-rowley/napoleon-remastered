# J34 report: Design tokens and component library in RCSS

Built: D43's Engraved Plate language as code in `uikit/napoleon/`: one `tokens.json` (15 colours, 6 derived, 48 dp lengths, 9 type
styles), a `$token` build into three committed stylesheets, a 70-class component library with forced-state twin classes, vendored
OFL fonts pinned by sha256, a lint for the brief's 7 rules, a four-corner overflow gate, a change detector that honours Liam's lock,
and a board in the viewer showing every component in every state. Faction tint is CSS custom properties on the body, selected by one
class. No `core/` change. Branch `job/J34`. All runs 2026-11-02 on the PC.

## What exists
Everything is in `uikit/napoleon/` unless noted.
- **Tokens.** `tokens.json` is the single source and supersedes the draft: 15 colours, 6 derived colours, 48 lengths in integer dp,
  9 type styles (LANGUAGE.md section 3's 7 plus `tip_title` and `tip_body`), 109 `$token` names. Names have no spaces
  (`line (decorative)` is `line`; `focus_ring` is the colour, `focus_width` the length). Derived colours are computed by rule:
  `hover` is panel_raised mixed 8 % toward text_dim and `pressed` 14 % (tuned from 18 % because the pairs lint caught text_dim on
  pressed at 4.48:1); they differ from the draft's hand values by a few levels.
- **`tokens.py`.** Pure functions: `load_tokens`, `contrast`, `mix`, `derived_colors`, `expand` (comments skipped),
  `faction_tokens(r, g, b)`, `default_faction`, `faction_sheet`, `pair_report`.
- **`build.py`.** Expands `src/*.rcss` into `dist/base.rcss` (920 B), `library.rcss` (12592 B) and `factions_synthetic.rcss`
  (999 B), all committed; `--check` compares them, `--stats` prints counts, `faction-sheet <factions.json> <out.rcss>` is for J35 and
  J53. It also writes the generated `viewer/napoleon/board/board_data.lua` (swatches, contrast pairs, faction picker), covered by `--check`.
- **Library** (`src/base.rcss`, `10_text`, `20_panel`, `30_controls`, `40_content`): controls (button neutral/primary/toggled, tab
  and tab group, checkbox, round order button, ability slot, manoeuvre button); content (list row plain and hatched, tooltip,
  progress bar plain/segmented/semantic, card frame, divider, number badge, icon at 16/20/24/28 dp, flag slot, frame slot,
  scrollbars); plate and text (panel plate with header band and double rule, section head, stat row, the 7 text styles and text
  colours). Every pseudo-class rule has its twin class (`.is-hover`, `.is-pressed`, `.is-focus`, plus `.is-selected`,
  `.is-disabled`). `:focus-visible` works in 6.3, so no `:focus` fallback.
- **Fonts.** Libre Baskerville 400 and 700 (impallari commit 9852edf7) and Public Sans 400 and 600 (uswds release v2.001), static
  TTFs in `fonts/`, each pinned by sha256 in `fonts/SOURCES.json` with its OFL text. No fonttools dependency, no decision row needed.
- **Board.** `viewer/napoleon/board/` (`screen.json` with `library: true`, a prefix and a length-token list): every state of every
  component beside a live one, a panel plate sample, a faction picker, token swatches with generated contrast ratios and a
  long-label stress strip. Test glyphs `test_plus/chevron/ring.png` come from the committed `test_glyphs.py`.
- **Artifact (private):** https://claude.ai/artifact/42q3Z3Ao64K4FCZJbZN4Za (the route J31 proved; not opened live from the build
  session). Liam plays it and locks it; `LOCK.json` is not written.
- **`lint.py`.** All 7 brief rules (details in the README); `tests/test_uikit.py` has a failing fixture per rule. The library and
  the board lint clean. Faction sweep: 4096 colours, 110 adjusted by the fix, 0 failing. The real extract (read-only): 77 rows,
  0 adjusted, 0 failing; only counts are printed.
- **`gate.py`.** Renders the board at 1080p x 85 % (dp 0.85), 4K x 125 % (2.5), 3440x1440 x 100 % (1.333) and 1920x1200 x 100 %
  (1.111): 0 findings at all four corners. It caught a real bug (an inline image in the slots adding about 3 dp), fixed. A
  deliberately overflowing fixture screen is caught in the tests.
- **`changes.py`.** Compares `rgba_sha256` against the committed `baseline.json`; two runs give no change. It honours `LOCK.json`
  (`{"locked": [...]}`): a locked screen that changed prints CHANGED SINCE LOCK and exits non-zero, and `--accept` refuses without
  `--allow-locked`.
- **Viewer changes** (hello and `test_viewer` results unchanged): `viewer.cpp` gains `viewer_key` (Tab, Enter, Space, Escape,
  arrows), `viewer_overflow_json`, and `class`, `focus`, `focus_visible` in the element JSON; `viewer_host.js` forwards keys, makes
  sub-folders for staged files, records `viewerTimings` and names the page by the screen's title; `render.py` stages `uikit/` for
  `library: true`, expands `$tokens` in screen RCSS using the screen's own `lengths`, and finds fonts in `uikit/napoleon/fonts`.
- **Registry:** 5 new `engine_facts` rows (`viewer.rcss.custom_properties`, `faction_route`, `library_recipes`, `no_text_shadow`,
  `shadow_needs_background`); tools rows for build, gate, test_glyphs, tokens, lint, changes, board.lua and board_data.lua, plus the
  existing `render.py` and `viewer_host.js` rows updated.
- **CI.** `tools/changed_inputs.py` includes `uikit/` and `tests/test_uikit.py` in the viewer set; the viewer job in `gates.yml`
  also runs `tests.test_uikit`, `lint.py`, `gate.py` and `changes.py`. Risk: `test_render_is_deterministic` compares the PC baseline
  hash on the Linux runner; J31 proved PC and CI renders pixel-identical, but fonts are new here. If CI differs, accept the CI hashes.
- **`docs/plans/UI_PIPELINE.md`:** a result line in section 2.2; the section 3 slider line now names the four D19 corners.

## Numbers for the next jobs
| Item | Value |
|---|---|
| Tokens | 15 colours, 6 derived, 48 lengths, 9 type styles, 109 `$` names |
| Classes | 70 library classes |
| Stylesheets | base 920 B, library 12592 B, synthetic factions 999 B |
| Board document load (parse, style, first layout, headless SwiftShader) | about 43 ms at each corner |
| Wasm instantiation | 67 to 101 ms |

The Lua data model runs inside the document load.

## Faction route
CSS custom properties on the document body. Probed in the viewer: `var()` with fallback works in plain properties, shorthands and
box-shadow lists, and a `:hover` rule using `var()` follows the current value. `base.rcss` sets the default record (accent fill,
white); `faction_sheet` emits `body.fac-<name> { --fac; --on-fac; --fac-hover; --fac-pressed }`, and one class on the body selects a
faction. Same in the viewer and the J30 host (both RmlUi 6.3), no host colour maths, and a class change restyles once (nothing per
frame). The default is the generated sheet, written at install time by J35 and J53; the board uses `factions_synthetic.rcss`
(France, Britain and made-up colours only). Tests prove the picker sets `fac-france`, selects its button and shows `#094f96`. In Lua
use `element.style["--x"] = v` (`element:SetProperty` is nil in the Lua binding).

### The fixed on-colour case
`faction_tokens` moves the fill 2 % at a time away from the better on-colour until 4.5:1 is reached and returns `adjusted=True`
(e.g. (240, 0, 70): 4.38:1 to fill `#f10f51` at 4.50:1). The host must log the flag. The grid sweep (18 x 18 x 18 in the tests)
shows hover and pressed never lower the ratio and a passing colour is never touched. All 77 real rows pass untouched; rebel
factions follow the same rule.

## RCSS feature table
Full table in `uikit/napoleon/README.md`. Features J30's brief does not promise, for J30, J32 and J35 to confirm: `image-color`,
`transform: translateY`, and `border-radius` on the round order button. Layers, gradients, inset and outer box-shadow, opacity and
flex are covered by J30's list or are core.

## Evidence
- `uikit/napoleon/runs/20261102_j34/`: README, the four corner PNGs (0.53 MB), `spike/` (screen, `run_spike.py`, `results.txt`,
  `spike.png`). Wasm build on this branch: viewer.wasm sha256 `2bdc8a11...0f78` (2122957 bytes), viewer.js `21876236...dcd2`
  (97837 bytes), both in full in the run README; `rgba_sha256` per corner in the README and `baseline.json`.
- `tests.test_viewer` and `tests.test_uikit` pass on the PC (43 tests, with the wasm built). The wasm built first time in Docker and
  rebuilt incrementally three times for the C++ additions, none failing.
- Gates and policy (2026-11-02, final branch with the row set): full `python3 core/wsc.py gates`: 10 ok, 2 warn (the worktree hook path; skipped tests for numpy/Pillow and capstone), 0 failed; `jobs check`: 68 rows, ok. `tools/pr_policy.py --branch job/J34 --base origin/main` refuses only on the reviewer's part (no `review.md`, row not `done`).

## Deviations
- **No blurred drop shadow.** In the viewer an outer box-shadow with no background paints its box black, and a blurred or alpha
  outer shadow composites against black (`engine_facts` `viewer.rcss.shadow_needs_background`). The plate's `0 12 36 black 45 %` is
  a hard 6 dp offset in an opaque token, the section head has a background, and lint rule 6 refuses blur and outer alpha shadows.
  J30's D3D9 host may behave differently; J32 and J35 should try a blurred shadow before the rule is relaxed.
- **`text-shadow` is not a property in RmlUi 6.3.** The brief lists it as allowed; it is not used and lint bans it.
- **Badge text** is Public Sans 600, not LANGUAGE.md's 700: only 400 and 600 are vendored.
- **Header and section double rules** are inset shadows plus a border, not a border plus an offset shadow.
- **Hatched bar fill** is faction colour with white 28 % lines: a lighter tint of a variable colour is not possible in RCSS.
- **Screen length tokens:** a screen's own layout lengths go in `screen.json` `lengths` as `<prefix_>name`, so "no bare length"
  stays enforceable.
- **Overflow gate** exempts a scrolling or clipping ancestor per axis; the board scrolls only vertically, so horizontal clipping is
  still caught.
- **`viewer_host.js`** names the page from the screen's title.
- **No `uikit/core/`** (rule 76); no variable fonts or fonttools.
- **Report written by the orchestrating chat:** the build ran as a subagent whose harness refuses writing report files; the
  orchestrating chat (same Claude-Session) wrote this from the subagent's text, with Liam's approval (2026-11-02).

## What moves to the core later (proposed promotion row, not made)
`tokens.py` contrast, mix and tint maths plus `lint.py`'s rule engine (the token and class lists stay Napoleon's); `gate.py` and
`changes.py`; the viewer's library staging in `render.py` (`library`, `lengths`, `prefix`).

## Proposed decision row (unnumbered, for the reviewer to number)
**Napoleon UI tokens and faction route (J34).** `uikit/napoleon/tokens.json` is the single source of colours, dp lengths, type
styles and faction rules; RCSS is authored with `$token` names and expanded by `uikit/napoleon/build.py`. Faction tint is four CSS
custom properties on the document body (`--fac`, `--on-fac`, `--fac-hover`, `--fac-pressed`), selected by one class from an
install-time sheet. The on-colour rule gains a fix: when neither on-colour reaches 4.5:1 the fill is moved in 2 % steps until it
does and the host logs it. Reversible: yes.

## Open questions
1. **Rebel factions** tint by the same rule: all 13 rows pass and none looks wrong on the board.
2. **The 24 new sprites and 4 missing order-button states** are not drawn; the board's text-only and unselected-plus-focus-ring
   fallbacks stand. Liam must accept the sprites under D14. The three `test_*` glyphs are board-only.
3. **On-colour fix** changes a LANGUAGE.md rule for factions the game does not ship: the decision row above.
4. **Engine-drawn text face mismatch:** J33 names Libre Baskerville Bold, J37's brief recommends Lora, D42 uses Lora for the
   stop-gap. J37's call.
5. **Tooltip behaviour** (delay, placement, the middle-click lock) is the panel host's (J35); the library has only the visual and `.is-shown`.
6. **The board's lock** goes in `uikit/napoleon/LOCK.json` (`{"locked": ["board"]}`), written by whoever records Liam's lock.
   Should the board also get a `ui_elements` row? Not decided.
7. **Blurred plate shadow:** LANGUAGE.md asks for one. Keep the hard shadow, or does Liam want J30 to prove blur first?
8. **Flag slot size** defaults to 48x32 dp; J33 said keep vanilla sizes, not looked up.
