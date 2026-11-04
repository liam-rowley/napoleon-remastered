# Direction C: Engraved Plate

**Stance.** A light, printed look: cool paper plates with ink text, double-rule frames, hatched fills and the vanilla colour art kept as-is; the faction shows as one keyline.

Review page and previews: `design/napoleon/previews/c_*.jpg` (three screens at 1080p x 100 %, the unit popup at the 4K x 125 % corner, the kit strip, and the faction pair). All lengths are dp (1 dp = 1 px at 1080p); minimum text 14 dp; every effect below is a border, gradient, box shadow, `image-color` tint, child element or sprite that RmlUi 6.3 draws. Derived colours (hover, pressed) are fixed tokens, never computed.

## Palette (roles; ratio is the colour against its pair, text and fills need 4.5, controls and icons 3)

| Role | Hex | Pair | Ratio | |
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

Derived tokens to fix in J34: `hover` and `pressed` fills for each surface (hover = panel_raised lightened 6 %, pressed = panel darkened 30 % in A and B; 6 % darker and 12 % darker in C), `focus ring` = 3 dp `box-shadow` spread in `focus_ring`.

## Type (dp, family, weight, size / line height)

| Style | Family | Weight | Size / line | Use |
|---|---|---|---|---|
| Title | Libre Baskerville | 700 | 21 / 28 |  |
| Section head | Libre Baskerville | 700 | 17 / 22 |  |
| Body | Public Sans | 400 | 15 / 21 | descriptions in Libre Baskerville 14 / 21 |
| Label | Public Sans | 600 | 14 / 18 | buttons, tabs |
| Numeral | Libre Baskerville | 400 | 14 / 20 | lining |
| Big numeral | Libre Baskerville | 700 | 28 / 30 |  |

Licences and sources (for `LICENSES.txt`, J38): Libre Baskerville, OFL 1.1, <https://fonts.google.com/specimen/Libre+Baskerville>; Public Sans, OFL 1.1, <https://fonts.google.com/specimen/Public+Sans>.

Engine-drawn text (unit banners, map labels, `engine.*` rows, J37; the `.cuf` route cannot use a variable font): Libre Baskerville Bold, instanced to a static TTF.

## Ornament (recipe, RCSS technique)

- **Panel:** 1 dp `control_border` plus two `box-shadow` rings 4 dp and 5 dp out (a double rule), light fill
- **Header:** double rule below: 1 dp border plus a 1 dp `box-shadow` offset 3 dp
- **Hatching:** alternate list rows and bars: `repeating-linear-gradient` 135 deg, 1 dp line every 4 dp at 8 % ink
- **Keyline:** 4 dp faction-colour line under the title and on the card top edge
- **Selected:** row fill `accent_fill` with white text; tab with a 3 dp `accent_fill` top inset
- **Divider:** two 1 dp rules 1 dp apart
- **Buttons:** 1 dp border plus two inset rings, radius 0

## Density

row 30 dp, control height 36 dp, panel padding 14 dp, gap 8 dp, order buttons 60 dp round (vanilla art). Region panel 700 dp wide, unit popup 820 dp wide, single column; about 11 stat rows visible.

## Iconography

The vanilla colour art at the J36 2.5x masters (round order buttons with their shipped normal, roll, depress, selected and inactive states; coins, plus and minus, religion pips, class faces, experience marks). About 24 new sprites: the ability and manoeuvre glyphs (12) drawn as line icons in the same 24 dp grid, 4 missing state sprites (halt selected, move speed roll/depress/selected, group depress) and the faction-less glyph set for the kit.

## What each screen drops or changes from the vanilla inventory

- `campaign.region_details`: same sections and fields; leather and scroll frame replaced by a paper plate with double rules; vanilla pips, class faces, plus and minus and coins stay; gilt corners and plaque dropped.
- `common.unit_information`: same inventory; the flag stays as vanilla art; stat bars are hatched fills; description set in the serif at 14 dp.
- `battle.land_battle_orders`: same inventory; the vanilla round buttons stay (they carry the states), the strip and flag ends are replaced by a light plate with a double rule.

## Cost in new art

about 24 sprites; the rest is vanilla art already upscaled by J36. If the missing state sprites are refused, those controls fall back to the unselected sprite plus the focus ring. New art is outside D14 unless Liam accepts it.

## Data cases (keys and ids only; strings stay in the private page)

- Units (`units_tables`, `unit_stats_land_tables`, `unit_to_unit_abilities_junctions_tables`; loc `units_on_screen_name_<key>`): normal `Inf_Line_French_Fusiliers` (men 160, create_cost 590, upkeep 140, 5 abilities); longest name `Inf_Line_French_18th_Ligne` (47 characters); largest numbers `Art_Foot_Grand_Battery_Convention` (create_cost 1860, upkeep 460, guns 8, men 48); empty `Inf_Mob_Armed_Citizenry` (cost 0, upkeep 0, no abilities). Faction pair: `Inf_Line_French_Fusiliers` / `Inf_Line_British_Foot`, factions `france` and `britain`.
- Regions (`regions_tables`; loc `regions_onscreen_<key>`, settlement `start_pos_settlements_onscreen_name_settlement:<region>:<town>`): normal `eur_tyrol` (settlement `eur_tyrol:innsbruck`); longest name `eur_moldova_bessarabia` (20 characters; settlement `eur_moldova_bessarabia:iasi`), with all 9 religions of `religions_tables`; negative and empty `spa_pyrenees_orientales` (19 characters; settlement `spa_pyrenees_orientales:perpignan`), no villages, negative order, income and growth, exempt. Public order, wealth, tax and population numbers are **placeholders** (the db holds rules, not values; `taxes_levels_tables` gives the rates 5, 10, 15, 20, 25); they are marked so on the page and settle in the contract stage.
- Orders (`unit_abilities_tables`, loc `random_localisation_strings_string_ability_<key>`, formations `shortcut_localisation_onscreen_battle_land_formation_<key>`): normal `fire_at_will`, `fire_and_advance`, `square_formation`, `wooden_stakes` (2 charges), `plug_bayonets`; longest names `light_infantry_behaviour` (31 characters), `pike_square_formation`, `unlimber`, `fire_and_advance`, `ring_bayonets` at 9 charges; empty: nothing selected, every order inactive, no ability slots. Nine formations, longest key `single_line_cav_right`.
- Art ids (J36 2.5x masters): `ui/units/icons/<faction>_<unit>_icon.tga`, `ui/flags/<faction>/flag_132.tga` (`france_republic` for the tricolour), `ui/battle ui/skins/button_{halt,movespeed_walk,movespeed_run,melee,group,group_forms,blank}_*.tga`, `ui/campaign ui/skins/{coins,plus,minus,up_arrow,down_arrow,xp0}.tga`, `ui/campaign ui/Pips/<religion>.tga`.

## The faction question

Keyline only. The faction primary is one 4 dp line (title and card top edge); text and fills never use it, so no contrast check per faction is needed. Shown with France and Britain on the unit popup.
