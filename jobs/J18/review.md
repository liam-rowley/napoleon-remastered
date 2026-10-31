# Review of J18 (PC-side rule guards)

## Round 2 (2026-10-31, branch `job/J18` at 076dae9)

Reviewer: session `8447249e-c752-4a91-ac0b-a52ac8a6c509` (did not build the branch; builder `ac3e361c-a547-407e-9359-4d1c376bf94e`).

**Verdict: merge.**

Round 1's only blocker (rule 79) is met, and nothing else on the branch has changed since round 1 except the report and the evidence.
The commits since round 1 are `41e1a7f` (the report's CI evidence now names run 41147641941, round 1 finding 6) and `076dae9`
(acceptance). Neither touches code.

### Machines
- `python3 tools/pr_policy.py --branch job/J18 --base origin/main` at 076dae9: rule 79 passes. The only refusals left were this
  review's verdict and the row, and both are settled by this commit.
- CI on 076dae9 (run 41189004189): `changes`, `gates`, `proxy`, `harness-windows` all success.
- `wsc gates`, run from PowerShell on the PC: `tests` fails in 11 `test_job_sh` cases with exit 127, and **main fails the same way**.
  `bash` there resolves to WSL's `WindowsApps\bash.exe`, which drops the backslashes in the path (later 2). Under Git Bash (D30's shell),
  `tests.test_job_sh`, `test_claude_hook`, `test_pc_deploy` and `test_setup` run 63 tests and pass.

### Acceptance evidence (blocker 1), checked against the PC
- The build id is right. `pr_policy.py:231` takes the last commit of the DLL inputs, and J18 changes none of them, so the id is
  `32c0b9a66de1` (main's J44 merge) on this branch. The kit was cut from `03354d8`, which includes both round 1 code fixes
  (`ca33dc3`, `5ac23b2`). From the PC install (`119004d`) to HEAD, `harness/core/` is unchanged. The only change in that range is
  `pc_deploy.py` sync-lua (+4), which runs from the repo, not the kit, so watcher 1.1.0 on the PC is this branch's watcher.
- The ledger has 21 new lines. The first is pass 1 of `20261031_j18acc`, which failed only `settings_identical`; the report explains
  why. After it come 20 passes in `20261031_j18acc2`, all `job/J18`, build `32c0b9a66de1`, watcher 1.1.0, and about 3m55s apart,
  which is a real game cycle. `pass_20.json` agrees with its ledger line (start 09:26:37, end 09:30:29, 26 steps, passed).
- Live `pc_deploy.py status` on the PC: kit `kit_20261031T080721Z_03354d8bfb63` installed 08:07:22, `exe: ok` (vanilla sha1 in the
  identity), `git: ok`, `foreign: 0`. One line reads `BAD napoleon_remastered.ini`: that is the ini change from `ctl.py`'s launch keys
  that the report names (later 1). It is not damage.

## Findings (round 2)

### Blocker
None.

### Should-fix
None.

### Later
1. **The PC's ini reads BAD after any acceptance run, and pass 1 after a fresh install always fails.** `ctl.py` leaves its launch keys
   in the installed ini through `pc_deploy set`. So `pc_deploy status` shows `BAD napoleon_remastered.ini` from then on, and
   `settings_identical` fails the first pass after a fresh install (run `20261031_j18acc`). The report proposes the fix, which is an
   Empire repeat. `acceptance.py run` should apply the launch keys before its "before" snapshot and read the build id after the first
   launch. `status` should treat the known launch keys as set, not as damage. Proposed `needs_brief` row.
2. **`wsc gates` fails falsely when run from PowerShell.** The bash found first on PATH is WSL's, so `tests/test_job_sh.py` gets exit
   127. Main fails the same way, so this is not from J18. The test (or `wsc setup`) should resolve Git Bash explicitly, or say which
   bash it found. Proposed `needs_brief` row.
3. Round 1 later items 4 (hooks only run in a session started in the repo folder), 7 (`origin/rescue/J18-7b8bd96` can be deleted,
   Liam's call) and 8 (`Script-RunsGit` word match) still stand. Item 5 (the PC runs an unmerged watcher) is settled by this merge.

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
