# Direction A: Staff Map

**Stance.** A cool, dense map-table: slate ink panels, chalk text, one seal-red accent; hairline rules and tick corners, line icons, chrome neutral to faction.

Review page and previews: `design/napoleon/previews/a_*.jpg` (three screens at 1080p x 100 %, the unit popup at the 4K x 125 % corner, the kit strip, and the faction pair). All lengths are dp (1 dp = 1 px at 1080p); minimum text 14 dp; every effect below is a border, gradient, box shadow, `image-color` tint, child element or sprite that RmlUi 6.3 draws. Derived colours (hover, pressed) are fixed tokens, never computed.

## Palette (roles; ratio is the colour against its pair, text and fills need 4.5, controls and icons 3)

| Role | Hex | Pair | Ratio | |
|---|---|---|---|---|
| `bg_deep` | #0e151e | surface | - |  |
| `panel` | #16202c | surface | - |  |
| `panel_raised` | #1e2b3b | surface | - |  |
| `line (decorative)` | #3c506a | surface | - |  |
| `control_border` | #6f88a6 | panel | 4.50 | ok |
| `text` | #e8eef5 | panel | 14.08 | ok |
| `text_dim` | #a6b5c7 | panel | 7.87 | ok |
| `accent_fill` | #c4402b | #ffffff | 5.10 | ok |
| `accent_text` | #ff9a85 | panel | 8.00 | ok |
| `positive` | #7dd3a0 | panel | 9.16 | ok |
| `negative` | #ff8f80 | panel | 7.43 | ok |
| `warning` | #f2c76e | panel | 10.31 | ok |
| `focus_ring` | #7cc4ff | panel | 8.77 | ok |

Derived tokens to fix in J34: `hover` and `pressed` fills for each surface (hover = panel_raised lightened 6 %, pressed = panel darkened 30 % in A and B; 6 % darker and 12 % darker in C), `focus ring` = 3 dp `box-shadow` spread in `focus_ring`.

## Type (dp, family, weight, size / line height)

| Style | Family | Weight | Size / line | Use |
|---|---|---|---|---|
| Title | Spectral | 700 | 24 / 28 | unit and region names |
| Section head | Spectral | 600 | 17 / 22 | accent_text colour |
| Body | Source Sans 3 | 400 | 15 / 20 |  |
| Label | Source Sans 3 | 600 | 14 / 18 | buttons, tabs, stat labels |
| Numeral | Source Sans 3 | 600 | 15 / 20 | tabular, lining |
| Big numeral | Spectral | 700 | 28 / 30 | tax rate, population |

Licences and sources (for `LICENSES.txt`, J38): Spectral, OFL 1.1, <https://fonts.google.com/specimen/Spectral>; Source Sans 3, OFL 1.1, <https://fonts.google.com/specimen/Source+Sans+3>.

Engine-drawn text (unit banners, map labels, `engine.*` rows, J37; the `.cuf` route cannot use a variable font): Source Sans 3 SemiBold, instanced to a static TTF.

## Ornament (recipe, RCSS technique)

- **Panel:** 1 dp border `line (decorative)`, `box-shadow` 0 12 40 black 55 %, background plus a ruled grid: `repeating-linear-gradient` decorator, 1 dp lines every 32 dp at 3 % white
- **Tick corners:** four child elements 10x10 dp with 2 dp borders on two sides in `accent_text` (no sprite)
- **Header:** `panel_raised` fill, 1 dp bottom border
- **Selected:** tab: `panel_raised` fill plus 2 dp `accent_fill` bottom border; row: 3 dp left border `accent_fill`
- **Divider:** 1 dp `line (decorative)` rule
- **Buttons:** 1 dp `control_border`, 2 dp inner bottom shade (`box-shadow` inset), radius 2 dp

## Density

row 24 dp, control height 32 dp, panel padding 12 dp, gap 6 dp, order buttons 56 dp square. Region panel 620 dp wide, unit popup 780 dp wide, both single column; about 14 stat rows visible at once.

## Iconography

