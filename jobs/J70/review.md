## Round 1 (2026-11-03, branch job/J70 at 101a3ae)

**Verdict: merge.**

Reviewed independently (fresh session; the build and report came from a different session).

### Machines
- Unit tests named in the brief (setup, repo_rules, claude_hook, harness_host, proxy_host, jobs_hooks): 107 tests OK, 1 skipped (run 2026-11-03).
- `wsc setup` on this PC after the fix: `ok   watcher: job.sh status exit 0`, so the right script runs. The one remaining FAIL is `pc_rules` (1 foreign file in the game folder), unrelated to this job.
- CI on 101a3ae: `gates` pass; `proxy` and `viewer` skipped; `harness-windows` was still pending at review time. Auto-merge waits for it. It is a required check, so a red result keeps the PR open.

### Claims against the brief
- Deliverable 1 (one owner for the core path): `core_path` and `JOB_SH` in `tools/verbs/setup.py`; all four checks use it; no second `job.sh` path remains. Present.
- Deliverable 2 (missing `job.sh` is its own failure): present, returns False with `core/harness/job.sh missing` and the submodule fix without running bash.
- Deliverable 3: both tests are present and mocked as specified. The report pastes the red output on the unchanged base (exit 127; bash ran on the missing path), consistent with the old code at line 202.
- Deliverable 4 (guard): `test_no_pre_j12_core_paths_in_tools`, driven by `PROMOTIONS`, fixture test included; `jobs_hooks.py` is the single exemption with a reason. Green.
- Deliverable 5: all listed test lines changed; the two items under `harness/` and `proxy/` correctly left alone (rule 79) and filed. My `git grep` over tools, tests, harness/napoleon and proxy/napoleon shows only those two plus the guard's own fixtures and comments.
- Nothing changed under `core/`, `harness/` or `proxy/`; no rule 79 passes needed.

### Deviations
Opus instead of Sonnet, and the guard also catching backslash paths: both named in the report with reasons. Fine.

### Risk-first reading
Read `check_watcher` and `check_lf_scripts` in depth (the code that touches the live watcher and path handling). `relative_to(root)` is safe because `core_path` always builds under `root`. The `is_file()` check precedes bash, as required.

### Findings
- **blocker:** none.
- **should-fix:** none.
- **later:**
  - `tools/verbs/setup.py` (check_watcher): the ok line shows only the last line of multi-line JSON (`exit 0: }`). Show the state or heartbeat age. Already in the report's open questions.
  - `tests/test_jobs_hooks.py` still uses pre-J12 `proxy/core/...` fixture paths outside the brief's scan; check whether deliberate. Already in the report.
  - The two filed stale comments (`harness/napoleon/adapter.json:82`, `proxy/napoleon/lua/ctl/cam_read.lua:3`) await a job that touches those files anyway.
