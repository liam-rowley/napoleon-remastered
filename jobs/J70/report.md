# J70 report: wsc setup: the watcher check runs the pre-J12 job.sh path

The orchestrator wrote this from the build agent's hand-back. The build ran as a subagent, and the harness refuses a subagent's Write of a
report file, so the parent writes it. The Claude-Session is the same as the build's.

## What was built
- **`tools/verbs/setup.py` has one owner for where the core is.**
  - `core_path(root, *parts)` returns `Path(root) / 'core' / ...`; its docstring names J12 and J70. `JOB_SH = ('harness', 'job.sh')` sits beside it.
  - All four checks that spelled the core path inline now go through the helper:
    - `check_core_pin`: `cwd=core_path(root)`;
    - `check_lf_scripts`: `git check-attr` on `core_path(root, *JOB_SH)`, relative to the root;
    - `load_pc_deploy`: `core_path(root, 'proxy', 'tools', 'pc_deploy.py')`;
    - `check_watcher`.
  - No second hard-coded `job.sh` path remains. `core/proxy/tools/layout.py` was not used, because it has no name for a file inside the core.
- **`check_watcher` checks that `job.sh` exists before it runs bash.**
  - When the file is missing, the check fails with `core/harness/job.sh missing` and the fix `git submodule update --init` (the core carries the
    watcher kit since J12). Bash is not run.
  - When the file is present, the behaviour is unchanged: `job.sh status`, its exit code and its last line.
- **Two regression tests in `tests/test_setup.py`:** `test_watcher_check_runs_the_core_job_sh` and
  `test_watcher_check_with_job_sh_missing_names_the_path_and_runs_no_bash`. `_run` and `git_bash` are mocked, so neither test runs the real `job.sh`.
- **A guard in `tests/test_repo_rules.py`:** `test_no_pre_j12_core_paths_in_tools`, with its fixture test `Fixtures.test_moved_paths`.
  - It reads the moved folders from `PROMOTIONS` in `tools/jobs_hooks.py`: the J12 keys `harness/core`, `proxy/core` and `saves/core`.
  - It scans the tracked `tools/**/*.py` and `tools/**/*.sh` for each folder, written with slashes, with backslashes, or as a `'harness' / 'core'`
    style join, and fails naming the file and line.
  - `tools/jobs_hooks.py` is the one allow-listed file, with its reason.
- **Scan fixes.** Every assertion holds unchanged on the new paths.
  - `tests/test_claude_hook.py:179`: now `bash core/harness/job.sh ...`. It passes, so `EXEMPT` still matches.
  - `tests/test_harness_host.py:88`: the route default is now `harness/napoleon/adapter.json`, still routed `run`.
  - `tests/test_harness_host.py:92`: now `proxy/napoleon/lua/ctl/cam_read.lua`, still `skip`.
  - `tests/test_proxy_host.py:220`: now `harness/napoleon/adapter.json`, with the same sets.
  - `tests/test_jobs_hooks.py:137`, `:140` and `:154`: now `harness/napoleon/adapter.json`, with `rule79_path` True.
  - `tests/test_repo_rules.py:78`: now `core/harness/job.sh`.

## Evidence
- **Red on the unchanged `setup.py`** (base 1ad7628):
  - `test_watcher_check_runs_the_core_job_sh`: `AssertionError: False is not true : job.sh status exit 127: C:\Users\liamr\repos\nap-J70\harness\core\job.sh:
    No such file or directory`
  - `test_watcher_check_with_job_sh_missing_names_the_path_and_runs_no_bash`: `AssertionError: bash ran a missing job.sh: ['stub-bash',
    '...\\harness\\core\\job.sh', 'status']`, raised from `setup.py` line 202.
- **Green after the fix:**
  - `tests.test_setup`: 13 OK.
  - The six modules the brief names together (`test_setup`, `test_repo_rules`, `test_claude_hook`, `test_harness_host`, `test_proxy_host` and
    `test_jobs_hooks`): 107 tests, OK, 1 skipped.
  - The orchestrator re-ran `tests.test_setup` and `tests.test_repo_rules` on 9ebd73b: OK.
