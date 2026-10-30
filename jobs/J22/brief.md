# J22: Windows host tests find Git Bash

Phase 1. On a Windows host the repo tests and two tools shell out to a bare `bash`, which on a PC without Git Bash first on PATH is the
WSL launcher (`WindowsApps\bash.exe` or `System32\bash.exe`): other paths, other `python3`, so `job.sh` exits 127. J6 (`jobs/J6/report.md`,
2026-10-29) saw 10 failures in `test_job_sh` and `test_pc_deploy` on the PC while CI on Linux stayed green, so the PC is the only place the
bug shows. Make every repo caller find Git Bash explicitly (or skip with a reason), make `wsc setup` say which bash it found, and prove it
on the PC and on the `harness-windows` runner.

Model: Sonnet (D15 default: Python test and tooling work, no reverse engineering). Budget about 60 tool calls; at the cap, stop, commit,
report what is left. No subagents. No game or watcher is started. CI waits go to the harness (`gh run watch` in a background shell), never a
polling loop of tool calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J22`). Read `docs/DECISIONS.md` D30, D31 and `jobs/J6/report.md` ("Open questions", the bash paragraph).
- Read, don't rediscover: `tools/verbs/setup.py` (`bash_kind`, `git_bash`: J41 already added the shared finder, with `nt`, `which`,
  `git_exec_path` and `isfile` injectable, and `check_git_bash`, `check_watcher`), `tests/test_setup.py` and `tests/test_proxy_host.py`
  (`git_bash` unit cases and its one caller to copy), `tests/test_job_sh.py` (`run()` uses bare `bash`), `tests/test_claude_hook.py`
  (`['bash', '-c', cmd]` three times), `harness/core/ctl.py` (`job_sh_transport` uses bare `bash`), `proxy/tools/pc_deploy.py`
  (`windows_images`, `running_check`) and `tests/test_pc_deploy.py` `test_running_check` (it guards its fallback assertions with
  `os.name != 'nt'`; read why the other test cases still fail on Windows).
- Find every other bare `bash` in `*.py`, `*.ps1`, `*.cmd`, `*.yml` and docs with a recursive grep for `'bash'`, `"bash"` and `bash ` and list
  each in the report with what you did (fixed, not a repo caller, or runs only on Linux/CI).

## Decisions already made for this job
- **One finder: `tools/verbs/setup.py` `git_bash()`** (J41). Do not write a second one. Tests and tools get the path from it. A tool outside
  `tools/` (`harness/core/ctl.py`, which also runs on the watcher's side where `tools/verbs` may not be importable) gets the smallest
  equivalent that keeps the same order (bash on PATH when it is Git's, then the install `git --exec-path` names, then the default folders),
  or imports it with a fallback to plain `bash` off Windows; say which and why in the report. If sharing is cleaner by moving the finder
  into a small module both import, do that and keep `setup.git_bash` as the same function (the `tests/test_proxy_host.py` cases stay green).
- **A test that needs bash and finds none skips with a reason** (`skipTest` naming `python3 core/wsc.py setup`), on Windows only; off
  Windows a missing bash is a failure as today. A test that finds the WSL bash must not run against it.
- **`test_running_check` must not depend on the host OS.** `running_check` takes the Windows process list on `nt`, so the no-watcher log
  fallback is untestable there. Add an injectable process-list provider to `running_check` (a keyword, default `windows_images`), have the
  test pass `lambda: None` for the fallback cases and a fake image set for the tasklist cases, and drop the `os.name` guard so the same
  assertions run on Linux, on the PC and on the runner. Behaviour with the default argument is unchanged.
- **`wsc setup` reports the bash it uses.** `check_git_bash` today looks only at `bash` on PATH and requires `MSYSTEM`; keep that rule for
  "a session started from Git Bash" but report both: the bash on PATH with its kind, and the explicit `git_bash()` path the repo's tools will
  use. It fails only when `git_bash()` finds none on Windows; PATH being WSL while an explicit Git Bash exists is a warning line with the
  fix (start from Git Bash, or put `C:\Program Files\Git\usr\bin` before `WindowsApps`), not a failure. `check_watcher` also uses
  `git_bash()`. Unit tests with the probes injected, as `tests/test_setup.py` does.
- **No change to what the tests assert** beyond the two rules above; no `core/` change; no harness behaviour change.
- The `harness-windows` runner is Windows PowerShell 5.1 and runs `harness/tests/*.ps1` only; the repo's Python tests run in the `gates`
  job on Linux. So "green on the harness-windows runner" needs a route. Check whether `harness-windows` can run these Python tests
  (`actions/setup-python` is already there and Git for Windows is on `windows-latest`); if so add a step limited to `tests.test_job_sh`,
  `tests.test_pc_deploy`, `tests.test_claude_hook`, `tests.test_setup` and the bash-finder cases of `tests.test_proxy_host`, and add the new
  inputs to `tools/changed_inputs.py` so the job runs when they change (with its unit test). The step must add no more than 3 minutes. If
  that is not feasible in 2 attempts, say so and use a `workflow_dispatch` run as the proof instead.

## Deliverables
1. Every repo caller of bash uses `git_bash()` (or skips with a reason on Windows); the call-site list in the report.
2. `running_check` with the injectable process provider; `test_running_check` OS-independent.
3. `check_git_bash` and `check_watcher` as above, with unit tests.
4. The Windows test step in `harness-windows` (or the dispatch route), its `changed_inputs.py` entry and test.
5. A unit guard so a new bare `bash` subprocess command in a test or tool is caught: a test that scans `tests/*.py`, `tools/**/*.py`,
   `harness/**/*.py` and `proxy/tools/*.py` and fails naming file and line, with an allow-list for Linux-only files (each entry has a
   reason). This is the "a learning becomes code first" rule.
6. `harness/README.md` Tests updated; `CLAUDE.md` untouched unless a rule for every session changed (it should not).

## Proof (each with the command and its output or run id in the report)
a) On the PC, started from Git Bash: `python3 -m unittest tests.test_job_sh tests.test_pc_deploy tests.test_claude_hook tests.test_setup
   tests.test_proxy_host` green; then the same with the WSL launcher first on PATH (prepend
   `/c/Users/liamr/AppData/Local/Microsoft/WindowsApps` to `PATH`): still green, because the tests find Git Bash explicitly. The "no Git Bash
   found" path is proved by the injected unit cases (skipped with a reason).
b) On the PC: full `python3 core/wsc.py gates`, the whole `tests` gate green (the 10 J6 failures gone), time in the report.
c) `python3 core/wsc.py setup` output showing the bash line for both cases (Git first on PATH; WSL first on PATH).
d) `harness-windows` (or the dispatch) green on the final code commit, run id in the report; `gates` and `proxy` green on the same commit.

## Kill criteria
- A test still fails on the PC with Git Bash found and chosen: stop after 3 attempts, record the failing test and its output, report.
- The runner step cannot be made to pass in 2 attempts: use the dispatch route and report the log.
- Any step would need the game or the watcher on the PC: it does not; stop and ask if one seems to.

## Finish
Write `jobs/J22/report.md`: what was built, the bash call-site list with what each became, proof a) to d) with commands, times and run ids,
deviations from this brief and why, open questions. Then `wsc reg set jobs J22 status=review report=jobs/J22/report.md`.
