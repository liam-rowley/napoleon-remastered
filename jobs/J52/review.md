# J52 review

## Round 1 (2026-10-31, branch job/J52 at 1eefcf9)

**Verdict: merge after fixes.**

Reviewer: a fresh Claude Code session on Liam's PC (not the builder: builder session 7c221f81, this one ecebdd8b).

### Machines
- `wsc gates`: 11 ok, 1 warn (hooks path). One earlier run had 8 errors, all in `tests/test_pc_deploy.py`
  (`refusing: tasklist: Napoleon.exe is running`); the game was open on the PC. The next run passed all 357 host tests. This is
  environmental and not caused by this branch (the report says the same).
- `tests.test_jobs` + `tests.test_pr_policy`: 83 ok.
- `pr_policy.py --branch job/J52 --base origin/main`: refused only for the missing review and the row not being `done`, as expected
  before a review.

### Claims against evidence
- Dry-run log lines: they match `_scratch/jobs_auto.log` on the PC (13:05:46, 13:06:09, 13:13:23 UTC), including the
  `J52-review: dry run, would start` line.
- `claude agents --json` finding: recorded with its date and version in the report and the `jobs.py` docstring. Name reuse is
  explicitly unproven, which the brief allows (the kill criterion needs a refusal).
- `LEGACY_REVIEWS` equals the `review.md` set at 39eab5e: a test proves it. CI checks out with `fetch-depth: 0`, so the commit exists there.
- Every brief deliverable is present. The deviations are named and argued, and live = `working` or `blocked` is the right call.

### Risk-first reading
I read in depth `JobServer.start`, `auto_tick` and `run_auto`, plus the new `not_ready`. That code starts paid sessions
unattended with no count cap (D34), so a mistake there costs most. The round parser, the status agreement rule and the view
changes were skimmed and read correctly.

### Findings

**blocker**
1. **The autopilot relaunches a session that ended without changing the row, every tick, forever.** `tools/verbs/jobs.py:797-803`
   (`auto_tick`) with `start()` (`LIVE_STATES`, `jobs.py:259`). The only guard is a live `J<n>-*` session. Here is how it plays out.
   A reviewer or fixer runs and ends (`state: "done"`) without pushing a new row. That happens when it crashes, runs out of budget,
   refuses, or hits a `jobs review` refusal (finding 2). The branch row still says `review` (or `fix`), so the next tick starts
   another session, and so on every `--interval` (5 min). That is about 288 sessions a day for one stuck job, with nobody watching.
   How to see it fail: using `tests/test_jobs.py` `Autopilot.make`, pass a `J4` row with `status='review'` and
   `agents=lambda: [{'name': 'J4-review', 'state': 'done'}]`, then call `auto_tick()` three times. `launched` comes out as
   `['J4-review', 'J4-review', 'J4-review']` (reproduced in this review).
   Fix: start each (job, action) at most once per branch head. Remember the `origin/job/<id>` sha the launch was made against, in
   process. Skip with one log line ("started at <sha>, waiting for a push") until the branch moves. Add a test that the stuck case
   launches once over three ticks, and launches again after the sha changes.

**should-fix**
2. **The round cap is not part of the one readiness rule.** `not_ready` (`jobs.py:239-247`) says `review` is ready whenever the
   branch row says `review`, even when `review.md` already has 3 rounds. It says `fix` is ready even when `review.md` has no round.
   `jobs review` and `jobs fix` refuse those cases afterwards (`jobs.py:1001-1010`). So the view's buttons and the autopilot offer
   and start a session that refuses at once, and with finding 1 that becomes a loop. The brief says readiness stays "one rule used by
   `jobs review`, the new `jobs fix`, the view's buttons, the server and the loop".
   How to see it fail: set a branch row to `review` with a 3-round `review.md`. `not_ready('review', ...)` returns None, while
   `jobs review --id` exits 1.
   Fix: carry the round count from `branch_rows` (or read it in `not_ready` through a seam), and move both refusals into `not_ready`.

**later**
3. **Overlapping fetches.** A page GET and an autopilot tick both run `branch_rows`, which does a `git fetch` of every job branch into
   the same refs (`jobs.py` `branch_rows`). When they overlap they can contend for ref locks. That fails closed (the tick is skipped,
   or the page errors), so it is not dangerous. Combined with the 23 s tick the report measured, it is worth one shared, cached
   snapshot per tick, and skipping branches whose main row is `done`.
4. **`test_pc_deploy` errors while Napoleon.exe is running.** It makes `wsc gates` red on the PC whenever the game is open. The report
   already proposes a separate job: stub the running-game check in those tests.

No should-fix item was small enough to fix in the review itself. Both findings above go to the fix session.