- **`python3 core/wsc.py setup` on the PC, verified 2026-11-03:**
  - Before:
    - `FAIL watcher: job.sh status exit 127: /usr/bin/bash: C:\Users\liamr\repos\nap-J70\harness\core\job.sh: No such file or directory`
    - `setup: 9 ok, 2 failed`. The second failure was pc_rules: 1 foreign file in the game folder, unrelated to this job.
  - After:
    - `ok   watcher: job.sh status exit 0: }`
    - `setup: 11 ok, 0 failed`
  - The read-only comparison `bash core/harness/job.sh status` exited 0. No other `job.sh` subcommand, no `ctl.py` and no `pc_deploy.py` write was run.
- **Rerun scan,** `git grep -n -E "harness/core|'harness' */ *'core'"`: 144 hits (132 when the brief was written; the difference is this job's own
  lines).
  - History, kept: `jobs/` (42 files), `registries/jobs/` (4), `harness/runs/` (4), `proxy/runs/` (1), `upscale/runs/` (2).
  - `tools/jobs_hooks.py:49`, `:210`, `:235` and `:342`: kept. They are `PROMOTIONS` and the fallbacks for a base before J12, and this is the guard's
    one exempt file.
  - `tests/test_repo_rules.py:73`, `:75`, `:106` to `:108` and `:184`, and `tests/test_setup.py:66`: kept. They are the guard's comment, fixtures and
    expected folder list, and the regression test's comment.
  - `harness/napoleon/adapter.json:82` and `proxy/napoleon/lua/ctl/cam_read.lua:3`: filed, see Open questions.
- **Gates:**
  - `python3 core/wsc.py gates` (full): 13 ok, 1 warn, 0 failed in 281.4 s.
  - `jobs check`: 70 rows, ok, 0 registry gaps in briefs.
  - Pre-push `gates --fast`: 13 ok, 0 warn, 0 failed.

## Deviations from the brief and why
- **No old path is spelled out in `setup.py`.** Its comment and docstring describe the old place in words ("its pre-J12 place") rather than writing
  `harness/core/`, because the new guard scans comments in `tools/` too.
- **The guard also matches the backslash form** (`harness\core`), which the brief did not ask for. A Windows-style string is the same bug.
- **Other `wsc setup` lines changed for reasons outside this job:** pc_rules went from 1 foreign file to 0. Nothing in this job touched the game folder.
- **Model:** the brief names Sonnet. The build ran as an Opus subagent, because Liam asked on 2026-11-03 for Opus at high effort across the board.

## Open questions
- **Two stale paths for the next job that changes these files anyway**, and so runs the 20 acceptance passes (rule 79):
  - `harness/napoleon/adapter.json:82`: the scenario note names `harness/core/ctl.py scene`; it should be `core/harness/ctl.py scene`.
  - `proxy/napoleon/lua/ctl/cam_read.lua:3`: the comment names `harness/core/campose.py`; it should be `core/harness/campose.py`.
- **The watcher's ok line reads `job.sh status exit 0: }`.** `job.sh status` prints multi-line JSON and the check shows the last line. The brief kept
  that unchanged. A later job could show the state or the heartbeat age instead.
- **`tests/test_jobs_hooks.py` still uses pre-J12 `proxy/core/...` paths**, for example `proxy/core/dev.cpp` and `proxy/core/README.md.bak`. They are
  outside the brief's scan pattern, and the guard covers `tools/` only. Some, such as the segment-exemption cases, may be deliberate.

## Worth remembering
- A path move needs a guard, not just a grep. The new `test_repo_rules` check reads the moved folders from `PROMOTIONS`, so a future promotion job
  (for example `discovery/core` once it has a row) is covered by setting its job id there.
