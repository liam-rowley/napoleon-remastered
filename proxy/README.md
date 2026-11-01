# Proxy d3d9.dll

Owner of: the proxy DLL skeleton (backend loading, log, crash capture, exe-identity guard, runtime patch engine), its build, and its
PC install and uninstall. Plan: `docs/plans/PLAN.md` phase 1 (and phase 6 for install/uninstall). Status: skeleton, no features: with
the DLL installed the game must look and behave exactly like vanilla. PC results: `proxy/runs/`.

## Layout

| Path | What | Moves to warscape-core at the end of phase 1 |
|---|---|---|
| `core/pe.h`, `sha1.h`, `guard.h`, `patch_engine.h`, `config.h`, `display_guard.h` | pure logic, no Windows headers, host-tested | yes |
| `core/dllmain.cpp`, `log.cpp`, `crash.cpp`, `guard_driver.cpp`, `patch_driver.cpp`, `backend.cpp`, `headless.cpp`, `runtime.h`, `adapter.h`, `d3d9.def` | in-process drivers, game-agnostic | yes |
| `napoleon/identity.json` | the exe pin, config file and mod folder names | no (adapter) |
| `napoleon/adapter.cpp`, `napoleon/generated/tables.h`, `napoleon/napoleon_remastered.ini` | adapter; the last two are GENERATED | no (generator moves) |
| `tests/` | host tests (`g++`, synthetic PE images) | yes |
| `tools/` | build, generator, DXVK fetch, kit/install/uninstall, exe info, WER LocalDumps | all but `exe_info.py` defaults |

`test_guard.cpp` fails if a `core/` file names a game (provenance links to empire-remastered excepted).

## Build

