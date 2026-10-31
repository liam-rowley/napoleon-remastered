# Review of J18 (PC-side rule guards)

## Round 1 (2026-10-31, branch `job/J18` at 4daf44e)

Reviewer: session `92704410-67e1-4f26-a0b0-9f495e9d8031` (did not build the branch; builder `ac3e361c-a547-407e-9359-4d1c376bf94e`).

**Verdict: merge after fixes.**

The guards are built and the evidence backs them. Rows 28, 31 and 32 each have a guard, a damage check and a failing-fixture test.
The live run's raw files match the report: `status_job.txt` has `exe.ok true`, `launch.txt` has `exe check: ok`, `setup.txt` has
`ok pc_rules`, and `hook.txt` shows the deny in the game folder and the allow in the repo. Every deviation is named in the report with
a reason. Two holes are fixed on the branch (should-fix 2 and 3). What still stands between this branch and a merge is the acceptance
gate (blocker 1). The branch was cut from `32c0b9a`, which is J44's merge, so rule 79 applies to it, and the report does not mention it.

### Machines
- `python3 core/wsc.py gates`: 12 ok, 0 warn, 0 failed (311 host tests).
- `python3 tools/pr_policy.py --branch job/J18 --base origin/main`: refused. The missing review and the row status are this round's
  business. **Rule 79** is not (blocker 1).
- CI on 4daf44e (run 41147641941): `gates`, `proxy` and `harness-windows` success.
- After the review fixes, `tests.test_claude_hook` (15) and `tests.test_pc_deploy` (29) pass.

### Risk-first reading
I picked these because a mistake in them costs the most:
- `tools/claude_hook.py`. It runs on every shell call, so a false positive blocks normal work, and a false negative is exactly the
  damage the job exists to stop.
- `proxy/tools/pc_deploy.py` `install`/`uninstall`/`set`/`sync_lua`. These write into the game folder.
- `harness/core/watcher.ps1` `Exe-Gate`/`Script-RunsGit`. These gate every launch.

What I found:
- The hook takes the event's cwd, quoted paths in all three spellings, `cd`/`Set-Location`, `-C`, `GIT_DIR` and the PowerShell
  writers. I probed it with about 15 real command shapes beyond the tests. One hole: should-fix 2.
- `Launch-Job` is the only caller of `Do-Launch`, and `Exe-Gate` runs first in it, before any display or config change. A missing
  identity is refused, not passed. The cache key is size and mtime.
- `install` refuses before `require_closed` and before any write, and the identity is in `install.json` before the first change, so
  a failed install's uninstall can check the exe. `uninstall` and `set` never refuse. `sync-lua` had no check at all: should-fix 3.
- Report open question 1 is settled: `origin/job/J36` no longer carries `7b8bd96` (J36 has merged). Only
  `origin/rescue/J18-7b8bd96` holds it, and its patch is line-identical to `6b0b368` on this branch, so nothing was lost.

## Findings

### Blocker
1. **Rule 79: no acceptance passes.** `tools/pr_policy.py:19`. The branch changes `harness/core/job.sh`, `harness/core/watcher.ps1`
   and `proxy/tools/pc_deploy.py`. `harness/acceptance/ledger.jsonl` holds 0 consecutive passes on this build with watcher 1.1.0,
   and 20 are needed. How to see it fail: `python3 tools/pr_policy.py --branch job/J18 --base origin/main`. Fix: on the PC, with
   watcher 1.1.0 installed (it already is, from run `20261030_j18pc`), run `python3 harness/core/acceptance.py run` on the final
   build, which includes the review commits below, and commit the ledger and pass files. J44's run took about 80 minutes of watcher
   time. Then set the row back to `review` for round 2.

### Should-fix (fixed on the branch)
2. **The hook missed Bash's escaped-space spelling.** `tools/claude_hook.py` `split_words` turned every backslash into a slash
   before `shlex`. That made `cd /c/Program\ Files\ \(x86\)/.../Napoleon\ Total\ War && git status` and `cp x.dll .../Napoleon\
   Total\ War/` pass both rules, and this is the spelling tab completion produces. Fixed in `ca33dc3`: an escaped space or
   parenthesis stays an escape, in words, redirect targets and `GIT_DIR`/`--git-dir`. Test:
   `test_bash_escaped_spaces_are_read_as_the_path` (6 deny shapes, 2 look-alikes pass).
3. **`sync-lua` did not check the exe.** `proxy/tools/pc_deploy.py` `sync_lua`. Row 28 and the job row say "after every install
   or sync". `sync-lua` writes into the game folder but recorded no verdict. Fixed in `5ac23b2`: it never refuses, records
   `sync-lua exe check` in `install.json`, and exits non-zero with the loud line on a mismatch, the same as `uninstall` and `set`.
   Test: `test_sync_lua_checks_the_exe_after_and_fails_loudly`. The J4 sync test now also checks the verdict.

### Later
4. **The hooks run only in a session started in the repo folder** (report open question 3). This review session started one folder
   up, so neither hook rule ran on its calls, which is the same thing the builder hit. That is an Empire repeat: the D30 rule is
   prose. Proposed for a `needs_brief` row: `wsc setup` (or a SessionStart hook in the user settings) warns when
   `CLAUDE_PROJECT_DIR` is not the repo.
5. **The PC runs an unmerged watcher.** The live run updated the PC's watcher to 1.1.0 from this branch. Until J18 merges, any other
   job's acceptance pass records watcher 1.1.0, not main's 1.0.1. Merging J18 settles it. If J18 is held back, roll the watcher
   back first.
6. **The report's CI evidence:** run 41146895956 (`d5ee0a5`) was cancelled because a later push replaced it. It was not a pass. The
   run that counts is 41147641941 on 4daf44e, where all jobs succeeded.
7. **`origin/rescue/J18-7b8bd96` can be deleted** (finding above). That is Liam's call.
8. `Script-RunsGit` is a word match per line, so a line like `echo "see git log"` in a `cmd` job is refused. The refusal names the
   line, so this is acceptable for now. Revisit it if a real job trips it.
