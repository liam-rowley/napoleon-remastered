# J3 report: dev control channel and load time (interim, stopped at the call budget)

Branch `job/J3`, 2026-10-29. Built by the session that picked the job up (Opus 5.5, as briefed). **Not ready for review:** the brief's
call budget (about 220) is spent; this report says what exists, what was measured and what is left. The row stays `queued` on the
branch until the remaining PC work is done (your call: a second sitting under a fresh budget). Last tested build: `edde0cedd087`;
the two later DLL commits (the 8 s battle settle and a JSON fix for timed-out resets) are not on the PC yet.

## What exists

| deliverable | state | where |
|---|---|---|
| 1 phase timeline | done: every phase the brief lists (process start from the OS, DllMain, Direct3DCreate9, device, first Present, every movie open/close/refusal, front-end first pump, autostart issued, loading started, scene ready, first Present after ready, exit) | `core/dev.cpp`, `core/devcore.h` Timeline, `tools/timeline_table.py` |
| 2 baseline | **partly**: single launches only (front end 130.3 s with movies, n=1; battle load 17.9-18.7 s, n=8). The 5-launch arms are not run | `proxy/runs/20261029_j3pc` |
| 3 file rules + survey | done; survey run (6,597 paths) | `core/filerules.h`, `core/files.cpp`, `tools/survey_table.py` |
| 4 intro skip | done, measured: main menu pumps at 7.0 s (n=7) instead of 130.3 s | adapter `kIntroMovies` |
| 5 Lua bridge | done: Lua 5.1 float, `package.loadlib` reachable; first approach worked | `core/luabridge.cpp`, `tools/fetch_lua.py`, `napoleon/lua/wsp.lua` |
| 6 scenes + state.json | done; `state.json` in the adapter's `heartbeat_files` | `core/devcore.h` SceneTracker |
| 7 control channel | done: every verb, unknown verbs and bad ids fail with the reason; host tests for the grammar, ids, targets and scenes (`tests/test_dev.cpp`, 135 checks) | `core/dev.cpp`, `harness/core/job.sh ctl` |
| 8 autostart | battle presets done with the map checked against the engine's own file probes (8 runs); naval/siege presets written, not run; campaign targets written, **not run** | `napoleon/lua/autostart.lua`, `battles/*.txt` |
| 9 warm reset | works from a battle (3 clean, 26-28 s back into the battle vs about 26 s for a relaunch to the same point + kill); one crash when quitting 1.2 s into a battle (now an 8 s settle, untested); **10 in a row not run** | `napoleon/lua/reset.lua` |
| 10 carried over | done: `proxy.minidump` default and release 2; `build.sh` refuses a shallow clone; `proxy.p<pid>.log` rotation (newest 5); `DXVK_STATE_CACHE_PATH` removed | `core/dllmain.cpp`, `core/backend.cpp`, `tools/build.sh` |
| 11 registries | config_keys (10 dev keys), tools (13 rows), engine_facts (13 rows); scenarios rows not added | `registries/` |

Also: `tools/pack_list.py` and `tools/luac_list.py` (pack reader, Lua 5.1 bytecode lister: used to read the front-end flows instead of
guessing them), `tools/build_dev_pack.py`, `build.sh` fixes (a SIGPIPE in the export check, `.def` comments).

## Measured (run `proxy/runs/20261029_j3pc`)

| phase | value | n |
|---|---|---|
| main menu pumps, with movies | 130.3 s | 1 |
| main menu pumps, `dev.skip_intro` | 7.0 s | 7 |
| autostart to the battle (custom land, Grassy Flatlands) | 17.9-18.7 s | 8 |
| warm reset: battle to front end | 6.7-8.8 s | 3 |
| warm reset + autostart back into the battle | 25.8-28.0 s | 3 |
| address space per reset cycle | +1 to +15 MB | 3 |

Targets (proposal, for the next sitting to confirm against a real baseline): front end under 10 s, land battle deployed under 30 s
from process start, warm reset into the same battle under 20 s (the reset loop's polling is now 0.5 s, not yet measured).

## Deviations from the brief, and why

- **Stopped at the budget** before the baselines, naval/campaign runs, 10-reset series, driver-cache test, profile restore and the
  uninstall check (deliverables 2, 8, 9 and PC test steps b, d, f, g, h are open).
- **Timeline is a key** (`dev.timeline`), so the "no dev keys" baseline arm must run with `dev.timeline=1` (it only records).
- **The Lua entry is a virtual dev pack** (D27, proposed): zero-touch, and the wrappers run the vanilla script from the real pack.
- **IAT hooks, not MinHook** (D26, proposed): nothing fetched or vendored for hooks.
- **Map check source:** the engine's battle details carry no map, so the check uses the engine's own preset-folder probes while loading.
- PC Lua files were synced between kits by sha-checked commits of the repo's file for fast iteration; every build was then reinstalled
  from a kit. The PC now holds kit `edde0cedd087` with every dev key off.

## Open questions for Liam

1. A second PC sitting (about 1 hour, game on your monitor) under a fresh call budget to finish the open items above?
2. D26 and D27 (proposed decisions, `docs/DECISIONS.md`).
3. The custom-battle setup created `%APPDATA%\The Creative Assembly\Napoleon\battle_preferences\.sp_default.battle_preferences` on
   your PC (it did not exist). It is now in the adapter's `config_files`; profiles restore it from the next watcher update on.
4. One watcher kill took 200 s (fact `napoleon.harness.kill_slow_once`); worth watching in J13/J4.

## Liam's answers (2026-10-29) and the next chat's start

1. Yes, in a new chat: "pick up the next job" finds this branch's row still `queued` with a remote `job/J3` branch, so the next chat
   continues J3 here (fresh call budget) instead of taking J5. 2. D26 and D27 accepted (D28). 3. The battle prefs file is fine.

Start of the next sitting, in order: kit and install the head build (it has the 8 s battle settle and the reset JSON fix), then
ask Liam before launching; 10 resets in a row (`resets.sh`-style loop through `job.sh ctl`, 5 per device call); the 5-launch arms
(`dev.timeline=1` with and without `dev.skip_intro`, each into the front end and `battle:land_small`); naval and siege presets;
campaign targets (the campaign root's update callback is unproven); driver cache cold/warm; profile restore of the settings files
after battles; uninstall byte-identical; then the scenarios rows, the final report and `status=review`.

## What moves to the core in J12

`proxy/core/{hooks,files,dev,luabridge}.cpp`, `dev.h`, `devcore.h`, `filerules.h`, `pack.h`, `tests/test_dev.cpp`, `tools/fetch_lua.py`,
`timeline_table.py`, `survey_table.py`, `pack_list.py`, `luac_list.py`, `build_dev_pack.py` (with the template's game paths as input),
`job.sh ctl`. Stays: `proxy/napoleon/adapter.cpp` dev specifics and `proxy/napoleon/lua/`.
