# Napoleon: Total War Remastered: rules for every chat and agent

**The repo is the single source of truth.** If it isn't in the repo, the next chat can't see it and it doesn't exist.

## Before you start
1. `git pull`. Read `README.md`, `docs/DECISIONS.md`, and the plan doc for your area (`docs/plans/`).
2. Look things up before rediscovering them: the registries (tools, scenarios, assets, UI elements, engine sites, config keys,
   hotkeys, engine facts) once they exist (`docs/plans/PLAN.md` section 3). Until then, `empire-remastered` holds the evidence:
   `docs/learnings/` and `docs/plans/PIPELINE_V2.md`. Napoleon is the same engine lineage, but every Empire fact about the exe,
   shaders or Lua API is checked again on Napoleon before it is relied on.

## The core (`core/`, warscape-core pinned at a tag)
- Clone with `git clone --recurse-submodules` (or `git submodule update --init` after a plain clone); set the hook once per clone:
  `git config core.hooksPath core/.githooks` (from core v0.2 the `hooks` gate warns until you do). Agent sessions attach `liam-rowley/warscape-core` too (read is enough here).
- Everything goes through `python3 core/wsc.py <verb>`: `find <words>` searches every registry, `reg add|set|render` changes them,
  `gates` runs the checks CI runs (`--fast` is what the pre-push hook runs). Never edit a generated `registries/*.md` view.
- **Never change files inside `core/`.** A change the game needs goes to warscape-core as a PR and arrives with a new tag
  (`core/docs/CONSUMING.md`); the `core_pin` gate fails on local edits.

## Jobs (D16, D21): what Liam means by "pick up the next job" and "review the next job"
- The queue is the `jobs` registry (`registries/jobs.jsonl`; status page: the generated `registries/jobs.md`). Each job has a folder
  `jobs/<id>/` with `brief.md` (the full prompt), then `report.md` and `review.md`. A job in progress is a remote branch `job/<id>`.
  `wsc jobs check` (run by the `tests` gate) enforces the statuses, their files and the brief shape (`tools/verbs/jobs.py`).
- **"Pick up the next job":** `git pull`, then `python3 core/wsc.py jobs next`. It names the job and its steps, or the brief to write
  (on `brief/<id>`, then stop for Liam's merge), or what every open job is waiting for. Say which job you took.
- **"Review the next job":** `python3 core/wsc.py jobs review` names the branch; follow `docs/REVIEW.md` on it.
- Never mark your own job `done`, and never review a job you built (CI's `policy` check refuses a review written by a session that
  wrote the report).
- **All work goes through the queue (D21).** The branch name decides what a pull request may change; the kinds and their files are
  the docstring of `tools/pr_policy.py`, which CI's `policy` check runs (run it locally before opening a pull request). Work Liam asks
  for that isn't in the queue becomes a `needs_brief` row on a `plan/` branch first. Reviewer fixes go on the job branch itself.

## While you work
- Work on a branch; commit and push after every meaningful step. `main` changes only by a merge Liam (or the orchestrator, once
  there is one) approves, after an independent review (`docs/REVIEW.md`). End every job with a report: what was built, evidence
  (run ids), deviations from the brief and why, open questions.
- **A learning becomes code first.** When something bites (a timing, a trap, a wrong default), fix it in the tool, its default, a
  guard or a gate so the next agent cannot hit it. Write prose only when it cannot be coded, and then into the doc that owns the topic.
- **Exe stays vanilla on disk** (D2). Runtime patches and detours go in the proxy DLL, every engine address in the engine-sites
  registry with its anchor bytes, behind the exe-identity guard.
- **The PC game folder is a deploy target.** Change the repo, then sync with a sha-checked copy. Experiments on the PC live under a
  `_scratch\<you>\` folder; anything worth keeping comes back to the repo. Never run git in the game folder.
- **Reuse before you write.** Search the tools registry first; extend an existing tool or CLI verb rather than adding a near-duplicate.
  Every tool has a header and a registry row (`tools` gate; header format: `core/warscape/tools.py`).
- **"Verified" carries a date and a run id** (`verified_dates` gate for docs; structured fields in registries).
- **One owner per topic.** When a fact changes, grep for the old claim and fix every living copy. Keep docs short: link, don't copy.
- Windows-safe names only: the `windows_paths` gate is the rule.
- Never edit generated copies: the claude.ai Project docs, review pages and anything a generator writes. Change the source and regenerate.

## Usage (D15)
Sonnet medium by default; Opus only with a reason in the brief (reverse engineering, shaders, DLL, crashes, independent checks);
at most 2 agents at once; every job brief states a call budget and a kill criterion; waiting and polling belong to the harness, not
to an agent making repeated calls.
