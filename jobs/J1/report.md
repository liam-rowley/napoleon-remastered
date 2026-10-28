# J1 report: proxy d3d9.dll skeleton

Branch `job/J1`. Built across several chats on 2026-10-28 (originally on `proxy/skeleton`, then the reviewer's `review/J1-fixes`;
both are contained in `job/J1`, which predates D21 and carries the fixes). Finished under D21 by this chat: merged `main`, PC
re-run, CI fix, this report. **Tested binary: build `30a7b815163a`, `d3d9.dll` sha256 `b15bf2bb…74e36`**, the head build at the
time of writing (`build.sh` build id = last commit touching `proxy/core`, `proxy/napoleon`, `proxy/tools/build.sh`).

## What exists

| brief deliverable | where | evidence |
|---|---|---|
| 1 exports, backend `dxvk` or `system` | `proxy/core/d3d9.def` (9 undecorated exports), `backend.cpp` (loads at first export call, never under the loader lock) | runs `20261028_pctest` b/c, `20261028_pcrerun` b/d |
| 2 config, every key in `config_keys` | `registries/config_keys.jsonl` (8 keys) -> `napoleon/generated/tables.h` + shipped `napoleon_remastered.ini` (`gen_tables.py`, `--check` in the gates); unknown keys warn | `test_config` 48 checks |
| 3 log, one per launch, UTC, previous kept | `log.cpp`: `logs\proxy.log` + `proxy.prev.log`, `launch <id>` first line | every run log |
| 4 crash capture | `crash.cpp` (minidump mode 1/2, first five fatal first-chance logged), `tools/wer/*` (WER LocalDumps, Liam ran it once) | wine smoke AV case (commit e776ec6); on the PC see open question 1 |
| 5 exe-identity guard | `guard.h` + `guard_driver.cpp`: file sha1 + TimeDateStamp + SizeOfImage, once, before the plan; mismatch = pass-through + `EXE_MISMATCH.txt` + first-difference line; `exe_guard_force_mismatch` | `test_guard` 81 checks; PC d in both runs |
| 6 runtime patch engine | `patch_engine.h` (rebased anchor/stock checks, all-or-nothing plan), `patch_driver.cpp` (`WritePlanAtomic`), `tools/gen_tables.py` | `test_patch_engine` 165 checks on a synthetic image at three bases; PC b: `delta 0x00210000` |
| 7 install / uninstall | `tools/pc_deploy.py` (kit with manifest and `<sha12>__<name>` staged names, sha-checked install, record saved before every change, uninstall by move to `_to_delete`, snapshot diff) | `tests/test_pc_deploy.py`; PC e in both runs: identical, 1564 files |
| 8 host tests in CI | `proxy/tests/*` (config, guard, patch engine, sha1) + wine smoke; `tests/test_proxy_tables.py`, `tests/test_pc_deploy.py` in the gates job | CI `proxy` job |

