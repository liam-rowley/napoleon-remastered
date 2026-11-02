# Direction B: Regimental Facings

**Stance.** A bold, roomy uniform-board look: charcoal body, big condensed capitals, a faction-coloured facing band and piping, studs, chunky badge icons; the chrome tints by faction.

Review page and previews: `design/napoleon/previews/b_*.jpg` (three screens at 1080p x 100 %, the unit popup at the 4K x 125 % corner, the kit strip, and the faction pair). All lengths are dp (1 dp = 1 px at 1080p); minimum text 14 dp; every effect below is a border, gradient, box shadow, `image-color` tint, child element or sprite that RmlUi 6.3 draws. Derived colours (hover, pressed) are fixed tokens, never computed.

## Palette (roles; ratio is the colour against its pair, text and fills need 4.5, controls and icons 3)

| Role | Hex | Pair | Ratio | |
|---|---|---|---|---|
| `bg_deep` | #101114 | surface | - |  |
| `panel` | #1b1d21 | surface | - |  |
| `panel_raised` | #272a30 | surface | - |  |
| `line (decorative)` | #3a3f47 | surface | - |  |
| `control_border` | #868d99 | panel | 5.05 | ok |
| `text` | #f3f0e8 | panel | 14.82 | ok |
| `text_dim` | #b9b5aa | panel | 8.24 | ok |
| `accent_fill` | #d4a537 | #14110a | 8.29 | ok |
| `accent_text` | #e8c15f | panel | 9.82 | ok |
| `positive` | #8fd694 | panel | 9.82 | ok |
| `negative` | #ff8c7a | panel | 7.46 | ok |
| `warning` | #f2c76e | panel | 10.58 | ok |
| `focus_ring` | #ffffff | panel | 16.88 | ok |
| `facing_fill (France)` | #094f96 | #ffffff | 8.17 | ok |
| `facing_fill (Britain)` | #de0000 | #ffffff | 5.11 | ok |

Derived tokens to fix in J34: `hover` and `pressed` fills for each surface (hover = panel_raised lightened 6 %, pressed = panel darkened 30 % in A and B; 6 % darker and 12 % darker in C), `focus ring` = 3 dp `box-shadow` spread in `focus_ring`.

## Type (dp, family, weight, size / line height)

| Style | Family | Weight | Size / line | Use |
|---|---|---|---|---|
| Title | Barlow Condensed | 700 | 34 / 38 | caps, +0.06 em |
| Section head | Barlow Condensed | 700 | 22 / 26 | caps, +0.08 em |
| Body | Barlow | 500 | 17 / 22 |  |
| Label | Barlow | 600 | 15 / 20 | stat labels in caps, +0.05 em |
| Button and tab | Barlow Condensed | 700 | 18 / 22 | caps, +0.07 em |
| Numeral | Barlow Condensed | 600 | 20 / 24 | tabular |
| Big numeral | Barlow Condensed | 700 | 40 / 40 |  |

Licences and sources (for `LICENSES.txt`, J38): Barlow Condensed, OFL 1.1, <https://fonts.google.com/specimen/Barlow+Condensed>; Barlow, OFL 1.1, <https://fonts.google.com/specimen/Barlow>.

Engine-drawn text (unit banners, map labels, `engine.*` rows, J37; the `.cuf` route cannot use a variable font): Barlow Medium (static TTF from Google Fonts).

## Ornament (recipe, RCSS technique)

- **Panel:** 3 dp black border, 1 dp `line (decorative)` outer ring (`box-shadow` 0 0 0 1), radius 6 dp
- **Facing band:** header fill = faction primary, text = black or white, bottom 5 dp double border in the on-colour at 55 %
- **Studs:** two 12 dp round child elements, `radial-gradient` brass (no sprite)
- **Section head:** 6 dp faction-colour left border
- **Selected:** tab, row and ordered button fill with the faction colour
- **Divider:** 2 dp dashed look from a `repeating-linear-gradient` (8 on, 4 off)
- **Buttons:** 2 dp black border plus 1 dp inset ring, 4 dp inset bottom shade, radius 4 dp

## Density

