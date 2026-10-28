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

**Release route: mingw-w64 i686 (`g++-mingw-w64-i686`, GCC 13 win32 thread model) on Linux**, in the cloud container and in CI
(`ubuntu-24.04`, the same apt toolchain). Why this one and not MSVC on the Windows runner:
- one toolchain everywhere an agent works: the container builds exactly what CI builds, so the DLL tested on the PC is reproducible
  from the commit (no PE timestamp, relative file names; build id = commit, `-dirty` if `proxy/` has local changes);
- DXVK's own release route is mingw (empire-remastered `dxvk_fork/docs/build.md`), so a later DXVK-side change needs no second toolchain;
- the DLL depends on system DLLs only (static libgcc/libstdc++, no winpthread): `build.sh` fails on any other import, and on a
  missing or decorated export (`Direct3DCreate9@4`).
MSVC stays the fallback (kill criterion: 3 failed loads on the PC -> stop and propose it).

```sh
apt-get install -y g++-mingw-w64-i686     # once per container
proxy/tools/build.sh all                  # gen --check, build/proxy/napoleon/d3d9.dll, host tests
```
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
stock equal after taking the load delta off every relocated dword; a patch's own bytes carry no relocation; no overlap. Already
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
  either way. WER LocalDumps (out of process, works on a corrupt heap) is the backstop: Liam runs `tools/wer/Enable crash dumps.cmd`
  once (admin); dumps go to `%LOCALAPPDATA%\CrashDumps\napoleon_remastered`, outside the game folder; the log states the key at start.

## DXVK

Stock, latest stable release, pinned by version and three sha256 (tarball, `x32/d3d9.dll`, LICENSE) in `tools/fetch_dxvk.py`
(3.1.1). Never committed. Shipped as `napoleon_remastered\dxvk\d3d9_dxvk.dll`. The proxy sets `DXVK_CONFIG_FILE`, `DXVK_LOG_PATH`
and the cache paths into that folder unless already set: DXVK's defaults write into the working folder (the game folder), which would
break the byte-exact uninstall.

## PC install and uninstall (`tools/pc_deploy.py`)

The PC is a deploy target; the device VM has `python3` and the game folder mounted.
1. Cloud: `proxy/tools/build.sh all && python3 proxy/tools/pc_deploy.py kit` -> `build/kits/kit_<utc>_<build>/`: `manifest.json`,
   payload files under unique names `<sha12>__<name>`, and `pc_deploy.py` itself.
2. Send the kit folder to the PC's state folder (`device_commit_files`, a new kit id every time: the stale-resend bug,
   empire-remastered LEARNINGS lesson 18).
3. PC: `python3 pc_deploy.py install --kit <kit> --game <game> --state <state>`: checks every staged sha256 first (a stale copy is
   refused, nothing installed), refuses while the game looks open, snapshots the game folder (first install), backs up any foreign file
   at an owned path, copies with a temp name + rename, re-hashes every destination, writes `<state>\install.json`.
4. `pc_deploy.py uninstall --game <game> --state <state>`: moves everything owned (`d3d9.dll`, the ini, the whole
   `napoleon_remastered\` with its runtime logs, dumps and DXVK files) to `<state>\_to_delete\`, restores backups, snapshots and diffs
   against the pre-install snapshot; exit 0 only when identical (sha256 for every file up to 100 MB, size + mtime above).
Never delete on the PC: removals are moves to `_to_delete\` after a verified copy. The state folder is outside the game folder; moving
out of the game folder from the device VM needs deletion allowed there for the session (asked once, at the uninstall).

## Open questions

1. `engine_sites` has no field for where the stock bytes start relative to the anchor; the fixed layout above works, a core field
   (`value_offset`) would allow anchors after the value. Core change (B2-style) if a real site needs it.
2. Real-display pass-through through DXVK in exclusive fullscreen is untested on Empire; the PC test (d) is its first run here.
