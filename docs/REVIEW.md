# Reviewing a job branch: napoleon's addendum

The procedure is warscape-core's, owned by `core/docs/REVIEW.md` (J62 moved it there with the job pipeline): setup, the rounds (D36), the steps, the
output format, the row after a verdict and the merge order (ready before the push: J57). Read that first, then this page, which only adds what is
this game's. Every `wsc ...` below is `python3 core/wsc.py ...`; the job steps (`wsc jobs next|review|fix`) print the exact commands.

## What this repo adds
- **Who reviews.** A fresh chat that did not build the branch; Opus is allowed (D15 names independent checks). The own-review rule reads the
  `Claude-Session` commit trailer (`wsc.toml` `[policy] session_trailer`); the hook in `.claude/settings.json` adds the flag check to every commit.
- **The machines (step 1).** `python3 core/wsc.py gates` and `python3 core/wsc.py policy --branch job/<id> --base origin/main` (the `policy` check CI runs).
  The required checks on `main` are `gates`, `proxy`, `harness-windows` and `policy`; `proxy` and `harness-windows` are skipped, which counts as passed,
  when the branch does not touch their inputs or the same input tree already passed (`wsc.toml` `[ci] inputs`, `.github/workflows/gates.yml` job `changes`).
  A red required check is a blocker for a `merge` verdict (`docs/CI_FAILURES.md` classes the failures).
- **Rule 79 (J4, J44, J45, J58).** A branch that changes `proxy/` or `harness/`, or moves the core pin so that the core's own `proxy/` or `harness/` changes,
  must carry 20 consecutive acceptance passes on its final DLL build id and watcher version (`harness/acceptance/ledger.jsonl`, `tools/gates/pipeline.py`
  `policy_rule`). Check that the passes name a run and an evidence file committed on the branch; a reword, rebase or merge of `main` that leaves the DLL
  inputs unchanged keeps them. Rule 79 runs for every branch kind (J73), so a `meta/` or `brief/` branch meets it too. A core pin bump is therefore a `job/`
  branch, never `meta/` or `plan/` (`core` is in neither glob list), and meets rule 79 whenever the core's own `proxy/` or `harness/` changed between the
  two pins; a registry edit outside `registries/jobs/*` is a `job/` branch as well.
- **Empire repeats (step 5).** Anything left as prose that Empire's history shows biting twice (a timing, a trap, a wrong default) and that could be a
  default, a guard or a gate is a finding. A *later* item for the core goes to warscape-core `docs/BACKLOG.md` through a warscape-core pull request.
- **Merging.** Liam merges and tags warscape-core; a job branch is merged by its reviewer on green CI (D32); `plan/` and `meta/` branches by Liam.
  If a merge changes a rule that other open job branches must meet (J20's trailer rule stranded `job/J19`), say so in the review and in your reply.
