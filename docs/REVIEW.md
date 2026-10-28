# Reviewing a job branch

Every job branch gets an independent review before Liam merges it. The reviewer is a fresh chat that did not build the branch
(Opus is allowed: D15 names independent checks). It starts cold from this file, the job prompt and the job's report.

## Starting a review (the prompt Liam pastes)

```
Independent review of branch <branch> in liam-rowley/napoleon-remastered (job: <job name>).
Follow docs/REVIEW.md. Budget about 60 tool calls.
Job prompt:
<paste the job prompt>
```

## Setup
Attach (push) and clone napoleon-remastered with `--recurse-submodules`, check out the branch, attach warscape-core (read).
Follow `CLAUDE.md`. Read, in this order: the job prompt, the job's report, `docs/DECISIONS.md`, then `git diff --stat main...HEAD`.
You did not build this branch: do not trust its report.

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
A verdict (`merge`, `merge after fixes`, `do not merge`) and findings ranked **blocker**, **should-fix**, **later**, each with
`file:line`, what fails, and how to see it fail.

- Fix small should-fix items yourself on the branch: one commit each, with a test where the code allows, listed in the review.
- Leave blockers and larger items as findings for the job chat.
- **Later** items for the core go to warscape-core `docs/BACKLOG.md` through a warscape-core PR; for this repo, into the review.
- Write the review as `reviews/<YYYY-MM-DD>_<branch-slug>.md` on the branch (a dated record: exempt from the doc size cap).

## Keeping this file useful
When a review finds something a gate could have caught, the fix is a new gate (in warscape-core if it is game-agnostic), not a
longer checklist here.
