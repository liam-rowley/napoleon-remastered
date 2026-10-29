# Proxy d3d9.dll

Owner of: the proxy DLL skeleton (backend loading, log, crash capture, exe-identity guard, runtime patch engine), its build, and its
PC install and uninstall. Plan: `docs/plans/PLAN.md` phase 1 (and phase 6 for install/uninstall). Status: skeleton, no features: with
the DLL installed the game must look and behave exactly like vanilla. PC results: `proxy/runs/`.

## Layout

| Path | What | Moves to warscape-core at the end of phase 1 |
|---|---|---|
| `core/pe.h`, `sha1.h`, `guard.h`, `patch_engine.h`, `config.h` | pure logic, no Windows headers, host-tested | yes |
| `core/dllmain.cpp`, `log.cpp`, `crash.cpp`, `guard_driver.cpp`, `patch_driver.cpp`, `backend.cpp`, `runtime.h`, `adapter.h`, `d3d9.def` | in-process drivers, game-agnostic | yes |
| `napoleon/identity.json` | the exe pin, config file and mod folder names | no (adapter) |
| `napoleon/adapter.cpp`, `napoleon/generated/tables.h`, `napoleon/napoleon_remastered.ini` | adapter; the last two are GENERATED | no (generator moves) |
| `tests/` | host tests (`g++`, synthetic PE images) | yes |
| `tools/` | build, generator, DXVK fetch, kit/install/uninstall, exe info, WER LocalDumps | all but `exe_info.py` defaults |

`test_guard.cpp` fails if a `core/` file names a game (provenance links to empire-remastered excepted).

## Build

**Release route: mingw-w64 i686 (`g++-mingw-w64-i686`, GCC 13 win32 thread model) on Linux**, in CI (`ubuntu-24.04`) and on the
PC inside Docker Desktop (`ubuntu:24.04` pinned by digest in `build.sh`, the same apt packages; D31). Why this one and not MSVC on the Windows runner:
- one toolchain everywhere an agent works: the local container builds exactly what CI builds, so the DLL tested on the PC is reproducible
  from the commit (no PE timestamp, relative file names; build id = commit, `-dirty` if `proxy/` has local changes);
- DXVK's own release route is mingw (empire-remastered `dxvk_fork/docs/build.md`), so a later DXVK-side change needs no second toolchain;
- the DLL depends on system DLLs only (static libgcc/libstdc++, no winpthread): `build.sh` fails on any other import, and on a
  missing or decorated export (`Direct3DCreate9@4`).
MSVC stays the fallback (kill criterion: 3 failed loads on the PC -> stop and propose it).

