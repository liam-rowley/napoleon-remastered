# J46 report: Scenario library: the rows J44 left out

J46 built the army route and the rows it enabled (land_40, naval_large), measured naval_storm, added the single-player historical row hist_lodi, and
recorded the siege-city, historical-cause and end-turn facts. The 20-pass gate is passed on DLL build 7631068c014b (watcher 1.2.0, 1920x1080, run
`harness/runs/20261102_j46acc`). campaign_mid and campaign_late are not built (kill criterion: ending turns is far over the 90 minute limit; two real
saves are asked for below). land_large and siege_city are not separate rows (facts below).

Written by the orchestrator from the build agent's hand-back: the build ran as a subagent, and the harness refuses a subagent's Write of a
report file, so the parent writes it. Same Claude-Session as the build.

## What was built
- **Army route** (deliverable 1). `proxy/napoleon/lua/autostart.lua` preset key `army=<n>` sets the custom-battle army size option (sp_battle2
  `dropdown_army_size`, 0-based) through the page's own `SetPerBattlePrefs{army_size=n}`, checks the readback (`Preferences().army_size`,
  `allowed_funds`) and errors if it did not take. sp_battle3 then fills both sides with `FrontEnd.RetrieveArmyPresets(...).balanced` at that size.
  The result is read back from sp_battle3 `main_panel:TeamSetups()` for every side: land_40 `20u0s,20u0s`, naval_large `0u10s,0u10s`. No memory
  write, no preference file written, no coordinate click. Probe `probes/army_options.lua`: land options 0/1/2 = 5000/10000/14000 funds = 9/15/20
  units; naval 0/1/2 = 5000/14000/24000 = 3/7/10 ships; the unit cap `MaxUnitsFromUnitScaleFactor` is 20 for every scale tried. Fact
  `napoleon.custom_battle.armies` verified (was open), run 20261102_j46pc. About 20 tool calls to the first result, well inside the 40-call line.
- **Rows**: `land_40` (20 against 20, the cap) and `naval_large` (10 ships a side, the cap). `land_large` equals land_40 (cap 20), so no separate
  row. Presets pin `army=` on land_small (9 units, option 0), naval_small and naval_storm (3 ships, option 0); siege_small is not pinned (its
  option set was not probed).
- **Siege city** (deliverable 2): no row, fact `napoleon.siege.city`. `EnumerateBattleMaps` for siege lists 7 forts for both arguments; classic,
  naval, historic and the names historical, settlement, land and city have no siege-flagged map; `EnumerateNapoleonsBattleMaps` has none. A
  settlement battle needs a played campaign: not reachable by the harness.
- **Historical cause** (deliverable 3): `EnumerateBattleMaps("historic", false)` is empty because the single-player battles are not in that list;
  they come from `FrontEnd.EnumerateNapoleonsBattleMaps()` (12 NHB_ battles), shown on the main menu's Napoleon's Battles page. Their icons carry
  the profile's unlock state: on this PC only NHB_Lodi is unlocked, NHB_Friedland and NHB_Waterloo_Well are `locked_land_dlc`, the other nine are
  `inactive`. Cheap enough, so `autostart.lua` got `type=napoleon` (SelectMap on the icon, then `movie_panel:SetupBattle`, which calls
  `FrontEnd.StartBattle`; a locked icon is refused) and the row `hist_lodi` (terrain hb_lodi). Austerlitz and Trafalgar single-player stay
  unreachable until the profile unlocks them. Fact `napoleon.autostart.historical` rewritten (verified 2026-11-02, run 20261102_j46pc).
- **naval_storm** (deliverable 4): load 3.5 s, poses stored, deterministic (diff 4.5 against threshold 9.0), in the acceptance order.
- **Campaign mid and late**: not built. Fact `napoleon.campaign.end_turn_time`: one end turn from the J14 base took 127 s (about 40 s more for
  launch and load). A third of the campaign is hours, past the 90 minute limit. Rows wait for two saves from a real playthrough.
- Tools: probes `army_options.lua`, `maps_matrix.lua`, `napoleon_battles.lua` (tools rows added). `tests/test_scenarios.py` accepts `type=napoleon`
  for historical rows and checks each row's "army size option N" against the preset's `army=`.