row 36 dp, control height 44 dp, panel padding 18 dp, gap 12 dp, order buttons 62 dp round. Region panel 1060 dp wide in two columns, unit popup 960 dp wide; about 9 stat rows visible at once.

## Iconography

New bold glyph set (about 50 sprites): 24 dp grid, 2.6 dp stroke, drawn inside a round badge 38 dp (a `border-radius` disc, not a sprite). Disc colour carries the state: `control_border` normal, `text` hover, faction colour selected, 45 % opacity disabled. Glyph is black on the disc.

## What each screen drops or changes from the vanilla inventory

- `campaign.region_details`: two columns instead of three stacked panes (Population moves beside Public Order and Wealth) so the roomier rows fit 1080p; drops leather, scroll frame, gilt corners and plaque; the faction facing band replaces the plaque.
- `common.unit_information`: same inventory; the faction flag moves into the card under the preview and the header band carries the faction colour. Stat bars are six larger squares. Title is allowed two lines (the longest name needs the condensed face at 28 dp).
- `battle.land_battle_orders`: same inventory; the buttons are round badges, the bar gets an 8 dp faction top border instead of the strip and flag ends.

## Cost in new art

about 50 glyph sprites; no frame art (studs and bands are gradients and borders). New art is outside D14 unless Liam accepts it.

## Data cases (keys and ids only; strings stay in the private page)

- Units (`units_tables`, `unit_stats_land_tables`, `unit_to_unit_abilities_junctions_tables`; loc `units_on_screen_name_<key>`): normal `Inf_Line_French_Fusiliers` (men 160, create_cost 590, upkeep 140, 5 abilities); longest name `Inf_Line_French_18th_Ligne` (47 characters); largest numbers `Art_Foot_Grand_Battery_Convention` (create_cost 1860, upkeep 460, guns 8, men 48); empty `Inf_Mob_Armed_Citizenry` (cost 0, upkeep 0, no abilities). Faction pair: `Inf_Line_French_Fusiliers` / `Inf_Line_British_Foot`, factions `france` and `britain`.
- Regions (`regions_tables`; loc `regions_onscreen_<key>`, settlement `start_pos_settlements_onscreen_name_settlement:<region>:<town>`): normal `eur_tyrol` (settlement `eur_tyrol:innsbruck`); longest name `eur_moldova_bessarabia` (20 characters; settlement `eur_moldova_bessarabia:iasi`), with all 9 religions of `religions_tables`; negative and empty `spa_pyrenees_orientales` (19 characters; settlement `spa_pyrenees_orientales:perpignan`), no villages, negative order, income and growth, exempt. Public order, wealth, tax and population numbers are **placeholders** (the db holds rules, not values; `taxes_levels_tables` gives the rates 5, 10, 15, 20, 25); they are marked so on the page and settle in the contract stage.
- Orders (`unit_abilities_tables`, loc `random_localisation_strings_string_ability_<key>`, formations `shortcut_localisation_onscreen_battle_land_formation_<key>`): normal `fire_at_will`, `fire_and_advance`, `square_formation`, `wooden_stakes` (2 charges), `plug_bayonets`; longest names `light_infantry_behaviour` (31 characters), `pike_square_formation`, `unlimber`, `fire_and_advance`, `ring_bayonets` at 9 charges; empty: nothing selected, every order inactive, no ability slots. Nine formations, longest key `single_line_cav_right`.
- Art ids (J36 2.5x masters): `ui/units/icons/<faction>_<unit>_icon.tga`, `ui/flags/<faction>/flag_132.tga` (`france_republic` for the tricolour), `ui/battle ui/skins/button_{halt,movespeed_walk,movespeed_run,melee,group,group_forms,blank}_*.tga`, `ui/campaign ui/skins/{coins,plus,minus,up_arrow,down_arrow,xp0}.tga`, `ui/campaign ui/Pips/<religion>.tga`.

## The faction question

Tint. `facing_fill` = the faction primary (`factions` table `primary_colour_r/g/b`), on-colour black or white by contrast. Of the 64 non-rebel factions 31 need a black on-colour; the worst best-of-two ratio is 4.74:1, so a pass is guaranteed without altering a faction colour. Shown with France and Britain on the unit popup.
