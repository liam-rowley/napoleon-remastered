# J85 review

## Round 2 (2026-11-07, branch job/J85 at 6acd299)

**Verdict: merge.**

Both of round 1's fixes are correct, checked against what `acceptance.py` really prints and not only against the fakes. No blocker and no should-fix. This round changed no code. Two new `later` items, neither needed for a merge.

### Machines
- `python3 core/wsc.py gates` at 6acd299: 14 ok, 2 warn, 0 failed in 242.8 s. 802 host tests passed, 47 skipped. The warnings are `hooks` (this worktree's clone setting) and `tests` (the skips), neither from J85.
- `python3 core/wsc.py policy --branch job/J85 --base origin/main` at 6acd299, before this round: refused only for the old verdict and the row not being `done`, as expected. Its one warning is round 1 citing the scratch branch.
- CI on 6acd299: `gates` success, `changes` success; `proxy`, `viewer` and `harness-windows` skipped, as no input of theirs changed; `policy` skipped on a draft, so it is judged on this commit.
- `tests/test_acceptance_auto.py`: 78 tests, OK (72 plus round 1's 6).
- `build_id.py --no-dirty`: `96722f4b8d52`, the same as the proof's ledger lines. The merge of `main` at 6acd299 brought in J105's rows and `CLAUDE.md` only: nothing the tool reads.

### Round 1's findings
**A `fail` during a stop (456c0ec5): fixed.** I ran `stop_point` on each line shape from `core/harness/acceptance.py` `cmd_run`, lines 641 to 653: a `pass` line and `flake 1 of 1 allowed` stop; `FAIL`, `FLAKE`, `flake 2 of 1`, `flake 1 of 0` and both `acceptance: stopped` lines do not. Those last paths reach `return 1`, which `supervise` reads as `consumed`. The flake line prints after the `FLAKE` line, so waiting for it loses nothing. Putting the old `PASS_LINE` back fails the three new `Run` tests, so they do test the fix.

**The proof still covers the stop.** The tool changed after the proof, but the real line in `tick_step3_4.log`, `acceptance pass 2: pass (harness/runs/20261107_j85auto1/pass_02.json)`, is a line `stop_point` stops on.

**A stop on a covered flake resumes correctly.** This is the path the fix keeps, and the proof never took it. I followed it through `flakes_in_streak`, `acceptance_problems` and `max_flakes_of`. A flake inside the streak takes the resumed run's allowance to 0, `--max-flakes 0` is accepted (`cli is not None`), and the gate reads each flake's own `flakes_allowed`, so the flake stays covered. A flake older than the streak's oldest pass is not counted, and it does no harm: the gate reaches 20 before it ends there. Read and traced, not run on the PC, as the ledger has no flake line yet.

**The action-line trap (b22be54d): fixed.** The check reads the registered task, not the caller's path, so running `task enable` from any checkout gets the same answer. Removing `enable_problem` fails `test_an_action_in_a_worktree_is_refused`. The real task, read at this round: `Disabled`, action still `.claude\worktrees\J85\tools\acceptance_auto.py launch tick`, so `task enable` refuses it today, as it should. I did not run `task enable`, and `Enable-ScheduledTask` has still only run on a fake.

`## Fix round 1` answers both and says plainly that the proof predates them. Its claims are true.

### Findings
**later:**
1. **The gate and the core disagree on a flake with no build.** `tools/gates/pipeline.py:419` takes a flake only if `build_id` equals the build. Core `streak()` also takes `None`, and `cmd_run` can write `None` when no launch of the pass logged a build. To see it: a ledger of 20 passes with a null-build flake as line 11 gives `acceptance_problems` `holds 10 consecutive`, and `streak()` 20. With a flake of the build itself, both say 20. For the runner this means a run reports `complete`, rule 79 still fails, and the next free tick runs the missing passes: about 80 minutes lost, no wrong result. This was on `main` before J85. No ledger line has a flake yet, so whether a lost launch does write `None` has not been seen. The fix is one condition in the gate, but it is a rule 79 change, so it needs its own job.
2. **Any exit 1 reads as `consumed`.** `supervise` (`tools/acceptance_auto.py:762`) treats every exit 1 as a fail or a spent allowance. An exception outside the pass loop in `cmd_run` (the `PcEnv` setup, `set_keys`, `load_baseline`'s `SystemExit`) also exits 1, with no ledger line. The request is then consumed and `last_result.json` says `a fail, or the flake allowance spent`, which is not what happened. It fails safe: no retry until someone asks again. Checking that the run wrote a new `fail` or `flake` line would tell the two apart, and it would also close round 1's later item 1. Found by reading, not run.

Round 1's six `later` items stand. Item 5 matters most: the first real request is the first `policy` run on a `job/` branch with an `acceptance-auto-*` trailer, so read that result.

### Claims against evidence
Round 1 checked the proof at 844c490, and the evidence has not changed. Checked again here: `origin/scratch/j85-proof` is at `242b38e3` with `63d67e81` and `f8025f0c` under it. I did not recount the ledger, the launches or the idle lines, and did not look at the shots.

### The brief
The diff since round 1 is the two fixes, the report, the row and the merge of `main`. Nothing outside the scope round 1 accepted. No workflow, `core/`, `proxy/` or counted `harness/` path changed, so rule 79 does not apply. The `tests/test_claude_hook_corpus.py` change (deviation 12) is narrow: it drops only the `releases it` line.

### Risk-first reading
I picked `tools/acceptance_auto.py` again, in full, as it drives the PC and pushes with nobody there, and spent the time on what round 1's fix touches: `supervise`, the flake allowance across a stop and a resume, and how the gate reads that afterwards. Finding 1 came from that.

### After the merge
- **For Liam:** run `python3 tools/acceptance_auto.py task install` from the main checkout, then `task enable`. Round 1's later item 6 (the `task enable` allow rules) is still yours to decide.
- `scratch/j85-proof` is left in place. It holds the only remote copy of the 20 ledger lines and their pass files, so deleting it is Liam's call.
- This merge changes no rule that other open job branches must meet.

## Round 1 (2026-11-07, branch job/J85 at 844c490)

**Verdict: merge after fixes.**

The runner does what the brief asked, and its proof holds up. One stated decision was broken in a narrow case, and one trap was left as prose. I fixed both on the branch, so a fresh round has to review those two commits. No blocker.

### Machines
- `python3 core/wsc.py gates` at 844c490: 14 ok, 2 warn, 0 failed in 238.8 s. The warnings are `hooks` (this clone's `core.hooksPath` is absolute) and `tests` (796 passed, 47 skipped), neither from J85.
- `python3 core/wsc.py policy --branch job/J85 --base origin/main` at 844c490: refused only for the missing verdict and the row not being `done`, as expected before a review.
- CI on 844c490: `gates` pass, `harness-windows` still pending when this was written, `proxy` and `viewer` skipped. Pull request #241 stays a draft.
- `build_id.py` is `96722f4b8d52` after the fixes, the same as the proof's ledger lines. Nothing under `core/`, `proxy/` or a counted `harness/` path changed.

### Findings

**should-fix (fixed in 456c0ec5): a `fail` during a stop did not consume the request.** `tools/acceptance_auto.py` `supervise`, the `PASS_LINE` check. Decision 9 says a `fail`, or the flake allowance spent, consumes the request. `PASS_LINE` also matched `acceptance pass N: FAIL` and `FLAKE`, so with a stop already wanted the run was killed on that line and returned `stopped`. To see it fail: on 844c490, feed `Fake` the lines `starting`, `tick`, `acceptance pass 1: FAIL (x)` with rc 1 and `liam_present` created at `starting`. The result was `stopped` and `consumed` was empty, so the next free tick would run 20 passes on a build that had just failed. The flake that spends the allowance did the same. The likely trigger is real: Liam coming back mid-pass is what sets the stop, and a window of his over the game can be what fails the pass (J64). Fix: `stop_point` stops only after a pass or a flake the allowance covers. Anything else runs on to `acceptance.py`'s own exit 1, which `supervise` already reads as `consumed`. Three tests added in `Run`.

**should-fix (fixed in b22be54d): the action-line trap was prose.** Report open question 1 tells Liam to run `task install` from the main checkout before `task enable`, because the registered action points at `.claude/worktrees/J85`. If he forgets, the task runs until that worktree goes, then fails with nothing logged, since the tool is what would log it. Fix: `task enable` reads the registered action and refuses one in a worktree (`enable_problem`), or a task it cannot read. Three tests added in `TaskEnable`, and a clause in `harness/README.md`. I checked the read against the real task without enabling it: it returns the J85 action line and `enable_problem` refuses it. The `Enable-ScheduledTask` branch has only run on a fake, because enabling is Liam's.

**later:**
1. `cleanup` (`tools/acceptance_auto.py`) calls every dead run `stopped`. If the runner dies after a `fail` line reached the ledger, the request is not consumed. Same result as the first finding, but it needs a crash at that moment. Reading the run's new ledger lines in `cleanup` would close it.
2. An outcome of `refused` after the install (`pc_deploy install` failing, or `acceptance.py run` exit 2) does not consume the request and has no limit. Each tick would install, wait 5 minutes and uninstall, every 30 minutes, until someone reads `last_result.json`. A count of refusals per request would cap it.
3. `start` reads `input0` after the build, and nothing repeats `person_guards` between the tick's guards and the install. Someone who sat down during a 5.5 minute build is noticed only at their next input. The cost is one install and uninstall.
4. `requests` accepts any JSON. A request that parses to something other than an object raises `AttributeError` in the sort, so one bad branch stops every tick, with only a traceback in `launch.out`. Found by reading, not run.
5. Two paths have not run on the PC: a real `update` in `follow_watcher` (the brief allowed this, as versions did not differ) and `policy` on a `job/` branch carrying an `acceptance-auto-*` trailer (the proof branch is `scratch/`, and CI never judged it). The first real request is the test of both, so read that run's `policy` result.
6. **For Liam:** `~/.claude/settings.json` allows any session to run `task enable`, and its auto-mode text says so. The report names this (deviation 6) and says Liam asked for it, but decision 12 says only Liam runs it, and that rule is now what stands between a session and a live task. Recommended: remove the `task enable` allow rules and that text once the task is enabled, along with the rules naming the J85 worktree.

### Claims against evidence
Checked and true:
- `origin/scratch/j85-proof` holds `63d67e81`, `f8025f0c` and `242b38e3`, each with its own `acceptance-auto-*` trailer.
- Its ledger has 20 lines for the branch: all `pass`, runs of 2, 3 and 15, one kit, one `dll_sha256` (`5dac94823fc5`), one `watcher_sha`, build `96722f4b8d52`. The line before them is `job/J78`, which fits deviation 2.
- `watcher_step3_4.log` and `watcher_step6.log` have 30 and 92 `launch:` lines, so 122 launches, with exactly 1 `no on_virtual status` line and 1 `exited before reporting on_virtual` line.
- All 133 idle lines say `last_input=25197562` and `layout=D`.
- `tick_step3_4.log` shows the stop after pass 2's line and the resume on the same kit.
- The observers' only windows are `Program Manager` and one untitled window, 66 lines each, all from pid 4948, so one shell process and nothing from the runner.
- `pass_08.json` has no retry field.
- The real task on the PC: Disabled, `PT30M` with no end, `IgnoreNew`, no time limit, `Interactive`, action as quoted.
- `tools/acceptance_auto.py` did not change after the proof branch was cut, so the proof covers 844c490's tool. It does not cover my two commits.

Not checked: the shots by eye, the WER signature and dump, the claim that no ctl result file says `failed`, and the VirtualStore explanation beyond the two committed status files.

The proof evidence lives on `scratch/j85-proof`, as the brief ordered, so it is not on `main`. **Keep that branch until the merging round:** the report's commits exist nowhere else on the remote.

### The brief
All five deliverables are present. Decisions 2 to 13 are followed, apart from the first finding. The twelve deviations are named with reasons, and the two outside the brief (`--ignore-session`, the corpus test) are small and sound: `--ignore-session` is refused on anything but a `scratch/` branch. Kill criteria were respected.

### Risk-first reading
I picked `tools/acceptance_auto.py` in full, because it is the one piece that drives the PC and pushes with nobody there, and read it against what it relies on: `acceptance.py cmd_run` (the ledger line is written before the pass line, so a stop loses no pass), `acceptance_problems` (the streak message, the flake rule, `dll_sha256`), `watcher.ps1` status keys, `update.ps1` (a fresh `run_<stamp>` folder per update, so `update_verdict` cannot read an old verdict), and `pc_deploy.HARNESS_SRC` (`watch.cmd` is in it, so the refusal is live). I also ran `claude agents --json`: interactive sessions carry `status: busy` and no `state`, and the guard reads that as working, as it should.

### For the fix session
Both should-fix items are done. Read them, append `## Fix round 1` to `report.md`, and set `review`. The `later` items are not required for a merge.
