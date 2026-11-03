# J46 PC run 20261102_j46pc: the army route, historical and siege probes, naval_storm, determinism, baseline, 20 passes

PC (RTX 4090, Windows 11), headless 1920x1080 through the watcher 1.2.0, 2026-11-02 22:40 to 2026-11-03 02:20 UTC, game lock `j46`. Builds: a
first dev build (kit `kit_20261102T224839Z_94ab2911bd30`, the probes) and the final merged build `7631068c014b` (kit `kit_20261102T232044Z_455d0431a13c`).
Raw ctl results in `raw/`. Other runs: `harness/runs/20261102_j46m1` (first measure, ten scenarios), `20261102_j46m2` (final measure, the
baseline), `20261102_j46acc` (the 20 passes, ledger lines `run: harness/runs/20261102_j46acc`).

## a) The game folder
Snapshot before the first install (`snapshots/j46_pre.json`, 1565 entries) differs from `pre_install_20261030T090208Z.json` (1564) by one file,
`napoleon_remastered.ini` in the game folder, which was there before J46 touched anything (not mine; `pc_deploy install` saved it and
`uninstall` restored it). After the last uninstall: identical to `j46_pre.json` (`snapshots/j46_post.json`), after the lock release and the
watcher's restore. `save_games` holds no `zz_` file (the staged `zz_j46_probe.save` was cleared to `_to_delete`); Liam's saves untouched.

## b) The army route (raw/army_options_*.json, land_40_scene.json, naval_large_scene.json)
`probes/army_options.lua`: sp_battle2's `dropdown_army_size` has 3 options; `FrontEnd.ArmyFundsForSize` 5000/10000/14000 (land) and
5000/14000/24000 (naval); `RetrieveArmyPresets(...).balanced` has 9/15/20 land units and 3/7/10 ships; the unit cap
(`MaxUnitsFromUnitScaleFactor`) is 20 for every scale. Preset key `army=<n>` sets the option through `SetPerBattlePrefs{army_size}`, reads it back,
and reads both sides back from sp_battle3 `main_panel:TeamSetups()`: land_40 `20u0s,20u0s`, naval_large `0u10s,0u10s`. 20 tool calls to the first result.

## c) Siege and historical (raw/maps_matrix.json, napoleon_battles_probe.json, hist_lodi_scene.json)
No city siege map (7 forts for every argument). The empty `EnumerateBattleMaps("historic", false)` is expected: the single-player list is
`FrontEnd.EnumerateNapoleonsBattleMaps` (12 NHB_), shown on the Napoleon's Battles page; on this profile only NHB_Lodi is unlocked. hist_lodi loads in 5.9 s.

## d) naval_storm, campaigns
naval_storm: load 3.5 s, poses, deterministic (diff 4.5). One end turn from the J14 base took 127 s (raw/campaign_end_turn_probe.log): campaign_mid and
late by ending turns exceed the 90 minute limit, not generated.

## e) Baseline and gate
Final baseline `harness/acceptance/baseline.json` (10 steps, measure run 20261102_j46m2); 20 passes 2026-11-02 23:49 to 2026-11-03 02:2x UTC, about 8 minutes a pass.