DXVK: stock 3.1.1, pinned by version and three sha256 in `tools/fetch_dxvk.py`, never committed; its log and caches are redirected
into `napoleon_remastered\dxvk\` so the uninstall stays byte-exact.

## Build, install, uninstall

`proxy/README.md` owns the steps (Build; PC install and uninstall). Short form: `apt-get install g++-mingw-w64-i686`;
`proxy/tools/build.sh all` (and `repro`); `python3 proxy/tools/pc_deploy.py kit`; on the PC `pc_deploy.py install --kit … --game …
--state C:\napoleon_remastered_pc`, `set key=value`, `uninstall`. The uninstall needs deletion allowed for the game folder from the
device VM (asked once per session).

## Test results

| run | build | result |
|---|---|---|
| `proxy/runs/20261028_exeinfo` | - | exe identity re-read on the PC; pinned in `napoleon/identity.json` |
| `proxy/runs/20261028_pctest` | 690ec1a93fd3 | a-e pass; found the zero rebase delta (fixed in 526e1c9) |
| `proxy/runs/20261028_pcrerun` | **30a7b815163a** | b, d, e pass on the head build: delta `0x00210000`, forced mismatch on DXVK, uninstall identical to the pre-install and vanilla snapshots; no dumps (listings committed) |
| container 2026-10-28 | 30a7b815163a | `build.sh all`: host tests 48 + 81 + 165 + 135 passed; `build.sh repro` identical; `wsc gates` 11 ok |
| CI 40771118137 (30a7b81), 40775169543 (7da33d4) | - | green; 40775169543 exposed the shallow-checkout build id (below) |
| CI 40776951182 (fe51d25) | **30a7b815163a** | green after the fix: CI's DLL sha256 `b15bf2bb…74e36`, the PC-tested bytes; repro identical |

Review findings (`jobs/J1/review.md`): 1 and 3 fixed by the reviewer; 4 (all-or-nothing writes) 7259833; 5 (crash capture end to end,
filter check) e776ec6; 2 and 6 closed by run `20261028_pcrerun`; 7 by the merge of `main`, this report and the row.

## Deviations from the brief, and why

- **Not a single PC sitting:** two sittings (`20261028_pctest`, then `20261028_pcrerun` for b, d, e) because code that runs in DllMain
  changed after the first. The re-run skipped a (vanilla) and c (d runs the DXVK path), and has no screenshots: Liam confirmed the
  main menu each time.
- **Unpinned adapter fails closed** (Empire allowed it): D23.
- **Merged `main` instead of rebasing:** run reports and build ids cite the branch's commits. The branch's proposed decisions were
  renumbered D22-D25 because Liam's D21 landed on `main` first.
- **CI build id (found while finishing):** the CI `proxy` job checked out shallow, so `build.sh` saw HEAD as the last commit touching
  the DLL inputs: run 40775169543 built `7da33d47485a` / `86343cff…` instead of the tested `30a7b815163a` / `b15bf2bb…`. Fixed in
  the workflow (`fetch-depth: 0` and a step that fails on a shallow clone; CI 40776951182 then built the tested bytes), not in `build.sh`, because `build.sh` is a DLL input
  and changing it would change the tested binary. A guard inside `build.sh` itself is for the next job that changes the DLL anyway.

## What moves to warscape-core at the end of phase 1

`proxy/core/*`, `proxy/tests/*`, `build.sh` (with `--disable-auto-image-base`, `repro` and the full-history requirement),
`gen_tables.py`, `fetch_dxvk.py`, `pc_deploy.py`, `tools/wer/*`. Stays: `proxy/napoleon/*` and `exe_info.py`'s defaults.

## Open questions (for Liam)

1. **`proxy.minidump` release value.** On this PC the top-level crash filter is replaced after DllMain (`CSERHelper.dll`, then
   `Napoleon.exe`; fact `napoleon.crash.toplevel_filter_replaced`), so the shipped mode 1 never dumps in-process. Mode 2 ran one
   launch without a false dump. Proposal: release value 2, changed in the next job that rebuilds the DLL (it is a DLL input). WER
   LocalDumps covers crashes meanwhile.
2. **Display mode through DXVK:** borderless in the menu (fact `napoleon.dxvk.menu_display_mode`, open). Matters for later
   performance work, not for J1.
3. `engine_sites` has no field for where the stock bytes start relative to the anchor (`proxy/README.md` open question 1): a core
   change if a real site needs it.
4. Clean-up on the PC for Liam: `C:\napoleon_remastered_pc\_to_delete\` (three uninstall folders). Old remote branches
   `proxy/skeleton`, `review/J1-fixes` and `jobs/queue` are fully contained in `job/J1` or `main`; they can be deleted.

## Later (carried from the review)

`pc_deploy.py` cannot see a vanilla game running during the first install (matters for J2's unattended watcher); second-process
`proxy.p<pid>.log` files are never rotated.
