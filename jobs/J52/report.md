# J52 report: Automatic review and fix rounds

Built on `job/J52` from `origin/main` at 39eab5e, in one interactive Claude Code session on Liam's PC (D36).

## What was built
- **Status `fix`** in `schemas/jobs.schema.json` (enum, and it requires `brief`, `report` and `review`) and in `STATUSES_WITH`.
- **Readiness** (`not_ready`, the one rule): `review` is ready when the job branch row says `review`, whether or not `review.md`
  exists, so round 2 and 3 can start; new action `fix`, ready when the branch row says `fix`. `branch_rows` now returns
  `{id: row or None}` (the `has review.md` half of the tuple had no other reader). `pick_branch(action, ...)` serves `jobs review`
  and `jobs fix`; `pick_review` stays as a thin wrapper.
- **`wsc jobs fix [--id J<n>]`**: picks or checks the branch, reads the newest round from the branch's `review.md`, prints the fix
  steps (address round N, append `## Fix round N` to `report.md`, gates and `pr_policy.py`, `status=review`, push; never touch
  `review.md`, never merge). `PROMPTS['fix']`, `LABELS['fix'] = 'Fix'`; the session uses the row's model, effort medium.
- **`jobs review` steps** name the round being written (rounds in `review.md` + 1), say it goes at the top, and give the status
  to set for each verdict. `jobs review` refuses a 4th round.
- **`wsc jobs check`**: on every `review.md` outside `LEGACY_REVIEWS`, the round rules (headings `## Round N (YYYY-MM-DD, branch
  job/J<n> at <sha>)`, counting up from 1 with no gap, newest first, at most 3, exactly one verdict line per round, none above the
  first round) and the row agreeing with the newest round (merge -> done; non-merge in round N < 3 -> `fix`, or `review` once
  `report.md` has `## Fix round N`; round 3 non-merge -> `blocked` with `blocked_by="3 review rounds without merge"`).
  `LEGACY_REVIEWS` freezes the 22 jobs with a `review.md` on main at 39eab5e; a test checks the set against that commit.
  The date and verdict rules still apply to them.
- **The view**: a `fix` lane ("Waiting for fixes") and a Fix button. `lane()` now reads the job branch's row for review, fix and
  blocked (the builder and reviewer set those on the branch, so main never showed them).
- **The autopilot**, `wsc jobs view --serve --auto [--interval SECONDS]` (default 300, minimum 30): `JobServer.run_auto` in a
  daemon thread. Each tick takes a fresh `snapshot()` and one `claude agents --json` list, then starts every job branch ready
  for `review` or `fix` through `JobServer.start()`, the launch path the buttons now share (token, Origin, Host and content-type
  checks stay in `launch_request`). It never starts a brief or a build, skips a job while any live `J<n>-*` session exists, and
  skips the whole tick on a snapshot or agent-list error. Every tick, launch and refusal is one UTC-stamped line on stderr and in
  `_scratch/jobs_auto.log` (git-ignored); `--dry-run` logs what it would start. The served page says the autopilot is on, its
  interval and when it last ran.
- **Docs**: `docs/REVIEW.md` gets a "Rounds (D36)" section; its Output section now has the round format, the status per
  verdict and the round-3 block. The `jobs.py` docstring and usage lines are updated. `CLAUDE.md` needed no change: no sentence
  in it became wrong.

## `claude agents --json` (read on the PC, 2026-10-31, Claude Code 2.1.316)
Read-only. It lists interactive sessions (no `state`, `status` idle or busy) and background sessions with a `state`: here one
`"done"` (`j7 brief`, finished, still listed) and one `"blocked"` (`J36-build`, waiting on input). The existing code knows
`"working"` too. So finished sessions **are** listed, and a live session can be told from a finished one by `state`. `claude
agents --help` says `--json` prints active sessions and `--all` adds completed ones, but a `done` session appeared without
`--all`. `claude --help` calls `--name` a "display name"; ids are separate, and `claude attach` takes an id or part of a name.
Starting a real session to test name reuse was out of scope (the brief: "not needed and not wanted"), so whether `claude --bg
--name J<n>-review` accepts a name a finished session already used is **not proven**. Nothing points to a refusal, and the
`kill` criterion needs one, so the naming stays `J<n>-<action>` (see Open questions). Recorded in the `jobs.py` docstring.

