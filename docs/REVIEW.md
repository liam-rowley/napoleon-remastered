# Reviewing a job branch

Every job branch gets an independent review before Liam merges it. The reviewer is a fresh chat that did not build the branch
(Opus is allowed: D15 names independent checks). It starts cold from this file, the job prompt and the job's report.

## Starting a review
Liam says "review the next job" (or "review J<n>"). `python3 core/wsc.py jobs review` names the branch. You must not have built it:
CI's `policy` check refuses a review written by a session that also wrote the report. The job's own brief is
`jobs/<id>/brief.md` on that branch: it is what you check the work against, so nothing needs pasting.

## Setup
A **new** Claude Code session (never the one that built the branch), in the napoleon-remastered folder: `git fetch`, check out the
job branch, `git submodule update --init`. Follow `CLAUDE.md`. Read, in this order: `jobs/<id>/brief.md`, `jobs/<id>/report.md`, `docs/DECISIONS.md`, then
`git diff --stat main...HEAD`. You did not build this branch: do not trust its report. Budget about 60 tool calls.

## Steps
1. **Run the machines first.** `python3 core/wsc.py gates`, plus any build or host tests the branch adds. Note failures. Do not
   spend calls re-checking anything a gate covers.
2. **Claims against evidence.** Every claim in the report needs evidence you can open: a run report, a log, test output, a
   registry row with a date and run id. A claim with no evidence is a finding, however plausible.
3. **The brief.** Every deliverable present, every stated decision followed, kill criteria respected, nothing outside scope (D14).
   A deviation is fine only if the report names it and says why.
4. **Risk-first reading.** Pick the code where a mistake costs most (anything touching engine memory, the PC, install or
   uninstall, persistent data), say what you picked and why, and read it in depth. Skim the rest.
5. **Empire repeats.** Anything left as prose (a timing, a trap, a rule) that could be a default, a guard or a gate is a finding.

## Output
A verdict line, exactly `**Verdict: merge.**`, `**Verdict: merge after fixes.**` or `**Verdict: do not merge.**` (CI's `policy`
check reads it: only `merge` lets the branch merge), and findings ranked **blocker**, **should-fix**, **later**, each with
`file:line`, what fails, and how to see it fail.

- Fix small should-fix items yourself on the branch: one commit each, with a test where the code allows, listed in the review.
- Leave blockers and larger items as findings for the job chat.
- **Later** items for the core go to warscape-core `docs/BACKLOG.md` through a warscape-core PR; for this repo, into the review.
- Write the review as `jobs/<id>/review.md` on the branch, dated at the top (`wsc jobs check` checks the date and the verdict line). With a `merge` verdict, set the row to
  `status=done review=jobs/<id>/review.md` (`CLAUDE.md` Jobs); otherwise leave it at `review` and say what must change.

## Keeping this file useful
When a review finds something a gate could have caught, the fix is a new gate (in warscape-core if it is game-agnostic), not a
longer checklist here.
