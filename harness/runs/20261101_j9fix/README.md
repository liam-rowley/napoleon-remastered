# J9 fix round run 20261101_j9fix: the API states review round 1 asked for

PC, watcher 1.2.0, 2026-11-01 19:06 to 20:24 UTC, game lock `j9`, session `4127895c-6413-43ca-81ff-480348089c8a`, final build
46f52d356ce8 (kit `kit_20261101T170343Z_6f201de1f8b2`, the 20-pass build; reinstalled for this sitting and uninstalled after it: the
game folder identical to the pre-install snapshot, 1564 files, twice). Probes run from `probes/` by absolute path through the proxy's
`lua` verb (`proxy/napoleon` is a DLL input: a probe there would have voided the 20 passes); the surface probe is the installed
`api_surface.lua`. Drivers `fix.sh` .. `fix6.sh` (one per attempt); raw ctl results and the proxy logs in `raw/`.

## Probes
- `getters.lua` + `probe_safe_list.lua` (generated: `discovery/core/engine_api.py probe-safe --lua`, list `discovery/napoleon/probe_safe.json`):
  calls each probe-safe getter of the pumping context's own table once under pcall, logs a sample.
- `camp_select.lua <army|fleet|agent|settlement>`: selects the player's first entry (characters through SelectAndZoomToCharacter,
  settlements through RegionsOwnedByFactionOrByProtectorates + SelectAndZoomToRegion, nil-guarded).
- `camp_panel.lua <root function | close>`: opens a campaign panel through the root function its menu button calls; `close` calls
  PanelManager.CloseAllPanels. `vis.lua`: the visible top-level components (which panel or popup is on screen).
- `fe_pages.lua`: from the main menu pump, lists the front-end root's pages, enters each known-safe page (TransitionTo, as autostart.lua
  does), counts what an enumeration probe can reach there, and returns to `main`.

## Results
| state | launch / log | result |
|---|---|---|
| campaign getters (Austria) | `j9f_campaign_crash_proxy.log` | 28 of 28 CampaignUI getters returned (samples in `discovery/napoleon/engine_api.json`) |
| army, agent selected | idem | selected (Brigadier, 12 armies; Spy, 2 agents); surface 3,787 / 3,765 names |
| settlement selected | attempt 1 crashed, attempt 2 `j9f_campaign2_proxy.log` | attempt 1: RetrieveFactionRegionList entries hold no Address, SelectAndZoomToRegion(nil, -1) faulted at Napoleon.exe+0x5f578e reading 0xfc (minidump `20261101T190641Z-p32588_c0000005.dmp`); attempt 2: Tyrol selected, 3,775 names |
| fleet selected | `j9f_fleet_proxy.log` | Austria has no navy at the start (attempt 1 found an empty list; that block is dropped); the coalition campaign as Britain through the proxy's `autostart campaign:new:mp_eur_napoleon:britain`: a Captain of 6 fleets selected, 3,735 names |
| campaign panels | `j9f_campaign6_proxy.log` | entity_lists 3,498, government_screens 3,747, diplomacy_panel 3,747, missions 3,747, technology 3,756, building_browser 3,756 names, each panel seen on screen (`vis6_*`, shots `j9f_campaign6_*.jpg`); ShowPrestige errors in the vanilla Huds.lua:51 ("Wrong da...", it needs arguments the menu passes), so `campaign_show_prestige` is the surface with the technology and missions panels still up |
| front end getters | `j9f_frontend_proxy.log`, `j9f_land_proxy.log` (after a warm reset) | 7 of 7 FrontEnd getters returned |
| front end screens | `j9f_frontend4_proxy.log` | the root has two children (`layout`, `main`); sp_battle1, sp_battle2, sp_battle2_scenario entered: no new global and no new registry entry; grand_campaign: 6 new registry classes (OptionsTable, Pointer<EMPIRE_MP_BASE>, Pointer<EMPIRE_MP_CAMPAIGN_DROP_IN>, Pointer<GAME_CORE>, Pointer<KEYBOARD_SHORTCUT_DESCRIPTION>, Pointer<>); back to `main` and the main menu pumps again; surface afterwards 761 names |
| land getters | `j9f_land_proxy.log` | 10 of 10 BattleUI getters returned |

## What did not work first (kept for the record)
- Panels, attempts 1, 2 and 5: the root's OnShortcut(<default_keys action>) handles none of the show_* actions (the engine opens those
  panels itself; no UI script holds the strings), and the campaign-start "Mission Issued" popup (event_message) arrives seconds after
  the campaign loads; the panel states of those attempts are dropped by the generator (`dropped_blocks`).
- Front-end pages, attempt 3: the probe checked Find(page) before the transition (pages are created by their first TransitionTo) and
  went back to the root child `layout` instead of the page `main`, which stopped the pump.
- Front end, attempt 2: the direct launch failed in the watcher's headless placement ("no on_virtual status within 180 s"); attempt 3's
  direct launch worked, and the warm reset from a land battle is the fallback the later attempts used.
- `campaign_britain_1805` cannot be launched by `ctl.py scene`: its row names no autostart target.
