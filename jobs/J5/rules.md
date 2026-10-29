# J5 rules ledger

Dated 2026-10-29. Sources are the baselines: napoleon-remastered `main` @ `0ec8aae` (prefix `N:`) and warscape-core `main` @
`d5275c2` (prefix `C:`); line numbers are on those commits. One row per prescriptive rule; exact duplicates merged into the first
source, near-duplicates kept apart and marked **near-dup**.

Classes: **E** enforced (gate, hook, schema or CI check, with a failing-fixture test named), **CN** codeable now (left undone, why),
**CL** codeable later (waits for what), **J** judgment (why), **R** removed: a verb or default does the step, the prose is gone.
"Before" is the class on the baselines; "after" is the class on `job/J5` plus warscape-core PR #2.

Scope: both `CLAUDE.md`, `README.md`, `docs/**`, workflow and hook comments, schema descriptions, the `pr_policy.py` docstring,
`harness/README.md`, `proxy/README.md` (agent-facing rules only; the descriptions of what the code does are behaviour, enforced by
its own tests), and the process rules of the briefs. J1-J3 brief deliverables are one-off scope, not standing rules, and are not rows.

## Counts

| Class | Before | After |
|---|---|---|
| E enforced | 36 | 53 |
| R removed (a verb or link does it) | 0 | 4 |
| CN codeable now | 25 | 6 |
| CL codeable later | 22 | 23 |
| J judgment | 37 | 34 |
| **Total** | **120** | **120** |

## Ledger

Abbreviations for tests: `tj` napoleon `tests/test_jobs.py`, `tp` `tests/test_pr_policy.py`, `tr` `tests/test_repo_rules.py`,
`cc` core `tests/test_checks.py`, `cl` core `tests/test_cli.py`, `cr` core `tests/test_registry.py`, `ct` core `tests/test_tools.py`.

### Napoleon `CLAUDE.md`

