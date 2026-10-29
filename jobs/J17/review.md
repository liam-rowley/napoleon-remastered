# J17 review: core pin bump to v0.2.0

Date: 2026-10-29. Reviewer: an independent Opus session (did not build the branch). Branch `job/J17` at `5d63863`.

**Verdict: merge.**

## What I checked
- **Gates, full run** (2026-10-29, core at `bbdf375`, `core.hooksPath` set): 12 ok, 0 warn, 0 failed; `core_pin` "core 0.2.0 as
  pinned (tag v0.2.0), unmodified", `tests` 54 host tests passed. `wsc jobs check`: 19 rows, ok. The report's run said 306 paths and
  24 living docs; mine says 307 and 25: the difference is `jobs/J17/report.md`, committed after the builder's run.
- **CI**, run 40889085698 on `5d63863`: `gates` and `proxy` passed; `harness-windows` still running when this was written (it has
  the known J19 flake; this branch changes no harness code).
- **The pin against the remote**: `git ls-remote --tags` on warscape-core gives `v0.2.0` -> `bbdf37519ca7` (lightweight tag),
  which is exactly the new gitlink; `core/VERSION` is `0.2.0`; `wsc.toml` `[core] version = "v0.2.0"`. No tag was moved or
  created (`V0.1.0` still on `d5275c2`).
- **Deliverable 1**: gitlink and `wsc.toml` in one commit (`e6088e2`, 2 files), per `core/docs/CONSUMING.md` "Game upgrade".
- **Deliverable 2**: `CLAUDE.md` loses only "from the next core tag". The remaining claim is true at v0.2.0: with
  `core.hooksPath` unset, `gates --fast` gives `WARN hooks pre-push hook not wired`.
- **Deliverable 3**: gates output pasted with a timestamp; the pre-review `pr_policy` refusal is shown and was not worked around.
  Rerun after this review: see below.
- **Deliverable 4 / scope**: `docs/DECISIONS.md` untouched; no files inside `core/` changed (`core_pin` "unmodified"); the only
  registry change is the J17 row. No other stale `v0.1.0` or "next core tag" wording in living docs (grep outside `core/` and
  `jobs/`; D20's "v0.1.0 first" stays, as the brief says).
- **Deviations**: all three are named with reasons (Opus instead of Sonnet at Liam's request, ~15 of 25 calls; warscape-core
  read through the public proxy instead of `add_repo`; taken by id rather than via `jobs next`). None affects the result.

Risk-first reading: nothing here touches engine memory, the PC or persistent data. The one thing that could cost is a gitlink
pointing at a commit that is not the tag (CI and every fresh clone would check out the wrong core), so I checked the sha against
the remote tag directly rather than trusting `core_pin` alone. It matches.

## Findings

### Blocker
None.

### Should-fix
None.

### Later
- `registries/jobs.jsonl:4` (J12): the description still says "cut v0.2.0 (fix the V0.1.0 tag case first)". `v0.2.0` is taken
  and the case fix is done, so J12 must cut `v0.3.0` or later. A `plan/` change before J12 is briefed (the report raises it too).
- Empire repeat, minor: "commit `core` and `wsc.toml` together" is prose in `core/docs/CONSUMING.md`. `core_pin` checks only the
  tip, so a split pair of commits passes gates. Low value for a two-line upgrade; noted, not filed.
