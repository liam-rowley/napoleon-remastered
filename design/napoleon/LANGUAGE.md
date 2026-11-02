# Napoleon design language: Engraved Plate with full faction tint

Chosen by Liam on 2026-11-02 (decision row in `docs/DECISIONS.md`): direction **C, Engraved Plate**, with the chrome showing faction colour (**full tint**), not C's original keyline-only rule. Review record: `design/napoleon/directions/c.md` and `previews/c_*.jpg` (the previews still show the keyline version of C; this file overrides them on faction colour). Written so J34 can write RCSS tokens without the review page. Lengths are dp (1 dp = 1 px at 1080p, D19); minimum text 14 dp; everything is a border, gradient, box shadow, `image-color` tint, child element, 9-slice or PNG sprite that RmlUi 6.3 draws (no blur, blend modes, clip-path or CSS `outline`).

**Look.** Cool paper plates, ink text, double-rule frames, hatched fills; vanilla colour art kept as content; the faction's colour fills the header band, the selected tab, the primary button, the progress bars and the selected row.

## 1. Palette (roles; ratio = colour against its pair, text and fills need 4.5, controls 3)

| Token | Hex | Pair | Ratio | |
|---|---|---|---|---|
| `bg_deep` | #c9d0d8 | surface | - |  |
| `panel` | #f1f3f5 | surface | - |  |
| `panel_raised` | #e1e6eb | surface | - |  |
| `line (decorative)` | #9aa5b3 | surface | - |  |
| `control_border` | #2a3547 | panel | 11.11 | ok |
| `text` | #1a2230 | panel | 14.35 | ok |
| `text_dim` | #4a586b | panel | 6.51 | ok |
| `accent_fill` | #1f4e8c | #ffffff | 8.31 | ok |
| `accent_text` | #1a478a | panel | 8.16 | ok |
| `positive` | #1f6a3a | panel | 5.93 | ok |
| `negative` | #a3231a | panel | 6.71 | ok |
| `warning` | #8a5a00 | panel | 5.33 | ok |
| `focus_ring` | #0b5fd0 | panel | 5.30 | ok |
| `hover` | #d3dae2 | text 11.32 | | fill for hover on panel_raised-style controls and rows |
| `pressed` | #c4ccd6 | text 9.85 | | fill for pressed |
| `on_faction_dark` | #0b0f16 | faction fill | | text on a light faction fill (see the rule) |
| `on_faction_light` | #ffffff | faction fill | | text on a dark faction fill |

Semantic colours (`positive`, `negative`, `warning`) never take the faction colour. `accent_fill` is the neutral accent used when no faction is set (front end, menus). `disabled` = the control at 50 % opacity (exempt from contrast, shown dashed-free: no border-style in RmlUi). Focus-visible = 3 dp `box-shadow` spread in `focus_ring` (no `outline` in RCSS).

## 2. Faction tint rule

Source: `factions` table `primary_colour_r/g/b` (the alternates are not used). Four faction tokens are set per screen from the owning faction: `fac` (the fill), `on_fac` (text and icons on it), `fac_hover`, `fac_pressed`.