```sh
proxy/tools/build.sh --docker all     # on the PC (Git Bash, Docker Desktop running): gen --check, build/proxy/napoleon/d3d9.dll, host tests
proxy/tools/build.sh --docker repro   # the same bytes from another checkout path
proxy/tools/build.sh all              # on Linux with g++-mingw-w64-i686 installed (CI)
```
`--docker` computes the build id on the host (a worktree's `.git` points at a host path the container cannot see) and passes it in;
`smoke` needs wine and runs in CI only. Fallback when Docker is down: the CI artifact, `gh run download <run id> -n proxy-d3d9-napoleon`.
CI: `.github/workflows/gates.yml` job `proxy` runs `build.sh all` on every push and keeps the DLL as an artifact; the `gates` job
runs `tests/test_proxy_tables.py` (generated tables current) and `tests/test_pc_deploy.py`.

## Start-up and the pass-through contract

DllMain (`core/dllmain.cpp`), in order: folders, config, launch id, log -> crash capture -> **exe-identity guard, once** ->
`PlanEngine` -> patch engine (only if `plan.patches`). The backend loads at the first export call, never under the loader lock.

`guard.h` `PlanEngine(enabled, engineOk)` is the only switch engine-side code may ask (same contract as empire-remastered
`rml_mod/docs/exe_guard.md`, `PlanD3DHooks`): pass-through = `patches`, `engineHooks`, `d3dHooks`, `engineReads` all false. What stays
in pass-through: config, log, crash capture, the notice, the backend (a d3d9 implementation, not engine memory). The skeleton installs
no hook at all; `test_guard.cpp` lints that DllMain runs the guard before the plan and the plan before the patch engine, and that the
backend, log and crash code never touch the exe image.

## Exe-identity guard

Identity = sha1 of the exe FILE (hashed in DllMain with a built-in SHA-1, about 18 MB) + the running image's PE TimeDateStamp and
SizeOfImage. Pin: `napoleon/identity.json` (from `proxy/runs/20261028_exeinfo`).

| verdict | when | result |
|---|---|---|
| match | pinned, nothing differs | engine features on |
| NOT PINNED | the adapter pins nothing | pass-through (fails closed; Empire allowed it) |
| OVERRIDE | `exe_guard=0` | engine features on whatever differs, warning every start (developers) |
| MISMATCH | pinned and anything differs, or the exe file unreadable | pass-through + `napoleon_remastered\EXE_MISMATCH.txt` + an ERROR line naming the first difference, one line per difference |
| FORCED MISMATCH | `exe_guard_force_mismatch=1` | the pass-through path on a matching exe (wins over `exe_guard=0`) |

The notice is rewritten at every pass-through start and removed at the next accepted start. Never a dialog.

## Runtime patch engine

Sites live in the `engine_sites` registry; `tools/gen_tables.py` turns them into `napoleon/generated/tables.h` (`--check` runs in the
gates). **Byte layout** (the registry has one RVA): `anchor_bytes` start at `rva`; `stock_bytes` follow immediately at
`rva + len(anchor)`; a patch replaces exactly the stock bytes with `patch_bytes`, a hook detours at `rva + len(anchor)` (at least
5 stock bytes). A function-entry hook anchors on the bytes before the entry (padding or the previous `ret`).
Checks per site after rebasing (`patch_engine.h`): inside one section's file-backed bytes (a hook in an executable one); anchor and
stock equal after taking the load delta off every relocated dword; a patch's own bytes carry no relocation; no overlap. The load delta is the actual base minus the exe FILE's ImageBase (read by the guard while hashing): the loader rewrites
ImageBase in the mapped header, so a delta from memory is always 0 (`pe.h` `LoadDelta`, PC run `20261028_pctest`). Already
patched counts as done. **Any bad site -> nothing is written**, every site still logged. A site with a `config_key` (a boolean key) is
checked always and written only when the key is on. No real sites yet: `tests/test_patch_engine.cpp` proves the engine on a synthetic
image with Napoleon's section layout at three load bases.

Adding a site: `python3 core/wsc.py reg add engine_sites ...` (with `exe=sha1:<pin>`), `python3 proxy/tools/gen_tables.py`, rebuild,
then a PC run that logs `patch_engine: apply` and the site `stock`, and set `verified`.

## Config, log, crash capture

- **Config**: `napoleon_remastered.ini` next to the exe; `[proxy] backend=dxvk` is registry id `proxy.backend`. Every key is a row of
  `registries/config_keys.jsonl`; the C++ key table and the shipped file (at the release values) are generated. Unknown keys, bad values
  and duplicates are logged as warnings; a bad value takes the default. Edit on the PC with `pc_deploy.py set`.
- **Log**: `napoleon_remastered\logs\proxy.log`, one per launch (the previous one becomes `proxy.prev.log`), UTC timestamps, first
  line `launch <id>` (`20261028T201500Z-p1234`), then every config key, the guard verdict, the plan, every patch site, the backend and
  its DXVK paths; a clean exit ends with `process detach (process exit)`. A second process logs to `proxy.p<pid>.log`.
- **Crash**: `proxy.minidump` 1 (default) = a minidump for an unhandled exception, 2 = also the first fatal first-chance one; dumps go
  to `napoleon_remastered\dumps\<launch id>_<code>.dmp` and the log names them; the first five fatal first-chance exceptions are logged
  either way. On Napoleon the top-level filter is replaced after DllMain (run `20261028_pcrerun`), so mode 1 does not dump in-process;
  the log warns at the first export call and at detach. WER LocalDumps (out of process, works on a corrupt heap) is the backstop: Liam runs `tools/wer/Enable crash dumps.cmd`
  once (admin); dumps go to `%LOCALAPPDATA%\CrashDumps\napoleon_remastered`, outside the game folder; the log states the key at start.

## DXVK

Stock, latest stable release, pinned by version and three sha256 (tarball, `x32/d3d9.dll`, LICENSE) in `tools/fetch_dxvk.py`
(3.1.1). Never committed. Shipped as `napoleon_remastered\dxvk\d3d9_dxvk.dll`. The proxy sets `DXVK_CONFIG_FILE`, `DXVK_LOG_PATH`
and the cache paths into that folder unless already set: DXVK's defaults write into the working folder (the game folder), which would
break the byte-exact uninstall.

## PC install and uninstall (`tools/pc_deploy.py`)

The game folder is a deploy target; everything runs in Git Bash in the repo.
1. `proxy/tools/build.sh --docker all && python3 proxy/tools/pc_deploy.py kit` -> `build/kits/kit_<utc>_<build>/`: `manifest.json`,
   payload files under unique names `<sha12>__<name>`, and `pc_deploy.py` itself.
2. `python3 proxy/tools/pc_deploy.py send --kit build/kits/<id> --state <state>` copies it sha-checked to `<state>\kits\<id>`; a kit id
   already there is refused (a new kit id every time: the stale-resend bug, empire-remastered LEARNINGS lesson 18).
3. `python3 proxy/tools/pc_deploy.py install --kit <state>/kits/<id> --game <game> --state <state>`: checks every staged sha256 first (a stale copy is
   refused, nothing installed), refuses while the game looks open, snapshots the game folder (first install), backs up any foreign file
   at an owned path, copies with a temp name + rename, re-hashes every destination, writes `<state>\install.json`.
4. `pc_deploy.py uninstall --game <game> --state <state>`: moves everything owned (`d3d9.dll`, the ini, the whole
   `napoleon_remastered\` with its runtime logs, dumps and DXVK files) to `<state>\_to_delete\`, restores backups, snapshots and diffs
   against the pre-install snapshot; exit 0 only when identical (sha256 for every file up to 100 MB, size + mtime above).
Never delete on the PC: removals are moves to `_to_delete\` after a verified copy. Both refuse while either title runs: the watcher's
process list when it is alive, else `tasklist`.

## Hooks (J3, D26)

`core/hooks.cpp`: `IatHook` swaps one import-table slot of the game exe (validated as snapped first; a slot not yet snapped at
DllMain is retried at the first `Direct3DCreate9`), `VtableHook` one slot of a D3D object (`IDirect3D9::CreateDevice` [16],
`IDirect3DDevice9::Present` [17]). Every hook is logged (`hook: iat|vtable ... slot old -> new`). Only the dev side installs hooks,
only with a dev key on and the guard's plan allowing them (`DevInit`; `tests/test_dev.cpp` lints it).

## Dev control channel (J3)

All `[dev]` keys default off with release value off (`registries/config_keys.jsonl`); with none set the proxy is the skeleton.
- `dev.timeline`: `napoleon_remastered\logs\timeline.json` (phases, UTC ms, t from process creation); `proxy/tools/timeline_table.py`.
- `dev.log_files`: the file survey `logs\files.log` (every distinct open, check and listing); `proxy/tools/survey_table.py`.
- `dev.skip_intro`, `dev.file_rules`: movie and file rules (`core/filerules.h`: redirect, fail, add, movie-fail, movie-redirect).
- `dev.state_json`: `napoleon_remastered\state.json` ~2/s (scene, frame, Lua context, battle probe, memory, Lua reports); in the
  adapter's `heartbeat_files`, so a watcher launch can wait on `"scene": "frontend"` (`wait_log` regex). For a consistent
  snapshot read the state with ctl `state` (the file is replaced by rename about twice a second).
- `dev.lua_bridge`: the wrappers listed in `napoleon/lua/wrappers.txt` (`tools/build_dev_pack.py`) are served by a virtual pack and
  load `napoleon_remastered\lua\wsp.lua`, which loads the bridge (`core/luabridge.cpp`, Lua 5.1.1 core from `tools/fetch_lua.py`).
  Scenes: `core/devcore.h` SceneTracker. Only the main menu pumps in the front end (fact `napoleon.lua.update_callbacks`).
- `dev.ctl` + `dev.ctl_dir`: requests `<dir>\<id>.cmd` (one line), results `<id>.done` (JSON written last: `status` ok | failed |
  timeout | refused, `reason`, `start_utc`, `end_utc`, verb fields, `state_at_end`, `log` = every proxy log line written meanwhile).
  Ids: 1-64 of `A-Za-z0-9._-`, never reused (`_ids.txt`). FIFO, one at a time. From Git Bash: `job.sh ctl <owner> '<line>' [wait_s]`; with no answer it
  withdraws the request (`<id>.cmd.expired`), because the proxy runs every `.cmd` it finds, including on a later launch.

| verb | result fields |
|---|---|
| `ping` | `pong` |
| `state` | `state` (= state.json) |
| `log <text>` | a `ctl: log:` line |
| `lua <file> [t]` | `chunk`: the chunk's returns (`a \| b \| c`) or its error; runs in the pumping script's environment, args `(id, ctx, wsp)` |
| `waitfor <scene>[\|<scene>] [t]` | `scene`, `waited_s`; timeout names the scene |
| `autostart <target> [t]` | `scene`, `lua`, `load_s`, `total_s`; battles: `map`, `map_folder_loaded`, `map_folder_selected`, `preset_map` (WRONG MAP fails) |
| `reset <target> [t]` | `steps`, `from`, `to_frontend_s`, `total_s`, `mem_before/frontend/after`, `autostart {...}` |
| `exit` | written, then the process exits |

Targets: `frontend`, `battle:<preset>` (`napoleon/lua/battles/<preset>.txt`: type, map key, prefs), `campaign:continue`,
`campaign:<save>`, `campaign:new:<campaign>:<faction>`. `<campaign>` must be a key a main-menu button carries (`grand` = the grand
campaign's, `mp_eur_napoleon`; `probes/campaign_keys.lua` lists them): an unknown key is an engine AV, so autostart refuses it.
Run on the PC (`proxy/runs/20261029_j3pc2`): every battle preset and `campaign:new`; `continue`/`<save>` need a save (none yet).
Warm reset works from a battle; from a campaign it is open (fact `napoleon.campaign.quit_to_menu`): use a relaunch.

## Open questions

1. `engine_sites` has no field for where the stock bytes start relative to the anchor; the fixed layout above works, a core field
   (`value_offset`) would allow anchors after the value. Core change (B2-style) if a real site needs it.
2. Exclusive fullscreen through DXVK: with the proxy on DXVK the main menu ran borderless (Liam, run `20261028_pcrerun` step d;
   fact `napoleon.dxvk.menu_display_mode`, open). Whether vanilla runs exclusive on this PC, and what the game's own display setting
   is, is not recorded yet.
3. `proxy.minidump` release value: the game replaces the top-level filter (fact `napoleon.crash.toplevel_filter_replaced`), so
   mode 1 never dumps in-process; mode 2 is the candidate (`jobs/J1/report.md` open question 1).
