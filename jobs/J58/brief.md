# J58: Rule 79: a core pin bump that leaves the DLL and harness unchanged needs no acceptance run

Phase 1, tooling. From J55's open question 1 (`jobs/J55/report.md` on `job/J55`, draft PR 100). Liam chose this on 2026-11-01 instead
of running 20 PC acceptance passes for J55. Rule 79 (`tools/pr_policy.py` `acceptance_problems`) counts any change to the `core`
gitlink as DLL or harness code (since J12). So every pin bump needs 20 acceptance passes on the PC, even when the new tag changes
only the core's Python, tests and docs. J55 bumps `v0.5.0` to `v0.6.0`: the core's `proxy/`, `harness/` and `saves/` are
byte-identical between the two tags, and the DLL build id is unchanged (`f3e33f228416`), yet `pr_policy.py` refuses the branch.
Target: such a bump passes rule 79 with no passes; a bump that changes the core's proxy or harness is judged exactly as today.
J55 merges after this job.

Model: Sonnet. Python in this repo (`tools/pr_policy.py`, `.github/workflows/policy.yml`, tests); no core change, no PC, no DLL.
Budget about 60 tool calls; at the cap, stop, commit, report what is left. Subagents are not needed.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J58`). Read `tools/pr_policy.py` in full (docstring rule 79, `acc_exempt`,
  `acceptance_active`, `acceptance_problems`, `dll_build_id`, `show`, `main`), `tests/test_pr_policy.py` (the rule 79 tests and
  the `PolicyOnGit` fixture), `.github/workflows/policy.yml` (how CI checks out the core) and `core/proxy/tools/build_id.py`
  (`INPUTS`: the DLL inputs, and how it reads paths inside the submodule at a gitlink).
- The history of the rule: `jobs/J4/review.md` (rounds 1, 2, 6, 7), `jobs/J44/review.md` (foreign passes) and `jobs/J12/report.md`
  (why the pin counts at all: since J12 the proxy and the harness live in the core).

## Target facts
Check each again before relying on it:
- `acceptance_problems` has `code = [p for p in changed if (p.startswith(('proxy/', 'harness/')) or p == 'core') and not acc_exempt(p)]`:
  `core` here is the gitlink path, so any pin move counts.
- On `job/J55`, `python3 tools/pr_policy.py --branch job/J55 --base origin/main` prints `rule 79: this branch changes core but ...
  0 consecutive acceptance passes on build f3e33f228416` (2026-11-01). `git -C core diff --stat v0.5.0 v0.6.0` lists only
  `README.md`, `VERSION`, `docs/`, `registries/tools.*`, `tests/test_storage.py` and `warscape/`.
- `policy.yml` checks out with `fetch-depth: 0` and `submodules: true`. Whether the core's commit at the BASE's pin is present in that
  checkout is not known: find out. Core backlog B12 records that a shallow submodule fetch may lack the pinned tag.

## Decisions already made for this job
- **A pin change counts for rule 79 only when the core's own tree changed in rule-79 paths between the two pins.** Read the base's
  gitlink and the head's gitlink (`git rev-parse <ref>:core`), list `git -C core diff --name-only <base pin> <head pin>`, and count
  the change when any listed path starts with `proxy/` or `harness/` and is not `acc_exempt`. That is the rule this repo already
  applies to its own `proxy/` and `harness/`, and it covers every `build_id.py` input in the core (`proxy/src`, `proxy/tools/*`).
  Do not restate `INPUTS` in `pr_policy.py`. A `core/saves/` change does not count, as `saves/` does not count in this repo.
- **Fail closed.** When either pin cannot be read, or the core diff cannot be computed (a missing commit, no submodule), the pin
  change counts as today, and the error says why ("cannot compare core pins <a>..<b>: ...") and how to fix it. Never skip.
- **CI must be able to compare.** If the policy job's submodule checkout lacks the base pin, add a step that fetches it (as
  `gates.yml` fetches the pinned tag for B12), so a real pin bump is judged on the diff, not by fail-closed.
- **Unchanged:** a branch that also changes this repo's `proxy/` or `harness/` is judged as today; the 20-pass streak rules, the
  foreign-pass rule (J44), the evidence rule and `acceptance_active` (the base's checker decides whether the rule is on) are untouched.
  The rule-79 paragraph of the `pr_policy.py` docstring says what a pin change now needs.
- Tests in `tests/test_pr_policy.py` on a real fixture: a game repo with a core submodule, two core commits.
  - A pin bump whose core diff is docs and `warscape/` only passes with an empty ledger.
  - A bump that changes the core's `proxy/src/...` or `harness/...` is refused without 20 passes.
  - A bump whose base pin is not in the submodule fails closed, with the message.
  - `acc_exempt` paths inside the core (a `runs/` folder, a `README.md`) do not count.

## Deliverables
1. `tools/pr_policy.py`: the pin-diff rule above, its docstring, and the fail-closed error.
2. `.github/workflows/policy.yml`: the base pin is fetchable in CI (only if it is not already; say which in the report).
3. The tests above, plus the existing rule 79 tests unchanged and green.
4. Evidence on the real case: on a local checkout of `job/J55` with this job's `pr_policy.py`, rule 79 no longer refuses (the
   remaining refusals are J55's own: no review, row not `done`). Do not commit to `job/J55`; quote the output in the report.
5. `python3 core/wsc.py gates` green.

## Kill criteria
- The base pin cannot be made available to CI's policy job without a token or a change to branch protection: stop and ask Liam
  (fail-closed stays the behaviour; do not weaken it).
- A test shows the rule can be switched off by the branch under review: stop and ask before going on.
- Over about 60 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J58/report.md`: what was built, the J55 evidence, whether `policy.yml` changed and why, the test list and the gates
result, deviations from this brief and why, open questions. Then `wsc reg set jobs J58 status=review report=jobs/J58/report.md`.