## Tests and gates
New in `tests/test_jobs.py`:
- `Ready`: fix ready from the branch row; a round-2 review ready after a fix (review.md present).
- `Rounds`: good rounds pass; round 3 non-merge requires `blocked`; a 4th round fails; out of order, gap or missing round 1
  fails; two verdicts, none, or one above the first round fails; an undated heading or no rounds fails; a status that disagrees
  with the newest verdict fails (four cases); the legacy set is exempt from the round rules only; the legacy set equals the
  `review.md` files on 39eab5e.
- `Steps`: review steps name the round and where it goes (rounds 1 and 3); fix steps; the fix argv uses the row's model; the fix lane and button.
- `Autopilot` (fake snapshot, agents and launch seams): a review starts, then after the branch row changes to `fix`, a fix;
  a job with a live (`working` or `blocked`) `J<n>-*` session is skipped, a finished one or another job's is not; nothing for a
  brief or a build; nothing after a snapshot or agent-list error; dry run logs and starts nothing; `run_auto` ticks until stopped
  and the page shows it; the log file gets one stamped line.

New in `tests/test_pr_policy.py`: the newest round's verdict decides (round-2 `merge` over round-1 `do not merge` passes, the
reverse fails); a fix session's commits on `report.md` do not trip the own-review rule, and a fixer who also writes the review does.

Results on the PC: `tests.test_jobs` 57 ok, `tests.test_pr_policy` 26 ok; `wsc jobs check`: 52 rows, ok. Full `wsc gates`: 10 ok,
1 warn (the hooks path is set absolute in this clone), 1 failed: the `tests` gate, with 11 errors, all in `tests/test_pc_deploy.py`
and all `pc_deploy: refusing: tasklist: Napoleon.exe is running` (the game was open on the PC). The same 11 errors appear with my
changes stashed; every other test file passes (328 tests, 12 skipped). CI runs on Linux with no game, so it does not hit this.

## PC test: dry run against the real origin
`python3 core/wsc.py jobs view --serve --auto --interval 60 --dry-run --no-open`, stopped after two ticks:

```
jobs view: serving http://127.0.0.1:59228/ (dry run: nothing is started); Ctrl+C stops it
2026-10-31 13:05:46 UTC jobs auto: on, every 60 s (dry run: nothing is started)
2026-10-31 13:06:09 UTC jobs auto: tick: nothing ready for review or fix (22 job branches)
2026-10-31 13:07:24 UTC jobs auto: tick: nothing ready for review or fix (22 job branches)
```

A tick takes about 23 s (it fetches all 22 job branches), and the interval counts from the end of a tick. In that run the second
line reached stderr but not the log file before the process was stopped. The log file is now written before stderr.

After this branch's row was set to `review` and pushed, one more dry-run tick found it:

```
2026-10-31 13:13:23 UTC jobs auto: J52-review: dry run, would start: C:\Users\liamr\.local\bin\claude.EXE --bg --name J52-review --model sonnet --effort medium "Review job J52: git pull, then run python3 core/wsc.py jobs review --id J52 and follow docs/REVIEW.md."
```

## Deviations from the brief, and why
- **Live means `working` or `blocked`**, for the buttons and the loop alike. The brief says "working", but the PC shows a
  `blocked` session (waiting on input) that has not ended. Starting a second `J<n>-build`, or a reviewer next to it, would race it.
- **`branch_file()`** reads `review.md` from `origin/job/<id>` for the round number, since `branch_rows` no longer carries it.
- **`jobs review` refuses a 4th round**, and `--auto` without `--serve` or with `--interval` under 30 is refused. These are small
  guards the brief did not list.
- **`docs/REVIEW.md` Merging**: "the next review round decides" (about a red check after a merge verdict) became "Liam decides
  whether it takes another round". The row is `done` by then, so no round starts by itself.

## Open questions
- **Name reuse, unproven**: the first real round 2 will be the first `claude --bg --name J<n>-review` that reuses a finished
  session's name. Watch that launch: if `claude` refuses it, the loop logs `claude --bg failed: ...` every tick for that job
  (it does not crash). The fix would be round-numbered names (`J<n>-review-2`), which Liam should choose.
- **How to watch the first real round 2**: run `--serve --auto` with the default interval, read `_scratch/jobs_auto.log` and
  `claude agents --json`, and check that the reviewer writes `## Round 2` at the top and sets the right status.
- **Tick cost**: every tick fetches every `job/*` branch on origin (22 today, most of them merged). Pruning merged job branches,
  or skipping branches whose main row is `done`, would make ticks faster.
- **`test_pc_deploy` fails while the game is running.** Those tests could stub the "is the game running" check so `wsc gates`
  passes on the PC with the game open. That belongs in a separate job.