**Release route: mingw-w64 i686 (`g++-mingw-w64-i686`, GCC 13 win32 thread model) on Linux**, in CI (`ubuntu-24.04`) and on the
PC inside Docker Desktop (`ubuntu:24.04` pinned by digest in `build.sh`, the same apt packages; D31). Why this one and not MSVC on the Windows runner:
- one toolchain everywhere an agent works: the local container builds exactly what CI builds, so the DLL tested on the PC is reproducible
  from the commit (no PE timestamp, relative file names; build id = a hash of the DLL inputs' content, `core/proxy/tools/build_id.py`, `-dirty` if an input has local changes: J45);
- DXVK's own release route is mingw (empire-remastered `dxvk_fork/docs/build.md`), so a later DXVK-side change needs no second toolchain;
- the DLL depends on system DLLs only (static libgcc/libstdc++, no winpthread): `build.sh` fails on any other import, and on a
  missing or decorated export (`Direct3DCreate9@4`).
MSVC stays the fallback (kill criterion: 3 failed loads on the PC -> stop and propose it).

```sh
core/proxy/tools/build.sh --docker all     # on the PC (Git Bash, Docker Desktop running): gen --check, build/proxy/napoleon/d3d9.dll, host tests
core/proxy/tools/build.sh --docker repro   # the same bytes from another checkout path
core/proxy/tools/build.sh all              # on Linux with g++-mingw-w64-i686 installed (CI)
```
`--docker` computes the build id on the host (a worktree's `.git` points at a host path the container cannot see) and passes it in;
`smoke` runs the built DLL under wine: `build.sh --docker smoke` (after `--docker all`; the same container plus CI's wine packages,
about 70 s, J42) or `build.sh smoke` on Linux with wine. Fallback when Docker is down: the CI artifact, `gh run download <run id> -n proxy-d3d9-napoleon`. When CI skipped `proxy` because the same input tree
already passed (J54), the run's summary names the run that built it: download from that one.
CI: `.github/workflows/gates.yml` job `proxy` runs `build.sh all` and `smoke` when the branch changes its inputs (`tools/changed_inputs.py`) and
keeps the DLL as an artifact; the `gates` job runs `tests/test_proxy_tables.py` (generated tables current) and `tests/test_pc_deploy.py`.

**Local gates run the host tests too** (J41): `python3 core/wsc.py gates` (the `tests` gate, not `--fast`) runs
`tests/test_proxy_host.py`, which skips in about a second when no proxy input changed against the merge base with `origin/main`
(uncommitted and untracked files count), and otherwise runs `build.sh all` (native mingw) or `build.sh --docker all` (~1 min) through
Git Bash, then the wine smoke test on the same route (`--docker smoke`, or native `smoke` with wine on PATH; otherwise a warning
that it is CI-only; J42). With neither toolchain it is a skip naming the suites not run, which the core's
`tests` gate shows as a warn (J41; since core v0.4.0, J12). CI still runs them.

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

Adding a site: `python3 core/wsc.py reg add engine_sites ...` (with `exe=sha1:<pin>`), `python3 core/proxy/tools/gen_tables.py`, rebuild,
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
1. `core/proxy/tools/build.sh --docker all && python3 core/proxy/tools/pc_deploy.py kit` -> `build/kits/kit_<utc>_<build>/`: `manifest.json`,
   payload files under unique names `<sha12>__<name>`, and `pc_deploy.py` itself.
2. `python3 core/proxy/tools/pc_deploy.py send --kit build/kits/<id> --state <state>` copies it sha-checked to `<state>\kits\<id>`; a kit id
   already there is refused (a new kit id every time: the stale-resend bug, empire-remastered LEARNINGS lesson 18).
3. `python3 core/proxy/tools/pc_deploy.py install --kit <state>/kits/<id> --game <game> --state <state>`: checks every staged sha256 first (a stale copy is
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
only with a dev key on and the guard's plan allowing them (`DevInit`; `tests/test_dev.cpp` lints it). Headless (below) hooks the
exe's user32 window imports and more `IDirect3D9` slots the same way, each slot once (a recreated `IDirect3D9` shares the vtable).

## Dev control channel (J3)

All `[dev]` keys default off with release value off (`registries/config_keys.jsonl`); with none set the proxy is the skeleton.
- `dev.timeline`: `napoleon_remastered\logs\timeline.json` (phases, UTC ms, t from process creation); `core/proxy/tools/timeline_table.py`.
- `dev.log_files`: the file survey `logs\files.log` (every distinct open, check and listing); `core/proxy/tools/survey_table.py`.
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
| `console <line>\|status\|on\|off` | line: `path` (system, tweak, campaign, unknown, refused), `command`, `args`, `forwarded`, `hits`, `chunk`; status/on/off: `gate`, `slot`, `campaign`, `cli`, `forwards`, `hits`, `refusals`, `gate_offset`, `gate_sets` (J15, below) |
| `exit` | written, then the process exits |

Targets: `frontend`, `battle:<preset>` (`napoleon/lua/battles/<preset>.txt`: type, map key, prefs), `campaign:continue`,
`campaign:<save>`, `campaign:new:<campaign>:<faction>`. `<campaign>` must be a key a main-menu button carries (`grand` = the grand
campaign's, `mp_eur_napoleon`; `probes/campaign_keys.lua` lists them): an unknown key is an engine AV, so autostart refuses it.
Run on the PC (`proxy/runs/20261029_j3pc2`): every battle preset and `campaign:new`; `continue`/`<save>` need a save (none yet).
Warm reset works from a battle; from a campaign it is open (fact `napoleon.campaign.quit_to_menu`): use a relaunch.

## Fixed sky (J44)

`proxy/tools/build_fixed_sky_pack.py` (run by `pc_deploy.py kit` where the packs are readable) cuts `battles_to_battle_sky_types_junctions` and
`battle_sky_types` to one sky per weather and time of day ("clear" first) into `napoleon_remastered\packs\zz_napoleon_remastered_fixed_sky.pack`;
`dev.file_rules=napoleon_remastered\lua\fixed_sky_rules.txt` lists it in `data\` virtually (no file written there). Presets pin weather and time
of day by option index (`weather=`, `time_of_day=`); historical presets use `type=historic`, `all_maps=1`, `terrain=`. Facts
`napoleon.battle.fixed_sky`, `napoleon.battle.weather_options`, `napoleon.autostart.historical`.
The kit manifest's `fixed_sky` says whether the pack is in the kit (`present` with its sha256, or not with the reason). A kit without it
(CI, or a PC whose packs did not read) installs, but `ctl.py` `Pc.launch` refuses before starting the game when the launch's
`dev.file_rules` adds a source the installed kit lacks, naming the rule, the file and the kit (J45).

## Battle camera (J43)

`dev.camera` (default and release value off) adds `wsp.cam_set(x, y, z, yaw, pitch)` to the dev Lua bridge: on the engine thread (the
battle pump) it calls the active camera mode's own `SetTargetAndPosition(target, position)` (vtable slot 0xbc, an engine call, no detour);
the mode comes from a pointer chain (battle owner global, +0xf8, +0x281b8, +0x800, engine_sites `battle.camera_*`) and its vtable slot is
compared with the checked site before every call. Pure parts in `core/camera.h` (`tests/test_camera.cpp`), driver `core/camera.cpp`.
The chunks `napoleon/lua/ctl/cam_set.lua`, `cam_read.lua` (readback through `BattleUI.BackProjectPosition`) and `speed.lua` (RequestSpeed)
are what `core/harness/ctl.py` `cam`, `pause` and `speed` run; facts `napoleon.battle.camera_route`, `napoleon.battle.speed_route`.
Engine Lua never calls `string.find`, `string.sub` or `gmatch`: one call stops the battle pump (fact `napoleon.lua.string_find_stalls_pump`,
`tests/test_repo_rules.py`).

## Frame capture (J8)

`dev.capture=1` (default and release off) hooks 36 `IDirect3DDevice9` vtable slots at `CreateDevice` (`core/capture.cpp`; pure parts and the hash in
`core/capture.h`, `tests/test_capture.cpp`); with it off nothing is hooked, and with it on and no capture running each hook is one flag test.
ctl `capture <name> [frames]` (1 to 8 frames, a new name each time) records every device call of the next frames to
`<dev.capture_dir>\<name>\frame.txt` and each shader's bytecode once per hash to `<dev.capture_dir>\shaders\<hash>.vs|ps`; `dev.capture_dir`
is outside the game folder (D25; empty refuses). Result fields: `dir`, `file`, `shader_dir`, `frames`, `bytes`, `lines`, `draws`, `shaders`,
`shaders_new`, `shaders_unwalked` and `shaders_size_differs` (both must be 0: the walked length agrees with `GetFunction`), `record_s`.
Hash: canonical FNV-1a-64 over the bytecode up to and including the walked end token (never the first `0x0000FFFF`, which a CTAB may hold);
Empire's hashes are not comparable. The vtable survives a device `Reset`, so the hooks stay armed across it. The engine's `D3DPERF` events
(`D3DPERF_BeginEvent` is imported by the exe) are recorded too. Offline: `discovery/core/shader_catalog.py` (summaries, disassembly, fx
mapping, the catalogue and the anatomy tables).

`frame.txt` is one call per line, in call order (pointers and hashes hex, states `name value`):
`CAPTURE <name> launch build frames utc scene` | `STATE` ... `ENDSTATE` (what the previous frame left bound, read back with `Get*`) |
`FRAME n` ... `PRESENT` | `BACKBUFFER ptr` | `SURF ptr w h fmt usage pool ms msq container` (first sight; container = the texture an RT
belongs to) | `TEX ptr type levels w h d fmt usage pool` | `DECL ptr n s.off.type.method.usage.index...` | `SHADER ptr vs|ps hash size walked` |
`RT i ptr` | `DS ptr` | `CLEAR n flags color z stencil` | `STRETCH src l t r b dst l t r b filter` | `FILL`, `UPDSURF`, `UPDTEX`, `READBACK` |
`VS|PS hash` | `VC|PC start count v...` (floats, exact) | `VI|PI`, `VB|PB` | `T stage ptr` | `SS sampler type value` | `RS state value` |
`TSS stage type value` | `VP x y w h minz maxz` | `SC l t r b` | `VD ptr` | `FVF` | `SSRC stream vb offset stride` | `FREQ stream value` |
`IDX ptr` | `XFORM state m16` | `DP type start count` | `DIP type base min nv start prims` | `DPUP`, `DIPUP` | `BEGIN`, `END` |
`SBBEGIN`, `SBEND ptr` | `EVENT name`, `EVENTEND`, `MARKER name`.

## Campaign console (J15)

`dev.console=1` (default and release off): at the first `Direct3DCreate9` the proxy checks the 8 console `engine_sites`, takes the slot address
from the executor's own instruction and claims the slot only if it holds 0 (never a foreign value). The forwarder (`core/console.cpp`, pure rules in
`console.h`, `tests/test_console.cpp`) refuses unless the key is on, the scene is `campaign` and the pointer chain to the live campaign context
holds; then it builds a CampaignCLI with the exe's ctor (no detour) and calls `Execute`, with the context's gate byte set for that one call if it
was 0 (Liam 2026-10-29). Every forwarded or refused line is logged, from the verb and from game Lua's `CliExecute` alike. The verb runs lines
through Lua `CliExecute` and refuses `;`, `#`, quotes, a name that is a file in the game folder (the executor would run it first) and the no-ops
of `runs/20261029_j15re/campaign_commands.tsv` (generated `napoleon/generated/console_table.h`). Units and limits: facts `napoleon.console.*`.

## Headless (J13)

`headless.enabled=1` (default and release value off; the watcher sets it for every launch that is not `visible=1`, `harness/README.md`)
puts every game window on the virtual display and never on a real monitor. Fail closed: there is no path that shows a window on a
real monitor. Decisions are pure functions in `core/display_guard.h` (`tests/test_display_guard.cpp`, including a millisecond
simulation of the display changes Empire hit); the driver is `core/headless.cpp`. Both are core candidates (J12).
- **Target**: the one attached, non-primary display whose adapter or monitor string contains `headless.display_name` and whose rect is
  exactly `headless.size` (physical pixels, per-monitor DPI aware V2 around every query and move). Never an index, a `DISPLAYn` name or
  an assumed origin. Resolved at the first `Direct3DCreate9` or the first game window; the monitor list is logged every launch.
- **Mode list**: `IDirect3D9` slots 6/7/8/15 answer `GetAdapterModeCount` / `EnumAdapterModes` / `GetAdapterDisplayMode` /
  `GetAdapterMonitor` from the target for every adapter (DXVK answers every adapter with the primary's modes).
- **Device**: `CreateDevice` [16] and `Reset` [16 on the device] refuse a fullscreen device or a back buffer that is not `headless.size`;
  a windowed device of at most 8x8 is the engine's helper (a 1x1 one while a battle loads, fact `napoleon.d3d.battle_helper_device`) and passes.
- **Windows** (IAT hooks on the exe's user32 imports, fact `napoleon.exe.window_imports`): a top-level window is created hidden,
  borderless (`WS_POPUP`), `WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW`, then placed on the target and shown with `SW_SHOWNA`; its geometry
  belongs to the guard (the engine's `SetWindowPos`/`MoveWindow` sizes and moves are dropped, its coordinates may be DPI-virtualised);
  a minimise becomes `SW_HIDE`; a show off the target is refused. Windows of at most 8x8 (a helper) are left alone and logged.
  `SetFocus` on a game window is dropped while another process has the foreground (it activates even a no-activate window, fact
  `napoleon.window.setfocus_activates`); the game keeps rendering unfocused (`napoleon.window.background_render`).
  `ChangeDisplaySettingsW` is never applied; `MessageBoxW` is logged and answered with its safe button; `DialogBoxIndirectParamW` -1.
- **Topology guard**: a thread polls the virtual-screen metrics (~4 ms), the target's live rect and the layout signature; with the main
  window's `WM_DISPLAYCHANGE`/`WM_DPICHANGED`/`WM_SETTINGCHANGE`/`WM_DEVICECHANGE` any change cloaks the window first (`DWMWA_CLOAK`),
  the render thread re-resolves by name and size at the next Present, moves and verifies, and the window is uncloaked after
  `headless.settle_ms` of quiet. No target for `headless.refuse_grace_ms`: refusal. Every Present post-checks the windows.
  Left out of Empire's guard: the blocked-poll watchdog and the WndProc chain ping (no other module subclasses the window here).
- **Refusal**: ERROR `headless: REFUSED: <why>`, every window of the process cloaked and hidden, status `refused`, **exit code 2160**.
  Causes: no unique target at the size; a fullscreen or wrong-size device; the guard in pass-through (no hooks) or `proxy.enabled=0`;
  an essential user32 import missing or never snapped; the target gone after a change.
- **Status** `napoleon_remastered\headless_status.json` (rewritten by rename, in the adapter's heartbeat files): `pid`, `launch_id`,
  `state` starting | target_ok | on_virtual | refused, `detail`, `target` {device, adapter, monitor, rect}, `window`, `client`,
  `backbuffer`, `exit_code`, `written_utc`. `on_virtual` = the device exists and a frame was presented with the main window visible
  inside the target.

## Open questions

1. `engine_sites` has no field for where the stock bytes start relative to the anchor; the fixed layout above works, a core field
   (`value_offset`) would allow anchors after the value. Core change (B2-style) if a real site needs it.
2. Exclusive fullscreen through DXVK: with the proxy on DXVK the main menu ran borderless (Liam, run `20261028_pcrerun` step d;
   fact `napoleon.dxvk.menu_display_mode`, open). Whether vanilla runs exclusive on this PC, and what the game's own display setting
   is, is not recorded yet.
3. `proxy.minidump` release value: the game replaces the top-level filter (fact `napoleon.crash.toplevel_filter_replaced`), so
   mode 1 never dumps in-process; mode 2 is the candidate (`jobs/J1/report.md` open question 1).
