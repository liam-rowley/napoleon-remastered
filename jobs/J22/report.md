# J22 report: Windows host tests find Git Bash

Branch `job/J22`. Built on the PC (Claude Code, Git Bash) on 2026-10-31.

## What was built
- **The one finder stays `tools/verbs/setup.py` `git_bash()`** (J41). There is no second finder. New in `setup.py`:
  - `bash_for_tests(nt, find)` returns `(bash, None)` or `(None, reason)`. On Windows it gives `git_bash()` or a skip reason that names
    `python3 core/wsc.py setup`. Off Windows it gives `git_bash()` or plain `'bash'`, so a missing bash still fails, as before.
  - `bash_check(on_path, explicit, msystem, nt)` is the pure part of the `git_bash` check. It reports the bash on PATH with its kind,
    `MSYSTEM`, and the explicit path the repo's tools use. It fails only when `git_bash()` finds nothing. If PATH holds a non-Git bash,
    or the session was not started from Git Bash, it prints a `warn:` line with the fix but does not fail.
  - `check_watcher` runs `job.sh status` with `git_bash()`. It fails with a fix when no Git Bash is found.
- **`harness/core/ctl.py` `bash()`** loads `setup.git_bash()` by path once and caches it. If the finder can't load or finds nothing, it
  falls back to plain `'bash'`, so behaviour without Git Bash is the same as before. Why load by path rather than copy the finder:
  `ctl.py` is not in the watcher kit (`HARNESS_SRC` and `HARNESS_KIT_FILES` in `pc_deploy.py` hold only .ps1/.cmd files and
  `job.sh`). It always runs from the repo, so `tools/verbs/setup.py` is always there. That file is stdlib-only and is already loaded
  by path in three test modules.
- **`pc_deploy.running_check(..., images=None)`** takes an injectable process-list provider. `None` means `windows_images`, looked up
  when the function is called. That is a deviation from "default `windows_images`": a default bound when the function is defined
  would bypass the existing `mock.patch.object(pd, 'windows_images', ...)` tests in `HarnessKit`. Behaviour with the default is
  unchanged. `test_running_check` no longer has its `os.name` guard. It passes `images=lambda: None` for the log-fallback cases and
  fake image sets for the tasklist cases, and patches `windows_images` around `install()`. The same assertions now run on Linux, on
  the PC and on the runner.
- **Guard (deliverable 5)** in `tests/test_repo_rules.py`:
  - `BARE_BASH` matches an argv that starts with a literal `bash` (`['bash', ...]`, `/usr/bin/bash`, `bash.exe`), or a shell string
    passed to `run`/`Popen`/`call`/`check_*`/`os.system` that starts with `bash `.
  - It scans the tracked files `tests/*.py`, `tools/**/*.py`, `harness/**/*.py` and `proxy/tools/*.py`, and names the file and line.
  - `BARE_BASH_ALLOWED` maps each file to a reason. Its one entry is the test file itself, whose fixtures are strings. The test fails
    if an entry has no reason.
  - Fixture cases cover both the bad and the good forms (`shutil.which('bash')`, `which_of('bash')` and a prose string are not
    flagged).
  - Run against `origin/main` it flags all 11 original call sites: ctl 5, acceptance 1, job_sh 1, claude_hook 3, setup 1.
- **CI**: `harness-windows` has a new step, "Python host tests that run bash (Git Bash found explicitly)", which runs before the
  PowerShell suite.
  - It runs `tests.test_job_sh tests.test_pc_deploy tests.test_claude_hook tests.test_setup tests.test_proxy_host.GitBash` under
    `shell: powershell`, with a 3-minute step timeout.
  - setup-python does not provide `python3` on Windows, and `job.sh` calls it, so the step first copies `python.exe` to `python3.exe`
    beside it (what `wsc setup --fix` does on the PC).
  - `tools/changed_inputs.py` now puts these into the `harness` set: those five test files, `tools/verbs/setup.py`,
    `tools/claude_hook.py` and `.claude/settings.json`. Unit test: `tests/test_proxy_host.py` `InputSet.test_harness_set`.
- `harness/README.md` Tests now describes the rule and the runner step. `CLAUDE.md` is untouched.

### Bash call sites (recursive grep for `'bash'`, `"bash"` and `bash ` in `*.py`, `*.ps1`, `*.cmd`, `*.yml`, `*.sh`, docs)
| Site | Became |
|---|---|
| `tests/test_job_sh.py` `run()` | `BASH` from `bash_for_tests()`; `JobSh.setUp` skips with the reason when none is found on Windows |
| `tests/test_claude_hook.py` `test_the_settings_command_never_blocks` (3 calls) | `BASH`, with the same skip. Claude Code runs the hook command with Git Bash on Windows |
| `harness/core/ctl.py` `Pc.job`, `Pc.status`, `Pc.ctl`, `Pc.shot`, `job_sh_transport` (5) | `bash()` (setup.git_bash, falling back to `'bash'`) |
| `harness/core/acceptance.py` `Acceptance.sh` | `self.ctlmod.bash()` |
| `tools/verbs/setup.py` `check_watcher` | `git_bash()`, failing with a fix when there is none |
| `tools/verbs/setup.py` `check_git_bash` | reports both bashes (`bash_check`) |
| `harness/core/shot.sh:41` `bash "$HERE/job.sh"` | `"$BASH" "$HERE/job.sh"`: the bash already running the script, never a PATH lookup. Same behaviour from Git Bash |
| `tests/test_proxy_host.py`, `tests/test_build_id.py` | already used `sv.git_bash()` (J41). Unchanged |
| `tests/test_claude_hook.py:179` `'bash harness/core/job.sh ...'` | a command string the hook is asked to judge, not a call. Not a repo caller |
| `tools/verbs/setup.py` `which('bash')`, `bash_kind` docstrings | lookups, not calls |
| `*.ps1`, `*.cmd` | none |
| `.github/workflows/*.yml` | none before this job, apart from the new step's comments (`proxy` runs `proxy/tools/build.sh` directly on Linux) |
| `*.md` docs | only the new `harness/README.md` lines. Job reports and run READMEs are history, not living callers |

