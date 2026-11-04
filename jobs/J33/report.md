# J33 report: Napoleon design language

Branch `job/J33`. Liam picked direction C (Engraved Plate) with full faction tint; the language is written down for J34 in
`design/napoleon/LANGUAGE.md` and recorded as D43. The exploration was never translated into the build: only the chosen rules survive.

## What was built
- **Review artifact (private):** https://claude.ai/artifact/5oWteGo6hWYQHfseLQrn29, a plain HTML artifact with an overview, a page
  per direction (A, B, C) and a "before" page.
  - Each direction page has its stance and token and type tables with contrast ratios, and the kit strip (button in all states
    including focus-visible, tab, list row, tooltip, progress bar, card frame, divider, number badge).
  - It draws the three test screens (`campaign.region_details`, `common.unit_information`, `battle.land_battle_orders`) at 1080p x
    100 % and at the 4K x 125 % corner (frame 1536x864 dp, 1 dp = 2.5 px, with a pixel-view toggle), each with a data-case switcher.
  - It shows the unit popup with France and Britain side by side for the faction question. Hover, pressed, disabled, selected and
    focus-visible are forced on specific controls and are also live.
  - The artifact is the only home of the HTML source; the source is not committed (brief rule).
- **Committed:**
  - `design/napoleon/directions/a.md`, `b.md`, `c.md` (about 7 KB each): stance, palette table with ratios, type scale and
    licences, ornament recipes in RCSS terms, density, iconography, per-screen changes, new-art cost, data cases by key and id,
    faction answer.
  - `design/napoleon/previews/` (18 JPEGs, 2.28 MB): per direction the three screens, the unit popup at the 4K x 125 % corner, the
    kit strip and the faction pair.
  - `design/napoleon/LANGUAGE.md` and `tokens.draft.json` (the pick), and decision row D43.
- **Data and art:** loc text decoded read-only from the game packs into the worktree's git-ignored `extract/napoleon/loc/` (the
  worktree had no `/extract`); db rows from the main checkout's extract; art is the J36 2.5x masters from
  `C:\napoleon_remastered_pc\upscale\work\out`, read-only; the vanilla "before" shots are `harness/runs/20261102_j10pc/shots/`. The
  throwaway scripts (data probe, art export, page build, renderer, contrast, md generators) live in the git-ignored `_scratch/`.
  Strings and values appear only in the private page and the preview images; committed files carry keys, table and field names, ids
  and sizes.

