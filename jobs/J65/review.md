## Round 1 (2026-11-02, branch job/J65 at 6fe2701)

**Verdict: merge.**

Checked against the brief by a fresh session (not the builder's).

- **Machines.** CI on 6fe2701: all 8 checks passed or skipped. Local `wsc gates`: 13 ok, 1 failed: `test_job_sh.JobSh.test_ctl_without_an_ini_uses_the_registered_default`,
  a file this branch does not touch; the run happened with a game running on the PC (Napoleon.exe; install tests skipped), as the report says. CI is green, so it is not a blocker.
  Local `policy` refused only for the missing review and the row not yet `done`, which this review and the row fix.
- **Patterns.** `deployment_end` and `player_stats` are out of their STATIC_ONLY patterns (`discovery/core/ui_atlas.py`). The regenerated `reach.json` differs from main in exactly
  those two units (both `reached`, run `20261102_j10pc`, with state, live path and agreement) plus the totals: 42 to 44 reached, 1,549/1,556 to 1,597/1,610. This matches the J10 report.
  `summary.json`, the README and the two `ui_elements.jsonl` rows moved with them; no unit id or `used_by` changed.
- **Guard.** `live()` now does the name match first and raises `StaticOnlyConflict` (unit, pattern, reason, live path, state, agreement) on a top-level own-name match at agreement 0.75 or more;
  a nested match keeps the pattern. Two new tests in `Live` cover both cases. The guard ran over all 220 units without raising, so no other pattern conflicts with the run (the kill criterion did not fire).
- **Deviation.** The top-level condition (no `/` in the live path) is named in the report and is needed to keep `password_entry` correct. Acceptable.

### Later (not needed to merge)
- The top-level rule misses an over-broad pattern whose live match is nested under the unit's own container (the report's open question). None exists today.
- `discovery ui` writes empty `reach.json` and `art_keys.json` without an error when `extract/napoleon` is missing (any worktree). It should fail loudly: a future job.
- I did not rerun `discovery ui` (no extract in this worktree); the sha256 claim rests on the committed output and the builder's and orchestrator's reruns.
