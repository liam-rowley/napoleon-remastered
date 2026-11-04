## Round 2 (2026-10-31, branch job/J22 at 4ede7b0)
**Verdict: merge.**

Machines: `wsc gates` on the PC: 12 ok, 0 warn, 0 failed (199.7 s) after the row was set (the one earlier failure, `jobs check`, was this round's own verdict seen before the row change); `tests` 385 host tests, 10 skipped. `pr_policy.py --branch job/J22 --base origin/main` before this review: the only
refusals are the two review-pending lines this round answers (verdict and row); rule 79 no longer refuses. CI run 41218396340 on
`4ede7b0`: `changes`, `gates`, `proxy`, `harness-windows` success (`gh run view`).

Round 1's one blocker (rule 79) is answered in `## Fix round 1`:
- `acceptance.py streak --build 41cde4716ac7 --watcher 1.1.0` here gives `20 consecutive passes ... (need 20)`.
- The ledger has 21 `job/J22` lines: the failed pass 1 of `20261031_j22acc` and 20 passes of `20261031_j22acc2`, each with its
  `pass_NN.json` on the branch; all 20 evidence files have `passed: true` and `build_id 41cde4716ac7`. The diff of the ledger
  since round 1 adds lines only.
- `proxy/tools/build_id.py` on this head gives `41cde4716ac7`, and the one commit `main` gained since the base (`e3b5a79`, a J12
  brief) touches no DLL input, so the passes stand for the merged code.
- Since round 1 the branch changed only `jobs/J22/report.md`, the job row and the run evidence: no J22 code changed, so round 1's
  reading of the code stands. Commit trailers: every commit carries `Claude-Session`; this review's session wrote neither the
  report nor round 1.

The builder deleted the first attempt's ledger line (a launch refusal before any pass, never committed); the report names it.
That is fine: nothing pushed was rewritten.

## Blockers
None.

## Should-fix
None.

## Later (this repo)
- Round 1's three later items stand (`ctl.bash()` silent fallback, `BARE_BASH` gaps, a brief check for rule 79).
- **Empire repeat:** the first acceptance pass after a fresh kit install fails `settings_identical` by construction (the launch
  config writes the dev keys after the "before" snapshot; `harness/runs/20261031_j22acc/pass_01.json`). That is a trap the next
  job will hit again. It wants a harness job: take the snapshot after the launch config is applied, or exclude the keys the pass owns.

## Round 1 (2026-10-31, branch job/J22 at 87b18c3)
**Verdict: merge after fixes.**

Machines: `wsc gates` on the PC: 11 ok, 1 warn (`hooks`: this clone's absolute `core.hooksPath`, local config), `tests` 385 host
tests passed (204.4 s). `pr_policy.py --branch job/J22 --base origin/main` refuses the branch on **rule 79** (0 acceptance passes on
build `41cde4716ac7`, watcher 1.1.0; the streak ends at J45's run). The other two refusals are the review-pending lines this round
answers. CI run 41208229617 on `02d6b5c`: `gates`, `proxy`, `harness-windows` success (checked with `gh run view`).

Reproduced here, from Git Bash, with `WindowsApps` first on `PATH` (`shutil.which('bash')` is the WSL `bash.EXE`):
`python3 -m unittest tests.test_job_sh tests.test_claude_hook tests.test_setup tests.test_pc_deploy`: `Ran 68 tests in 40.166s / OK`.
`ctl.bash()` under the same PATH: `C:\Program Files\Git\bin\bash.exe`.

Read in depth: `harness/core/ctl.py` `bash()` and its five callers, and `acceptance.py` `PcEnv.sh`. These are the code that drives the
watcher and the game, and the code rule 79 guards. If they pick the wrong bash, every PC session's `job.sh` call fails. The change keeps
the argv the same apart from argv[0]. From Git Bash, `git_bash()` gives the same `usr\bin\bash.exe` that PATH used to give. The fallback
is plain `'bash'`, as before. I also read `setup.py` (`bash_for_tests`, `bash_check`, `check_watcher`), `pc_deploy.running_check`, the guard in
`tests/test_repo_rules.py`, and the new `harness-windows` step. I skimmed the rest.

Brief: deliverables 1 to 6 are present. The call-site table matches a grep of the branch. The three deviations (the `images=None`
default, `ctl.py` loading the finder by path, `shot.sh` using `"$BASH"`) are named and justified. `CLAUDE.md` and `core/` are
untouched. Nothing is out of scope.

## Blockers
1. **Rule 79 is not met** (`tools/pr_policy.py` acceptance_problems; reproduce with `python3 tools/pr_policy.py --branch job/J22 --base origin/main`).
   The builder left the choice to the reviewer. My decision is **run the acceptance passes; do not exempt or split**:
   - The edit changes argv[0] of every `job.sh`/`shot.sh` call that `Pc` and `job_sh_transport` make. That is exactly the path an
     acceptance pass drives. So 20 passes are real proof for this change, not ceremony.
   - An exemption would be a `pr_policy.py` change that a branch cannot grant itself (J44: the base's checker judges). It also
     belongs in its own decision, not in this job.
   - Splitting would leave `ctl.py` on the WSL-prone bare `bash` and keep the guard (deliverable 5) red, or need an allow-list
     entry with no Linux-only reason.

   Fix round: on the PC, from Git Bash, with no game running, run `python3 harness/core/acceptance.py run` on the final build until
   `acceptance.py streak --build 41cde4716ac7 --watcher 1.1.0` gives 20. Commit the ledger lines and the run folder, add
   `## Fix round 1` to the report with the run id, and set the row back to `review`. If the J22 code needs another change first,
   make it before the run, because the passes must be on the final build.

## Should-fix
None.

## Later (this repo)
- `harness/core/ctl.py` `bash()` catches every exception and falls back to plain `'bash'` without a word. On Windows that is the
  WSL launcher this job exists to avoid. The fallback is right to keep behaviour unchanged, but one stderr line when the finder
  fails to load would make the failure visible.
- `tests/test_repo_rules.py` `BARE_BASH` misses `[shutil.which('bash'), ...]` used as argv (on Windows that is the WSL launcher too),
  and a list whose `'bash'` starts on the line after its `[`. Neither exists today. It also does not scan `.sh` files (the report
  says so).
- The builder's open question is an Empire repeat: no brief said whether rule 79 applies to a `harness/core/*.py` change. That can be
  code. `wsc jobs check` could flag a brief whose files list names `harness/` or `proxy/` code without a line on acceptance passes,
  so the brief writer has to decide up front.
