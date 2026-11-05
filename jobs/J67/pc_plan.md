# J67 PC plan (for the PC slot; written in the desk phase, 2026-11-03)

The desk phase built and host-tested the Lua classifier, the patch list, the overflow check and the 1.25x and 1.5x factor data (branch `job/J67`).
Nothing was built into `C:\napoleon_remastered_pc` and the game was not touched. The PC slot runs headless through the watcher with lock owner `J67`.
Budget: about 90 calls.

## 0. Before the lock (3 calls)
- Run `git pull`.
- Check that J30's game is closed, with `python3 core/proxy/tools/pc_deploy.py status`. The play tests and `install_packs` tests skip while `Napoleon.exe` runs.
- Run `python3 core/wsc.py setup`.

## 1. Build, game read-only (6 calls)
- `python3 core/wsc.py uiscale lua-patches --check`: every assert against the installed scripts. A failure means the game changed. Stop and report.
- `python3 core/wsc.py uiscale lua-consts --check`: the committed files match the game's scripts.
- `python3 core/wsc.py uiscale build --factor 2`:
  - the art is cached, so this is quick;
  - the pack gains the patched scripts, which changes its sha;
  - check that the fonts pack is still `5f510b27afa3`.
- `python3 core/wsc.py uiscale build --factor 1.5` and `--factor 1.25`. These are the first art builds at those factors, so they are long. Then record the pack sizes for the README factor table.

## 2. Snapshot and kit (3 calls)
- Snapshot the game folder and compare it with the last known one (`post_uninstall_20261102T161306Z`).
- Kit and send the proxy.

## 3. Lua route probe (1 launch, about 8 calls; record `napoleon.ui.lua_pack_route`)
- Packs in: the 2x set. Launch `land_small` at 3840x2160 and take a shot.
  - `ui/huds.luac` is not wrapped. If the radar group sits at the top-right corner, a movie-pack entry at a script's path replaces the script.
- In the same sitting, the wrapped scripts:
  - Probe `ui/battle_ui/root.luac`, a dev wrapper, with a probe script that logs which copy `wsp.vanilla` loads. Use main#80 K7: it is 38 in vanilla and 76 in the 2x pack.
  - Take a front-end shot for `ui/frontend_ui/main.advert.luac` (the "New content" box) and compare it with J66's `r2_frontend.jpg`.
  - If the harness copy differs from the play copy, say so in the fact. The play condition (`dev.lua_bridge` off) is then checked in Liam's play install.
- If the pack entry is ignored, try a `dev.file_rules` `add` line (config only) with one more launch (+6 calls).
- If both fail, stop and ask Liam (kill criterion).

## 4. 4K sweep, 3840x2160 (about 35 calls)
Shots are 1280-wide JPGs. After every launch, check WER and the dumps folder, and record the load time against J66's 3.8 s.

| Scenario or probe | Screens and `ui_elements` ids | What to look at | Calls |
|---|---|---|---|
| front end, `fe_page.lua` (J10 `sit1fe.sh`, `sit1fe2.sh`) | `frontend.main`, `frontend.sp_battle1`, the twelve pages | "New content" box not clipped (`main.advert`); army box, recruitment cards, unit list, team list (`frontend_ui/common/*`, `sp_battle3 team_list`); graphics options | 6 |
| `land_small` | `battle.hud.radar`, `engine.battle_radar`, Start Battle box | radar group at the top-right corner; the pip frame (`root` main#5); the group formations panel (757/84) | 4 |
| `land_small` minimised HUD, if a key verb exists | `battle.minimised_hud.radar` | minimised radar offset (`root` main#80, 38) | 2 |
| `naval_small` | naval HUD, naval group formations panel (762) | radar and orders group | 3 |
| `siege_small` | siege deployment | `siegeequipment` card rows | 3 |
| `campaign_start` | `campaign.hud.radar`, `engine.campaign_radar`, message icon stack | minimap content fills its frame; message icons and dropdown banner (40/255) | 3 |
| J9 `camp_select.lua settlement` | `campaign.region_details` | settlement panel, pip rows (26), city info bar (20) | 2 |
| J9 `camp_select.lua army` | campaign unit-card row | `template.campaignunitcard`, recruitment card width 76 | 2 |
| J9 `camp_select.lua agent` | agent panel | agent rows (`agents.luac`, `row_template_agent`) | 2 |
| J9 `camp_panel.lua` building, technology, diplomacy, government, missions | construction, tech, diplomacy, government, missions | construction grid (104), tech entries, diplomacy flags and map (`map_image`), government, mission entries | 8 |

- Pre-battle, battle results and tooltips: shoot them if a probe or a ctl verb reaches them. Otherwise mark them `unreached`, or `unseen` for tooltips, for Liam.
- If a screen is still unusable after one fix round, leave it, record its cause and go on.

## 5. 1440p, 2560x1440 (about 20 calls)
- Display check first (2 calls): can `ctl.launch.size` and the virtual display give 2560x1440? If not after one honest try, mark 1.25 and 1.5 unproven in the README, the facts and `play.py status`, and leave the shot list below for Liam.
- 1.25 set in (2 calls). Shoot `campaign_start`, `land_small` and the front end (5 calls).
- 1.5 set in (2 calls). Take the same shots (5 calls). Also open the six bleed pages through `fe_page`: credits, load_replay, mp_load_game, player_stats, sp_episodic_campaign, sp_load_game (2 calls).
- Decide the factor: choose 1.5 only if its shots read better, since the check already allows it. Update `config.json` `resolution_factor` and the fact `napoleon.ui.scale_factor_1440p`.

## 6. Everything out (4 calls)
- Take the packs out.
- `pc_deploy uninstall` must end `identical`.
- The end snapshot must be identical to the start one.
- Check that no proxy is left, and release the lock.

## 7. Acceptance passes, because the shipped files change (about 8 calls batched, or about 22 one by one)
- The release component `ui_scale_2x` ships `ui_scale_2x.pack`, which now carries the patched Lua, so its sha changes. The DLL inputs do not change, so rule 79's DLL rerun does not apply.
- Run the 20 release acceptance passes on the rebuilt 2x set: install from the release build, play the acceptance scenario, uninstall `identical`.
- Batch them in one watcher job if `job.sh` takes a repeat count.

## 8. Record (6 calls)
- `engine_facts` rows with the run id:
  - `napoleon.ui.lua_pack_route`;
  - `napoleon.ui.lua_pixel_constants`: 1014 uses, 258 scale, 756 leave, 204 items in 69 scripts;
  - `napoleon.ui.radar_placement`: `ui/huds.luac` RegisterHud clamps the HUD width to 1280;
  - `napoleon.ui.scale_factor_1440p`;
  - `napoleon.ui.scale_1_25x_packs` and `napoleon.ui.scale_1_5x_packs`;
  - an update to `napoleon.ui.scale_2x_packs`.
- A dated run report under `uiscale/runs/`, with the screen table: screen, id, state.
- Then `jobs/J67/report.md` and the row set to review. That is the finishing session's step.

Total: about 93 calls, or about 107 if both Lua routes are needed and the acceptance passes run one by one.
