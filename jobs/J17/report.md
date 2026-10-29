# J17 report: core pin bump to v0.2.0

## What was built
- `core` gitlink moved from `v0.1.0` to `v0.2.0` (warscape-core tag commit `bbdf375`, `core/VERSION` = `0.2.0`) and `wsc.toml`
  `[core] version = "v0.2.0"`, in one commit ("J17: pin warscape-core v0.2.0").
- `CLAUDE.md`, "The core": dropped "from the next core tag" from the `hooks` sentence; the rest unchanged.
- `docs/DECISIONS.md` D20 left as is, per the brief. No other files, registry rows or `core/` contents touched.

## Evidence
Full gates run, 2026-10-29T14:11:09Z, branch `job/J17`, core at `bbdf375` (`v0.2.0`), `core.hooksPath` set:

```
ok   schemas           9 schemas within the supported subset  (0.0 s)
ok   registries        9 registries, 116 rows, all valid and rendered  (0.0 s)
ok   tools             38 tools, each with a header and a matching row  (0.0 s)
ok   json              51 .json/.jsonl files parse strictly  (0.0 s)
ok   windows_paths     306 paths Windows-safe  (0.0 s)
ok   doc_size          24 living docs under 30 KB  (0.0 s)
ok   verified_dates    24 living docs: every "verified" carries a date or run id  (0.0 s)
ok   conflict_markers  no conflict markers  (0.0 s)
ok   eol               .gitattributes present; no CR in indexed .py/.sh  (0.0 s)
ok   core_pin          core 0.2.0 as pinned (tag v0.2.0), unmodified  (0.0 s)
ok   hooks             pre-push hook wired (core/.githooks)  (0.0 s)
ok   tests             54 host tests passed (tests)  (15.5 s)
gates: 12 ok, 0 warn, 0 failed in 15.6 s (napoleon-remastered)
```

The pre-push hook (`gates --fast`) also ran on both pushes: 11 ok, 0 warn, 0 failed.

`python3 tools/pr_policy.py --branch job/J17` before this report and the review existed (expected refusal, not worked around):

```
policy: jobs/J17/report.md is missing: every job ends with a report
policy: jobs/J17/review.md is missing or has no "Verdict:" line: every job is reviewed before merge (docs/REVIEW.md)
policy: row J17 must be `done` on the branch (the reviewer sets it with a merge verdict)
policy: job/J17: REFUSED (3 files changed)
```

The reviewer reruns it once `review.md` exists and the row is `done`.

## Deviations from the brief, and why
- Model: run by an Opus session (Liam asked for J17 by name in a session already on Opus), not Sonnet medium. The work is
  mechanical; the call budget (~15 of 25) was kept.
- `warscape-core` was not attached with `add_repo`: it is public, so the tag fetch worked through the git proxy without it.
- `wsc jobs next` named J6, not J17; J17 was taken because Liam asked for it by id (queued, its dependency J5 is `done`).

## Open questions
- J12's row still says "cut v0.2.0 (fix the V0.1.0 tag case first)". `v0.2.0` is now taken by J5's release, so J12 has to cut
  `v0.3.0` (or later). Fixing that row is a `plan/` change, outside this job.
