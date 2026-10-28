# Review of J1 (proxy d3d9.dll skeleton)

## Round 2 (2026-10-28, branch `job/J1` at 3a4a0b0)

Reviewer: a fresh Opus chat (session `012gysszKfgEDZBam12C2XKX`) that built none of the branch and did not write round 1
(builders: `012gyst2WGieh6E9fBXeYUbt`, `012gyst2KMskWjuqMKwjyWoq`; round 1: `012gysszNeXGg95BXVQ4NhXy`). Checked against
`jobs/J1/brief.md`, `jobs/J1/report.md` and round 1 below.

**Verdict: merge.** Every round-1 finding is closed with evidence in the repo, and the head DLL is the PC-tested DLL, reproduced
here independently. One new latent bug in the atomic write (no effect with 0 engine sites) goes to the next DLL rebuild on purpose,
so the tested binary stays the head binary. Merging also accepts **D22-D25**, which are still marked "for Liam's review".

### Machines (this container, 2026-10-28)

| check | result |
|---|---|
| `python3 core/wsc.py gates` at 3a4a0b0 | 11 ok, 0 failed |
| `proxy/tools/build.sh all` | build `30a7b815163a`, `d3d9.dll` sha256 `b15bf2bba2f6fb97fac57429d295da7158cf5ef289b2f0cda4392670ea774e36`: **the bytes of PC run `20261028_pcrerun`**; imports kernel32, advapi32, dbghelp, msvcrt; 9 undecorated exports; host tests 48 + 81 + 165 + 135 passed |
| `proxy/tools/build.sh repro` | identical from another path |
| `proxy/tools/build.sh smoke` (wine 9.0) | passed: 5 launches, 2 dumps (mode 1 dump named in the log with an MDMP signature; host-replaced filter logged REPLACED, mode 2 still dumps) |
| CI runs cited in the report | not opened: this session has no GitHub API access to the repo. The local build matching the PC sha covers the claim that matters |

### Round-1 findings

| # | status | evidence |
|---|---|---|
| 1 ImageBase / repro | closed (round 1 fix) | sha above; `repro` identical |
| 2 head build untested on PC | closed | `proxy/runs/20261028_pcrerun/b_system_proxy.log`: build `30a7b815163a`, `file ImageBase 0x00400000, delta 0x00210000`; `d_mismatch_dxvk_proxy.log`: forced mismatch, plan all off, `patch_engine: not run (pass-through)` |
| 3 failed install | closed (round 1 fix) | `tests/test_pc_deploy.py` in the gates |
| 4 write-time all-or-nothing | closed, one new bug (below) | `proxy/core/patch_engine.h` `WritePlanAtomic`; `test_patch_engine` failure cases |
| 5 crash capture end to end | closed | smoke cases 4 and 5 (run here); filter checks at first create and at detach in both PC logs |
| 6 evidence outside the repo | closed | `e_install_history.json` (`identical: true, diffs: []`), `crashdumps_before.txt` / `_after.txt` (identical but for the VM session path) |
| 7 bookkeeping | closed | `jobs/J1/report.md`; row `review`; `main` merged in |

### Findings

#### Blocker
None.

#### Should-fix
None left on the branch.

#### Later
1. **Successful writes restore page protections in the wrong order.** `proxy/core/patch_engine.h:171` (the reprotect loop after
   the `memcpy`). VirtualProtect is per page and returns the page's current protection. When two sites share a page, the second
   saves `PAGE_EXECUTE_READWRITE` as its "old", and restoring forward leaves that page RWX with no log line and
   `reprotectFailures == 0`. The rollback path already restores in reverse. To see it fail: a page-level fake `MemOps` with two
   sites in one page; `test_patch_engine` then reports `f.Writable() == 0 (1 != 0)`. Fix: restore in reverse order (one line).
   The fix and that test are ready as `same_page_reprotect.patch`, delivered with this review; the test fails on 3a4a0b0 and passes
   with the fix. **Not committed here:** `patch_engine.h` is a DLL input, so committing it would make the head DLL differ from the
   PC-tested one (round-1 finding 2 again). It cannot fire today because with 0 sites `WritePlanAtomic` returns before this loop.
   It must land in the next job that rebuilds the DLL, before the first `engine_sites` row, alongside the report's
   `minidump=2` change. The J3 brief should list both.
