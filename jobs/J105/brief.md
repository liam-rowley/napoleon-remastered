# J105: Decisions as one file per row: three meta/ pull requests

Phase 1. `docs/DECISIONS.md` is at the `doc_size` cap, so no decision can be recorded until the rows move to one file each. The core has had that
storage since W43 and J78 brought it into the pin. A pull request is judged with its base's rules, so the move takes three `meta/` pull requests in
order, each cut after the one before it merged. All three are Liam's to merge (D50). Then `job/J105` adds the first two new rows.

Model: Opus, reason: Liam's "Opus across the board" (2026-11-06), the first row this job records. Budget about 80 tool calls over all sessions; sized from
J84 (40) and J76 (90), neither of which records its real count. No subagents. No PC: no launch, no `job.sh`.

No rule 79: no DLL or harness input changes. Nothing here touches `proxy/`, `harness/`, the core pin, the acceptance folder or the UI baseline, and
`wsc.toml`, `registries/decisions/`, `design/` and `tests/test_repo_rules.py` are in none of the `[ci.inputs]` sets. Deliverable 5 proves it.

## Start
- Follow `CLAUDE.md`. If this session's model is not the row's, stop and say so.
- **This job runs in several short sessions, because it waits for Liam between steps.** A session does one step, then stops. No session waits or polls.
- First session: `python3 core/wsc.py jobs next --id J105` claims `job/J105`. Later sessions: that verb refuses once the branch exists, so do not rerun it;
  `git fetch origin job/J105` and check it out. A new worktree has no `core/`: run `git submodule update --init` first.
- Read `jobs/J78/report.md` "## Fix round 1", from "### Decisions as one file per row, corrected" on, and `jobs/J78/review.md` "## Round 2", findings 2 and
  Later item 2. **Do not use the report's older "## Decisions as one file per row" section above them:** its two-pull-request recipe is refused by `policy`.
  Also read `core/docs/CONSUMING_OPTIONS.md` "Decisions as one file per row", which has the same gap, and the docstring of `core/warscape/policy.py`.
- **Find your step from `origin/main`, never from memory:** `git fetch origin main`, then read `wsc.toml` there.

| `wsc.toml` on `origin/main` | This session does |
|---|---|
| `[policy] plan` has no `registries/decisions/*` | Deliverable 1 |
| The glob is there and `[policy] decisions` is still the Markdown path | Deliverable 2 |
| `[policy] decisions_retired` is set | Deliverable 3 |
| `decisions_retired` is gone and `docs/DECISIONS.md` is gone | Deliverable 4, then 5 and Finish |

If the pull request for that step is already open (`gh pr list --state open`), say so in one line and stop.

## Who does what
| Order | Branch | Opened by | Merged by | Next |
|---|---|---|---|---|
| 1 | `meta/decisions-glob` | builder session | **Liam** | Liam starts the next session |
| 2 | `meta/decisions-registry` | builder session, cut from `main` after 1 merged | **Liam** | Liam starts the next session |
| 3 | `meta/decisions-retire` | builder session, cut from `main` after 2 merged | **Liam** | Liam starts the next session |
| 4 | `job/J105` (the two rows, the report) | builder session, draft | the independent reviewer, on green CI (D32) | normal review |

**What Liam must do:** merge those three pull requests in that order once CI is green on each, and after each merge start a session with
`Continue J105: follow jobs/J105/brief.md`. No agent can merge them: the hook denies `gh pr merge` of a `meta/` branch, and that is not to be routed around.
Each `meta/` pull request is opened ready, not draft, because a draft skips `policy`, and its body names the step and says "Liam merges (D50)". A session's
last message gives the pull request number and says it is ready to merge.

## Target facts
Check each again before relying on it.
- The recipe's order of commands, and the rule that a row file on the base never changes: `core/warscape/policy.py`, `decision_row_errors`.
- What the shipped ini holds for the D46 row: `release/napoleon/components.json` sets `proxy.file_rules`, and `allowed_dev_keys` in `release/napoleon/release.json`
  is empty. J78 review round 2, finding 1. If either has changed, stop (Kill criteria).
- The route's state: fact `napoleon.ui.templates_route`; the keys are `config_keys` rows `proxy.file_rules` and `dev.file_rules`.
- Who still names the file: `git grep -n DECISIONS -- ':!jobs' ':!docs/audits' ':!core'`. A plain mention in a test fixture (`tests/test_proxy_host.py`) can stay.
- `design/napoleon/LANGUAGE.md` is named by `uikit/napoleon` and `tests/test_uikit.py` in prose only; no code reads it, and `design/` is not a build input.

