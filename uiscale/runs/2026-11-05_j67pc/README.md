# J67 PC run 2026-11-05_j67pc

Session `37d9d2f9-15cf-4c9e-8dd4-c06811d0d1b9`, branch `job/J67`, lock owner `j67` (the watcher's owner rule is lower case), watcher 1.4.0, headless.
Kit `kit_20261105T191805Z_86900aa937bf`, DLL copied from the main checkout as J37 did (sha `0f8209c5647f`; `build_id.py` gives a005f6cccc17 at HEAD and origin/main, so no DLL input differs).
Driver `sit.sh <label> <adapter> <parts>`; scratch adapters from `mk_adapter.py`; probes in `probes/`. Shots are the harness's 1280-wide copies.

| Cell (`raw/`) | Size | Set | Result |
|---|---|---|---|
| `x2_route` | 3840x2160 | 2x | Lua route probe: load 3.8 s (J66: 3.8) |
| `x2_4k`, `x2_army`, `x2_pages` | 3840x2160 | 2x | battles, campaign panels, field army, twelve front-end pages |
| `v1080` | 1920x1080 | vanilla, proxy only | reference for the suspect pages and panels |
| `x2_fix`, `x2_fix2` | 3840x2160 | 2x, fixed | credits and Load Game after the fixes |
| `c125`, `c15` | 2560x1440 | shipping 1.25x, 1.5x | front end only: no bridge pump |
| `v1440` | 2560x1440 | vanilla, proxy only | pumps; load 3.8 s |
| `x2_1440` | 2560x1440 | 2x | pumps; load 3.8 s |
| `c15_nolua` | 2560x1440 | 1.5x, no Lua, no art | pumps; load 3.7 s |
| `h15`, `h125` | 2560x1440 | `--no-wrapped` builds | battle, campaign, front-end pages |
| `h15b`, `h125b` | 2560x1440 | the same, slot header fixed | final look |

## Screens at 4K (2x set)
State: `ok` seen right, `fixed here` wrong before this job and seen right, `left` with the reason, `unreached` not opened headless, `unseen` patched but not seen.

| Screen | `ui_elements` id | State |
|---|---|---|
| Battle radar group, Start Battle box | `battle.hud.radar`, `engine.battle_radar` | fixed here: matches the 1080p layout (`x2_route/land.jpg`) |
| Minimised battle radar | `battle.minimised_hud.radar` | unreached: no key verb used; `root` main#80 is patched |
| Campaign minimap content | `campaign.hud.radar`, `engine.campaign_radar`, `template.map_image` | fixed here for the draw size; the hover mapping is unseen |
| Tooltips | `template.tooltip`, `engine.tooltips` | unseen: no hover verb |
| Settlement panel, construction grid | `campaign.region_details` | fixed here (`x2_4k/camp_settlement.jpg`) |
| Unit-card row | `template.campaignunitcard` | fixed here (`x2_army/camp_field.jpg`) |
| Lists, Government, Technology, Diplomacy, Objectives, building browser | - | ok |
| Agent panel | - | not separately seen: the probe's first agent sits in a settlement |
| Recruitment tab, pre-battle, reinforcements, battle results | `campaign.popup_pre_battle` | unreached |
| Naval and siege deployment | - | ok; naval group panel and siege equipment rows not opened |
| Main menu "New content" box | `frontend.main` | fixed here |
| Twelve front-end pages | `frontend.sp_battle1` and others | ok, with the three below |
| Credits | - | fixed here: wide glyphs were cut (fact `napoleon.fonts.cuf_cell_width`) |
| Load Game | `frontend.sp_load_game` | fixed here: the time wrapped over the next row |
| Options | - | tabs ok; the body is empty under the probe in vanilla too, so its content is unreached |
| Page titles | - | left: about half their vanilla share; the largest slot, see `uiscale/README.md` |
| Player Stats first four rows | - | left: slot quantisation, readable |
| Accented letters in the credits | - | left: a loose gap beside `é`, cosmetic |
| Loading screen, cursor | `engine.loading_screen`, `engine.cursors` | left: after the cut line |

The Mission Issued popup stayed up through the campaign shots (`campaign_modal_close.lua` does not know it) and Objectives stays after `CloseAllPanels` (J10 saw that too): harness effects, the same in `v1080`.

## 1440p
The virtual display gives 2560x1440, so nothing here is held back by the display. The choice is **1.5** (fact `napoleon.ui.scale_factor_1440p`):
`uiscale check` at 1.5 and 1440 lists 0 layouts that lose content, 6 that bleed 1 vanilla px, 0 abutting pairs off; 1.25 leaves 160 px of black across the front end. At 1.5 the mission popup touches the top edge.

**The bridge does not pump with the shipping 1.25x and 1.5x packs** (fact `napoleon.ui.dev_wrapper_lost_at_fractional`). The table above is the bisect. Cause unknown; the battle and campaign shots at 1440p are therefore of `--no-wrapped` builds (67 of 69 scripts).
Not run at all: the 1.5x battle root patch in a battle, and any shipping 1.5x pack beyond the front end. Liam's first 1440p session covers both.

## Bugs this run found, all fixed
1. Engine-text fonts kept the vanilla cell width `h9`: wide glyphs cut. From J37; the loading quote uses the same files.
2. Date cells wrapped: `date_cell_pass`.
3. 112 of 122 templates stayed vanilla at 1.25x and 1.5x: a swallowed `ValueError`. The desk phase's tests were green throughout. The build now refuses it.
4. Slots drawn below their vanilla size kept the vanilla header: text sat low and was clipped. Mine, from the desk phase.

## Crashes
WER has every one as `c0000374` at `ntdll+0xfd71f`: the known `napoleon.proxy.init_heap_corruption`, each within a second of launch, each retried by ctl.py. Dump names per cell: `raw/*/dumps.txt`. At least 14 in the run, 4 of them with no scale pack. 6 of 18 launches in `x2_pages`.

## End state: NOT snapshot-identical
`snap_start` (1564 entries) against `snap_end` (1565): one difference, `added napoleon_remastered.ini`. No proxy, no packs, no lock, exe vanilla.
**How:** I released the lock and ran `play.py uninstall` at once; the watcher's profile restore then wrote the ini back after `pc_deploy` had removed it. Later snapshots took it as a baseline, so every later uninstall said `identical`. `play.py` now refuses both halves of this.
**Not removed:** moving it out through a watcher job was denied by the permission classifier, so it stays for Liam. It is inert: nothing reads it without `d3d9.dll`. Later play installs need `--keep-ini` until it is gone.