2. **Build id on a shallow local clone** (carried from the report): `build.sh` mislabels the DLL on a shallow checkout. CI is
   guarded; a guard inside `build.sh` belongs to the same next DLL rebuild.
3. **`DXVK_STATE_CACHE_PATH` was already set on the PC** (`d_mismatch_dxvk_proxy.log`: "already set by the environment, left
   alone"), so DXVK's state cache goes wherever that variable points, not `napoleon_remastered\dxvk\cache`. The uninstall was still
   identical, so it is not in the game folder. J3 (warm the DXVK state cache) needs to know where it is and who sets it.
4. Carried from round 1, still open: a vanilla game running during the first install is not detected (matters for J2), and
   `proxy.p<pid>.log` files are never rotated.
5. Housekeeping for Liam: once merged, delete `proxy/skeleton`, `review/J1-fixes` and `jobs/queue` (contained in `job/J1` or
   `main`); `C:\napoleon_remastered_pc\_to_delete\` on the PC.

### Risk-first reading
Read in depth: the code changed since round 1 that runs in the game or touches engine memory: `WritePlanAtomic` and
`patch_driver.cpp` (engine memory: finding 1), `crash.cpp` `CrashCheckFilter` with its calls in `backend.cpp` and `dllmain.cpp`
(under the loader lock at detach; it only swaps the filter and puts the game's back), the `pc_deploy.py` record-before-move change
and the uninstall's skip of a backup that was never moved, and the CI full-history guard. Skimmed: run READMEs, tests, README.
Nothing out of scope.

## Round 1 (2026-10-28, branch `proxy/skeleton` at 846b72a)

Date 2026-10-28. Reviewer: a fresh Opus chat that did not build the branch (D15 independent check). Brief: the J1 job prompt
(the branch predates `jobs/J1/brief.md` on main, so it was checked against the prompt Liam pasted). Report: there is no
`jobs/J1/report.md`; the claims were taken from `proxy/README.md` and `proxy/runs/20261028_pctest/README.md`.

Round-1 outcome - merge after fixes. The skeleton is well built and the brief is covered, but the PC run tested a binary that is not the
one on the branch head, and the build was not reproducible (fixed here). One short PC re-run on the final build closes it.

### Machines

| check | result |
|---|---|
| `python3 core/wsc.py gates` at 846b72a | 11 ok, 0 failed |
| `proxy/tools/build.sh all` (container, mingw-w64 i686 13-win32) | DLL built; imports kernel32, advapi32, dbghelp, msvcrt only; all 9 exports undecorated; host tests 48 + 79 + 133 + 135 passed |
| CI on the branch (runs 40760696817, 40761540903, 40767684592, 40767913153, 40767962457) | all green, incl. the wine smoke test |
| merge into current `main` | clean (`git merge-tree`) |

### Findings

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

### Risk-first reading
Read in depth: `pc_deploy.py` (writes to the PC, the only code that moves files in the game folder), `patch_engine.h` +
`patch_driver.cpp` (engine memory), `guard_driver.cpp`, `dllmain.cpp`, `backend.cpp`, `crash.cpp` (all run under the loader lock in
the game). Skimmed: config, log, sha1, generator, fetch_dxvk, WER scripts, tests. The guard contract matches the brief: one
evaluation before the plan, pass-through touches no engine memory, forced mismatch wins over the override, notice written and
cleared, unpinned fails closed (a stated, recorded deviation from Empire: D23, numbered D22 before main gained D21). DXVK is stock 3.1.1, sha-pinned, never committed,
and its log and caches are redirected out of the game folder (the byte-exact uninstall depends on it). Nothing out of scope found.

### Commits by the reviewer (branch `review/J1-fixes`, on top of 846b72a)
- 01405e2 proxy build: fixed DLL ImageBase, `build.sh repro` + CI step (finding 1)
- 094ce2d pc_deploy install: write `install.json` before every change to the game folder, with a test (finding 3)
