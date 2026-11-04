# J12 review

## Round 1 (2026-10-31, branch job/J12 at caec308)

**Verdict: merge.**

Reviewed cold by a session that did not build or fix the branch. Budget: about 30 tool calls.

### Machines
- `wsc gates`: 10 ok, 2 warn (hooksPath written as an absolute path in this clone; 14 skips, all numpy/Pillow or the viewer wasm), 0 failed, 411 host tests.
- `pr_policy.py --branch job/J12 --base origin/main`: only the missing review and the `done` row, which this review supplies. No rule 79 error.
- `acceptance.py streak --build 31094f6055c2 --watcher 1.2.0`: 20. `core/proxy/tools/build.sh id`: `31094f6055c2`, unchanged after this review's two commits.
- No pull request existed yet, so there were no CI results to read.

### Is the move pure? (checked independently)
I compared git object ids between the pre-move commit `3dce3b4` (where the 20 passes ran) and core `v0.4.0`:
- `proxy/core` = core `proxy/src`: tree `2874c2ab1338`, identical.
- `harness/tests`, `saves/core` = core `saves/`: trees identical.
- `harness/core` against core `harness/` without `tests/`: every file blob identical.
- `proxy/tests`: every blob identical. The only additions are the core's `null_game/` fixtures.
- `build.sh`, `build_id.py`, `fetch_lua.py`, `gen_tables.py`, `pc_deploy.py`, `layout.py`, `fetch_dxvk.py`, `build_dev_pack.py`: blobs identical.

So the build id, the DLL and the watcher 1.2.0 that the 20 passes ran on are the same as what ships. The report's repro and kit sha claims agree with this.

### Claims against evidence
- 1a: `harness/runs/20261031_j12pc/1a_proxy_headless.log` shows the relocation verified on the guard thread t20712 and an uncloak about 490 ms later, for both `-Origin` and `-Restore`.
- 20-pass run: the README and `pass_01..20.json` are in `harness/runs/20261031_j12acc3`. The two failed starts and their pass files are in `20261031_j12acc` and `20261031_j12acc2`. Each cause was turned into a guard in `acceptance.py` before the restart, as kill criterion 3 requires.
- Deviations (the fixed-sky pack stays, the tool rows were removed rather than superseded, the Python host tests stay, `WSP_BUILD_ID` in core CI, 109 ms for 1b) are each named with a reason. The 1b result is honest: a polling sweep cannot reach 0 ms, and B19 tracks the WinEvent fix.

### Risk-first reading
I picked the code where a mistake costs most: the headless guard (`display_guard.h` `IsOwnMove`/`SweepHides`, `headless.cpp` `GuardProc`/`SweepCb`, which run inside the game), the watcher's VirtualStore move (it moves files on the PC), `update.ps1` (it replaces the live watcher), the `job.sh` lock, and `pr_policy.py` (the merge gate). I skimmed the rest.
- Guard: the sweep runs outside `s_cs` and takes the lock per window. `CloakWindow`/`ShowWindowAsync` from the guard thread cannot deadlock against the window thread. `IsOwnMove` is bounded to 2 s and to an exact rect. Sound.
- VirtualStore: files are moved, never deleted, into a timestamped `_to_delete` folder. A failure refuses the launch. Sound.
- `update.ps1`: the kit_id check and NOTHING TO DO both come before any backup or copy. The L1 change passes only a needs_reboot flag that was already set. Sound.
- `pr_policy.py`: reading `core/...` through the base's gitlink keeps "the BASE's checker decides" (J44) intact, and a pin change is in rule 79's scope. Sound.

### Findings

**Blocker:** none.

**Should-fix:** fixed on the branch by this review, one commit each:
1. `docs/CI_FAILURES.md:71-72`: the switch hand-edited two rows of this generated file (`tools/ci_failures.py`, "do not edit the table by hand"). It rewrote CI's quoted step name and log line for J15 runs 40953826497 and 40953862308 to `core/...` paths, but those runs printed `proxy/...`. Restored from main.
2. `registries/config_keys.jsonl` `dev.file_rules`: the description named `proxy/core/filerules.h`, which the switch deleted. It now names `core/proxy/src/filerules.h`. This row is not a build-id input and is not in `generated/tables.h`, so the id stays `31094f6055c2`.

**Later**: all of these are in core code, so they are filed in warscape-core `docs/BACKLOG.md`, liam-rowley/warscape-core#8 (Liam merges):
- B20 `core/harness/job.sh:134` (and the watcher's lock expiry): taking over a stale lock is not race-free. Two takers both see the stale lock. The first moves it aside and creates its own, then the second's `mv` moves that fresh lock aside and creates again, so both print "taken". To see it fail: hold a stale lock, then run two `lock` calls with a pause injected between the age check and the `mv`. The happy path is tested; the race is not.
- B21 `core/harness/watcher.ps1:1296` (fix 1f): `if ($LASTEXITCODE) { exit $LASTEXITCODE }` uses the last native exit code anywhere in the script. A handled early failure, or `robocopy` (1 to 7 mean success), now fails a job whose last statement succeeded. To see it fail: a ps1 job `robocopy a b /L; Write-Output done` ends `failed exit=1`. No current job body is affected: `shot.sh` and `procfreeze.ps1` make no native calls.
- B22 `core/proxy/src/display_guard.h:216`: `IsOwnMove` compares physical pixels. At a scaled target DPI with a DPI-unaware worker thread, the J13 bug remains (the comment admits it). The report does not mention it.
- B23: `headless_status.json` is not rewritten after a relocation (report question 3). Since fix 1c, `shot.sh` reads this file, so a shot taken after a display move uses the old rect.
- B24 `core/harness/job.sh:5`: the comment still names `harness/core/watcher.ps1`. The game-name lint does not check for repo paths that no longer exist.
- Napoleon (no action now): `SweepHides` hides a window when either side is larger than the helper size, where the old code checked width only. This is stricter and passed 20 times, but it is a behaviour change the report does not name.

### Rule changes for other branches
After this merges, `proxy/core`, `harness/core` and `saves/core` no longer exist on main, and `wsc jobs check` (rule 76) fails if any of them comes back. `job/J16` changes `proxy/core`, so as the report says, its change has to become a warscape-core PR against `proxy/src` plus a pin bump. A plain merge of main into J16 would bring the folder back and fail the `tests` gate.
