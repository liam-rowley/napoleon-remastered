# J44 PC run 20261030_j44pc: the verbs on the PC, the fixed sky, the historical route, the baseline

PC (RTX 4090, Windows 11), headless 1920x1080 through the watcher 1.0.1, 2026-10-30 14:00 to about 15:00 UTC, game lock `j44`. Every launch through
`ctl.py scene` with the adapter's `ctl.launch.keys` (`dev.ctl dev.lua_bridge dev.state_json dev.skip_intro dev.camera dev.perf dev.timeline`
and `dev.file_rules=napoleon_remastered\lua\fixed_sky_rules.txt`). Builds: main's eb9a8a170243 (first verbs), 59c6fa717ed0 (perf fix, sky
junction), dc95ededfbe8 (final: baseline and the 20 passes, kit `kit_20261030T144407Z_dc95ededfbe8`). Raw ctl results and shots in `raw/`.
The 20 passes are run `harness/runs/20261030_j44acc/`.

## a) The game folder before the first install
`pc_deploy snapshot` of the game folder against `C:\napoleon_remastered_pc\snapshots\pre_install_20261030T090208Z.json`: **identical** (1564
files). J43's stray `napoleon_remastered.ini` was already gone. Every uninstall in this run (four) ended "identical to the pre-install
snapshot (1564 files)", always after the lock release and the watcher's restore (`redeploy` order: exit, unlock, wait for no active profile,
uninstall).

## b) The verbs on the PC
| verb | result (raw/) |
|---|---|
| `scene land_small` | ok: launch with the keys 20.0 s, autostart, load 3.6 s, settle 2.7 s (`land_small_scene1.json`) |
| `cam 0 30 200 180 -25` | ok, readback within 0.0005 m and 0.0001 degrees (`land_small_cam1.json`) |
| `shot` | ok, 108 KB JPEG after a settle (`land_small_shot1.json`, `land_small_a.jpg`) |
| `perf 10` | first **failed**: p50 0.0, max 16.0 (24-bit FPU; fact `napoleon.proxy.fpu_precision`); after the fix p50 1.868, p99 3.464 ms, 5136 frames, VRAM 579.6 MB (`sky_a_perf.json`) |
| `state` | ok (`land_small_state1.json`) |
| `scene` from a battle | warm reset (`via: reset`); from a campaign or a historical battle a relaunch (`hist_dresden_scene4.json`: `relaunch`) |
| `cam read` | the engine's deployment view, used for the stored poses (`poses.json`) |

Settle (adapter `ctl.settle`, unchanged values, now measured): scene ready + 30 frames + 2000 ms stable ends about 2.7 s after the load answer
(300 to 960 frames); a shot then differs from one 10 s later by 2.56/255 (`floor_shot2.json`), the floor of grass and idle animation plus JPEG.

## c) Sky and weather, determinism
- Options (`probes/weather_options.lua`): weather Dry, Light rain, Heavy rain, Rain storm; time of day Morning, Afternoon, Evening (caribbean:
  Afternoon, Evening). No random option: the remembered prefs already fix both. Presets pin them by 0-based index (`SetPerBattlePrefs`), read
  back in the autostart result (`weather=dry/Dry time_of_day=2`).
- Without a sky pin, land_small at one pose on three launches: mean abs diff 9.6 to 11.0 (`det_land_*.jpg`: one blue-grey, one warm haze).
- Junction cut only (pack v1): still 9.6 to 11.0. Junction plus `battle_sky_types` cut (pack v2, 705 of 858 junction rows, 599 of 1675 skies):
  2.6 to 2.7 (`det_land2_*.jpg`), against the 2.56 floor. Fact `napoleon.battle.fixed_sky`.
- Per kind, from the baseline's two measure launches (`harness/acceptance/baseline.json` `measured_diff`): land 0.97, siege 1.19, naval 4.47,
  historical 4.20 (Dresden) and 3.19 (Nile): deterministic, thresholds max(4, 2 x diff). Campaign 20.1: **not deterministic** (the camera pans
  by itself; fact `napoleon.campaign.determinism`), kept out of the shot comparison.

## Historical route
`EnumerateBattleMaps("historic", false)` lists 0 maps here (the single-player NHB_ battles); `true` lists 15 NHMPB_ battles. Presets with
`type=historic`, `all_maps=1` and `terrain=` load Dresden (3v3, 7.1 s) and the Nile (1v1, 4.1 s). A warm reset out of a historical battle hung
after `mp_postbattle` (the game was killed through the watcher); `scene` now relaunches instead. Fact `napoleon.autostart.historical`.

## Incidents
- 14:29 a launch died 10 ms after init with a heap corruption (0xc0000374, first-chance dump `napoleon_remastered\dumps\20261030T142951Z-p30708_c0000374.dmp`,
  WER AppCrash report); the next launch was clean, no second case in this run.
- 14:44 to 14:55 every launch failed `HEADLESS FAILED` with the game itself fine: UAC file virtualization had put `headless_status.json` and
  `state.json` into `%LOCALAPPDATA%\VirtualStore\...\napoleon_remastered\` after one failed rename, and the watcher read the stale real file
  (fact `napoleon.harness.uac_virtualstore`). `ctl.py Pc.launch` now moves such copies to `C:\napoleon_remastered_pc\_to_delete\virtualstore_*`
  before every launch (test `tests/test_ctl.PcLaunch`); the proxy side is J16's.

## d) Perf at the acceptance size
land_small at its `deploy` pose, 1920x1080, DXVK, build dc95ededfbe8 (`baseline.json` `perf`): frame time p50 1.841 ms, p99 3.308, max 14.5,
5215 frames in 10 s; address space 1899 of 4096 MB used, commit 1213 MB, working set 989 MB (peak 1064); VRAM 595.4 MB for the process (device
2501 of 24564 MB). The 40-unit battle does not exist yet (fact `napoleon.custom_battle.armies`).
