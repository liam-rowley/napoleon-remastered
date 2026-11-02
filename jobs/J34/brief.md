# J34: Design tokens and component library in RCSS

Phase 5, foundation (`docs/plans/UI_PIPELINE.md` section 2, step 2, second half). Turn the language Liam chose in J33 (D43: Engraved Plate
with full faction tint) into design tokens and a component library written in RCSS, show it on a component board in the review viewer with
every state, lint it, and gate it at the D19 corners. No screens (the first three are J35's proof and the screen rows after it), no panel
host, no in-game work, no new art (D14). The result is what every later screen is assembled from, so it is built to be changed safely:
a library change re-renders everything and reports what moved. Liam plays the board and locks it; this job does not lock it.

Model: Sonnet, no reason needed (D15 default: RCSS, Python and the viewer's existing tooling, no DLL or reverse engineering). Budget about 300
tool calls; at the cap, stop, commit, report what is left. Subagents only for independent read-only work. Waiting belongs to the harness:
one background call for the wasm build and the renders, never repeated polling.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J34`). Read `docs/DECISIONS.md` (D5 to D9, D14, D19, D37, D43), `docs/plans/UI_PIPELINE.md` sections
  2.2, 2.5, 3 (the `design` gate and "Library and token changes") and 4 (S1 and S2 results).
- `design/napoleon/LANGUAGE.md` is binding: palette, faction tint rule, type, ornament recipes, density, icon grid, and section 7, the list
  of components with their states and RCSS technique. `design/napoleon/tokens.draft.json` has the names and values; this job owns the final
  shape. The previews under `design/napoleon/previews/` still show C's keyline faction rule; LANGUAGE.md overrides them on faction colour.
- `jobs/J33/report.md` (the "Open questions" are yours below) and `jobs/J31/report.md` plus `viewer/README.md`: the viewer you build on.
  Read `viewer/pins.json` (RmlUi 6.3), `viewer/napoleon/hello/` (the only RCSS in the repo: it shows the missing user-agent base),
  `viewer/core/render.py` and `viewer/core/web/viewer_host.js` (how a screen is staged, sized and driven; the scale picker is D19's).
- `jobs/J30/brief.md` (queued, being built): the in-game host this library must also draw on. Its D3D9 render interface ports Empire's
  advanced features (layers, filters, clip masks, gradients, box-shadow); anything the library uses must be on that list or recorded as a
  risk for J32 and J35 (deliverable 8).
- Registry ids for what the library replaces or must cover: `campaign.region_details`, `common.unit_information`,
  `battle.land_battle_orders` (the three test screens whose widgets set the component list), `engine.unit_3d_preview` (an engine render
  target, so the library gives it a plain frame slot, nothing more), and the shared widgets `template.tab`, `template.checkbox` and
  `template.bottom`. Search first: `python3 core/wsc.py find rcss tokens viewer render font contrast`. No contrast or RCSS tool exists yet.
- Read-only anti-reference, `../empire-remastered`: `rml_mod/docs/UI_PERF.md` and `rml_mod/docs/PANEL_GUIDE.md` section "RmlUi gotchas".
  Learn from them, do not copy its tokens, names or chrome (D8). Two of its findings bind the library: never nest `flex: 1 1 auto`
  (relayout cost grows exponentially with depth; use `flex: 1 1 0` for growing items), and a hidden tooltip is `display: none`, not
  `opacity: 0`. Also: RmlUi data expressions have no `%`.

## Decisions already made for this job
- **Where things live.** `uikit/napoleon/`: `tokens.json` (the single source of every colour, length, type style and faction rule), `src/` (the
  library RCSS sources), the generated or final `library` stylesheets, `fonts/` (each face with its OFL text), `lint.py`, `changes.py`,
  `README.md` (the contract for J35 and for screen authors). The board is a viewer screen at `viewer/napoleon/board/` (own `screen.json`).
  No `uikit/core/` folder: it would trigger rule 76 (`PROMOTIONS` in `tools/verbs/jobs.py`); say in the report which parts are core
  candidates (lint, contrast and tint maths) and propose the promotion row, do not move them.
- **Components** (LANGUAGE.md section 7, each with normal, hover, pressed, disabled, selected, focus-visible where it has them): button
  (neutral, primary, toggled), tab and tab group, list row (plain, hatched even rows), tooltip, progress bar (plain and segmented), card
  frame, divider, number badge, plus what the three test screens need from section 5: panel plate with header band and double rule, section
  head, stat row (label, dotted or ruled gap, right-aligned numeral), checkbox, scrollbar, icon (tinted glyph slot at 16, 20, 24, 28 dp),
  round order button and ability slot and manoeuvre button (frame and art slot, art supplied by the screen), flag slot, text styles (the seven
  type styles of section 3 as classes). Nothing beyond this: a component a later screen needs is that screen's change to the library.
- **Tokens, final shape.** `tokens.json` supersedes the draft. Names use no spaces (the draft's `line (decorative)` becomes `line`), colours
  are hex, lengths are integers in dp, type styles are family, weight, size, line height. Derived values (`hover`, `pressed`) and the
  faction record (below) are computed by one tested Python function each, not typed twice.
- **Units and scale (D19).** Every length is `dp`; nothing else except `0`, `%` and unitless line-heights and `flex` values. Minimum text
  14 dp. One-pixel rules in dp are fine; the board is looked at at 1080p x 85 % where 1 dp is 0.85 px, so judge hairlines there.
- **Fonts (D7).** Libre Baskerville 400 and 700, Public Sans 400 and 600, as static TTFs (RmlUi's FreeType route; do not rely on variable
  fonts). Take the static files from the upstream releases or the pinned google/fonts commit that `viewer/napoleon/fonts/` already
  cites, pin each by sha256 in `uikit/napoleon/fonts/SOURCES.json`, keep the OFL text and the source URL beside them (they feed J38's
  `LICENSES.txt`). Instancing a variable font needs `fonttools` in the Python the tools use: that is a new dependency and needs a
  decision row (D41's pattern), so avoid it unless no static file exists, and then say so. Engine-drawn text is J37's.
- **Tokens reach RCSS through one build step** unless the evidence below says otherwise. Authoring format for the library and for screens is
  RCSS with `$token` references; `uikit/napoleon/build.py` expands them into the stylesheets the viewer and the host load (`--check`
  regenerates and compares, registered as a tool, run by the tests). Lint runs on the authoring files, so "tokens only" is a real rule: a
  hex colour or a bare length outside `tokens.json` and the build's own output fails. If step 1 of the order of work shows RmlUi 6.3 has
  CSS variables (`var()`), you may emit variables instead of values; either way the screen author's format is the same and the choice is an
  `engine_facts` row with the probe that decided it.
- **Faction tokens (the J33 open question).** Four values per screen from the owning faction's primary colour (`fac`, `on_fac`, `fac_hover`,
  `fac_pressed`), by LANGUAGE.md section 2, as one pure function `faction_tokens(r, g, b)` with host tests, plus the default record
  (no faction: `accent_fill` with white). How they reach RCSS is the open design point; settle it with the viewer, in this order, and record
  the result as an `engine_facts` row and in `uikit/napoleon/README.md`: (1) CSS variables set on the document body, if 6.3 supports them;
  (2) a generated faction sheet, one rule set keyed by a class on the document root (for example `fac-france`), loaded after the library,
  produced by a tool from the factions table at install time (J35 and J53 call it) and never committed with game values; the board and the
  gate use a small synthetic set of factions instead. Hover and pressed need pseudo-class rules, so inline `SetProperty` from Lua is not
  enough on its own. The route must work the same in the viewer and in the J30 host (plain RCSS, no host-side colour maths beyond writing a
  file or a variable) and must cost nothing per frame.
- **The on-colour rule has a hole; close it.** LANGUAGE.md picks `on_faction_dark` or white, whichever contrasts more, and checked all 77 real
  rows (lowest 4.75:1). The rule does not hold for every colour: over the whole RGB cube the best of the two falls to about 4.38:1 (for
  example 240, 0, 70), below the 4.5 limit, so a modded or future faction could be unreadable. `faction_tokens` must cope: when neither
  on-colour reaches 4.5, move the fill away from the better on-colour in 2 % steps until it does, return a flag saying the fill was
  adjusted, and log it at the host. Test it with a grid sweep, not only the 77 real colours. Do not alter any real faction (none needs it).
  Also confirm hover (12 %) and pressed (24 %) never lower the ratio, again by sweep.
- **Rebel factions.** Default: they tint by the same rule from their own primary colour (all 13 rows already pass). Do not special-case them.
  Raise it in the report as a Liam question only if the board shows it looks wrong.
- **No new art (D14).** The 24 sprites and the missing order-button states are not drawn here. The icon component takes a PNG and tints it
  with `image-color`; the board proves it with a few throwaway test glyphs generated by a committed script (plus, chevron, ring at 60 px,
  near-black on transparent, named `test_*` and never used by a real screen). Where a control would carry a glyph, the library also has the
  text-only form (LANGUAGE.md section 6 fallback). Whether Liam accepts the new sprites is his call, reported not decided here.
- **Forced states.** Every pseudo-class rule (`:hover`, `:active`, `:disabled`-style, `:focus-visible`) has a twin class (`.is-hover`,
  `.is-pressed`, `.is-disabled`, `.is-selected`, `.is-focus`) sharing the same declarations, so the board can show all states at once
  and so a screen can drive state from its model. Disabled is the control at 50 % opacity; focus-visible is the 3 dp ring in `focus_ring`
  (box-shadow, inset for list rows). If the viewer's RmlUi 6.3 lacks `:focus-visible`, fall back to `:focus` plus the twin class and say so.
- **RCSS the library may use:** borders, `box-shadow` (outer and inset), `linear-gradient` and `repeating-linear-gradient` decorators,
  `image-color`, `opacity`, `transform` (translate only), flex, `overflow`, `text-align`, `line-height`, `text-shadow`. Not allowed
  (RmlUi cannot draw them or J30 does not promise them): blur, backdrop filters, blend modes, clip-path, `outline`, `border-style: dashed`,
  `filter` other than none. If a recipe in LANGUAGE.md section 4 does not render in the viewer (the double rule from two box-shadow rings,
  the hatching), use the nearest recipe that does, record it in the README with the screenshot, and tell the report.
- **Perf and layout rules the library enforces** (lint where it can): no nested `flex: 1 1 auto`; hidden tooltips and collapsed content are
  `display: none`; no `*` selectors; no selector deeper than three levels; no `!important`. The user-agent base the hello-world showed
  missing (`display: block` for `div`, `body`, scrollbar parts, form controls) is in `src/base.rcss`, which every screen links first.
- **Lint** (`uikit/napoleon/lint.py`, registered, with tests that include a failing fixture per rule): reads a screen folder or the library and
  checks (1) tokens only (no literal colour, no length that is not a token or a layout length inside the allowed set), (2) library classes
  only, or classes starting with the screen's own prefix declared in its `screen.json` (an unknown class fails), (3) `dp` only, (4) text size
  at least 14 dp after resolving tokens, (5) contrast: every text-on-fill pair the library declares (`pairs` in `tokens.json`, 4.5 for text
  and fills, 3 for controls and icons) computed from the tokens, and the same for `fac`/`on_fac` over the synthetic faction set and the
  grid sweep; with the game's extract present it also checks all real factions and prints counts only (no values committed), (6) the
  perf and layout rules above, (7) the `$token` names exist. Output is readable text and `--json`; exit code is non-zero on any finding.
- **Corner gate** (`uikit/napoleon/gate.py` or an option of `render.py`, your choice; reuse `viewer/core/render.py`): renders the board at the
  four D19 corners: 1920x1080 at 85 %, 3840x2160 at 125 %, 21:9 (3440x1440 at 100 %), 16:10 (1920x1200 at 100 %). It fails on clipping or
  overflow found by the renderer, not by eye: any element box outside the viewport or outside its parent's content box (unless the parent
  scrolls), and text wider than its box (extend the viewer's element-box JSON in `viewer/core/src/viewer.cpp` if it cannot report that; the
  wasm rebuild is `viewer/core/build.sh --docker all`, as J31). UI_PIPELINE section 3 still says "slider 1.0, 1.5 and 2.0"; D19's 85 to 125 %
  wins, so correct that line when you add the S-style result line to section 2.2. The board includes a long-label stress strip.
- **"A library change re-renders and reports what changed"** (`uikit/napoleon/changes.py`): renders the board and every screen folder under
  `viewer/napoleon/` whose `screen.json` sets `"library": true` at the four corners, compares `rgba_sha256` with the committed
  `uikit/napoleon/baseline.json`, and prints which screens and corners changed; `--accept` rewrites the baseline. If `uikit/napoleon/LOCK.json`
  exists (Liam's lock, written by the step after this job, never by you), a locked screen that changed is printed as "changed since lock"
  and the tool exits non-zero without `--accept --allow-locked`. It is never silently demoted.
- **The viewer screen mechanism** (small change in this repo's viewer): `screen.json` gains `"library": true` (stage `uikit/napoleon/` build
  output under a fixed folder next to the screen, and the faction sheet if the route needs one), `"prefix"`, and a font list that can
  name `uikit/napoleon/fonts/` (today `render.py` reads only `viewer/napoleon/fonts/`). Keep `hello` working unchanged; `tests/test_viewer.py`
  stays green. The folder layout in the staged site is the layout J35 will install in game: record it in the README.
- **The board** (`viewer/napoleon/board/`): one screen, one section per component with every state laid out side by side (forced-state
  classes) and the live component beside it; a panel plate sample with header band, tabs, rows and bar; the text styles; the token swatches
  with their contrast ratios; the icon sizes tinted `text`, `on_fac`, `text_dim`; a faction picker (default, France, Britain, a very light
  faction fill, a very dark one, the synthetic 4.38 worst-case colour) that switches the tint live, so the route in the faction decision is
  exercised; the long-label stress strip. Interactive: hover, press, tab selection, row selection, toggle and keyboard focus work. Text on
  the board is English test text written for it; no loc strings and no db values.
- **Review by playing (D9, D17).** Publish the board as a private artifact the way `viewer/README.md` and D37 describe (`render.py
  --stage-only`, then the Artifact tool, private). Report the URL. Liam plays it and locks it in chat; do not set the job done on his behalf
  and do not write `LOCK.json`. If this session has no Artifact tool, stage the folder, give the local serve command, and say so.
- **Data rule (J7).** Loc text and decoded db row values are never committed. The only faction colours committed are France and Britain
  (already in LANGUAGE.md) and the synthetic test set; the 77-row check reads the git-ignored extract when present and prints counts.

## Order of work
1. Spike (about 30 calls): in the built viewer, probe on a scratch screen the RCSS the library relies on: `var()`, `image-color`,
   box-shadow outer and inset, `repeating-linear-gradient`, `:focus-visible`, `transform: translateY`, `text-shadow`, a variable-weight
   font, scrollbar part styling, `display: none` toggling. Source check first: the pinned RmlUi sources come from `viewer/core/fetch_sources.py`.
   Record the answers as `engine_facts` rows (verified with date and run, or open with owner). This settles the token route and the recipes.
2. `tokens.json`, `faction_tokens`, contrast helper and their tests; fonts vendored with their pins.
3. `build.py`, `src/base.rcss`, the library components, the viewer mechanism, the board.
4. `lint.py`, the corner gate, `changes.py`, baseline; registry rows and headers for every tool (tools gate), tests in `tests/`.
5. Publish the artifact; write the README, the report.

## Deliverables
1. `uikit/napoleon/`: `tokens.json`, the build step, library sources and generated stylesheets, base sheet, fonts with licences and pins,
   `README.md` for screen authors and for J35 (how a document links the library, the classes, the forced-state classes, the faction
   record and how a faction reaches the sheet, the staged folder layout, the RCSS features used, how to run lint, the gate and `changes.py`).
2. `faction_tokens` and the contrast helper as tested pure Python (grid sweep, France and Britain worked examples from LANGUAGE.md section 2,
   the adjusted-fill case, hover and pressed never lowering the ratio).
3. The board at `viewer/napoleon/board/`, its artifact (private) and its baseline renders at the four corners (committed under
   `uikit/napoleon/runs/<date>_j34/` with a README: build id of the wasm, sizes, `rgba_sha256` per corner; keep the total under 3 MB).
4. `lint.py` with tests (one failing fixture per rule), `gate.py` (or the render option), `changes.py` and `baseline.json`; all registered
   as tools with headers; the tests run in the `tests` gate and the corner gate and lint run in CI's `viewer` job where the wasm exists
   (extend `.github/workflows/gates.yml` and `tools/changed_inputs.py` only as far as J31 did, so `uikit/` changes trigger the job).
5. The viewer change for library screens and, if needed, element-box text overflow; `hello` and `tests/test_viewer.py` unchanged in result.
6. `engine_facts` rows for the RCSS feature probes and the faction route.
7. A short results line for UI_PIPELINE section 2.2 (as S1 and S2 have in section 4) and the slider line corrected; no other plan edits.
8. In the README, a table "RCSS features the library uses" (property, where used, viewer verdict) for J32 (parity) and J35 (host) to check
   against J30's render interface; mark each one that J30 does not yet promise.
9. `jobs/J34/report.md` (Finish), including the numbers the next jobs need: the token and class counts, stylesheet sizes and parse time of
   the board in the viewer, the faction route chosen and why, the fixed on-colour case, and a proposed decision row for Liam (the final token
   format and faction route), left unnumbered for the reviewer.

## PC test
None. `needs_pc` is false: no game launch, no watcher job, nothing written in a game folder. The wasm build and the Playwright renders run
as in J31 (Docker Desktop on the PC, or the same command in CI; the fallback is `gh run download <run> -n viewer-wasm`). Reading the
git-ignored extract for the 77-faction check is optional and read-only.

## Kill criteria
- The spike (order of work 1) shows RmlUi 6.3 cannot draw a recipe the library depends on (a state, the ring, the tint) and no nearby recipe
  works after 2 attempts: stop that component, record the engine fact, ship the rest, and report which LANGUAGE.md rule needs Liam.
- No faction route works in the viewer after 3 attempts (variables, generated sheet, and a third you can justify): stop, report the evidence,
  and propose the cheapest route that needs host work (J35); do not ship a tint that costs per-frame work.
- The wasm build or the headless render fails 3 times for a cause you did not introduce: stop, report the exact failure; do not retry.
- After about 200 tool calls the board does not yet show every component in every state: cut to the eight kit-strip components plus the panel
  plate, ship that as the library, and list the rest as follow-ups in the report.
- Liam asks for a different direction, or a change to the language itself (not a token value): stop and report; that is a new brief.

## Open questions
Written here so the builder does not stall; each has a default and goes in the report if it still stands.
- **Rebel factions tint?** Default yes, same rule (above). A Liam question only if it looks wrong on the board.
- **The 24 new sprites and 4 missing order-button states** need Liam's acceptance (D14, D43). Not drawn here; text-only fallback and the
  unselected sprite plus focus ring remain. Ask in the report; do not draw them.
- **On-colour rule fix** (fill adjusted when no on-colour reaches 4.5): default as above; a proposed decision row for Liam, since it changes
  a rule in LANGUAGE.md for factions the game does not ship.
- **Engine-drawn text face** (unit banners, map labels, `.cuf` route): J37's. J33's note names Libre Baskerville Bold; J37's brief recommends
  Lora (D42 uses Lora for the stop-gap). Out of scope here; mention the mismatch in the report.
- **Tooltip behaviour** (hover delay, placement, the "locked" middle-click variant if kept) is the panel host's (J35); the library provides
  the visual and the `display: none` / shown class only.
- **Where the board's lock lives** is `uikit/napoleon/LOCK.json`, written by whoever records Liam's lock; whether the board also gets a
  `ui_elements` row is not decided (the board is not a vanilla screen); raise it in the report.

## Finish
Write `jobs/J34/report.md`: what exists (files, tools, the artifact URL, run ids and wasm build id), the faction route and the evidence for
it, the corner-gate results, the RCSS feature table, deviations from this brief and why, what moves to the core later (lint, contrast and
tint maths, the viewer's library staging), and the open questions that still stand. Run `python3 core/wsc.py jobs check` and
`python3 core/wsc.py gates` before pushing; run the viewer tests where the wasm is built. Then
`wsc reg set jobs J34 status=review report=jobs/J34/report.md`.
