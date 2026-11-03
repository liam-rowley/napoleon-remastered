# Run report 2026-11-02: the vanilla UI at 2x for 4K (J66)

Session `b9b37f03-a480-468a-b3c0-a59240b794b8`, branch `job/J66`. PC: headless 3840x2160 on the virtual display, game lock `J66` from 16:38:07 to about
16:55 UTC. Every launch went through `core/harness/ctl.py` with a scratch copy of the adapter (`_scratch\j66\adapter_4k*.json`: `ctl.launch.size` 3840x2160;
the `_tpl` copy also points `dev.file_rules` at `raw/rules_2x.txt`, which is the fixed-sky line plus the templates redirect, and adds `frontend` to the settle scenes so the front end can be shot).
Shots in `raw/` are the harness's 1280-wide copies of 3840x2160 frames.

## Build (`python3 core/wsc.py uiscale build`)
| output | entries | size | sha256 |
|---|---|---|---|
| `ui_scale_2x.pack` | 9539 (174 layouts + 9365 textures) | 1809.3 MB | `bd351fa39ae9a26c3cc82de0b7d0b6597c9c64bcc7fb69c1a0a883c51ee30ae3` |
| `ui_scale_2x_fonts.pack` | 5 (`frontend_24`, `frontend_38`, `ingame_18`, `ingame_24`, `ingame_b_24`) | 1.8 MB | `f699ca5db25b9cb972345184d58bae73590e5dfbbc561ccd1deac7a4109eaf63` |
| `uied.templates.ui_scale_2x` | 122 of 126 records scaled; 7 upgraded to v33 | 39.1 MB | `4797e415b6ea589272e6ae6b400709f70c42de6d6ed2f6a9da1b411e3cbe1fb8` |

- **Layouts:** all 174 scaled with edge snapping, the 23 V039 keyframes included. Every output round-trips through `uic.py`.
- **Templates:** `Cursor`, `slider`, `InputWindow` and `BattleEditor` pass through unchanged. The records upgraded to v33 are `minister_effect_cartouche`, `minister_details`, `turns`, `numerical_input`, `diplomacy_allies_list_item`, `sortable_list` and `character_info_list_entry`; Napoleon has them at v20-v26 under Empire's names.
- **Art:** all 9365 textures were resampled from the J36 2.5x masters (`art_methods` in the `.pack.json`). Every texture a layout or template names had a master, so there was no Lanczos-from-vanilla fallback.
  - 34 pixel helpers (`1x1*`, `1px_*`, `fe_1x1*`) are kept vanilla.
  - `loading_screen` and `cursor` are not in `art_roles`.
- **Speed:** the art resample took about 40 s on all CPUs.
- **Determinism:** a second build in another folder gave the same bytes for its 60 art files and for the templates file. A re-run in place reuses the cache and keeps the pack (same plan signature).

## PC sequence
| step | result | evidence |
|---|---|---|
| a) start snapshot | 1564 entries, **identical** to `snapshots\post_uninstall_20261102T161306Z.json` | `_scratch\j66\snap_start.json` |
| a) kit | `kit_20261102T154016Z_23dbc9e2d143` (build id 715e9dfc0727 = this branch's DLL inputs), installed, exe vanilla | pc_deploy install |
| b) packs in: `ui_scale_2x`, `ui_scale_2x_fonts`, route-1 probe `zz_j66_tplprobe.pack` (scaled templates at `ui\templates\uied.templates`) | ok, sha256 checked | job `J66-20261102T163918Z-106224043` |
| b) route 1: `scene campaign_start` + shot | ok, campaign, load 3.0 s | `raw/r1_campaign.jpg` |
| b) route 2 (redirect): `scene campaign_start` + shot | ok; proxy.log: `redirect: data\ui\templates\uied.templates -> ...uied.templates.ui_scale_2x (rules line 6)` | `raw/r2_campaign.jpg` |
| warm reset from the campaign | stalled in loading for 5 min (known: `napoleon.campaign.quit_to_menu`), killed | job `J66-20261102T164639Z-86862644` |
| `scene land_small` + shot | ok, battle_deploy, **load 3.8 s** (J53: 3.9 s), launch `20261102T164658Z-p36980` | `raw/r2_land_scene.json`, `raw/r2_land.jpg` |
| `reset` (battle to front end) + shot; Single Player page (J10 `fe_page.lua single_player stay`) + shot | ok | `raw/r2_frontend.jpg`, `raw/r2_fe_single_player.jpg` |
| proxy log | `packs: 14 packs, 96540 entries indexed` = 86995 vanilla + 9539 + 5 + 1 | |
| c) kill, packs out, kit out | ok; pc_deploy uninstall identical to its pre-install snapshot | job `J66-20261102T165343Z-1342610164` |
| c) end snapshot vs start | **identical** (1564 entries) | `_scratch\j66\snap_end.json` |
| c) lock released | the watcher restores the headless profile itself | |

- No dump: `napoleon_remastered\dumps` was never created.
- No new Napoleon WER report: the newest is from 13:53, before the lock.
- `%APPDATA%\The Creative Assembly\Napoleon\ui_cache` was empty before and after. This Napoleon session wrote no UI cache.

## What the shots show (by eye)
- **2x and docked as at 1080p:**
  - campaign HUD, bottom-centred;
  - advisor panel, top-left;
  - battle HUD, bottom-centred: unit cards fill their 2x slots, the counts are legible;
  - main menu, centred;
  - Single Player page.
  So the scaled root canvas is what the engine docks (fact `napoleon.ui.canvas_docks_scaled`).
- **Text:** Lora at the slot sizes, no tiny fallback (fact `napoleon.ui.font_slots_2x`).
- **Wrong:**
  - the battle radar and the Start Battle box sit about 1290 px left of the top-right corner;
  - the front-end "New content" box is clipped on its right;
  - the Single Player labels are dark in the shot, probably caught during the page's open animation (one shot only).
- **Stays 1x:** the map and unit labels, the version string (engine-drawn text).
- **Route 1 vs route 2:** the two campaign shots are the same. No template-built element was on screen, so the probe cannot tell whether the pack entry is read. Route 2 is the one shipped, because it is proven read.
- **Not seen** (there is no click or hover verb, `ctl.py` rule 78): tooltips, the settlement panel and the campaign unit-card row.
