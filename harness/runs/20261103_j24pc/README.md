# J24 PC run 20261103_j24pc: shadow map resolution and fit

PC: RTX 4090, Windows 11, DXVK 3.1.1, watcher 1.2.0, headless at 1920x1080 (fit and shots) and 1080p / 4K (perf). Prefs: Liam's
(`gfx_shadow_quality` 3, `gfx_hardware_shadows` false), the watcher's headless overlay. Game lock owner `j24`. 2026-11-03, 03:02 to about
11:00 UTC. Static RE (no PC): the fit chain and fields in `registries/engine_facts/napoleon.shadow.fit_code.json` and `.fit_fields.json`.

## Builds and kits
| build | kit | what | used for |
|---|---|---|---|
| 679422b9443a | kit_20261103T030351Z_3ace3b8f0adc | the first nine J24 rows, map row at 8192 | stock, explore, fit sweep sitting 1 |
| 679422b9443a-dirty | kit_20261103T032438Z_ab5896f8453d | the same with the map row at 4096 (the ladder's 4096 step; rows sharing an RVA are refused, so one build per value) | ladder 4096, shots f3_4k* |
| e876198be89a | kit_20261103T035945Z_354011cb0fc6 | + trapezoid focus and near-scale rows | fit sweep sitting 2, ladder control / 8192 / q4, shots |
| 75739186b92e | kit_20261103T063744Z_6bab276b0030 | main merged (J46), release values on | idle check, 20-pass acceptance, release perf |

Every launch's `raw/<tag>/proxy.log` lists the 64 sites: all `stock` with the keys off ("key off"), and `wrote <row>` for each key on.

## Drivers (run from the repo root)
- `fit.sh <tag> "<keys>" [yaw|shots|both]`: one launch: land_small, the J8 yaw sweep (camera (-0.08, 59.02, 446.14), pitch -25, yaw
  0..315 in 45 degree steps; a capture per yaw), the six shot poses (capture + shot each), then siege_small at its deploy pose (s1).
- `fitsweep.sh`, `fitsweep2.sh`, `fitsweep3.sh`: the fit sittings; `ladder.sh`: the perf ladder; `shots.sh`: the before/after sitting;
  `final.sh`: the final build's idle check, acceptance and release perf. Helper: `summ.py` (a launch's summary). The reusable
  helpers are registered tools since review round 1: `tools/shadow_density.py --run 20261103_j24pc <tags>` (import + density table,
  `density.tsv`), `tools/shot_sheet.py --shots harness/runs/20261103_j24pc/raw` (contact sheets), `tools/perf_baseline.py ladder`
  (`ladder_table.md`) and `tools/acceptance_summary.py` (per-pass results of the acceptance runs).

## Shot poses (`ctl.py cam` x y z yaw pitch; land_small, the same before and after)
| pose | camera | what it shows |
|---|---|---|
| p1 | -0.08 18.2 285 0 -12 | low, sun behind the camera, the line ahead |
| p2 | -0.08 18.2 300 90 -10 | low among the line, side-on to the sun |
| p3 | -0.08 18.2 285 45 -12 | low, 45 degrees to the sun |
| p4 | -0.08 18.2 340 180 -12 | low behind the cavalry, facing the sun |
| p5 | -0.08 59.02 446.14 180 -25 | the deploy pose |
| p6 | -0.08 59.31 525.65 180 -20 | distant (asked 120 / 700; the engine clamps the height above terrain to 44.556 m, so the read-back pose is the one used) |
| s1 | siege_small's deploy pose | the wall and units |
Yaw 270 of the sweep reads back outside tolerance in every launch (J8 had the same); the first stock launch asked p1..p4 at y 15, which
the engine clamps to 18.2 (2.5 m above terrain), hence 18.2 from then on. `explore` found the poses.

## Incidents
- `f_8k_crop`: the driver file was edited while bash was reading it (syntax error after the land scene); the game stayed open and the
  next launch `f_hw` reused that process ("via reset"), so `raw/f_hw` and its captures are 8192 + crop keep, not the hardware path.
  The hardware path is `f_hw2`. Guard: the driver headers say never edit while it runs; `fit.sh` now stops a launch whose scene fails.
- `f2_focus` first launch: HEADLESS FAILED, the game exited at DllMain (first-chance access violations in ntdll on another thread, before
  any shadow code runs); the retry with the same key was clean (`raw/f2_focus_fail1`, `raw/f2_focus`). One failure, not two.
- No hang, no WER dump.

## Results
Fit (texels per metre at 20 m, `tools/shadow_density.py`; the full table is `density.tsv`), the map-size ladder (`ladder_table.md`), the shots
(`sheets/`), acceptance and release perf: `jobs/J24/report.md`.
