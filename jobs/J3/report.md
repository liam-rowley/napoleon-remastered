# J3 report: dev control channel and load time

Branch `job/J3`, 2026-10-29, two PC sittings: `proxy/runs/20261029_j3pc` (build and first measurements) and
`proxy/runs/20261029_j3pc2` (baselines, every autostart target, 10 resets, cache, restore, uninstall), plus the 4K crash Liam hit
between them (`proxy/runs/20261029_4kcrash`) and the review re-check (`proxy/runs/20261029_j3review`). Built by Opus 5.5 as briefed.
The PC ends on kit `kit_20261029T113002Z_753dd22bcc85` (build `753dd22bcc85`, the review fix) with every dev key off.

## What exists

| deliverable | state | where |
|---|---|---|
| 1 phase timeline | done: process start (OS), DllMain, Direct3DCreate9, device, first Present, every movie open/close/refusal, Lua bridge, front-end first pump, autostart issued, loading started, scene ready, first Present after ready, exit | `core/dev.cpp`, `core/devcore.h`, `tools/timeline_table.py` |
| 2 baseline | 5 launches per arm (movies / intro skip) to the front end and into `battle:land_small`; naval, siege and campaign only with intro skip (see Deviations); table below | run `20261029_j3pc2` |
| 3 file rules + survey | done (6,597 paths) | `core/filerules.h`, `core/files.cpp`, `tools/survey_table.py` |
| 4 intro skip | done: main menu at 6.99 s instead of 131.36 s | adapter `kIntroMovies` |
| 5 Lua bridge | done (Lua 5.1, `package.loadlib`; first approach worked) | `core/luabridge.cpp`, `napoleon/lua/wsp.lua` |
| 6 scenes + state.json | done; in the adapter's `heartbeat_files` | `core/devcore.h` SceneTracker |
| 7 control channel | done: every verb, unknown verbs, bad ids, timeouts; 135 host checks | `core/dev.cpp`, `harness/core/job.sh ctl`; verbs and result format: `proxy/README.md` "Dev control channel" |
| 8 autostart | done for land, naval, siege (3+ launches each; the map check counts only the load's own probe since build `753dd22`, confirmed once per preset in run `20261029_j3review`) and `campaign:new` (4 launches, key checked); `campaign:continue` and `campaign:<save>` written but untestable: no saves on the PC | `napoleon/lua/autostart.lua`, `battles/*.txt`, `probes/campaign_keys.lua` |
| 9 warm reset | battle: 10 in a row, no crash, +1.5 MB per cycle; campaign: **open** (below) | `napoleon/lua/reset.lua` |
| 10 carried over | done: `proxy.minidump` 2; `build.sh` refuses a shallow clone; `proxy.p<pid>.log` rotation; dead `DXVK_STATE_CACHE_PATH` removed | `core/dllmain.cpp`, `core/backend.cpp`, `tools/build.sh` |
| 11 registries | config_keys (10 dev keys), tools (14 rows), engine_facts (19 rows), scenarios (`land_small`, `naval_small`, `siege_small`) | `registries/` |

## Baseline and after (run `20261029_j3pc2`, seconds from process creation, median and range, n=5 per arm)

| phase | movies (baseline) | intro skip (after) |
|---|---|---|
| Direct3DCreate9 / device | 1.09 / 1.78 | 1.10 / 1.80 |
| main menu pumps | 131.36 (130.70-131.70) | 6.99 (6.85-7.39) |
| land battle deployed | 154.17 (153.79-158.87) | 26.36 (26.13-26.81) |
| battle load (StartBattle to pumping) | 18.2 | 18.2 |
| naval / siege load (n=3) | | 19.1-19.4 / 20.5-20.9 |
| new campaign load (n=4) | | 16.7-17.3 |
| warm reset back into the battle (n=10) | | 27.1-33.4 |

**Absolute times depend on the PC's state:** after Liam's PC restarted (11:06Z) the same battle loaded in 3.4 s on this build and on
the one before it (run `20261029_j3review`, `raw/R_old_land`), against 18.2 s in the morning. The arms above were measured in the same
state, so the comparison holds; the absolute numbers are that morning's.

**Targets:** front end under 10 s: **met** (7.0 s). Land battle deployed under 30 s from process start: **met** (26.4 s). Warm reset
into the same battle under 20 s: **not met** (27-33 s, of which 8 s is the settle that stops the mss32.dll crash); a relaunch reaches
the same point in 26.4 s, so the warm reset only saves the process (and the lock), not time. DXVK cache cold vs warm makes no
difference (fact `napoleon.dxvk.pipeline_cache`): no warm step built.

PC test steps: a) dev keys off as J1 (sitting 1); b) baseline above; c) survey and intro skip; d) every autostart target, map checked,
3+ launches each; e) every verb, a bad verb, timeouts (sitting 1, and the campaign timeouts in sitting 2); f) 10 resets then relaunch
comparison; g) DXVK cache cold/warm (the NVIDIA driver cache was not cleared: it is shared with every game); h) every settings file
byte-identical after about 25 battles and campaigns (watcher auto-restore, 0 mismatches); uninstall identical to the pre-install
snapshot (1564 files).

