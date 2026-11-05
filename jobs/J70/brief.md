# J70: wsc setup: the watcher check runs the pre-J12 job.sh path

Phase 1 fix. `wsc setup` reports a running watcher as FAIL: `tools/verbs/setup.py` `check_watcher` (line 202) runs `harness/core/job.sh status`, the path J12
moved to `core/harness/job.sh`, so bash exits 127 (seen 2026-11-02 22:40 UTC with the watcher up and its heartbeat current; also in the J8 PC run's notes,
`harness/runs/20261101_j8pc/README.md` line 50). Point the check at the core's `job.sh` through one helper, prove it with host tests that fail on today's
code, and clear or file every other pre-J12 path the scan below lists.

Model: Sonnet medium (D15). One Python verb and its host tests: no reverse engineering, shader, DLL or crash work, and no independent check, so nothing
here earns Opus. Budget about 25 tool calls; at the cap, stop, commit, report what is left. No subagents, no game launch.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J70`). Read `tools/verbs/setup.py` whole (it is short), `tests/test_setup.py`, and the J12 move in `CLAUDE.md`
  ("Since J12 the core carries ...") and `core/docs/CONSUMING.md` "The proxy, the harness and the save tools".
- `needs_pc` is false. The one live call allowed is read-only (see Proof); everything else runs on the host with the watcher mocked.

## Deliverables
1. **One owner for "where the core is" in `setup.py`.** Today four checks each spell the core path inline: `check_core_pin` (`cwd=root / 'core'`),
   `check_lf_scripts` (`'core/harness/job.sh'` for `git check-attr`), `load_pc_deploy` (`root / 'core' / 'proxy' / 'tools' / 'pc_deploy.py'`) and
   `check_watcher` (the wrong `root / 'harness' / 'core' / 'job.sh'`). Add one helper, for example `core_path(root, *parts)` returning
   `Path(root) / 'core' / ...`, with a docstring naming J12 and J70, and make all four go through it; `job.sh`'s place is one name beside it
   (for example `JOB_SH = ('harness', 'job.sh')`), used by both `check_lf_scripts` and `check_watcher`. No second hard-coded path to `job.sh` remains.
   - Why not `core/proxy/tools/layout.py`: it answers where the game root and the adapters are, seen from the core's side; it has no name for a file
     inside the core, and giving it one is a change inside `core/` (never done here). Use it only if it already answers this without a core change.
2. **A missing `job.sh` is its own failure.** `check_watcher` checks the resolved `job.sh` exists before running bash. When it is missing it returns
   `False`, a detail naming the repo-relative path (`core/harness/job.sh missing`), and the fix `git submodule update --init (the core carries the
   watcher kit since J12)`, without running bash. The present-file path is unchanged: `job.sh status`, its exit code and last line.
3. **Regression tests in `tests/test_setup.py`.** Write them first and run them against the unchanged `setup.py`; both must fail there (paste the two
   failures in the report). Neither runs the real `job.sh`: `_run` and `git_bash` are mocked, so the tests pass on CI with no watcher.
   - **Watcher up:** `git_bash` returns a stub; a fake `_run` records the command and returns `(0, '{"state": "idle"}')` only when the script argument
     is an existing file and the subcommand is `status`, else `(127, '<path>: No such file or directory')`. Assert `ok` is true and the recorded script
     path resolves to `ROOT / 'core' / 'harness' / 'job.sh'`, which exists. Today's code passes `harness/core/job.sh`, so it gets 127 and fails.
   - **Path moved:** a temporary root with no `core/harness/job.sh`; `git_bash` stubbed; a fake `_run` that fails the test if it is called with a
     `job.sh` path. Assert `ok` is false, the detail names `core/harness/job.sh` and `missing`, and the fix names `submodule`. Today's code runs bash
     on the missing path and reports `job.sh status exit 127`, so it fails.
   - Keep `test_watcher_check_without_git_bash_fails_with_a_fix` and `test_every_check_has_a_function` passing.
4. **A guard so the class cannot come back** (a learning becomes code first). In `tests/test_repo_rules.py`, a test that scans the tracked
   `tools/**/*.py` and `tools/**/*.sh` for the folders J12 moved (the `tools/jobs_hooks.py` `PROMOTIONS` keys whose job is `J12`: `proxy/core`,
   `harness/core`, `saves/core`), as a slash path or a `'harness' / 'core'` style join, and fails naming file and line. `tools/jobs_hooks.py` is the one
   exempt file (it names the old paths on purpose, see the scan). It must be green after deliverable 1.
5. **The scan.** Work through every hit below: fix the ones marked fix, leave the ones marked keep, and file the ones marked file in the report.
   Then run `git grep -n -E "harness/core|'harness' */ *'core'"` again and put the remaining hits, each with its class, in the report.
6. `python3 core/wsc.py gates` green; `python3 -m unittest tests.test_setup tests.test_repo_rules tests.test_claude_hook tests.test_harness_host
   tests.test_proxy_host tests.test_jobs_hooks` passing.

## The scan (2026-11-03, main cbf3105, `git grep -n -E "harness/core|'harness' */ *'core'"`)
132 hits. Outside the history folders, 19 lines:

**Fix in this job** (tools/ and tests/: not rule 79 inputs):
- `tools/verbs/setup.py:202`: the bug (deliverables 1 to 3).
- `tests/test_claude_hook.py:179`: two sanctioned-writer fixtures run `bash harness/core/job.sh ...`; use `core/harness/job.sh`, the command agents run
  (`tools/claude_hook.py` `EXEMPT` matches `job.sh` by name, so the test should still pass; if it does not, that is a hook bug: report it, do not loosen the test).
- `tests/test_harness_host.py:88`: the `route` default `files=('harness/core/watcher.ps1',)`; use a harness input that exists after J12 (for example
  `harness/napoleon/adapter.json`) with the same expected route. Line 92 has the same class for the proxy (`proxy/core/console.cpp`): fix it the same way.
- `tests/test_proxy_host.py:220`: `ci.classify(['harness/core/job.sh'])`; use a post-J12 harness path, same expected sets.
- `tests/test_jobs_hooks.py:137`, `:140`, `:154`: `acceptance_problems` on `harness/core/ctl.py` and `harness/core/job.sh`; use post-J12 paths that
  `rule79_path` still counts (check with it), same assertions.
- `tests/test_repo_rules.py:78`: the allowed example `"x = 'bash harness/core/job.sh'"`; use `core/harness/job.sh`.
- If any of these assertions holds only for the old path, keep that line as it is and report it as a finding: it may be a real bug in the code under test.

**Keep** (deliberate pre-J12 names, or records):
- `tools/jobs_hooks.py:49` (`PROMOTIONS`, rule 76: the moved folder must stay gone), `:210` (`ACC_CHECKERS`, the base's `acceptance.py` before J12),
  `:235` (`show_first` docstring) and `:342` (the watcher source on an older base): fallbacks for a base before J12, the guard's one exempt file.
- History, never edited: `jobs/*/brief.md` and the other job files, `registries/jobs/J12.json`, `J19.json`, `J43.json` descriptions, `harness/runs/*/README.md`,
  `proxy/runs/20261029_j13pc/README.md`, `upscale/runs/2026-10-31_j50/README.md` and `probe_run.sh` (what ran then, as it ran).

**File, do not fix** (a change under `harness/` or `proxy/` is a rule 79 input: it would need 20 acceptance passes, `docs/REVIEW.md`):
- `harness/napoleon/adapter.json:82`: a scenario note names `harness/core/ctl.py scene`; should be `core/harness/ctl.py`.
- `proxy/napoleon/lua/ctl/cam_read.lua:3`: a comment names `harness/core/campose.py`; should be `core/harness/campose.py`.
- Put both under `## Open questions` as text for the next job that changes those files anyway and so carries the 20 passes.