| # | Rule | Source | Before | After | Enforced by (test) or reason |
|---|---|---|---|---|---|
| 1 | The repo is the single source of truth | N:CLAUDE.md:3 | J | J | a principle; its checkable parts are rows 8, 33, 40 |
| 2 | `git pull`, read README, DECISIONS and the plan doc first | N:CLAUDE.md:6 | J | J | reading cannot be observed |
| 3 | Look things up in the registries before rediscovering; recheck Empire facts on Napoleon | N:CLAUDE.md:7-10 | J | J | `engine_facts` schema enforces state/evidence fields, not whether an agent looked |
| 4 | Clone with submodules (core present) | N:CLAUDE.md:13 | CN | CN | the pre-push hook refuses with no core, but no failing-fixture test; core-side, left for budget |
| 5 | Set `core.hooksPath` once per clone | N:CLAUDE.md:13-14 | J | CL | core `hooks` gate (cl `test_hooks_gate_warns_until_wired`, PR #2); active here after the pin bump (J16) |
| 6 | Agent sessions attach warscape-core | N:CLAUDE.md:14 | J | J | session setup, not repo state |
| 7 | Everything goes through `wsc` verbs | N:CLAUDE.md:15 | J | J | a habit; its effects are rows 8, 35 |
| 8 | Never edit a generated `registries/*.md` view | N:CLAUDE.md:16 | E | E | `registries` gate, view stale (cr `test_hand_edits_are_caught`) |
| 9 | Never change files inside `core/` | N:CLAUDE.md:17-18 | CN | CN | `core_pin` fails on a dirty core but has no failing-fixture test (core backlog B7) |
| 10 | Job statuses are `needs_brief`/`queued`/`review`/`done`/`blocked` | N:CLAUDE.md:22-23 | E | E | jobs schema enum (cr `test_invalid_row_is_refused`) |
| 11 | Each job has `brief.md`, then `report.md`, `review.md` (files exist, belong to the job) | N:CLAUDE.md:21-22 | CN | E | `wsc jobs check` (tj `test_status_needs_its_files`, `test_link_to_another_jobs_file`, `test_folder_without_row`, `test_brief_present_but_needs_brief`) |
| 12 | Pick up: lowest-numbered `queued`, deps `done`, no remote `job/<id>` branch | N:CLAUDE.md:24-25 | CN | R | `wsc jobs next` (tj `Next`) |
| 13 | Finish with `report.md` and `status=review report=...` | N:CLAUDE.md:26 | E | E | schema `review` needs `report`; `jobs check` needs the file (tj `test_status_needs_its_files`) |
| 14 | A new brief has the shape of `jobs/J1/brief.md` | N:CLAUDE.md:27-28 | CN | E | `jobs check` brief shape (tj `test_brief_shape`) |
| 15 | A brief goes on `brief/<id>`, set `queued` with `brief=`, stop for merge | N:CLAUDE.md:28 | E | E | `pr_policy` brief branch (tp `test_brief_branch`) |
| 16 | If nothing is ready, say what each job waits for | N:CLAUDE.md:29 | CN | R | `wsc jobs next` prints the waiting list (tj `test_then_a_brief_then_nothing`) |
| 17 | Review: the `job/<id>` branch whose row says `review` and has no `review.md` | N:CLAUDE.md:30-31 | CN | R | `wsc jobs review` (tj `test_review_pick`) |
| 18 | With a `merge` verdict set `done` on the branch | N:CLAUDE.md:31-32 | E | E | `pr_policy` (tp `test_job_branch_complete`, `test_job_branch_unreviewed_or_unfinished`); `jobs check` (tj `test_done_needs_merge_verdict_and_date`) |
| 19 | Never mark your own job `done` | N:CLAUDE.md:33 | J | J | the half that matters is enforced (done needs a merge review by another session, rows 18, 20); who typed `done` is not |
| 20 | Never review a job you built | N:CLAUDE.md:33 | CN | E | `pr_policy` compares `Claude-Session:` trailers of report and review commits (tp `test_review_by_the_builder_is_refused`) |
| 21 | Branch kinds and their files (**near-dup** of D21 and the `pr_policy.py` docstring) | N:CLAUDE.md:34-37 | E | E | `pr_policy` (tp `test_unknown_branch_refused`, `test_plan_and_meta_scopes`); one owner now: the docstring, CLAUDE.md links |
| 22 | Work not in the queue becomes a `needs_brief` row on `plan/` first | N:CLAUDE.md:37-38 | E | E | any other branch is refused (tp `test_unknown_branch_refused`) |
| 23 | Reviewer fixes go on the job branch, never a separate branch | N:CLAUDE.md:38 | E | E | a fix branch has no legal name (tp `test_unknown_branch_refused`) |
| 24 | Work on a branch; `main` only by an approved merge after review | N:CLAUDE.md:41-42 | E | E | `pr_policy` + branch protection (D21); protection could not be read (API 403), see report |
| 25 | Commit and push after every meaningful step | N:CLAUDE.md:41 | J | J | "meaningful" is judgment |
| 26 | Every job ends with a report: built, evidence, deviations, open questions | N:CLAUDE.md:42-43 | CN | E | `jobs check` report headings (tj `test_report_shape`); that the evidence is real stays review work |
| 27 | A learning becomes code first | N:CLAUDE.md:44-45 | J | J | the meta-rule this job applies (**near-dup** of C:CLAUDE.md:14, which adds "a schema rule"; each repo's entry file keeps its own) |
| 28 | Exe stays vanilla on disk | N:CLAUDE.md:46 | CL | CL | an exe-sha check after every install needs the PC; J4 acceptance gate |
| 29 | Every engine address in engine_sites with anchor bytes, behind the guard | N:CLAUDE.md:46-47 | E | E | `proxy/tools/gen_tables.py` + `tests/test_proxy_tables.py` |
| 30 | The PC game folder is a deploy target; sha-checked sync | N:CLAUDE.md:48 | E | E | `pc_deploy.py` refuses stale copies (`tests/test_pc_deploy.py`) |
| 31 | PC experiments live under `_scratch\<you>\` | N:CLAUDE.md:48-49 | CL | CL | a `job.sh` guard on write paths; J17 |
| 32 | Never run git in the game folder | N:CLAUDE.md:49 | CL | CL | a `job.sh` guard; J17 |
| 33 | Reuse before you write; search the tools registry | N:CLAUDE.md:50 | J | J | intent; near-duplicate detection would be guesswork |
| 34 | Every tool has a header and a registry row | N:CLAUDE.md:51 | E | E | `tools` gate (ct `test_missing_row_then_add_then_drift`, `test_header_problems`) |
| 35 | "Verified" carries a date and run id | N:CLAUDE.md:52 | E | E | `verified_dates` gate (cc `test_plain_claim_flagged`); prose now links it |
| 36 | One owner per topic; grep and fix every copy | N:CLAUDE.md:53 | J | J | sameness of meaning needs a reader; this ledger did one pass |
| 37 | Keep docs short | N:CLAUDE.md:53 | E | E | `doc_size` (cc `test_size_cap_is_kib`) |
| 38 | Windows-safe names (**near-dup**: core adds `\`) | N:CLAUDE.md:54 | E | E | `windows_paths` (cc `test_reserved_bad_chars_trailing_and_case`); both files now link the gate instead of listing |
| 39 | Never edit generated copies (Project docs, review pages) | N:CLAUDE.md:55 | CL | CL | the review page is not built (UI phase); the Project mirror lives outside the repo |
| 40 | Sonnet default; Opus only with a stated reason | N:CLAUDE.md:58 | CN | E | `jobs check`: Model line matches the row, Opus needs "reason" (tj `test_brief_shape`) |
| 41 | At most 2 agents at once | N:CLAUDE.md:59 | J | J | runtime behaviour of a chat; no record to check |
| 42 | Every brief states a call budget and a kill criterion | N:CLAUDE.md:59 | CN | E | `jobs check` (tj `test_brief_shape`) |
| 43 | Waiting and polling belong to the harness | N:CLAUDE.md:59-60 | J | J | agent behaviour; `job.sh` already blocks inside one call |

### Napoleon README, DECISIONS, REVIEW

| # | Rule | Source | Before | After | Enforced by (test) or reason |
|---|---|---|---|---|---|
| 44 | Project docs, review pages and the PC folder are generated or deployed, never edited (dup of 39, 30) | N:README.md:7-8 | J | J | merged into rows 30 and 39 |
| 45 | `core/` is never edited here (dup of 9) | N:README.md:20 | CN | CN | row 9 |
| 46 | Decisions are append only; a reversal is a new row | N:DECISIONS.md:3-4 | CN | E | `pr_policy` `decisions_problems` (tp `test_decisions_are_append_only`) |
| 47 | Decision detail lives in the owning doc | N:DECISIONS.md:4 | J | J | length is not the test; content is |
| 48 | D4 deterministic gates wherever possible | N:DECISIONS.md D4 | J | J | the goal of this job |
| 49 | D11 one game at a time | N:DECISIONS.md D11 | J | J | the watcher lock serialises the PC; choosing which game to work on is Liam's |
| 50 | D14 scope is D1 only | N:DECISIONS.md D14 | J | J | scope needs a reader |
| 51 | D16 the status page is generated, nobody hand-keeps state | N:DECISIONS.md D16 | E | E | `registries` gate renders `jobs.md` (cr `test_render_fixes_order_and_view`) |
| 52 | D20 core is a submodule pinned at a tag, repeated in `wsc.toml` | N:DECISIONS.md D20 | E | E | `core_pin` (cl `test_core_pin`); the tag itself from core v0.2 (row 107, J16) |
| 53 | The reviewer is a fresh chat that did not build the branch (dup of 20) | N:REVIEW.md:63-64 | CN | E | row 20 |
| 54 | Review setup: clone, check out, attach, read in order | N:REVIEW.md:71-73 | J | J | session steps |
| 55 | Review budget about 60 tool calls | N:REVIEW.md:73 | J | J | no record of a review's calls |
| 56 | Run the machines first | N:REVIEW.md:76 | J | J | order of work |
| 57 | Every claim needs evidence you can open | N:REVIEW.md:78-79 | J | J | the dated "verified" half is row 35 |
| 58 | Brief deliverables present, kill criteria respected, nothing out of scope | N:REVIEW.md:80-81 | J | J | needs a reader |
| 59 | Risk-first reading | N:REVIEW.md:82-83 | J | J | judgment |
| 60 | Empire repeats left as prose are findings | N:REVIEW.md:84 | J | J | judgment |
| 61 | Verdict line exactly one of three | N:REVIEW.md:87-89 | CN | E | `jobs check` (tj `test_done_needs_merge_verdict_and_date`); `pr_policy` reads it |
| 62 | Findings ranked blocker / should-fix / later with `file:line` | N:REVIEW.md:88-89 | CN | CN | a word check is cheap but weak; left for budget |
| 63 | Fix small should-fix items on the branch, one commit each | N:REVIEW.md:91 | J | J | "small" is judgment |
| 64 | Later core items go to the core backlog by PR | N:REVIEW.md:93 | J | J | cross-repo intent |
| 65 | Review dated at the top | N:REVIEW.md:94 | CN | E | `jobs check` (tj `test_done_needs_merge_verdict_and_date`) |
| 66 | Merge verdict: set `done`; otherwise leave `review` | N:REVIEW.md:94-95 | E | E | rows 18, 61 |
| 67 | A finding a gate could catch becomes a gate | N:REVIEW.md:98-99 | J | J | the meta-rule |

### Napoleon PLAN and UI_PIPELINE

| # | Rule | Source | Before | After | Enforced by (test) or reason |
|---|---|---|---|---|---|
| 68 | Anything new in scope enters through a dated decision with a kill criterion | N:PLAN.md:27-28 | J | J | scope needs a reader |
| 69 | Every registry is JSONL + schema + view + check | N:PLAN.md:37-38 | E | E | `registries` gate (cr `test_empty_registries_render_and_check`) |
| 70 | Hotkeys: a gate fails on any clash | N:PLAN.md:48, 140 | E | E | cr `test_hotkey_clashes`; modifier-agnostic clashes wait for core B3 (CL part) |
| 71 | A standalone tool says why it is not a verb | N:PLAN.md:51-52 | E | E | ct `test_header_problems` |
| 72 | Unused tools are flagged for retirement | N:PLAN.md:52 | CL | CL | core B6 (`last_used` stamping) |
| 73 | CI on every push; pre-push hook for the fast set | N:PLAN.md:54-55 | E | E | workflows; cl `test_hook_runs_the_fast_gates_from_a_game_repo` |
| 74 | PC jobs verify against a baseline file | N:PLAN.md:55 | CL | CL | J4 acceptance gate |
| 75 | Status page also shows PC state, what ran, usage | N:PLAN.md:57-58 | CL | CL | no generator yet; belongs with J4 or a later meta job |
| 76 | Core candidates live under `*/core/` and move in one promotion job per phase | N:PLAN.md:78-80 | CL | CL | J12 |
| 77 | Control API commands wait for their settle and check their result | N:PLAN.md:102-104 | CL | CL | J4 |
| 78 | Camera poses are stored by id, never as key-tap scripts | N:PLAN.md:104 | CL | CL | J4 (scenarios schema has poses; the ban on key scripts needs the control API) |
| 79 | Acceptance passes 20 times in a row after every harness or DLL change | N:PLAN.md:106-107 | CL | CL | J4, J13 |
| 80 | Briefs cite registry ids, never searched paths | N:PLAN.md:119 | CL | CL | J11 |
| 81 | Every later change is reported against the baseline | N:PLAN.md:123-124 | CL | CL | phase 3 baseline |
| 82 | Memory gate: stop at a set headroom | N:PLAN.md:132-133 | CL | CL | phase 3 |
| 83 | Concepts are never translated, only chosen from | N:UI_PIPELINE.md:28-29 | J | J | design process |
| 84 | Data feed sends diffs, never full rebuilds | N:UI_PIPELINE.md:34 | CL | CL | panel host (UI phase) |
| 85 | Every length in dp; lint: tokens and library classes only | N:UI_PIPELINE.md:42, 62 | CL | CL | the design lint (UI phase) |
| 86 | Design gate renders the four corners and fails on clipping | N:UI_PIPELINE.md:47-48 | CL | CL | the viewer (spike S1) |
| 87 | Every status but `locked` is set by a tool; review titles generated one way | N:UI_PIPELINE.md:55-56 | CL | CL | UI tooling |
| 88 | A locked screen that changed is flagged, never silently demoted | N:UI_PIPELINE.md:67-68 | CL | CL | UI tooling |
| 89 | Status changes only through the CLI | N:UI_PIPELINE.md:71 | CL | CL | UI tooling (the `ui_elements` schema exists; the verb does not) |

### Napoleon harness, proxy, workflow, schema

| # | Rule | Source | Before | After | Enforced by (test) or reason |
|---|---|---|---|---|---|
| 90 | Cloud agents never touch the PC directly; jobs go through the watcher | N:harness/README.md:3 | J | J | architecture; the bridge's own tools are outside the repo |
| 91 | Harness is PS 5.1 ASCII-only; data UTF-8 without BOM | N:harness/README.md:5 | CN | E | tr `test_harness_sources_are_ascii_and_data_has_no_bom` (fixtures in `Fixtures.test_text_problems`) |
| 92 | Never Empire's watcher task; refuse while a game runs | N:harness/README.md:11-12 | E | E | harness integration tests (Windows CI job) |
| 93 | Write the request under a temp name, then rename; ids never reused | N:harness/README.md:22 | E | E | `job.sh` does it (`tests/test_job_sh.py`); the watcher refuses reused ids |
| 94 | Read-only scripts need no lock | N:harness/README.md:28 | J | J | what is read-only is judgment |
| 95 | DXVK binaries are never committed | N:proxy/README.md:97 | CN | E | `.gitignore` refuses `*.dll`/`*.exe`/`*.pdb`; tr `test_no_binaries_committed` |
| 96 | A new kit id every time; stale copies refused | N:proxy/README.md:106-109 | E | E | `tests/test_pc_deploy.py` |
| 97 | Never delete on the PC: removals are moves to `_to_delete` | N:proxy/README.md:114 | E | E | `pc_deploy.py` (`tests/test_pc_deploy.py`); the bridge refuses deletes by default |
| 98 | Only the dev side installs hooks, only with a dev key and the guard's plan | N:proxy/README.md:121-122 | E | E | `tests/test_dev.cpp` lint |
| 99 | Require the `gates` check in branch protection | N:gates.yml:3 | J | J | GitHub settings, not readable from a session (API 403) |
| 100 | The proxy CI job needs full history | N:gates.yml:161-162 | E | E | the "not shallow" step |
| 101 | Opus only with the reason in the brief (schema text) | N:jobs.schema.json model | CN | E | row 40 |
| 102 | `blocked` needs `blocked_by`; `depends_on` names real jobs | N:jobs.schema.json | E | E | schema `allOf`, `x-ref` (cr `test_cross_registry_refs`) |
| 103 | No gate silenced by `skip` or an exemption without a dated decision | N:jobs/J5/brief.md:47 | CN | E | tr `test_no_gate_silenced_without_a_decision` (fixtures `test_silenced`) |

### warscape-core

| # | Rule | Source | Before | After | Enforced by (test) or reason |
|---|---|---|---|---|---|
| 104 | The core is game-agnostic: no game paths, addresses or facts | C:CLAUDE.md:4 | CN | CN | the obvious half (absolute Windows paths, `0x` RVAs in core sources) is a grep; left for budget |
| 105 | Set the hook once per clone | C:CLAUDE.md:9 | J | E | core `hooks` gate (cl `test_hooks_gate_warns_until_wired`) |
| 106 | Work on a branch; `main` only by Liam's merge | C:CLAUDE.md:12 | CL | CL | the core has no PR policy yet; core B8 starts one |
| 107 | Tags `vX.Y.Z`, cut after merge, `VERSION` the same | C:CLAUDE.md:12-13 | CN | E | `core_pin` in the core (cc `CorePin.test_core_tags_match_version`). **Fails on core `main` today: tag `V0.1.0`** |
| 108 | A new capability is a verb unless there is a reason | C:CLAUDE.md:16-17 | E | E | ct `test_header_problems` |
| 109 | Header in the first 40 lines; row; commit file, JSONL and view together | C:CLAUDE.md:18-22 | E | E | ct `test_header_must_be_in_the_first_40_lines`, `test_missing_row_then_add_then_drift` |
| 110 | Retire with `superseded:<id>`; a move keeps its id | C:CLAUDE.md:21-22 | E | E | ct `test_removed_file_superseded_chain_and_retirement`, `test_a_moved_tool_keeps_its_id` |
| 111 | Registries change through `wsc reg` | C:CLAUDE.md:23 | E | E | cr `test_hand_edits_are_caught` |
| 112 | Registries use structured verified fields | C:CLAUDE.md:24-25 | E | E | cr `test_engine_site_verified_needs_date_and_run` |
| 113 | Standard library only; a dependency needs a decision first | C:CLAUDE.md:26 | CN | E | cc `StdlibOnly` (fixture `test_fixture`) |
| 114 | Python 3.12 | C:CLAUDE.md:26 | E | E | the hook refuses older Python; CI pins 3.12 |
| 115 | Run the gates before you push | C:CLAUDE.md:29 | E | E | the pre-push hook (cl `test_hook_runs_the_fast_gates_from_a_game_repo`) |
| 116 | Bypass the hook only with `--no-verify` and a reason in the commit | C:CLAUDE.md:29-30 | J | J | a bypass leaves no trace a gate can see |
| 117 | Game repos never patch the core in place (dup of 9) | C:CLAUDE.md:31 | CN | CN | row 9; core B7 |
| 118 | Usage rules (**near-dup** copy of napoleon D15) | C:CLAUDE.md:34-37 | J | R | replaced by a link to napoleon's `CLAUDE.md` "Usage" |
| 119 | Core decisions append only | C:DECISIONS.md:3-4 | CL | CL | core B8 (port `decisions_problems`) |
| 120 | Tags are never moved | C:CONSUMING.md:203 | J | J | tag history is remote state a gate cannot see offline |


## Near-duplicates (drift) and what happened

| Topic | Copies | Outcome |
|---|---|---|
| Windows-safe names | N:CLAUDE.md:54 (no `\`), C:CLAUDE.md:28 (with `\`), the gate's regex | both files link the `windows_paths` gate; the regex is the owner |
| Usage rules (D15) | N:CLAUDE.md:57-60, C:CLAUDE.md:34-37, N:DECISIONS D15 | the core links napoleon's `CLAUDE.md`; D15 stays as the dated record |
| Branch kinds (D21) | N:CLAUDE.md:34-38, N:DECISIONS D21, `pr_policy.py` docstring | the docstring owns the list; CLAUDE.md links it; D21 stays as the record |
| Core visibility | N:README.md:23, N:PLAN.md:63, N:DECISIONS D18, N:gates.yml:5, C:README.md:7, C:CONSUMING.md | public (GitHub API, 2026-10-29); D29 records it; every living copy fixed |
| Tag case | C:CLAUDE.md `vX.Y.Z`, the tag `V0.1.0`, N pin `v0.1.0` | the gate now refuses the mismatch; Liam tags `v0.2.0` |
| Pick-up and review procedures | N:CLAUDE.md:24-32, N:REVIEW.md:67 | the `jobs` verb does them; both docs name the verb |
| "A learning becomes code" | N:CLAUDE.md:44-45, C:CLAUDE.md:14-15 | kept: each repo's entry file needs it; wording differs only by "a schema rule" |