## Decisions already made for this job
- **Step 2's order is settled, and differs from the report's list** (J78 review round 2, Later item 2; re-run 2026-11-06 in a throwaway copy, nothing committed).
  `reg migrate` before the `[registries]` line says `unknown registry decisions`. With `[registries]` but not `[storage]`, the registry resolves to
  `registries/decisions.jsonl`, not the folder. So edit `wsc.toml` first, then migrate.
- **`design/napoleon/LANGUAGE.md` is repointed, not hidden.** `meta` does not match `design/`, so step 1 adds that one file to `meta` and step 3 removes it again.
  `path_ignore` would add a stale path for J110 to clean up. Open question 1.
- **The two rows land on `job/J105`,** which may change any file; `decisions_cite_job` is not set here. Until that branch merges a row file is not on the base, so a reviewer's
  fix may still change it. After the merge it never changes.
- **Queued briefs are not edited.** Several tell the builder to read `docs/DECISIONS.md`. `CLAUDE.md` gains one line that covers them (deliverable 3). Open question 3.

## Deliverables
1. **`meta/decisions-glob`, from `origin/main`.** Only `wsc.toml`:
   - add `"registries/decisions/*"` to `[policy] plan` and `[policy] meta`;
   - add `"design/napoleon/LANGUAGE.md"` to `[policy] meta`.

   Check, push, open, stop (see "Every `meta/` step" below).
2. **`meta/decisions-registry`, from `origin/main` after 1 merged.** Only `wsc.toml` and the new row files.
   - `wsc.toml` first: `[registries] decisions = "core:decisions"`; add `"decisions"` to `[storage] dir`; `[policy] decisions = "registry:decisions"` and
     `decisions_retired = "docs/DECISIONS.md"`.
   - Then `python3 core/wsc.py reg migrate decisions --from-md docs/DECISIONS.md`, then the same with `--check`, which must exit 0 and say every row was found.
   - `docs/DECISIONS.md` stays byte for byte. No `registries/decisions.jsonl`. No committed view.
   - Run `gh pr list --state open` first: from this merge `policy` refuses any change to the file's table on every branch. Name any open branch that changes it in the pull request.
3. **`meta/decisions-retire`, from `origin/main` after 2 merged.**
   - Delete `docs/DECISIONS.md`. Remove the `decisions_retired` key, and `"design/napoleon/LANGUAGE.md"` from `[policy] meta`.
   - Repoint `CLAUDE.md`, `README.md`, `docs/plans/PLAN.md`, `docs/plans/UI_PIPELINE.md` and `design/napoleon/LANGUAGE.md` line 3. Any other hit from the Target facts grep that `doc_paths` fails on goes the same way.
   - `CLAUDE.md` "Before you start" says how to read the decisions: `python3 core/wsc.py find <words>`, or `reg render decisions` then `_scratch/registries/decisions.md`
     (`core/CLAUDE.md` has the wording). "While you work" gains the rule that a decision is a row file from `reg add decisions --mint`, and a reversal a new row with `replaces`.
     One line more: a brief that says `docs/DECISIONS.md` means these rows.
   - `tests/test_repo_rules.py`: `test_no_gate_silenced_without_a_decision` reads the rows from `registries/decisions/*.json`, each as a `| id | date | who | decision | reversible |`
     line, so `silenced`, `quoted_by_a_row` and their unit tests stay as they are. It asserts the rows are not empty, so it cannot pass on nothing. Fix the module docstring and the `GRANDFATHERED` comment.