## Proof
- The two new tests failing on the unchanged `setup.py`, then passing (deliverable 3), and the guard green (deliverable 4).
- **`python3 core/wsc.py setup` on this machine, before and after the fix**: paste the `watcher` line and the summary line of each run. Before: `FAIL watcher:
  job.sh status exit 127`. After: `ok   watcher: job.sh status exit 0: ...` with the watcher up, or, if it is down, `FAIL watcher: job.sh status exit 1:
  watcher heartbeat is ...s old` (the right script ran: that is a pass for this job; do not start the watcher, that is Liam's). Exit 127 or `No such file`
  after the fix is a failure.
- The live watcher may be read, read-only: `wsc setup` (which runs `job.sh status`) and, once for comparison, `bash core/harness/job.sh status`. `status`
  reads the heartbeat and status files in the state folder; it takes no lock, submits no job and launches nothing, so `needs_pc` stays false. No other
  `job.sh` subcommand (no `lock`, `launch`, `kill`, `profile`, `ctl`, `noop`, `touch`, `scratch`), no `ctl.py`, no `pc_deploy.py` write.

## Out of scope
- Any change under `core/`, `harness/` or `proxy/` (the last two are rule 79 inputs; see the scan's file list), and any settings file.
- Other `wsc setup` checks beyond routing their core paths through the helper; new checks.

## Kill criteria
- The fix would need a change inside `core/` (for example a new name in `layout.py`): stop, change nothing there, and report what the core would need
  as a warscape-core backlog item.
- After the fix `wsc setup` still reports exit 127 or `No such file` for the watcher: stop and report the full output; do not hard-code another path.
- A new test passes on the unchanged `setup.py`: it does not test the bug; stop and rewrite it before touching the fix.
- Any tool call is refused by a deny rule or the hook: stop and report the call; do not retry another way.

## Finish
Write `jobs/J70/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`): the helper and the checks that use it,
the two red-then-green test runs, the `wsc setup` lines before and after, the rerun scan with each remaining hit's class, the two filed items, and the
gates output. Then `wsc reg set jobs J70 status=review report=jobs/J70/report.md`.
