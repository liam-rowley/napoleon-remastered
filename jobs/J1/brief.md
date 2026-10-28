# J1: proxy d3d9.dll skeleton

Phase 1, job 1: the proxy d3d9.dll skeleton for Napoleon: backend loading, logging, crash capture, exe-identity guard and
the runtime patch engine. No features: the game must look and behave exactly like vanilla with the DLL installed.

Model: Opus, reason: DLL and Windows native work (D15). Budget about 200 tool calls; at the cap, stop, commit, report what is left.
At most 2 subagents, only for independent cloud work.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J1`). Read `docs/DECISIONS.md` and `docs/plans/PLAN.md` (phase 1, phase 6).
- Attach `liam-rowley/empire-remastered` (read only, never modified) as the evidence base. Port, don't copy blindly:
  `rml_mod/src/{proxy.cpp, d3d9.def, dllmain.cpp, config.cpp, log.cpp, exe_guard.cpp/.h, exe_guard_sites.h, exe_patches.cpp/.h,
  heap_guard.cpp, hooks.cpp (PlanD3DHooks: the pass-through contract)}`, `rml_mod/src/tests/{exe_guard_test, exe_patches_test}.cpp`,
  `rml_mod/docs/exe_guard.md` (the pass-through contract: read it fully), `rml_mod/tools/gen_exe_patches.py` (table generator idea),
  `rml_mod/tools/crash_dumps/`, `dxvk_fork/docs/build.md` (mingw cross-compile recipes), `docs/learnings/LEARNINGS_HARNESS.md` section
  "PC access" and `LEARNINGS.md` lessons 18 and 23 (stale file resends; start-up heap corruption, read WER first).
  Do NOT port RmlUi, shader swap, controls, dev keys or anything feature-level.

## Target facts
Read from the PC 2026-10-28 in the planning chat; check them again yourself and record them as `engine_facts` rows with date and run id.
`Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`, PE timestamp `0x645e917f`, large-address-aware, ASLR (rebase
every static address), NX. Game folder: `C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War`.
AppData: `C:\Users\liamr\AppData\Roaming\The Creative Assembly\Napoleon`. 32-bit process.

## Decisions already made for this job
- Code lives in this repo under `proxy/`, split `proxy/core/` (game-agnostic: everything except identity pins, sites and paths)
  and `proxy/napoleon/` (the adapter). `proxy/core/` is a core-candidate; it moves to warscape-core at the end of phase 1.
- Build never on Liam's PC: mingw-w64 i686 in the cloud container and/or MSVC x86 on GitHub Actions' Windows runner. Pick one
  as the release build, justify it in `proxy/README.md`, and make CI build the DLL and run the host tests on every push (a second
  workflow job; the Python gates job stays as is). The PC only receives built files.
- DXVK: stock, latest stable release, pinned by version and sha256, fetched by a committed tool (never committed as a binary).
  No DXVK fork.

## Deliverables
1. Proxy exports (`Direct3DCreate9`, `Direct3DCreate9Ex` and whatever else `d3d9.def` needs) forwarding to the configured backend:
   `dxvk` (DXVK's d3d9 shipped under another name next to the exe) or `system` (the real d3d9 from the system folder).
2. Config file next to the exe; every key in the `config_keys` registry (default, release value, owner, what it does). Unknown
   keys are logged, never fatal.
3. Log: one file per launch with a launch id, UTC timestamps (Empire's local-time logs caused misreads), the identity verdict,
   the backend, and every hook or patch applied. Keep the previous launch's log.
4. Crash capture: an in-process minidump plus a committed script that turns on WER LocalDumps for `Napoleon.exe` (needs admin:
   Liam runs it once). Dumps go to a known folder; the log names them.
5. Exe-identity guard, evaluated once before any hook, patch or engine read: pinned identity means engine features on; a mismatch
   means plain pass-through (backend only, no engine memory touched, ever), a notice file for the player, a log line naming the
   first difference; a config key forces the mismatch path for testing. Same contract as Empire's `exe_guard.md`.
6. Runtime patch engine: a generator turns the `engine_sites` registry into a C++ table (`--check` mode, registered as a tool and
   run by CI); each site is checked against its anchor and stock bytes after rebasing, all-or-nothing, logged. There are no real
   sites yet: prove it with host tests on a synthetic image.
7. Install and uninstall tools for the PC: built files go over by sha-checked copy with a manifest and unique staged names (the
   stale-resend bug), game closed first; uninstall restores the folder byte for byte. Never delete on the PC: move to `_to_delete`.
8. Host tests for every pure-logic part (guard verdicts, config parsing, patch table, manifest), green in CI.

## PC test
One short sitting with Liam present: ask before starting. The watcher does not exist yet, so Liam launches the game.
a) vanilla baseline launch to the main menu; b) proxy + system backend; c) proxy + DXVK backend; d) forced mismatch;
e) uninstall, then check the folder is byte-identical to before. For each: the log, zero dumps, the process exits cleanly,
and a screenshot of the main menu. Results go in a dated run report under `proxy/runs/` and as `engine_facts` rows.

## Kill criteria
- The chosen build route cannot produce a DLL the game loads after 3 attempts: stop, report, propose the other route.
- Any intermittent start-up crash with the pass-through proxy: stop, collect WER dumps, report; do not keep relaunching.

## Finish
Write `jobs/J1/report.md`: what exists, how to build, install and uninstall it, the test results with run ids, deviations from this
brief and why, what moves to the core later, open questions. Then `wsc reg set jobs J1 status=review report=jobs/J1/report.md`.
