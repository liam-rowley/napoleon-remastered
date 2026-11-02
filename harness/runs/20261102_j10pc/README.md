# J10 live pass run 20261102_j10pc: the vanilla UI component trees against the static atlas

PC, watcher 1.2.0, 2026-11-02 07:58 to 10:59 UTC, game lock `j10`, session `1bbe2745-8ed4-4d4c-9684-e1adf6bab382`, the installed 20-pass
build (kit `kit_20261101T205936Z_f08b12c3806a`, DLL 46f52d356ce8), headless at 1920x1080. Uninstalled at the end: the game folder is
identical to the pre-install snapshot (1564 files) and the exe is vanilla. Probes run from `probes/` by absolute path through the proxy's
`lua` verb (`proxy/napoleon` is a DLL input), and J9's `getters.lua`, `vis.lua`, `camp_select.lua` and `camp_panel.lua` run from
`harness/runs/20261101_j9fix/probes/`. Shots: `shots.json` (state, PC file, sha256, the units each shows) and three of them in `shots/`.
What the atlas made of it: `discovery/ui/reach.json` (`python3 discovery/core/ui_atlas.py live --run harness/runs/20261102_j10pc`).

## Probes
- `tree.lua <label> [<component> | *]`: logs every descendant of the visible root children (or of one component): path, visible, position,
  size, current state, as `j10tree <label> <n>:` lines. Unit flags (`3D_*`) are counted, not walked.
- `fe_page.lua <page> [stay]`: enters a front-end page with the root's `TransitionTo` (as its button does), logs the page's tree, and returns
  to `main` in the same call, because only the main menu pumps Lua. `stay` leaves the page open for a shot (no tree), and a relaunch follows.

## Sittings
| driver | what | raw |
|---|---|---|
| `sit1.sh` attempt 1 (07:58) | crashed on its first getters call (J9's `getters.lua` without its list: `dofile(nil)`) and kept running after its stop | `raw/attempt1/` |
| `sit1.sh` attempt 2 (08:04) | ran beside attempt 1's driver; attempt 1's two more argument-less getters calls crashed the game at 08:06:21 and 08:19:33 | `raw/attempt2/` |
| `sit1.sh` attempt 3 (10:03) | battles: all states below, no crash. Its front-end half ran inside the Dresden battle (a warm reset from a historical battle stops at the post-battle screen) and is not used | `sit1_proxy.log`, `raw/attempt3_fe_in_battle/` |
| `sit1fe.sh` (10:24) | front end: main menu and the page trees up to options; credits stopped the Lua pump | ctl results `page_*.txt` |
| `sit1fe2.sh` (10:40) | front end: the three page trees after credits and the eight missing shots | ctl results |
| `sit2.sh` (10:52) | campaign (Austria, `campaign_start`), then the coalition campaign as Britain for a fleet | `sit2_proxy.log`, `sit2b_proxy.log` |

All three crash dumps fault at `Napoleon.exe+0x538e5` (read access violation, Lua thread): `20261102T075837Z-p34880`, `20261102T080506Z-p39796`
and `20261102T081232Z-p27716` (`_c0000005.dmp`, moved with the uninstall to `C:\napoleon_remastered_pc\_to_delete\uninstall_20261102T105953Z\napoleon_remastered\dumps`).

## States
| state | how | nodes | visible top level | units reached here |
|---|---|---|---|---|
| land_deploy | `ctl scene land_small` | 684 | veneer_DY, radar_group, menu_bar, advice_interface, finish_deployment | battle HUD radar, balance of power, card strip, timer; menu bar; advisor |
| land_running | `ctl scene land_small deploy=end` | 665 | veneer_DY, radar_group, menu_bar, advice_interface | (same as deployment; spot check 1) |
| naval_deploy | `ctl scene naval_small` | 532 | radar_group, veneer_DY, menu_bar, advice_interface, finish_deployment | naval orders bar |
| naval_running | `ctl scene naval_small deploy=end` | 513 | veneer_DY, radar_group, menu_bar, advice_interface | (same as deployment) |
| siege_deploy | `ctl scene siege_small` | 684 | veneer_DY, radar_group, menu_bar, advice_interface, finish_deployment | (land HUD) |
| hist_deploy | `ctl scene hist_dresden` | 739 | radar_group, veneer_DY, menu_bar, finish_deployment | land orders bar, deployment end panel, unit card, unit group frame and tab |
| fe_main | warm reset from land_small | 76 | layout, main | front-end root layout, main menu |
| fe_single_player .. fe_grand_campaign | `fe_page.lua <page>` | 17 to 957 | the page | the 12 pages: single_player, sp_battle1, sp_battle2 (spot check 2), sp_battle2_scenario, napoleon_battles, sp_load_game, sp_tutorials, sp_episodic_campaign, options, player_stats, load_replay, grand_campaign |
| credits | `fe_page.lua credits` | - | - | none: entering it stops the front-end Lua pump |
| camp_popup | `ctl scene campaign_start` | 451 | veneer_DY, menu_bar, advice_interface, map labels (`label*`) | campaign HUD radar, theatres, card strip, orders |
| camp_hud | `campaign_modal_close.lua` x4 | 147 | veneer_DY, menu_bar, advice_interface | |
| camp_army, camp_agent, camp_settlement | `camp_select.lua army|agent|settlement` | 333, 152, 256 | veneer_DY, menu_bar, advice_interface (+ the selection's label) | city info bar, building card, region tooltip; settlement: the construction cards (spot check 3) |
| camp_lists, camp_gov, camp_diplomacy, camp_missions, camp_technologies, camp_buildings | `camp_panel.lua <root function>`, closed with `close` | 696, 642, 622, 449, 810, 542 | the panel (the missions panel stays up after CloseAllPanels, as in J9) | entity lists, government, diplomacy, objectives, technology, building browser and their list templates |
| camp_fleet | Britain, `camp_select.lua fleet` | 229 | label2, veneer_DY, menu_bar, advice_interface | campaign unit card |

Getters were sampled once per context with J9's list (`getters_land.txt`, `getters_naval.txt`, `getters_frontend.txt`, `getters_campaign.txt`).