## Evidence
a) On the PC, Claude Code started from Git Bash (`MSYSTEM=MINGW64`), commit `561ccbe` plus the `test_running_check` fix:
   - Command: `python3 -m unittest tests.test_job_sh tests.test_pc_deploy tests.test_claude_hook tests.test_setup tests.test_proxy_host`
   - Git Bash first on PATH: `Ran 91 tests in 171.120s / OK`.
   - With `PATH="/c/Users/liamr/AppData/Local/Microsoft/WindowsApps:$PATH"`, where `shutil.which('bash')` is
     `C:\Users\liamr\AppData\Local\Microsoft\WindowsApps\bash.EXE`: `Ran 91 tests in 168.928s / OK`.
   - Most of the 170 s is the proxy host build in `ProxyHostTests`, which runs because this branch changes `pc_deploy.py`.
   - Baseline on `origin/main` at `9a8058d` (this branch's base, same day), WSL first: `FAILED (failures=10, errors=2)`. That is the 10 `test_job_sh`
     failures J6 saw, plus 2 errors (`test_owner_is_added_to_control_jobs_only_when_missing` and the claude_hook settings test).
   - The "no Git Bash" path is covered by injected unit cases (`Setup.test_bash_for_tests`, `test_bash_check_reports_both_bashes`,
     `test_watcher_check_without_git_bash_fails_with_a_fix`).
b) On the PC: `python3 core/wsc.py gates` gave `gates: 11 ok, 1 warn, 0 failed in 203.3 s`, with `tests` reporting
   `385 host tests passed (202.2 s)`. The J6 failures are gone. The one warn is `hooks`: this clone's `core.hooksPath` is an absolute
   path. That is local config, not this job (see Open questions).
c) `python3 core/wsc.py setup --skip pc_rules playwright docker`:
   - Git Bash first:
     `ok   git_bash: bash on PATH: C:\Program Files\Git\usr\bin\bash.EXE (git); MSYSTEM=MINGW64; repo tools use: C:\Program Files\Git\usr\bin\bash.EXE`
   - WSL first, with `MSYSTEM` cleared:
     `ok   git_bash: bash on PATH: C:\Users\liamr\AppData\Local\Microsoft\WindowsApps\bash.EXE (wsl); MSYSTEM=unset; repo tools use: C:\Program Files\Git\bin\bash.exe`
     followed by `warn: this session is not a Git Bash one: start Claude Code from Git Bash, or put C:\Program Files\Git\usr\bin before WindowsApps and System32 on PATH`.
   - `ok   watcher: job.sh status exit 0` in both cases.
d) CI run 41208229617 on `02d6b5c`: `gates`, `proxy` and `harness-windows` all succeeded. The new step ran from 14:02:26 to 14:03:07
   (41 s, under the 3-minute limit) with `Ran 72 tests in 38.233s / OK` and no skips, so the runner found Git Bash itself. It passed on
   the first attempt, so the dispatch route was not needed. The final commit (this report plus the `shot.sh` line) is checked by its
   own push run. Its id is on the pull request.

## Deviations
- `running_check`'s provider defaults to `None` (meaning `windows_images`, looked up at call time) instead of `windows_images`
  itself, so the existing patch-based tests keep working. See above.
- `ctl.py` loads the finder by path instead of keeping a smaller copy. The brief allowed either. There is one finder, and `ctl.py`
  never runs outside the repo.
- `harness/core/shot.sh:41` changed from `bash` to `"$BASH"`. The brief's grep list includes `*.sh`. Without the change a WSL-first
  PATH inside the script could still pick the WSL launcher.
- This session started in `C:\Users\liamr\repos`, not the repo folder, so the commit hook did not run. I added the `Claude-Session`
  trailer by hand (`--trailer`) and checked it with `git log --format='%(trailers)'`.

## Open questions
- **Rule 79 blocks the merge.** `python3 tools/pr_policy.py --branch job/J22 --base origin/main` refuses the branch: it changes
  `harness/core/acceptance.py` and `ctl.py`, and the acceptance ledger holds 0 consecutive passes on build `41cde4716ac7`
  (20 needed). Those passes launch the game through the watcher, and the brief says J22 needs neither. Following the kill
  criterion, I stopped and asked. Liam (2026-10-31) chose to leave it to the reviewer. The options are: run
  `python3 harness/core/acceptance.py run` for 20 passes on the final build; exempt a change that only swaps which bash runs `job.sh`;
  or split the `ctl.py`/`acceptance.py` edits into their own job. The brief did not foresee this. A future brief that touches
  `harness/core/*.py` should say whether rule 79 applies.
- This clone has `core.hooksPath` set to an absolute path (`wsc setup` FAIL hooks_path, gates WARN hooks). `wsc setup --fix` sets it
  to `core/.githooks`. That is for Liam to run, since it is clone config and not repo content.
- The `BARE_BASH` guard covers Python only. `.sh` scripts that call `bash` inside themselves are not scanned. The only one was
  `shot.sh`, now `"$BASH"`. A `.sh` rule could be added if more appear.
