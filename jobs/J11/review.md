## Round 1 (2026-11-02, branch job/J11 at 9147875)

**Verdict: merge.**

Checked: `python3 core/wsc.py gates` (10 ok, 2 warn = skipped numpy/capstone/wasm tests, 0 failed), `wsc discovery gate` (exit 0, 12 ok, 1 warn "install not compared", findings table as in the report), `wsc jobs check` (67 rows, 0 registry gaps), `tools/pr_policy.py` (refuses only for the missing review and row, fixed by this commit), CI on 9147875 green. Legacy set recomputed: `git ls-tree c674fb1` has 52 briefs, matching `LEGACY_BRIEFS` (the brief said 48; the report's 52 is right); J24 and J37 are the declared `LATE_LEGACY`.

Risk-first reading: `discovery/core/briefpaths.py` (it decides whether every future brief is accepted) read in full; the `tools/verbs/jobs.py` hook skimmed. No game, PC, `core/`, `proxy/` or `harness/` files touched (rule 79 not applicable). Deviations 1 to 10 are named with reasons in the report and are reasonable.

### Blockers
None.

### Should-fix
None.

### Later
- `briefpaths.py:196-199`: everything between `## Registry gaps` and the next heading is skipped, including non-bullet prose, so a found path written as a sentence there is not checked. Only bullets should be exempt, and only for their own `path:` field.
- The four open facts now say "Owner: liam" (report Q9) and `config_keys` owner `proxy` (Q7): Liam decides; neither blocks.
- The first PC sitting should run `wsc discovery gate --install` once and record the result (not run against the real game here, as the report says).
- Only J66 among queued briefs would fail the rule (`ui\templates\uied.templates` should be `ui/templates/uied.templates`); its builder applies the one-line fix.
