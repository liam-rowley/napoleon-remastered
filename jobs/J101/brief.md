# J101: Start-up crash c0000374: rate by display layout and DLL, then the cause

Phase 1 pipeline job, `needs_pc`. Fact `napoleon.proxy.init_heap_corruption` has been open since 2026-10-31 with no job on it, and it now costs more than the retries: about 1 launch in 4 in the
worst recent sittings. Liam wants the answer before J59, and J67 warned that a player meets it if it is not proxy-only. This job measures, then reads, then names a cause. **It does not fix.**

**Runs after J78 (`depends_on`).** J78 brings W33, which moves the dev threads off DllMain, and that is the leading suspect's fix. So this job can run the old and new DLLs side by side in one
sitting, which is the only test of W33 worth having. J78's own count of retried exits cannot prove the fix: J64's 20 passes on the *old* DLL had 1 death in 127 launches, on the layout where the rate is low.
J78 also brings the crash maps (W35), `dump_read.py` (W39) and watcher 1.5.0.

**No DLL or harness input changes; no 20 passes (rule 79).** The soak is a tool under `tools/`, its evidence goes in a `runs/` folder, and diagnostic DLLs stay in `_scratch` and are never committed.
A branch diff touching `proxy/`, `harness/` outside `runs/`, `core` or `viewer/pins.json` means the job has left its scope (Kill criteria). A fix is a later job with its own passes.

Model: Opus, reason: a crash with heap forensics on minidumps and engine reverse engineering (D15, D52). Budget about 160 tool calls (J50 about 140, J96 about 95 on a smaller PC part; this has about 40 soak
blocks, each one call, and dump work). The budget is not to be lifted in prose. At most 2 subagents, only for independent host work, never for the PC run (D59: a PC job counts as one session, finished ones stopped).
Waiting belongs to the harness: one blocking call per block, no polling.

