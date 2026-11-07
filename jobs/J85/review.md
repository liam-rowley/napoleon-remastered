# J85 review

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