## The pick
Liam answered in chat on 2026-11-02, in his words: "C, Engraved Plate" to "Which direction becomes the Napoleon design language?",
and "Full tint" to "Should the chrome show faction colour?" (option text: "Header band, selected tab, primary button and bars take
the faction colour."). No revision round was asked. Decision row: D43. The result is C's palette, type, ornament, density and
iconography with B-style full faction tinting instead of C's keyline.

### Faction on-colour rule for C (worked out after the pick)
- Source: the factions table `primary_colour_r/g/b`. `on_fac` is near-black `#0b0f16` or white, whichever gives the higher
  contrast, always solid (the ink `text` token `#1a2230` as the dark option would fail `ita_trent` at 4.0:1 and `crimean_khanate`
  at 4.23:1). Hover and pressed move the fill 12 % and 24 % away from the on-colour, so contrast only rises. Every faction fill is
  drawn with a 1 dp `control_border` outline.
- Over all 77 factions (64 non-rebel, 13 rebel): 46 take white, 31 take dark; lowest on-colour ratio 4.75:1, hover 5.81:1, pressed
  7.05:1. No faction fails and none needs its colour altered. 28 light faction fills sit below 3:1 against the paper panel; the
  outline rule covers them (LANGUAGE.md section 2 lists them). France `#094f96` with white 8.17:1; Britain `#de0000` with white
  5.11:1; no faction set: `accent_fill` with white.
- `fac` applies to the header band, selected tab, primary button, non-semantic bar fills, selected row, number badge and card top
  edge; everything else stays neutral, and semantic colours never tint.

## How the directions differed
| | A Staff Map | B Regimental Facings | C Engraved Plate (picked) |
|---|---|---|---|
| Palette | cool slate ink, chalk text, seal-red accent | charcoal, warm-white text, brass default, faction facing fills | cool paper, ink text, ink-blue accent |
| Type | Spectral + Source Sans 3 | Barlow Condensed (caps) + Barlow | Libre Baskerville + Public Sans |
| Ornament | hairlines, tick corners, ruled grid | facing band with piping, studs, thick keylines | double rules, hatching, plate corners |
| Density | compact, row 24 dp | roomy, row 36 dp | medium, row 30 dp |
| Icons | new line set, about 50 sprites | new bold badge glyphs, about 50 sprites | vanilla colour art kept, about 24 new sprites |
| Faction (as drawn) | neutral | full tint | keyline only (Liam changed this to full tint) |

## Contrast numbers
Computed with a throwaway script (no tool in the tools registry does contrast). WCAG ratios; text and fills need 4.5, controls and icons 3.
- **A:** text 14.08, text_dim 7.87, accent_fill with white 5.10, accent_text 8.00, positive 9.16, negative 7.43, warning 10.31,
  control_border 4.50, focus_ring 8.77.
- **B:** text 14.82, text_dim 8.24, accent_fill with dark text 8.29, accent_text 9.82, positive 9.82, negative 7.46, warning
  10.58, control_border 5.05, focus_ring 16.88, France facing with white 8.17, Britain facing with white 5.11.
- **C:** text 14.35, text_dim 6.51, accent_fill with white 8.31, accent_text 8.16, positive 5.93, negative 6.71, warning 5.33,
  control_border 11.11, focus_ring 5.30.
- **C with full faction tint:** see "Faction on-colour rule for C" above.
- Min text is 14 dp everywhere in the mock-ups; three review-page notes (the kit label, the render-target caption and a 12 px
  preview caption) are annotations, not shipped UI.

## Evidence
- Local Chrome renders of every screen, case and corner (headless Chrome, device scale factor 2.5 for the corner); the previews are
  those images.
- 2026-11-02: `python3 core/wsc.py jobs check`: 67 rows, ok; `python3 core/wsc.py gates --fast`: 10 ok, 1 warn (the worktree's
  `core.hooksPath` is absolute, an environment warning), 0 failed.
- 2026-11-02, final branch with the row set: full `python3 core/wsc.py gates`: 10 ok, 2 warn (the hook path, and skipped tests for numpy/Pillow, capstone and the viewer wasm), 0 failed. `tools/pr_policy.py --branch job/J33 --base origin/main` refuses only on the reviewer's part (no `review.md`, row not `done`).
- Route used: a plain HTML artifact. Calls used: about 135 of the 250-call budget; no kill criterion was triggered.

## What was left out and why
- No RCSS, Lua or viewer work (J34's). No `LICENSES.txt` entries (J38): the font sources and OFL 1.1 licences are named in
  LANGUAGE.md section 3 and in the directions files.
- No second revision round and no fourth direction. The campaign map, unit banners and any screen beyond the three are untouched (D14).
- The previews still show C with the keyline faction rule; LANGUAGE.md overrides them on faction colour and says so.

## Deviations
- **Plain HTML artifact instead of a Claude Design canvas.** The quickstart listed a Design type and one was created
  (https://claude.ai/artifact/Vk56bxT5HdF3sakNth4KFu), but its format forbids script-built UI, and the three directions are
  generated from one data set so they stay comparable. The Design canvas is an empty private shell, left undeleted (brief: delete
  nothing); Liam can remove it.
- **`region_details` is not tabbed.** The brief calls it a "tabbed info panel", but the atlas shows three stacked panes (Public
  Order, Region Wealth, Population) and no tab group; it is drawn as in the atlas, with tab states on the `unit_information` tabs and
  in the kit strip.
- **B changes the region panel layout** to two columns (a stated per-direction change). C, the pick, keeps three stacked sections.
- **The directions files, LANGUAGE.md and tokens.draft.json were generated by scripts** (`_scratch/gen_md.py`,
  `_scratch/gen_language.py`) so the numbers match the tokens exactly.
- **The order button size in LANGUAGE.md is 56 dp** (the J36 140 px master drawn 1:1 at 2.5x); the review mock-up drew 60 dp.
- **`origin/main` was merged into the branch** (main had moved to D42) before D43 was added.
- **Region numbers are placeholders** on the page (public order, wealth, tax and population): the db holds rules, not values.
- **Report written by the orchestrating chat:** the build ran as a subagent whose harness refuses writing report files; the
  orchestrating chat (same Claude-Session) wrote this from the subagent's text, with Liam's approval (2026-11-02). Liam's pick was
  relayed to the subagent by the orchestrating chat.

## What moves to the core later
Nothing expected. The contrast and tint check would be a candidate for a core helper if another game reuses the faction on-colour rule.

## Open questions
- **Region numbers:** the contract stage must supply real public order, wealth, tax and population values and fixtures; the review
  used placeholders.
- **New art needs Liam's acceptance (D14):** about 24 sprites for C (12 ability and manoeuvre glyphs, 4 missing state sprites for
  halt selected, move speed roll/depress/selected, group depress, plus kit glyphs). If refused, the fallbacks are the unselected
  sprite plus the focus ring, and text-only buttons.
- **J34 must settle** how `fac`, `on_fac`, `fac_hover` and `fac_pressed` reach RCSS: there is no `color-mix` and no per-screen CSS
  variables, so they are per-screen values computed once by the host (J35). RmlUi's `image-color` tint and the box-shadow focus ring
  were assumed available in the pinned 6.3 and must be confirmed in the viewer.
- **Engine-drawn text face:** LANGUAGE.md names Libre Baskerville Bold instanced to a static TTF; J37 confirms it fits the `.cuf`
  route and whether a sans is also needed for small engine text (J37's brief currently recommends Lora).
- **Faction colour source:** only `primary_colour_*` is used; the alternates and the 13 rebel rows follow the same rule, but J34
  should decide whether rebel factions tint at all.
- **Unit and region data checks:** the db did not give a longest settlement name; only region names were measured (20 and 19 characters).
- **D43 numbering:** taken on this branch with main at D42; if another branch lands a D43 first, renumber here.
