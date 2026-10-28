# Run 20261028_pctest: proxy skeleton on the PC (phase 1, job 1, test a-e)

Date 2026-10-28, 20:44Z to 20:55Z. PC `officepc` (Windows x64, RTX 4090, NVIDIA 617.14). Liam present and launching the game from
Steam; the agent installed and uninstalled through the device VM and took the screenshots. Build under test: **690ec1a93fd3**
(`d3d9.dll` sha256 `211d8ee0246c448eeba69ead275bb8ffaf4c757769fcbd735b7c984e61bc4962`), kit `kit_20261028T203729Z_690ec1a93fd3`,
DXVK 3.1.1 (`d3d9_dxvk.dll` sha256 `265888c31ca7...`). WER LocalDumps on for Napoleon.exe (Liam ran `Enable crash dumps.cmd`; every
log confirms `on, DumpType 2`).

| step | setup | launch id | result | evidence |
|---|---|---|---|---|
| a | vanilla, no proxy | - | main menu, clean exit | `a_vanilla_menu.jpg`, snapshot `vanilla_before_a.json` (PC state folder) |
| b | proxy, `backend=system` | `20261028T205019Z-p16716` | guard `match`, plan all on, patch engine 0 sites, system d3d9 from `C:\WINDOWS\system32`, main menu, `process detach (process exit)` | `b_system_proxy.log`, `b_system_menu.jpg` |
| c | proxy, `backend=dxvk` | `20261028T205129Z-p26948` | as b with DXVK 3.1.1; DXVK log and caches in `napoleon_remastered\dxvk\`; no `err:` lines; clean exit | `c_dxvk_proxy.log`, `c_dxvk_d3d9.log`, `c_dxvk_menu.jpg` |
| d | `backend=dxvk`, `exe_guard_force_mismatch=1` | `20261028T205215Z-p12440` | `FORCED MISMATCH` -> plan all off, `patch_engine: not run (pass-through)`, notice written, DXVK serving, main menu, clean exit | `d_mismatch_proxy.log`, `d_EXE_MISMATCH.txt`, `d_forced_mismatch_menu.jpg` |
| e | `pc_deploy.py uninstall` | - | owned files moved to `_to_delete\uninstall_20261028T205301Z\`; folder identical to the pre-install snapshot (1564 files) **and** to the vanilla snapshot taken before (a) | `e_install.json`, PC `snapshots\after_e.json` |

Dumps: none. `napoleon_remastered\dumps\` was never created (no in-process minidump), and Liam checked that
`%LOCALAPPDATA%\CrashDumps\napoleon_remastered` was empty or missing after the sitting. Kill criteria: not hit (first build loaded,
no start-up crash). The main menu looks the same in a-d; the background art changes between launches (vanilla rotates it).

## Found, and turned into code (commit 526e1c9)

1. **Rebase delta was always 0.** Every log read `image base 00610000 (preferred 0x00610000, delta 0x00000000)`; the file's ImageBase is
   0x00400000. The loader rewrites ImageBase in the mapped header, and `patch_driver.cpp` read it from there. With real sites, every
   anchor or stock holding an absolute address would have refused (fail-safe: nothing written, but the engine would never apply).
   Fix: the guard parses the file header while hashing (`Runtime::fileImageBase`), `pe.h` `LoadDelta`, the patch engine refuses if it is
   unknown; `testkit.h` `Mapped()` now rewrites ImageBase like the loader; `test_patch_engine` proves it at three bases; a `test_guard`
   lint forbids a delta from the mapped header. **Host-tested only: not re-run on the PC** (Liam chose to stop); the next PC launch
   should log `file ImageBase 0x00400000, delta 0x00210000` (or whatever the boot's base gives).
2. `pc_deploy.py set backend=system` crashed with a traceback (it wanted `proxy.backend`). Bare keys now resolve to their one section,
   or exit with the list of valid ids (`tests/test_pc_deploy.py` `test_resolve_bare_keys`).
3. The run logs were git-ignored (`*.log`); `.gitignore` now keeps `proxy/runs/**/*.log`.

## Facts recorded

`registries/engine_facts.jsonl`: `napoleon.loader.mapped_imagebase_rewritten`, `napoleon.exe.observed_base`,
`napoleon.d3d9.proxy_load`, `napoleon.dxvk.v3_1_1_menu`, `napoleon.env.dxvk_state_cache_path`, `napoleon.proxy.passthrough_vanilla`,
`napoleon.steam.installscript_vdf_mtime` (open: `installscript.vdf` mtime changed during the session with identical content; the
uninstall check compares sha256 so it is unaffected).

## Not covered here

- A real exe mismatch (the "first difference" log line) cannot happen on the pinned exe; it is covered by `test_guard.cpp` only.
- Battle or campaign load, alt-tab, resolution changes: beyond the skeleton's main-menu bar.
- On the PC, `C:\napoleon_remastered_pc\_to_delete\` holds the uninstalled files for Liam to delete; deletion stays enabled for the
  game folder only for this session.