## Evidence
Scenario table (load s from the final baseline measure 20261102_j46m2; determinism = two launches' mean abs diff /255; threshold max(4, 2x diff)):

| id | kind | army | load s | poses | determinism (diff, threshold) |
|---|---|---|---|---|---|
| land_small | land | 9 units, option 0 | 4.2 | deploy, turned | 1.36, 4.0 |
| land_40 | land | 20 v 20, option 2 | 4.9 | deploy, turned | 1.19, 4.0 |
| siege_small | siege | remembered prefs | 5.6 | deploy, turned | 1.01, 4.0 |
| naval_small | naval | 3 ships, option 0 | 3.7 | deploy, turned | 4.47, 8.93 |
| naval_large | naval | 10 ships, option 2 | 5.0 | deploy, turned | 5.09, 10.18 |
| naval_storm | naval | 3 ships, option 0, rain storm | 3.6 | deploy, turned | 4.51, 9.02 |
| hist_dresden | historical | NHMPB 3v3 | 7.3 | deploy, turned | 3.90, 7.8 |
| hist_nile | historical | NHMPB 1v1 | 4.2 | deploy, turned | 5.15, 10.29 |
| hist_lodi | historical | NHB_Lodi (single player) | 5.9 | deploy, turned | 1.98, 4.0 |
| campaign_start | campaign | | 2.7 | default view | 21.1: not deterministic, shot not compared |

The 10 scenarios are all in the acceptance order (order: hist_dresden, hist_nile, hist_lodi, campaign_start, naval_small, naval_large,
naval_storm, siege_small, land_small, land_40). It covers every kind and ends on a plain battle, so land_40's perf is in the baseline: p50
2.68 ms, p99 4.40 ms, VRAM 835 MB for the process. Poses are the deployment view from `cam read`, then turned 60 degrees: inside the pitch clamp,
enforced by `test_scenarios`.

The 20 passes: loads hist_dresden 7.2 to 7.6 s, hist_nile 4.2 to 4.4, hist_lodi 6.0 to 6.4, campaign_start 2.6 to 2.8, naval_small 3.3 to 3.4,
naval_large 4.9 to 5.1, naval_storm 3.5 to 3.6, siege_small 5.5 to 5.7, land_small 4.1 to 4.4, land_40 4.8 to 5.0. Worst shot differences against
thresholds: hist_dresden 4.12/7.8, hist_nile 5.05/10.29, hist_lodi 2.00/4.0, naval_small 4.23/8.93, naval_large 5.99/10.18, naval_storm
4.67/9.02, siege_small 1.12/4.0, land_small 1.43/4.0, land_40 1.24/4.0. Settings byte-identical after every pass. Ledger lines with
`run: harness/runs/20261102_j46acc`, evidence `pass_01.json` to `pass_20.json`. A pass takes about 8 minutes of watcher time (20 passes about
2h40), a little over the "about 7 minutes" in the brief; nothing was left out for that reason because every added row was deterministic and a pass
stayed close.

Baseline: `harness/acceptance/baseline.json` written only by `acceptance.py measure` (runs 20261102_j46m1 first, a development run, and
20261102_j46m2 final). Facts `napoleon.siege.city`, `napoleon.autostart.historical`, `napoleon.custom_battle.armies`,
`napoleon.campaign.end_turn_time` carry run paths. PC run report and raw results: `harness/runs/20261102_j46pc/` (README.md and raw/).

History-edit note: main (J49, J65, J68 brief) was merged into the branch, never rebased. The merge changed the DLL build id from 19810d0c3578 to
7631068c014b; the final kit, the measure and the 20 passes were all run on 7631068c014b.

PC state after the job: game not running, lock released, no active profile. `pc_deploy uninstall` ended "identical to the pre-install snapshot"
(j46_pre.json, 1565 entries). Settings files byte-identical after every pass. The staged `zz_j46_probe.save` was cleared to `_to_delete`; save_games
has no zz_ file. Liam's saves and preferences untouched.

Gates (builder, on 5ea3c81): `wsc gates` 13 ok, 1 warn (skipped tests: no numpy, Pillow or capstone).

Verified by the orchestrator (2026-11-03, on 5ea3c81): `python3 core/harness/acceptance.py streak --build 7631068c014b --watcher 1.2.0` prints
"20 consecutive passes on build 7631068c014b, watcher 1.2.0 (need 20)"; `python3 core/proxy/tools/build_id.py` prints 7631068c014b; the ledger has
20 `j46acc` lines; `job.sh status` shows no lock, no current job, game `not_running`, exe sha1 vanilla; `wsc setup` 10 ok, 1 failed (the watcher
line, the stale `harness/core/job.sh` path filed as J70, not this job).

## Deviations from the brief and why
- naval_small and naval_storm changed from 10 ships (the remembered naval option was 2) to 3 ships by pinning `army=0`, so that "small" and "large"
  differ and no army depends on the remembered prefs. Their baselines were re-measured. land_small is unchanged (9 units).
- `land_large` is not a separate row: the screen cap is 20 units, same as land_40.
- campaign_mid and campaign_late not built: kill criterion (see above).
- The acceptance order grew to 10 scenarios (the brief said join only if deterministic and under about 7 minutes a pass): all deterministic; a
  pass takes about 8 minutes.
- `ctl.py scene` stays unchanged (core); the preset reads of both sides use `TeamSetups()`, which was not in the brief's call list.
- Calls: about 125 of 250 (the hand-back counts about 151 tool uses in total).

## Open questions
- Two saves from a real playthrough (one mid, one late) are needed for campaign_mid and campaign_late; Liam to supply them or ask for a long
  overnight generation run.
- Core backlog proposal: "scene stages the row's save" in `ctl.py` (D38), with campaign_mid and campaign_late as its test rows; campaign rows stay
  out of the acceptance order until then.
- Profile unlock state: Austerlitz and Trafalgar single-player (NHB_) need the profile to unlock them (only Lodi is unlocked here); a harness
  profile edit would write Liam's profile, which was not done.
- Siege city: only reachable through a settlement battle in a played campaign; revisit with the staged campaign saves.
- J28: land_40 plus the preset key `army=` are the 20-against-20 route. J23: build on land_40's `perf` in the baseline and the 10-scenario order.
- A stray `napoleon_remastered.ini` was in the game folder before J46's first install (1565 entries against the official 1564-entry snapshot
  `pre_install_20261030T090208Z.json`); install and uninstall restored it unchanged. Who left it?
