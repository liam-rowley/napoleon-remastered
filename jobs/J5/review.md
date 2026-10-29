# Review of J5: determinism audit (rules into gates)

2026-10-29, fresh chat (Opus, independent check, D15), session `012gysszWeUvYf1aEhEA2hyD`; the builder was `012gyst1s64uQU2S7kPetFHf`.
Reviewed `job/J5` @ `37b3c91` and warscape-core PR #2 (`napoleon-j5` @ `e0fbb0c`), against `jobs/J5/brief.md`.

**Verdict: merge.**

No blockers. Two small should-fix items fixed on the branch (below). warscape-core PR #2 is sound and can merge on its own; it does not
gate this branch, which still pins core `v0.1.0` (J17 moves the pin after Liam tags `v0.2.0`, lower-case).

## Evidence checked
- `wsc gates` on `job/J5` @ `37b3c91`: 11 ok, 0 warn, 0 failed, 53 host tests. After the review fixes: 11 ok, 54 host tests.
- `wsc jobs check`: 16 rows ok. `jobs review` named J5; `jobs next` names J6 (brief), as the report says.
- CI run 40871518126 on `77176d3`: `gates`, `proxy`, `harness-windows` success (GitHub API, 2026-10-29). The run on `37b3c91`
  (report-only commit) was still in progress when checked.
- `pr_policy.py --branch job/J5` before this review: refused for the missing review and `done` row only, as expected.
- Session trailers: every builder commit carries `session_012gyst1s64uQU2S7kPetFHf`; the `git log --format=%(trailers:...)`
  query in `pr_policy.main` returns it for `jobs/J5/report.md` on this branch, so the builder/reviewer check works on real history.
- Depends-on ids: the ledger says row 102 is enforced by the schema's `x-ref`; confirmed by editing J5's `depends_on` to `J99`:
  the `registries` gate fails with `depends_on 'J99' is not an id in jobs`.
- Ledger counts recomputed from the table: before E36 CN25 CL22 J37, after E53 R4 CN6 CL23 J34, 120 rows: match the report.
- warscape-core PR #2: open, not merged; `wsc gates` on its head: 11 ok, 1 warn (`hooks`, this clone unwired: the new gate firing
  as designed), 69 host tests. Every core `git` subprocess now passes `env=git_env()` (grep of `warscape/`). Only tag on core is `V0.1.0`.

## Risk-first reading
Picked `tools/pr_policy.py` (it decides what reaches `main`) and `tools/verbs/jobs.py` (it now decides what every chat builds or
reviews), read in full; the core `core_pin`/`hooks`/`git_env` diff in full. Skimmed the prose changes, `tests/test_repo_rules.py`
and the ledger.

## Findings

### Should-fix (fixed on the branch)
1. `.gitignore:21-24`: `tests/test_repo_rules.py:77` bans tracked `*.dmp`, but `.gitignore` refused only `*.dll`/`*.exe`/`*.pdb`, so
   a crash dump in the tree shows as untracked and is one `git add .` from failing the test. Fixed in `8204079`.
2. Brief deliverable 3 (a `needs_brief` row or a note on the existing row for each codeable-later item) was met only for J17/J18;
   the other owners (J4 rows 28, 74-79; J11, J12, J13 ...) exist only in `jobs/J5/rules.md`, and J4 is still `needs_brief`, so its
   brief writer would not see them (`jobs next` pointed at the row, PLAN and dependency reports only). Not named as a deviation.
   Fixed as code, not prose: `jobs next` now lists every codeable-later ledger row naming the job it hands out
   (`tools/verbs/jobs.py` `waiting_rules`, test `tests/test_jobs.py` `Ledger`). See it: `jobs.waiting_rules(rules.md, 'J4')`
   returns rows 28, 74, 75, 77, 78, 79.

### Later
3. `tools/pr_policy.py:115-119`: the builder/reviewer check compares `Claude-Session:` trailers only, so a review commit without a
   trailer passes silently. It catches honest mistakes, not evasion; fine for now. See it: commit `review.md` from the builder chat
   with no trailer, `pr_policy.py --branch job/Jn` is ok. A stronger rule (review commits must carry a trailer, or Liam's sign-off)
   belongs with the core PR policy (core B8).
4. `tools/pr_policy.py:156-157`: job rows are compared at the merge base but `DECISIONS.md` at the base tip, so a branch that adds a
   decision after `main` gained one is refused as "rows changed, moved or removed" instead of "rebase first". Right outcome, wrong
   message; fix when it moves to the core (B8).
5. `tests/test_repo_rules.py:58`: any decision row that mentions `` `tests` `` in backticks clears `[gates] skip = ["tests"]`. The
   match should require the row to name `wsc.toml` and the section. Weak but not wrong today (no skips exist).
6. warscape-core PR #2 `warscape/gates.py` `pin_problems`: `if version != want[1:] if want[:1] == 'v' else version != want:` is
   correct but reads as a precedence bug; parenthesise when next touched. After merging PR #2, core `main` passes `core_pin`
   only while `HEAD` carries no upper-case tag: tag the merge `v0.2.0`.
7. Remote `job/J3` still exists although J3 is `done` on `main`; `jobs review` handles it, but it is noise in every listing. Delete it.
8. Report finding 3 stands: branch protection (D21 required checks) could not be read from a session; Liam should confirm `gates`
   and `policy` are required on `main`.

## Brief compliance
All four deliverables present (ledger dated with before/after counts; codeable-now fixes one commit each, except the one named
two-in-one; core PR #2; planning PR #18 with J17/J18; prose with one owner per rule). Kill criteria respected: the new `core_pin`
fails on core `main` at `V0.1.0` and was left failing there, not weakened. Nothing touched the PC. Deviations are named with reasons;
the only unnamed one is finding 2, now fixed. D29 is an agent row "for Liam's review", the same pattern as D26/D27; merging takes it.