- **Where `fac` is used:** panel header band (with the double rule below it drawn in `on_fac`), selected tab fill, primary button fill, progress-bar fill (non-semantic bars only), selected list row, number badge, the 4 dp top edge of a card frame. Nowhere else: body text, paper, rules, controls and icons stay neutral ink on paper.
- **On-colour:** `on_fac` = `on_faction_dark` (#0b0f16) or `on_faction_light` (#ffffff), whichever gives the higher ratio against `fac`. Always solid (no alpha on header subtitles).
- **Hover and pressed:** move `fac` 12 % and 24 % **away from** `on_fac` (towards white when the text is dark, towards black when it is white), so the ratio only rises.
- **Light fills:** a faction fill is always drawn with a 1 dp `control_border` outline (bars and badges too), so the shape never relies on the fill's own contrast against paper.
- **Checked over all 77 rows of the factions table (64 playable and minor, 13 rebel):** 46 take white, 31 take dark. Lowest `on_fac` ratio 4.75:1 (limit 4.5), lowest hover 5.81:1, lowest pressed 7.05:1. **No faction fails and none needs its colour altered.** With the ink `text` token (#1a2230) as the dark on-colour, two factions would fail (`ita_trent` 4.0:1, `crimean_khanate` 4.23:1), which is why the dark on-colour is the near-black #0b0f16.
- **Fills below 3:1 against `panel`** (the reason for the outline rule; they pass because of it): 28 factions: austria, bavaria, belgium, brittany, egy_mamelukes, greece, hannover, hessen, ita_austrian_alliance, ita_genoa, ita_lucca, ita_milan, ita_modena, ita_papal_states, ita_parma, ita_piedmont, naples, netherlands, piedmont_savoy, portugal, sardinia, saxony, sicily, spa_portugal, spa_spain, spain, tut_sardinia, united_netherlands.
- France (`france`, 9,79,150): fill #094f96, white, 8.17:1. Britain (`britain`, 222,0,0): fill #de0000, white, 5.11:1.
- No faction set: `fac` = `accent_fill`, `on_fac` = white.

## 3. Type (dp, family, weight, size / line height)

| Style | Family | Weight | Size / line | Use |
|---|---|---|---|---|
| Title | Libre Baskerville | 700 | 21 / 28 | panel and unit names (two lines allowed at 21) |
| Section head | Libre Baskerville | 700 | 17 / 22 | |
| Body | Public Sans | 400 | 15 / 21 | |
| Label | Public Sans | 600 | 14 / 18 | buttons, tabs, stat labels |
| Description | Libre Baskerville | 400 | 14 / 21 | background text, tooltips body stays Public Sans 14 / 19 |
| Numeral | Libre Baskerville | 400 | 14 / 20 | lining figures, right-aligned in columns |
| Big numeral | Libre Baskerville | 700 | 28 / 30 | tax rate, population |

Sources and licences (for `LICENSES.txt`, J38): Libre Baskerville, SIL OFL 1.1, <https://fonts.google.com/specimen/Libre+Baskerville>; Public Sans, SIL OFL 1.1, <https://fonts.google.com/specimen/Public+Sans>. Engine-drawn text (unit banners, map labels, `engine.*` rows, J37; the `.cuf` route cannot use a variable font): Libre Baskerville Bold instanced to a static TTF (Public Sans static for small text if J37 needs a sans).

## 4. Ornament recipes (RCSS technique)

- **Panel plate:** fill `panel`; 1 dp `control_border`; two `box-shadow` rings 4 dp and 5 dp out (`0 0 0 4px panel, 0 0 0 5px control_border`) make the double rule; drop shadow `0 12 36 black 45 %`.
- **Header band:** fill `fac`, text `on_fac`; below it a double rule from a 1 dp border plus a 1 dp `box-shadow` offset 3 dp, both in `on_fac`.
- **Hatching:** alternate list rows and bar fills: `repeating-linear-gradient` decorator, 135 deg, 1 dp line every 4 dp, ink at 8 % (rows) or the bar colour against a lighter tint of itself (bars).
- **Frame for cards and controls:** 1 dp `control_border` plus two inset rings (`inset 0 0 0 2px panel, inset 0 0 0 3px control_border`); radius 0.
- **Divider:** two 1 dp `control_border` rules 1 dp apart. **Section head:** bold serif, underlined by that double rule.
- **Selected:** tab = `fac` fill, `on_fac` text; row = `fac` fill, `on_fac` text; button toggled = `fac` fill.
- **Tooltip:** `panel_raised` with the card frame, max width 340 dp, body 14 dp.
- No bespoke chrome art: no 9-slice sprites are needed for the chrome.

## 5. Density

| Item | dp |
|---|---|
| list row height | 30 |
| button / tab height | 36 / 36 |
| panel padding | 14 |
| gap between groups | 8 |
| section head to first row | 12 |
| bar height | 12 |
| number badge | 22 high, min 22 wide |
| checkbox | 22 |
| order button | 56 (the J36 140 px master drawn 1:1 at 2.5x; the review used 60) |
| ability slot / manoeuvre button | 56 / 44 |
| region panel / unit popup width | 700 / 820 (about 11 stat rows visible) |

## 6. Iconography

- Content art is vanilla at the J36 2.5x masters: round order buttons with their shipped states (normal, roll, depress, selected, inactive), coins, plus and minus, religion pips, class faces, experience marks, flags, unit cards. State on vanilla art comes from the shipped sprites; where one is missing (halt selected, move speed roll, depress and selected, group depress) the unselected sprite plus the focus ring is the fallback until a sprite is added.
- New glyphs (about 24 sprites: ability and manoeuvre set, kit icons): 24 dp design grid, 2 dp stroke, round caps, drawn once in near-black at 60 px (2.5x), used at 16, 20, 24 and 28 dp and tinted with `image-color`: `text` normal, `on_fac` on a faction fill, `text_dim` for secondary, 50 % opacity disabled. New art is outside D14 unless Liam accepts it; the fallback is text-only buttons.

## 7. J34 handoff: components in the kit strip

Each component has the states: normal, hover, pressed, disabled, selected, focus-visible.

| Component | RCSS technique | State changes |
|---|---|---|
| Button | 36 dp, frame recipe, label 14 dp Public Sans 600; primary = `fac` fill | hover `hover` / `fac_hover`; pressed `pressed` / `fac_pressed` plus 1 dp `transform` down; disabled 50 % opacity; selected `fac` fill; focus 3 dp ring |
| Tab | 36 dp, 1 dp border (no bottom), sits on the panel's rule | normal `panel_raised`, text_dim; hover `hover`; pressed `pressed`; disabled 50 % opacity; selected `fac` fill, `on_fac` text |
| List row | 30 dp, 1 dp bottom border `line (decorative)`, even rows hatched | hover `hover`; pressed `pressed`; selected `fac`; disabled 50 %; focus ring (inset 3 dp) |
| Tooltip | frame recipe on `panel_raised`, 12 x 14 padding, title serif 15 bold | none (appears on hover delay) |
| Progress bar | 12 dp track `panel` with 1 dp `control_border`; fill hatched; segment variant: 6 squares 12 x 10 | fill `fac` (neutral bar), `positive`, `negative` (semantic bars) |
| Card frame | frame recipe, 12 padding; top edge 4 dp `fac` | none |
| Divider | double 1 dp rule | none |
| Number badge | 22 dp high, 1 dp `control_border`, radius 0, fill `fac`, text `on_fac` 14 dp 700 | negative count uses `negative` fill with dark text |

Contract notes for J34: derived tokens (`hover`, `pressed`, `fac_hover`, `fac_pressed`) are values, computed once per faction by the host and passed to RCSS as variables, because RCSS has no `color-mix`. The faction tokens belong in the panel host (J35) as one per-screen record.

## 8. Open for J34 and later
- The unit-card art area, flags and the 3D preview slot keep vanilla sizes; the review drew the preview as a placeholder.
- Public order, wealth, tax and population numbers on `region_details` were placeholders in the review; the contract stage supplies real ones.
- Missing state sprites and the 24 glyph sprites need Liam's acceptance (D14).