## Also fixed in this job (found on the PC or in review)

- **The map check did not show what the engine loaded** (review finding 1): the front end's map-list walk probes every preset folder
  and ends on the selected one, and the proxy reports a folder only when it changes, so the load's probe of the same folder was
  hidden. `FilesMapReset` now clears that after `autostart.lua` returns; the result carries `map_folder_loaded_after_request_ms`, and
  a load that probes nothing fails ("the engine opened no map preset folder"). Lint in `tests/test_dev.cpp`. PC: one launch per
  preset, the load's probe 125-171 ms after the request, right map each time (run `20261029_j3review`). The "map checked" claims of
  run `20261029_j3pc2` rested on the front end's selection probe; they are confirmed only by this re-check.
- **`job.sh ctl` left an unanswered request to run on a later launch** (review finding 3, fixed by the reviewer in `8c0fa90`); the
  PC's copy is re-synced (`e1644cb6...`).

- **The proxy crashed the game at a 4K resolution change** (Liam, 2026-10-29): the main thread's stack overflowed and the vectored
  crash handler formatted a log line on the exhausted stack, faulting inside `d3d9.dll`. Now the handlers only record an exception
  when the stack is short and log it later (`core/crashpolicy.h`, `tests/test_crash.cpp`, build `99c4503`). The overflow itself
  remains (it now dies in ntdll); launching straight into 4K works. Follow-up: **J16** (PR #15, `plan/j16-res-switch-crash`).
- **Watcher profiles failed on the hidden `.sp_default.battle_preferences`** that this job added to the adapter (`Get-Item` without
  `-Force`); fixed, host tests carry a hidden file, PC watcher updated (`harness_20261029T093851Z_ac394b158f25`, confirmed).
- **Campaign autostart** guessed the key and the faction widget: an unknown key is an engine AV in `FrontEnd.OpenMapDataFile`. It now
  reads the keys from the main-menu buttons (as `main.main` does) and selects factions through `faction_selection` or the button group.

## Deviations from the brief, and why

- **Campaign warm reset is not done.** The campaign root has no `QuitToMainScreen`; the escape menu's `QuitToMainScreenFromEscapeMenu`
  is now sent, but the campaign stayed both times (fact `napoleon.campaign.quit_to_menu`). Stopped there for the budget; relaunch is
  the fallback, which the brief allows.
- **No campaign scenario row:** the scenarios schema requires a `save` for campaigns, and there are none yet (J14).
- **Baseline narrower than deliverable 2** (review finding 2): the movies arm ran 5 launches to the front end and a land battle only.
  Naval and siege (n=3) and the new campaign (n=4) ran with the intro skip on, so they have no movies-arm baseline. Battle load does
  not depend on the movies (18.2 s in both arms), so the missing arms would only add the same 124 s of movies.
- **Timeline is a key** (`dev.timeline`), so the baseline arm ran with the timeline, Lua bridge and ctl on (they only observe; the
  movies arm is otherwise vanilla behaviour).
- **IAT hooks (D26) and the virtual dev pack (D27)**, accepted by Liam (D28).
- The sitting driver `j3run.sh` stayed a PC scratch helper (`C:\napoleon_remastered_pc\_scratch\j3s2\tools`): it only wraps `job.sh`
  and `pc_deploy.py`; J4's control API replaces it.
- Two sittings instead of one (the first ran out of its call budget).
- CI's `proxy` job failed from the first J3 commit (`858aa97`): the wine smoke test's crash step still expected J1's default
  `proxy.minidump=1`. The step now sets it explicitly.
- `hooks.cpp`'s garbled header (review Later 7) is fixed with the map-check change, the next DLL change as the review asked.

## What moves to the core in J12

`proxy/core/{hooks,files,dev,luabridge,crash}.cpp`, `dev.h`, `devcore.h`, `filerules.h`, `pack.h`, `crashpolicy.h`, `tests/test_dev.cpp`,
`tests/test_crash.cpp`, `tools/fetch_lua.py`, `timeline_table.py`, `survey_table.py`, `pack_list.py`, `luac_list.py`, `build_dev_pack.py`
(game paths as input), `job.sh ctl`, the watcher hidden-file fix. Stays: `proxy/napoleon/adapter.cpp` dev specifics, `proxy/napoleon/lua/`.

## Open questions

1. J16 (PR #15): the in-game resolution switch overflow. Merge the row when you want it briefed.
2. Campaign warm reset: worth a small follow-up inside J4 (it needs the quit confirmation flow), or accept relaunch for campaigns?
3. Unattended runs show on the primary display until the headless job exists; today's swap left `DISPLAY1` primary and the game was
   invisible to you (flicker on the Dell). Making the VDD primary during sittings would keep runs off your screens.
4. A pre-push gate oddity: from a linked git worktree the `core_pin` gate sees the superproject's status (the hook's `GIT_DIR` leaks
   into the core check). Pushing from the main checkout works. A warscape-core fix, not done here.