4. **The rows, on `job/J105`, after 3 merged.** `git merge origin/main` first. Quoting below is for Git Bash.
   - **Opus, replacing D52:**
     ```
     python3 core/wsc.py reg add decisions --mint who=Liam date=2026-11-06 reversible=yes 'replaces:=["D52"]' 'decision=**Opus across the board: builds, reviews, fixes and briefs (replaces D52).** Every background session runs on Opus; a row or brief that says Sonnet does not override this. Effort stays medium unless a brief asks for more. The rest stands: a call budget and a kill criterion per job, no polling by agents, at most 4 background sessions (D59). Liam, 2026-11-06: "Opus across the board".'
     ```
   - **The line that supersedes the exception in D46:**
     ```
     python3 core/wsc.py reg add decisions --mint "who=J105 (recording core W33 and J78), for Liam's review" reversible=yes 'replaces:=["D46"]' 'decision=**The exception in D46 is over; the rest of D46 stands.** The player ini still omits the dev keys, and now without exception: the shipped UI rules are in `proxy.file_rules` (core W33, J78), so no component sets `dev.file_rules` and `allowed_dev_keys` is empty. `upscale/pc/play.py` stays on `dev.file_rules`, a dev launch, until J106 has passed. No Napoleon launch has used `proxy.file_rules` yet (fact `napoleon.ui.templates_route`); J106 must run one before the next release.'
     ```
   - `CLAUDE.md` "Usage": replace "Sonnet medium by default; Opus only with a reason in the brief (...)" with the Opus rule, citing the new row's id. The rest of that section stays.
     Then `git grep -n -i sonnet` the living docs and fix any other copy of the old rule.
5. **The proof.** `python3 core/proxy/tools/build_id.py` on each branch says the same id as `origin/main` at that branch's cut. Record each.

**Every `meta/` step:** commit; run `python3 core/wsc.py gates --fast`, `python3 -m unittest tests.test_repo_rules` and `python3 core/wsc.py jobs check`; `git push`;
`python3 core/wsc.py policy --branch <branch> --base origin/main`, which must say ok; `gh pr create --base main --head <branch>`. Then append the step's lines to `jobs/J105/report.md` on `job/J105`,
push that, give Liam the number, and stop. This is the only state a later session has beyond `main`.

## Out of scope
- Anything under `core/`. Not bumping the pin past `[core] version`, though v0.48.0 is out.
- `jobs check` still wants `reason:` on a `Model: Opus` line and `wsc.toml` `ref_models` still says D15: leave both, and name them under `## Open questions` for a core row.
- J103 (`plan/` narrowed rules), J106 (the launch), J109 (the `tests` cap), J110 (`path_ignore`). J78 review's Later item 1, adding the `play.py` move to J106's row, is a `plan/` edit and not this job's.
- Rewriting old rows, renumbering, or editing `jobs/*/brief.md` of any other job.
- The skills outside this repo that name the file (`warscape-brief`, `warscape-decisions`): Liam's; say so in the report.

## Open questions
1. Should `design/napoleon/LANGUAGE.md` be repointed through a temporary `meta` glob, or hidden with `path_ignore`? recommended: repoint, as Deliverables say. default after: 2026-11-09
2. Should the Opus row say effort stays medium? Liam did not ask for high effort, and that is what the row records. recommended: keep the sentence. default after: 2026-11-09. taste
3. Should queued briefs be edited to stop naming `docs/DECISIONS.md`? recommended: no, the `CLAUDE.md` line covers them and other jobs' briefs stay untouched. default after: 2026-11-09

## Kill criteria
- `reg migrate decisions --from-md docs/DECISIONS.md --check` exits non-zero after the migrate: stop, do not push, report the rows it names.
- `wsc policy` does not say ok on a `meta/` branch: stop, report its line. Never widen a glob beyond Deliverables to get past it.
- `build_id.py` differs from `origin/main` on any branch: stop and report; this job then carries rule 79, which this brief does not budget.
- `release/napoleon/components.json` no longer sets `proxy.file_rules`, or `allowed_dev_keys` is not empty: stop, do not mint the D46 row, report.
- A required check is red after two pushes on one `meta/` pull request: stop and report the check and the run id. The local `tests` gate timing out at its cap is not a red check (J109); `gates` in CI decides.
- The step's pull request is open and not merged: say so and stop. `gh pr merge` on a `meta/` branch is denied: stop, never route around it.
- Over about 80 tool calls: stop, commit, report what is left.

## Finish
After Deliverable 4 and 5, on `job/J105`: the report's required sections (`## What was built`, `## Evidence`, `## Deviations from the brief and why`, `## Open questions`). Only this job knows, so it must give:
the three pull request numbers and their merge commits, each `policy` verdict, the `--check` line, the two minted ids, each build id, and any living copy found beyond this brief's list.
Then `wsc reg set jobs J105 status=review report=jobs/J105/report.md` (`wsc` is `python3 core/wsc.py`), and open the draft pull request as the verb's build steps say.

## Registry gaps
None.