## Start
- If this session's model is not Opus, stop and say so.
- `CLAUDE.md` (Jobs: branch `job/J101`); `docs/DECISIONS.md` (D2, D15, D52, D56, D59); fact `napoleon.proxy.init_heap_corruption`; the rows of J98 and J59.
- **J78's report** (`jobs/J78/report.md`): the build id, the watcher version, the retried start-up exits per pass, and its Deviations and Open questions are the state of the world.
- `jobs/J64/report.md` (the 08:51 event, Open question 1), `jobs/J67/report.md`, `jobs/J96/report.md`, `jobs/J32/report.md` (its Later items).
- Empire, read-only (`--add-dir ../empire-remastered`): `orchestrator/reports/2026-10-23_crash-triage.md`, `orchestrator/reports/2026-10-23_crash-soak.md`, `docs/learnings/LEARNINGS_HARNESS.md` ("Display topology
  matters", "Reading a crash", "Soak mechanics"), and `rml_mod/tools/crash_dumps/triage/` (`heap_failure.py`, `ldr.py`, `ours_on_stacks.py`). Port, don't copy. Every Empire claim here is a hypothesis on Napoleon until
  this job's own run shows it. Do not port the `cs.sh` driver or the device-relay workarounds.

## Target facts
Read on 2026-11-06 from `watcher.log`, `watcher.log.1`, the watcher's win-probe folders and the dump folders. Deliverable 1 derives every number again; check each before relying on it.
- **The history is much bigger than the reports.** 2,610 launches from 2026-10-29 to 2026-11-06 09:38 UTC, 123 deaths with the last status `starting DllMain`. Most deaths never reached a report: `ctl.py` retries them.
- **The layout flips; it did not change once.** Every launch since 2026-10-29 17:37 has a win-probe with `monitor` lines (2,551 of 2,610). Two layouts appear, 15 stretches in that time:
  **D** (Dell primary at 0,0, virtual display at 2560,1440, MSI absent) and **M** (MSI primary at 0,0, Dell at -2560,327, virtual display at 3839,2160). M looks like daytime and D evenings and nights.
  So J64's "the layout changed at 08:51" and the row's "J67's 6 of 18 came after it" mislead: **J67 ran on D**. D held from 2026-11-05 18:28 to 2026-11-06 09:10, and M returned at 09:13.
- **Observed rates (deaths/launches):**

  | Period | D | M |
  |---|---|---|
  | to 2026-11-02 18:00 | 7/565 (1.2%) | 8/708 (1.1%) |
  | 2026-11-02 18:11 to 2026-11-05 08:49 | 74/1006 (7.4%) | 0/4 |
  | 2026-11-05 09:36 on | 32/135 (24%) | 2/133 (1.5%) |

  All launches: D 113/1706 (6.6%), M 10/845 (1.2%). **This is the Empire lead with support, not a finding.** It is observational: layout goes with time of day, with who is at the PC and with the job, and load was recorded for almost no launch. Two things it does not explain: the layouts were equal until 2026-11-02 evening, and D then rose from 1.2% to 7% and on to 24%.
- **Same DLL, different rate.** J64's run 20261105_j64pc7 and J67's run both log build `6e89faf06754`: 1/127 and 18/56 the same day. So the build alone does not explain the gap. (J67's README names a005f6cccc17 from `build_id.py`; its logs say `6e89faf06754`. Say which is right.)
- **Empire's numbers are weaker than the row says.** Its "vanilla" 0/60 is the soak's V arm, which is `heap_serialize=0` **with the DLL installed**, not a game without the proxy. At Napoleon's 1.2%, 60 launches show no death about half the time, so 0/60 proves little. Its "about 6 of 7" came from other jobs, not the soak, which reported **inconclusive**, and `heap_guard` was promoted unproven. **Neither game has a count of launches without the DLL.**
- **Counts by job:** J67: 18 deaths of 56 launches, 17 dumps (12 c0000374, 5 c0000005, 4 of the 17 zero bytes). J25 (2026-11-06): 9 of 40, 8 dumps (3 zero bytes). J32 (2026-11-06): 3 of 31, 3 dumps, 07:36, 07:53 and 09:30 UTC.
  Its report names two and calls the 07:36 cause not shown; dump `20261106T073630Z-p22448_c0000374` shows it. J96 (2026-11-06): 2 of 10, 2 dumps at 09:06 and 09:08. Of those five, four are on D and one on M. J64 (2026-11-04 and 05): 9 of 228, 9 dumps.
- **Where dumps are.** Proxy dumps leave the game folder at uninstall and sit under `<state>/_to_delete/uninstall_<utc>/napoleon_remastered/dumps`, so the row's "in the J64 worktree" is out of date: `20261105T081227Z-p20920` and
  `20261105T094426Z-p19168` are there. 127 unique in all. The in-process dump is **empty when the heap is gone** (8 zero-byte files since 2026-11-04). WER's full dumps (about 205 MB) keep only 5 in `%LOCALAPPDATA%\CrashDumps\napoleon_remastered`
  and evict the oldest, so the 5 of 2026-11-06 will probably be gone by the time this job starts. The fact says WER shows c0000374 at ntdll+0xfd71f even for dumps the proxy names c0000005.
- **Suspect from Empire (hypothesis).** Empire's allocator uses the process heap with HEAP_NO_SERIALIZE until TBB starts; a thread from DllMain allocating in that window corrupts the free lists (`DevInit`, StateThread). Napoleon has the same ntdll offset, and the site
  `guard.heap_serialize_setter` is matched and verified but nothing is hooked: **no heap guard exists in this repo or the core** (v0.45.0 searched). W33 removes the DllMain thread but not the window, and Empire also saw OS worker threads (inputhost, CoreMessaging) start in it, so vanilla is not obviously immune.
- **Harness.** `core/harness/ctl.py` `Pc.launch` retries a dead launch once and folds it into `retried_after`. A headless launch needs the proxy (the watcher refuses without the marker in `d3d9.dll`), so **a vanilla launch must be `visible=1`**, which the watcher allows only with Liam present,
  and `dev.skip_intro` is a proxy key, so vanilla cannot skip the intro. `DevInit` returns early with no dev key on, so `dev.skip_intro` itself turns the dev path on: the row's "dev.skip_intro" launch cannot test a no-dev-key DLL. Check all of this on the pinned core.
- **Kits on the PC.** `kit_20261106T071945Z_b5a7ccec7f29` is the last pre-W33 acceptance kit (J32's). `pc_deploy.py` history (`<state>/history/install_*.json`) ties kits to dates. Check that a kit built before J78 still installs under the new `pc_deploy.py`.

## Decisions already made for this job
- **Measure before reading.** Liam's order: no dump is opened for cause until the soak's tally is committed. Deliverable 1 reads logs, not dumps.
- **Layout is read, never assumed.** Every launch takes its layout from its own win-probe `monitor` lines. A block that flips mid-way counts each launch under its real layout.
- **Sample sizes are fixed before the first launch** and cells are not stopped early on a good or bad look (Deliverable 3). Arms are interleaved in blocks of 10, because the crash comes in bursts: a whole cell run in one stretch measures the hour, not the arm.
- **The soak is `tools/startup_soak.py`, written once.** A game tool with a header and a `tools` row. J98 later wraps it as the verb and pays the 20 passes for that; do not put it in `harness/` or `core/`. It must fit J98's row (launch, front end, kill, N times, layout per launch, exited signal).
- **Every launch counts.** A death is a row, never absorbed by a retry. If the soak goes through `ctl.py`, it reads `retried_after` and writes both launches.
- **DLL arms run to the front end, as the row says.** Vanilla arms instead count as survived when the process is alive 20 s after start, then `kill`: the crash is within a second, and a vanilla launch cannot skip the intro.
- **One size:** 1920x1080 for every arm, as the launch default. The history has 3840x2160 worse than 1920x1080 on D (18/116 and 86/1521), so size is a confounder; it gets a cell only if Deliverable 3's optional block fits the budget.
- **Fix is out.** A heap guard or anything else that changes a DLL input is proposed as a row, not built on this branch.

## Deliverables
1. **History table (no launches, no dumps).** Join `watcher.log`, `watcher.log.1`, the win-probe folders, `<state>/history` and the dump folders into launches with: time, owner, size, layout, build id, dead or not, dump and code. Commit the table and script in the run folder.
   Rates by layout x build, by size, by owner, by hour, by gap since the last launch. **Answer: did a build, a key or a pack enter at 2026-11-02 18:11 that explains D's rise?** Name the last kit before it, if it can still be installed: that is arm **P**. Check every Target fact and correct what is wrong.
2. **`tools/startup_soak.py`** with host tests (fake job results; no PC). `run --arm <name> --n <n> --run <id> --owner j101` and `tally --run <id>`. One JSONL row per launch: UTC, arm, kit, DLL sha, build id, ini sha, layout signature, size, outcome (survived, died at status, other), exit code, seconds to death, the
   dump names and codes, the WER dump copied or not, gap since the last launch, CPU load, free RAM, counts of `claude` and Docker processes. `tally` prints cells with counts and Wilson 95% intervals. It copies each new WER dump to `job.sh scratch j101` **after every block** (WER keeps 5). It stops at a refusal or a changed exe.
3. **The soak, fixed plan.** Arms: **N** J78's DLL, adapter dev keys. **O** the pre-W33 DLL, same keys where it knows them. **Q** J78's DLL with no dev key (the player's ini plus the headless keys; survived = alive 20 s after `on_virtual`). **V** vanilla, `visible=1`, after `pc_deploy.py uninstall`, `status` saying vanilla.
   **P** if Deliverable 1 names one.

   | Layout | Arms, 60 launches each | Then |
   |---|---|---|
   | D (first: the rate is high) | N, O, Q, V (and P) | **Load pair:** arm O, 30 quiet and 30 under a CPU spinner from `_scratch`, interleaved |
   | M | N, V | O as well if the budget holds |

   That is about 420 launches, about 3 hours of PC time at Empire's 21 s a launch; measure the real figure in the first block and say it. The load pair's spinner stops with the block. Optional, only under budget: arm O at 3840x2160 on D, 60.
4. **Verdicts, by rule, in the report and the fact.** A difference counts at Fisher's exact one-sided p < 0.01 on the cells named; every rate carries its interval and n. A cell with no deaths is an upper bound (0/60 is under about 6%), never "does not happen".
   - **Layout:** N on D against N on M.
   - **Who owns it:** V on D against O on D. V 0/60 with O at 5 or more: not seen on vanilla. Any death on V: the game or the OS does it too, and **a player meets it** without us.
   - **Players on the DLL:** Q on D against N on D. Q is the configuration that ships.
   - **W33:** N on D against O on D.
   - **Load:** the pair.
   - If O on D has under 3 deaths in 60, the burst is not on: run one more sitting of O on another day (the only planned extension). Still under 3 in 120: **inconclusive** for every verdict that uses O, as Empire's was. Say so, do not reach for the history.
5. **Answer: should the MSI stay on during PC jobs?** Yes, no or no evidence, from verdict 1 and the load pair. Name what flips the layout if Liam says (J64 Open question 1), and what it costs J78-style runs: `-X 3839 -Y 2160` is the M layout only, D needs the virtual display's rect at 2560,1440.
6. **Read the dumps (only after the tally is committed).** Use `dump_read.py` (WinDbg's cdb; `winget install Microsoft.WinDbg` is Liam's if missing) and extend before adding; what it lacks becomes one tool in `tools/`, ported from `heap_failure.py`, with a row, and a W row proposal in the report. At least 10 WER dumps, across arms and layouts, and the proxy dumps where WER's are gone. For each:
   HEAP_FAILURE_INFORMATION (type, heap, address, failure stack), the crashing thread, every other thread and when it started (`ldr.py`'s timeline), the process heap, and whose code is on the stacks, symbolised from the proxy map (W35). Read the flag behind `guard.heap_serialize_setter` from each dump: is the heap unserialised at the crash?
   **Answer: is the damage the proxy's or the game's, and which thread and allocation made it.** Also: why the proxy names c0000005 where WER says c0000374; why in-process dumps are empty; whether J30's 180 s spin at `starting DllMain` (run 20261103_j30acc6 pass 18) is the same defect.
7. **Only if 6 points at the flag:** a scratch DLL that clears it before any thread, built from a copy under `_scratch` (never `core/`, never committed; Empire's `heap_guard` is the model), arm **F**, 60 on D interleaved with O. Empire never got this result; it would be the first proof on either game. Otherwise skip it and say why.
8. **Registry.** Update `napoleon.proxy.init_heap_corruption`: `state`, the counts, and the date and run id behind each. New facts for what is proved, including the layouts. A proved cause closes the fact; an unproved one leaves it `open` with what was ruled out. Tools row for the soak.
9. **Proposals, not work:** the fix as a row with the keys and sites it needs and its 20 passes; the W rows for the core (`ctl.py` retry counted in a report, `heap_failure`); what J98 has left; the corrections for J64's and J78's layout text.

## PC test
One job at a time. Evidence in `harness/runs/<YYYYMMDD>_j101pc/`, with a README whose paths exist (`run_refs`). Dumps stay in `_scratch\j101`; only tables, reads and small extracts come to the repo. The game is launched and killed **only through `job.sh`**; `dev.skip_intro` from the adapter on N, O and P (every test launch skips the intro where it can).
1. `python3 core/proxy/tools/pc_deploy.py status --game <game> --state <state>`: exe vanilla (D2), no foreign files, nothing installed from another job. `bash core/harness/job.sh status`: J78's watcher version, `not_running`, no `game.lock`.
2. **Nothing else on the PC job side:** no J78, J98 or J59 run; ask whoever started you. Record load per launch either way. Do not stop Liam's other work to get a quiet PC: the load columns are there for that.
3. **Layout.** Read it with one win-probe or the last launch's `monitor` lines. **Never change a display, a window or a monitor setting yourself.** To move between D and M, stop, say which layout the next stage needs, and ask Liam. A layout that is neither D nor M: stop and report its lines.
4. Install arm by arm: `pc_deploy.py install` of the arm's kit, `status`, then blocks of 10, rotating arms (N, O, Q, then V when Liam sits for it). Check the sha after each install. Re-installing per block is the cost of interleaving: if it takes over 2 minutes, use blocks of 20 and say so.
5. V cells: Liam present (Open question 1), `pc_deploy.py uninstall`, `status` must say vanilla, `launch visible=1`, `kill` at 20 s. Audio: mute it or warn Liam first. A death in V has no proxy dump: WER only.
6. End: `pc_deploy.py uninstall`, `status` vanilla, no lock, prefs unchanged by sha. Foreign files or a changed prefs sha go in the report. Look at the shots and logs of at least one launch per arm, and say so: an arm that is not what its name says voids its cell.
7. Every `failed` ctl result in a cited run is named under Deviations, deaths included (as a count with a pointer to the JSONL when there are many).

## Out of scope
- Any fix, including a heap guard: a later job, 20 passes. Anything under `proxy/`, `harness/` (outside `runs/`), `core/` or `viewer/pins.json`.
- J98's verb and its acceptance run; J85; the J78 bump. J59's run.
- Page heap or any `gflags` change without Liam's yes (Open question 3). Any display or monitor change. Anything in `empire-remastered`.
- The 08:51 hardware question beyond asking Liam once.

## Open questions
1. **Liam sits the V cells?** They show a window on a real display and play the intro, about 25 minutes per layout. Recommended: yes, both layouts; V on D is the cell that says whether a player meets this. If D only happens when Liam is away, recommended: he leaves the Dell free for that stretch and says so. Tag: risk (never defaults; without his yes V is not run and verdict 2 is reported unanswered).
2. **How is the layout flipped?** It looks like the MSI going to the work dock, as on Empire, but nobody has said. Recommended: Liam names it and flips it when the job asks, twice at most. Tag: risk.
3. **Page heap if the dumps do not name the writer?** It changes heap timing, which may hide the race, and it is a machine setting for the exe. Recommended: only if Deliverable 6 ends without a writer, one sitting, removed after, with Liam's yes. Tag: risk.
4. **J59 waits on this?** Its row has no dependency on J101 and Liam wants this first. Recommended: add J101 to J59's `depends_on` on a `plan/` branch. Default after: 2026-11-10.

## Kill criteria
- `git diff --name-only origin/main...HEAD` lists a path under `proxy/`, under `harness/` outside `runs/`, `core` or `viewer/pins.json`: stop and report.
- `jobs/J78/report.md` is absent or J78's row is not `done` at pickup: stop and say so.
- `pc_deploy.py status` says the exe is not vanilla, at any point: stop, report, no launch.
- A launch ends in a hang (`HANG handled` in `watcher.log`), a `PC NEEDS REBOOT` refusal or exit 2160: stop the block, keep the evidence, report it with the layout. Exit 2160 is a display drop: resume only after Liam says the display is back.
- `tally` shows O on D under 3 deaths after 120 launches over two sittings: stop soaking, commit, report inconclusive, go on to the dumps already held.
- A cell's kit will not install under the new `pc_deploy.py` after 2 attempts: drop that arm, say which verdicts go with it.
- Free space on the state drive under 20 GB: stop copying WER dumps, keep the first 10 per arm.
- `dump_read.py` or cdb cannot read a WER dump after 3 attempts: stop Deliverable 6 and report what was tried.
- Over about 160 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J101/report.md` with `## What was built`, `## Evidence` (run ids, build ids, kits, watcher version, the cell table with n and intervals, the layout of every block, the history table's path, WER dumps read), `## Deviations from the brief and why` (every `failed` ctl result; any cell run short), `## Open questions`.
State up front, in this order: who owns the crash, whether a player meets it, whether W33 helped, whether layout is the cause, whether the MSI stays on, and the cause or what was ruled out. Then `wsc jobs usage J101 --write` where it applies. Then `wsc reg set jobs J101 status=review report=jobs/J101/report.md`. Never mark `done`, never merge, never `--no-verify`.
