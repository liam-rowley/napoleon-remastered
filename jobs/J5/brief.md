# J5: determinism audit (rules into gates)

Audit napoleon-remastered and warscape-core for every rule an agent is told to follow in prose, and make each one that a machine
can check or perform into a gate, schema rule, default or verb, so the next agent cannot get it wrong. This is "learnings become
code" (`CLAUDE.md`, PLAN section 1) applied to the rules themselves. The lasting output is gates in CI, not a recurring audit.

Model: Opus, reason: independent check (D15): you are auditing the harness, and you did not write most of it. Budget about 150 tool
calls; at the cap, stop, commit, report what is left. At most 2 subagents, only for independent read-only sweeps.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J5`). Read `docs/DECISIONS.md`, `docs/plans/PLAN.md` and `docs/REVIEW.md`.
- Attach `liam-rowley/warscape-core` with push access and follow its `CLAUDE.md`; read `docs/DECISIONS.md`, `docs/BACKLOG.md`,
  `docs/CONSUMING.md` and `warscape/gates.py`. Game-agnostic fixes land there as a PR on its own branch.
- Start fresh: do not port Empire's `audit_repo.py`. Empire may be read only to confirm a trap really happened.
- Run `python3 core/wsc.py gates` on `main` of both repos first and record the result as the baseline.

## Method
1. **Inventory.** Collect every prescriptive statement (must, never, always, only, every, "set ...", "run ...", numbered procedures)
   from both repos' `CLAUDE.md`, `README.md`, `docs/**`, `jobs/*/brief.md`, tool headers, schema descriptions, workflow comments
   and the `policy` docstring. One row per rule, with its source `file:line`. Merge exact duplicates; keep near-duplicates apart
   and flag them, because a near-duplicate is drift.
2. **Classify** each rule as exactly one of:
   - **enforced**: name the gate, hook, schema rule or CI check, and point to a test with a failing fixture that proves it fires.
     A gate with no failing-fixture test is **codeable**, not enforced.
   - **codeable now**: a check or default can be written today with the standard library (core rule: Python 3.12, no dependencies).
   - **codeable later**: needs something not built yet (core backlog B1 game gates, the J2 watcher, the proxy). Name what it waits for.
   - **judgment**: a machine cannot decide it (for example "link, don't copy"). Give the reason in one line. Partial checks count:
     if a machine can catch the obvious half, that half is codeable.
3. **Prefer removing the rule over checking it.** If a tool can do the step itself (a verb that picks the next job, a generator that
   writes a list, a default that makes the wrong value unreachable), build that and delete the prose. A gate is second best; a
   checklist line is last.
4. **One owner.** Every rule that survives as prose lives in exactly one place; other places link to it. Fix copies that disagree.

## Leads (unverified: check each one, do not trust it)
- Core `CLAUDE.md` says tags are `vX.Y.Z`; the only tag is `V0.1.0`; napoleon pins `v0.1.0`; `core_pin` compares `VERSION` only (B5).
- Job status invariants are prose: `queued` needs an existing brief, `review` a report, `done` a review whose verdict is `merge`,
  and `depends_on` must name real ids. These could be a jobs-registry check, not only `tools/pr_policy.py` on pull requests.
- "Pick up the next job" is a procedure an agent runs by hand; it could be a verb (`wsc jobs next`) that also checks remote branches.
- Brief shape (model with a reason when Opus, call budget, kill criteria, Finish section) is checkable on every `jobs/*/brief.md`.
- "Never review a job you built": the commits on the branch carry `Claude-Session:` trailers, so report and review authorship can be compared.
- Branch rules are written in three places (`CLAUDE.md`, D21, the `pr_policy.py` docstring); the path lists live only in code.
- The D15 usage rules are copied into warscape-core's `CLAUDE.md`; the Windows-name rules differ between the two files (`\`).
- `.gitmodules` points at `../warscape-core.git` while the workflow comment calls the core private and the repo is public; check which is true.

## Rules for the fixes
- Every new gate or check comes with a host test that feeds it a bad fixture and shows it fail, plus a good one that shows it pass.
- Never make a gate pass by adding it to `skip`, loosening an existing gate, or adding an exemption without a dated decision row.
- Game-agnostic checks go in warscape-core (`warscape/gates.py` or a verb), as a PR with host tests and a `docs/BACKLOG.md` or
  `docs/DECISIONS.md` row. You cannot cut the tag: the napoleon pin bump waits for Liam's merge and tag, so add it as a
  `needs_brief` row unless the tag exists before you finish.
- Napoleon-only checks go in `tools/` with a header and a tools-registry row, run from CI, until B1 lets them become game gates.
- Delete or shorten the prose each fix replaces in the same commit, and link to the gate.
- Nothing on the PC: this job never touches the game or AppData folders (`needs_pc` false).

## Deliverables
1. `jobs/J5/rules.md`: the ledger table (rule, source `file:line`, class, enforcing gate and test, or reason), dated, plus a
   count per class before and after this job.
2. The codeable-now fixes, one commit each, gates green on `job/J5`; and the warscape-core PR for the core-side ones.
3. A `needs_brief` row for each codeable-later item that is bigger than this job, or a `depends_on` note on the existing row it
   belongs with (for example J2).
4. The prose cleanup: duplicates removed, near-duplicates reconciled, each surviving rule with one owner.

## Kill criteria
- The inventory passes about 200 rules: stop, classify what you have, and report the sources you did not reach.
- A new gate fails on `main` for something that is not a one-line fix: do not weaken the gate. Leave it failing on the job branch,
  report it as a finding, and stop that thread.
- A fix needs a core change that cannot ship without B1 or B2: record it as codeable later and move on; do not build B1 in this job.

## Finish
Write `jobs/J5/report.md`: the baseline and final gate output (run ids), what was enforced before and is now, the warscape-core PR
link and its state, deviations from this brief and why, every rule left as judgment with its reason, and open questions. Then
`wsc reg set jobs J5 status=review report=jobs/J5/report.md`.