New single-colour line set (about 50 sprites): 24 dp design grid, 1.75 dp stroke, round caps. Shipped as white PNG sprites at 2.5x (60 px) and tinted with `image-color`: text for normal, `accent_text` for selected, `text_dim` at 45 % opacity for disabled. Order buttons are 56 dp rounded squares with a 28 dp glyph.

## What each screen drops or changes from the vanilla inventory

- `campaign.region_details`: keeps all three sections and every field. Drops the leather fill, scroll frame, gilt corners, title plaque and the 34 px round arrow buttons (replaced by square 34 dp buttons); the three paper panes become flat sections. The advice button (top left) is not drawn: it belongs to the HUD, not to the panel.
- `common.unit_information`: keeps portrait slot (engine render target), Statistics and Abilities tabs, background text with scrollbar, custom name, disband and general. The stat bars become six squares (vanilla used 76x6 px bar art) so a stat reads as a number plus a level.
- `battle.land_battle_orders`: keeps five order buttons, five ability slots with charge badges and the six manoeuvre buttons; drops the button strip and the flag ends (hud_left, hud_right). The formations list is a plain panel above the group-formations button.

## Cost in new art

about 50 small sprites (one colour, tinted in RCSS); no frame art, no textures. New art is outside D14 unless Liam accepts it.

## Data cases (keys and ids only; strings stay in the private page)

- Units (`units_tables`, `unit_stats_land_tables`, `unit_to_unit_abilities_junctions_tables`; loc `units_on_screen_name_<key>`): normal `Inf_Line_French_Fusiliers` (men 160, create_cost 590, upkeep 140, 5 abilities); longest name `Inf_Line_French_18th_Ligne` (47 characters); largest numbers `Art_Foot_Grand_Battery_Convention` (create_cost 1860, upkeep 460, guns 8, men 48); empty `Inf_Mob_Armed_Citizenry` (cost 0, upkeep 0, no abilities). Faction pair: `Inf_Line_French_Fusiliers` / `Inf_Line_British_Foot`, factions `france` and `britain`.
- Regions (`regions_tables`; loc `regions_onscreen_<key>`, settlement `start_pos_settlements_onscreen_name_settlement:<region>:<town>`): normal `eur_tyrol` (settlement `eur_tyrol:innsbruck`); longest name `eur_moldova_bessarabia` (20 characters; settlement `eur_moldova_bessarabia:iasi`), with all 9 religions of `religions_tables`; negative and empty `spa_pyrenees_orientales` (19 characters; settlement `spa_pyrenees_orientales:perpignan`), no villages, negative order, income and growth, exempt. Public order, wealth, tax and population numbers are **placeholders** (the db holds rules, not values; `taxes_levels_tables` gives the rates 5, 10, 15, 20, 25); they are marked so on the page and settle in the contract stage.
- Orders (`unit_abilities_tables`, loc `random_localisation_strings_string_ability_<key>`, formations `shortcut_localisation_onscreen_battle_land_formation_<key>`): normal `fire_at_will`, `fire_and_advance`, `square_formation`, `wooden_stakes` (2 charges), `plug_bayonets`; longest names `light_infantry_behaviour` (31 characters), `pike_square_formation`, `unlimber`, `fire_and_advance`, `ring_bayonets` at 9 charges; empty: nothing selected, every order inactive, no ability slots. Nine formations, longest key `single_line_cav_right`.
- Art ids (J36 2.5x masters): `ui/units/icons/<faction>_<unit>_icon.tga`, `ui/flags/<faction>/flag_132.tga` (`france_republic` for the tricolour), `ui/battle ui/skins/button_{halt,movespeed_walk,movespeed_run,melee,group,group_forms,blank}_*.tga`, `ui/campaign ui/skins/{coins,plus,minus,up_arrow,down_arrow,xp0}.tga`, `ui/campaign ui/Pips/<religion>.tga`.

## The faction question

Neutral. No faction token in the chrome; flag, crest and unit card carry identity. Shown on the unit popup with France (`france`, primary 9,79,150) and Britain (`britain`, 222,0,0): identical chrome.
