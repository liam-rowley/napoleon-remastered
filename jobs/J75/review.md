## Round 1 (2026-11-04, branch job/J75 at 090b22e)
Verdict: merge

Reviewer: a fresh session that did not build the branch. The report was written by the orchestrating session from the builder's hand-back, so I checked its claims against the branch.

## What I checked
- **Hook diff** (`tools/jobs_hooks.py`, `git diff origin/main...HEAD`): read in full against Decisions 1-7. `acc_exempt` is `path == ACC_LEDGER`. `streak_problem` and `evidence_problem` give uniqueness, run folder, field agreement, step agreement, pass-number sequence and shas. `ledger_append_problems` and `pass_file_problems` run before the "nothing to count" return. `acc_sha_fields` parses with `ast` and never runs the core. Every removed line is in the report's mapping and each is stricter or equal. No existing assertion was changed (the diff only adds to `tests/test_jobs_hooks.py`).
- **Tests:** `python3 -m unittest tests.test_jobs_hooks tests.test_acceptance tests.test_discovery_gate tests.test_usage_reader tests.test_build_id`: Ran 135, OK (2026-11-04, on this checkout). The red-first claim is credible: the red commit `ad126ea` precedes the hook change `3a4cbc4`.
- **Independent run on the real ledger** (my own script, not the builder's): `collect_acceptance` gives active True, build `cb34c06baf42`, watcher 1.2.0, `sha_fields` None, `runs_diff` empty.
  - Branch `job/J30` with a `proxy/` change: `[]` (the honest 20-pass tail still counts).
  - `baseline.json` only: a rule 79 error, 0 passes.
  - Tail replaced by 20 copies of one line: two errors, append-only and "already counted by pass 21". This is the audit's H3 attack, now refused.
- **Brief claims:** the sha rule is off at the pin (no `LEDGER_SHA_FIELDS`), as reported. The deviations are sensible: fail-closed `runs_diff`, and "shot" in a field name marks a shot sha.
- **CI:** `changes` passed; `gates` was still running at review time; `proxy`, `harness-windows` and `viewer` skipped (inputs untouched). The merge is queued with `--auto`, so it waits for green `gates` and `policy`.

## Findings
None blocking.
- Note (not a defect): the new append-only rule would have refused J30's PR #164 history (ledger "both sides" merge order). The error text already says main's lines go first, and `docs/REVIEW.md` now says it. The report's Open question 1 (a helper to merge ledgers) is a core backlog item for Liam; no change needed here.
- Note: report open question 2 (a deterministic scene gives repeated shot shas) belongs to core W9 when it names the fields; the sha check is off until then.
- Other open job branches that carry passes must keep main's ledger lines first when they merge main. No open branch is stranded today.
