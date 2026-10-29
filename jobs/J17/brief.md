# J17: Core pin bump to v0.2.0

Phase 1, job 17: move napoleon-remastered from warscape-core `v0.1.0` to `v0.2.0` (the release J5's core PR produced: `core_pin`
checks the tag (B5), the `hooks` gate, stdlib-only test). A mechanical upgrade; no game code changes.

Model: Sonnet medium (D15). Budget about 25 tool calls; at the cap, stop, commit, report what is left. No subagents.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J17`). The upgrade recipe is `core/docs/CONSUMING.md`, section "Upgrading and releasing".
- Attach `liam-rowley/warscape-core` (read). `v0.2.0` is tag commit `bbdf375` on warscape-core `main` (merged PR 2).
- Dependency: J5 is `done`; the tag exists (checked 2026-10-29 with `git ls-remote --tags`).

## Facts from the dry run (2026-10-29, briefing session, nothing committed)
With `core` checked out at `v0.2.0` and `[core] version = "v0.2.0"`, `python3 core/wsc.py gates` gave 12 ok, 0 warn, 0 failed:
`core_pin` "core 0.2.0 as pinned (tag v0.2.0), unmodified", `hooks` "pre-push hook wired (core/.githooks)", `tests` 54 host tests passed.
Rerun it yourself; the run is evidence only when your report has its output.

## Deliverables
1. `core` gitlink at `v0.2.0` (`git -C core fetch --tags && git -C core checkout v0.2.0`) and `wsc.toml` `[core] version = "v0.2.0"`,
   committed together in one commit.
2. `CLAUDE.md`, section "The core": drop "from the next core tag" from the `hooks` sentence; the gate now exists. Keep the rest.
3. `python3 core/wsc.py gates` green (full run, not `--fast`), output pasted into the report; `python3 tools/pr_policy.py
   --branch job/J17` run locally once the report and review exist (it will refuse before then: say so, do not work around it).
4. `docs/DECISIONS.md` D20 says "v0.1.0 first": leave it (append only, and it stays true). No new decision row is needed.

## Out of scope
- J12's row says "cut v0.2.0"; that tag is now taken. Fixing J12's row is a `plan/` change, not this job: list it under open questions.
- No edits inside `core/`, no new tools, no other registry rows.

## Kill criteria
- Any gate fails at `v0.2.0` and the fix would need a change inside `core/`: stop, report the failure, propose a warscape-core PR.
- `core_pin` disagrees with the tag (case or sha): stop and report; never move or recreate a tag.

## Finish
Write `jobs/J17/report.md`: what changed, the gates output with date, deviations from this brief and why, open questions.
Then `wsc reg set jobs J17 status=review report=jobs/J17/report.md`.
