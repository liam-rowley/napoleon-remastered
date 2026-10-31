# J52: Automatic review and fix rounds

Phase 1, tooling. D36 (Liam, 2026-10-31): a job that reaches `status=review` gets a fresh reviewer session; a non-merge verdict starts a fix
session on the job branch, then a new review round; at most 3 rounds, then the job is blocked for Liam. Today every review and every fix is
started by hand, and a second review round is impossible to start from the tools at all: `not_ready('review', ...)` refuses any branch that
already has `jobs/<id>/review.md`. This job adds the `fix` status and action, makes review readiness depend on the branch row instead of the
file, teaches `wsc jobs check` the round format, and adds an autopilot loop to `wsc jobs view --serve` that launches ready reviews and fixes.

Model: Sonnet. Python tooling and tests in this repo; no engine, DLL or PC work. Budget about 120 tool calls; at the cap, stop, commit, report
what is left. Subagents are not needed. Waiting belongs to the harness: the loop you build waits; you do not poll anything yourself.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J52`). Read `docs/DECISIONS.md` (D15, D16, D21, D30, D32, D33, D34, D36), `docs/REVIEW.md`, and
  `tools/verbs/jobs.py` in full (its docstring is the contract for the launch server), `tools/pr_policy.py` (`verdict()`, the job-branch
  rules), `schemas/jobs.schema.json`, `tests/test_jobs.py` and `tests/test_pr_policy.py`.
- Search before writing: `python3 core/wsc.py find jobs review verdict serve launch`. Extend `tools/verbs/jobs.py` and its tests; add no new
  tool for what a `jobs` subcommand can do. Never change `core/`.
- Look at how reviews are written today: most `jobs/*/review.md` on main already use `## Round N (YYYY-MM-DD, branch job/J<n> at <sha>)`
  with the verdict inside it (J1, J13, J18, J20); some (J2, J15, J17) have no round heading at all; J1 keeps only its round 2.

## Target facts
Check each again before relying on it:
- Job statuses are the enum in `schemas/jobs.schema.json` (`needs_brief`, `queued`, `review`, `done`, `blocked`); `STATUSES_WITH` in
  `jobs.py` ties `brief`, `report` and `review` fields to statuses.
- `verdict()` in `pr_policy.py` returns the first `Verdict:` line of a file; `wsc jobs check` and CI's `policy` check both use it.
- `pr_policy.py` refuses a job branch when any session that touched `report.md` also touched `review.md` (`Claude-Session:` trailers). A fix
  session appends to `report.md` and never touches `review.md`, so this rule already holds across rounds: keep it that way and test it.
- The launch server names sessions `J<n>-<action>`, runs `claude --bg --name ... --model ... --effort medium <prompt>`, and refuses a launch
  when `claude agents --json` lists a session of the same name in `state == 'working'`. Whether `claude agents --json` also lists finished
  sessions, and whether `claude --bg --name` accepts a name a finished session already used, is not known: find out on the PC (read-only,
  `claude agents --json` and one `--dry-run`) and record the answer with its date in the report and in the `jobs.py` docstring.

## Decisions already made for this job
- **Status `fix`.** Add it to the schema enum and to `STATUSES_WITH` (it needs `brief`, `report` and `review`). Only a reviewer sets it.
- **Rounds in `review.md`.** Each round is a section `## Round N (YYYY-MM-DD, branch job/J<n> at <sha>)`, newest first, N counting up from 1
  with no gaps, at most 3, exactly one verdict line per round (inside its section). Newest first keeps `verdict()` returning the latest
  verdict with no change to its parser; add a test that proves it.
- **Fix rounds in `report.md`.** A fix session appends `## Fix round N`, where N is the review round it answers: what it changed for each
  finding (commit sha), what it left and why. It never edits `review.md` or earlier report sections.
- **Status after each verdict** (the reviewer sets it): `merge` -> `done` (as today); `merge after fixes` or `do not merge` in round 1 or 2
  -> `fix`; the same in round 3 -> `blocked` with `blocked_by="3 review rounds without merge"`. A fix session ends with `status=review`.
- **`wsc jobs check`** (on every `review.md` it checks): rounds numbered, newest first, at most 3, one verdict each, each round heading dated;
  and the row agrees with the latest round: `done` only after `merge`; after a non-merge in round N < 3, `fix`, or `review` once
  `report.md` has `## Fix round N`; after a non-merge in round 3, `blocked` with that `blocked_by`. Reviews already merged keep their old
  form: freeze the set of job ids that have a `review.md` on main at your base as a named constant, exempt from the round rules only (the
  verdict and date rules still apply), with a comment saying why. Every other `review.md` follows the new rules.
- **Readiness.** `not_ready('review', ...)`: ready when the job branch row says `review` (whether or not `review.md` exists); the
  `on_branch` tuple no longer needs `has review.md` for this, so simplify it if nothing else reads it. New action `fix`: ready when the job
  branch row says `fix`. Both stay one rule used by `jobs review`, the new `jobs fix`, the view's buttons, the server and the loop.
- **`wsc jobs fix [--id J<n>]`**, mirroring `jobs review`: picks or checks the branch and prints the fix steps (check out `job/<id>`, read
  the newest review round, address its blockers and should-fix items, append `## Fix round N`, run `wsc gates` and
  `pr_policy.py --branch job/<id>`, set `status=review`, push; never touch `review.md`, never merge). `PROMPTS['fix']` runs it;
  `LABELS['fix'] = 'Fix'`. The fix session uses the row's model (as a build does), effort medium.
- **`jobs review` and its steps** name the round the reviewer is writing (N = rounds in `review.md` + 1) and say where it goes (top of the file).
- **The autopilot: `wsc jobs view --serve --auto [--interval SECONDS]`** (default 300). A thread in the server process: each tick it takes a
  fresh snapshot (the same `snapshot()` the buttons use), and for every job where `review` or `fix` is ready, launches it through the same
  checks as `launch_request` (refactor so the button path and the loop share one function; the token, Origin and Host checks stay on the HTTP
  path only). No count cap (D34). It never launches `brief` or `build`. It also skips a job while any session named `J<n>-*` is working
  (a build or fix that has pushed `status=review` but not yet ended must not race its reviewer). It fails closed: a snapshot or
  `claude agents --json` error skips that tick and is logged. Each launch, refusal and skipped tick is one UTC-stamped line on stderr and in
  `_scratch/jobs_auto.log` (git-ignored). `--dry-run` with `--auto` logs what it would start and starts nothing. The page shows that the
  autopilot is on and when it last ran.
- **`docs/REVIEW.md`**: the round format, the status to set after each verdict, the round-3 block, and that the round's reviewer is a fresh
  session (the loop starts one). Update the `jobs.py` docstring and usage lines, and `CLAUDE.md` "Jobs" only where a sentence becomes wrong.
- **Out of scope:** auto-starting briefs or builds; merging anything other than the reviewer's existing `merge` path; `plan/` and `meta/`
  branches; a count cap; changing `pr_policy.py` rules other than tests for the newest-verdict reading; anything in `core/`.

## Deliverables
1. `schemas/jobs.schema.json` and `jobs.py`: the `fix` status, the new readiness rules, the `fix` action, `jobs fix`, round-aware `jobs review`
   steps, the lanes and buttons of `jobs view` for `fix`.
2. `wsc jobs check`: the round rules and the status-verdict agreement, with the frozen legacy set.
3. `--auto` and `--interval` on `jobs view --serve`, sharing one launch path with the buttons; the log file.
4. `docs/REVIEW.md`, the `jobs.py` docstring, and `CLAUDE.md` if needed.
5. Tests in `tests/test_jobs.py` and `tests/test_pr_policy.py`, at least: fix readiness from a branch row; a round-2 review ready after a fix;
   round 3 non-merge requires `blocked`; check fails on a 4th round, on rounds out of order or with a gap, on a round with two verdicts, and
   on a status that disagrees with the latest verdict; the legacy set is exempt; `pr_policy` reads the newest verdict (a round-2 `merge` over
   a round-1 `do not merge` passes, the reverse fails); a fix session's commits on `report.md` do not trip the never-review-your-own-job rule;
   the loop, with fake snapshot, agents and launch seams, starts a review and then, after the fake branch row changes to `fix`, a fix; it
   skips a job with any `J<n>-*` session working; it starts nothing for `brief` or `build`; it starts nothing after a snapshot error.
6. `python3 core/wsc.py gates` green; `jobs check` passes on main's current rows.

## PC test
Read-only, no game launch: on the PC, `claude agents --json` (does it list finished sessions, with what `state`?) and
`python3 core/wsc.py jobs view --serve --auto --interval 60 --dry-run --no-open` for two ticks against the real origin, its log lines quoted
in the report. Starting a real session is not needed and not wanted.

## Kill criteria
- `claude agents --json` gives no reliable way to tell a running session from a finished one: stop the loop work (keep everything else),
  report what it prints, and propose options to Liam.
- `claude --bg --name J<n>-review` refuses a name that a finished session already used: stop and ask Liam how to name round 2 and 3
  sessions (for example `J<n>-review-2`) before changing the naming.
- Meeting the round rules would mean rewriting a merged `review.md` on main, or changing `core/`: stop and ask.
- Over about 120 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J52/report.md`: what was built, the `claude agents --json` finding with its date, the test list and the gates result, the
dry-run log lines, deviations from this brief and why, open questions (for example how the first real round-2 review should be watched).
Then `wsc reg set jobs J52 status=review report=jobs/J52/report.md`.
