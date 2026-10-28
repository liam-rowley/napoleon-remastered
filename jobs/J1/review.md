# Review of J1 (proxy d3d9.dll skeleton), branch `proxy/skeleton` at 846b72a

Date 2026-10-28. Reviewer: a fresh Opus chat that did not build the branch (D15 independent check). Brief: the J1 job prompt
(the branch predates `jobs/J1/brief.md` on main, so it was checked against the prompt Liam pasted). Report: there is no
`jobs/J1/report.md`; the claims were taken from `proxy/README.md` and `proxy/runs/20261028_pctest/README.md`.

**Verdict: merge after fixes.** The skeleton is well built and the brief is covered, but the PC run tested a binary that is not the
one on the branch head, and the build was not reproducible (fixed here). One short PC re-run on the final build closes it.

## Machines

| check | result |
|---|---|
| `python3 core/wsc.py gates` at 846b72a | 11 ok, 0 failed |
| `proxy/tools/build.sh all` (container, mingw-w64 i686 13-win32) | DLL built; imports kernel32, advapi32, dbghelp, msvcrt only; all 9 exports undecorated; host tests 48 + 79 + 133 + 135 passed |
| CI on the branch (runs 40760696817, 40761540903, 40767684592, 40767913153, 40767962457) | all green, incl. the wine smoke test |
| merge into current `main` | clean (`git merge-tree`) |

## Findings

### Blocker
None in the code. The PC evidence gap below must close before merge, but it is a re-run, not a code change.

### Should-fix
1. **The DLL depended on the checkout path; the PC-tested binary is not the CI binary.** `proxy/tools/build.sh:21` (846b72a).
   Commit 690ec1a built three ways gave three DLLs: PC kit `211d8ee0…` (run report), CI artifact `0352a18a…` (run 40761540903 log),
   a review worktree `ff1ff850…`. Cause: mingw ld's default `--enable-auto-image-base` hashes the output path into the DLL's
   ImageBase (`objdump -p`: `6a680000` vs `6c880000` for the same objects linked to two names). The README's "the PC test binary is
   the CI binary" was false. **Fixed by the reviewer, commit 01405e2**: `-Wl,--disable-auto-image-base` (DYNAMIC_BASE unchanged), one
   shared compile function, `build.sh repro` (rebuilds from a copy at another path, fails unless byte-identical) and a CI step for it.
2. **The head build never ran on the PC.** `proxy/runs/20261028_pctest/README.md` "Found" 1: 526e1c9 changed `guard_driver.cpp`
   and `patch_driver.cpp` (code that runs in DllMain on the PC) after the sitting, and 01405e2 changes the DLL's ImageBase. Wine smoke
   covers the start-up path but not Napoleon. Fix (job chat, needs Liam): re-run b (system) and d (forced mismatch) on the final build,
   check the log shows `file ImageBase 0x00400000, delta 0x…` with a non-zero delta, add the run to `proxy/runs/`, then update the
   `napoleon.loader.mapped_imagebase_rewritten` fact's notes.
3. **A failed install left nothing to uninstall from.** `proxy/tools/pc_deploy.py:203-235` (846b72a): `install.json` was written only
   at the end, after foreign files had been moved to the state folder. A copy failing half-way (disk full, file locked) made
   `uninstall` answer "nothing installed by this tool" and stranded the player's own `d3d9.dll`. **Fixed by the reviewer, commit
   094ce2d**: the record is saved before every change to the game folder; `tests/test_pc_deploy.py`
   `test_failed_install_still_uninstalls` fails on the old code and passes now.
4. **Patch writes are not all-or-nothing at write time.** `proxy/core/patch_driver.cpp:53`: a `VirtualProtect` failure on one site
   `continue`s and the other sites stay written, against the brief's all-or-nothing. Latent (0 sites). Fix (job chat): protect every
   site first, write only if all succeeded, restore protections otherwise; log it as a refusal.
5. **Crash capture is untested end to end.** `proxy/core/crash.cpp:87`, `proxy/tools/build.sh` smoke: no run, host or PC, has ever
   produced a dump, so "dumps go to a known folder; the log names them" has no evidence. Also, if the game or the Steam overlay
   replaces the top-level filter after DllMain, mode 1 silently never dumps (the Empire trap that mode 2 exists for). Fix: a
   fourth smoke case where `smoke_host.cpp` raises an access violation and the check finds the `.dmp` and the log line; at the first
   export call, log whether the top-level filter is still ours.
6. **Evidence outside the repo.** `proxy/runs/20261028_pctest/README.md` row e cites the PC's `snapshots\after_e.json`, and the
   empty CrashDumps folder is "Liam checked". Commit the post-uninstall `history\install_<utc>.json` (it holds `identical` and the
   diffs) into the run folder; for the dumps, a `dir` listing captured by the agent.
7. **Job bookkeeping.** No `jobs/J1/report.md`; the J1 row on `main` is still `queued`. Rebase on `main` (clean), add the report
   (the brief's "short report": what exists, build/install/uninstall, results with run ids, what moves to the core, open questions),
   set the row to `review`.

### Later
- `proxy/tools/pc_deploy.py:142`: on the device VM the "game closed" check only sees a running proxy; a vanilla game running during
  the first install is not detected. Harmless today (Liam is present), matters once the watcher (J2) runs unattended.
- `proxy/core/dllmain.cpp:60`: second-process logs `proxy.p<pid>.log` are never rotated, so they accumulate (inside the owned
  folder, so uninstall still cleans them).
- `proxy/README.md` "Open questions" 2 is stale: test d has now run on DXVK in the menu (exclusive fullscreen not stated; say which).
- For warscape-core when `proxy/core/` moves: carry `build.sh repro` and the `--disable-auto-image-base` flag with it.

## Risk-first reading
Read in depth: `pc_deploy.py` (writes to the PC, the only code that moves files in the game folder), `patch_engine.h` +
`patch_driver.cpp` (engine memory), `guard_driver.cpp`, `dllmain.cpp`, `backend.cpp`, `crash.cpp` (all run under the loader lock in
the game). Skimmed: config, log, sha1, generator, fetch_dxvk, WER scripts, tests. The guard contract matches the brief: one
evaluation before the plan, pass-through touches no engine memory, forced mismatch wins over the override, notice written and
cleared, unpinned fails closed (a stated, recorded deviation from Empire: D23, numbered D22 before main gained D21). DXVK is stock 3.1.1, sha-pinned, never committed,
and its log and caches are redirected out of the game folder (the byte-exact uninstall depends on it). Nothing out of scope found.

## Commits by the reviewer (branch `review/J1-fixes`, on top of 846b72a)
- 01405e2 proxy build: fixed DLL ImageBase, `build.sh repro` + CI step (finding 1)
- 094ce2d pc_deploy install: write `install.json` before every change to the game folder, with a test (finding 3)
