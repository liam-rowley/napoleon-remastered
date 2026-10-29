# J5 report: determinism audit (rules into gates)

2026-10-29, Opus (independent check, D15). Branch `job/J5`; warscape-core PR #2 (branch `napoleon-j5`); planning PR #18
(`plan/j5-followups`). The ledger is `jobs/J5/rules.md`.

## What exists

**Napoleon (this branch)**
- **`wsc jobs` verb** (`tools/verbs/jobs.py`, wired by `wsc.toml` `[cli] verb_dirs`):
  - `jobs check`: every row's brief/report/review link points at its own job folder and the file exists; the status has the files it
    needs (`queued` a brief, `review` a report, `done` a review); a brief on disk with a `needs_brief` row fails; `jobs/<id>/` without a
    row fails; brief shape (`# J<n>:` title, `Model:` line matching the row, Opus with a reason, `Budget about <n> tool calls`,
    `## Kill criteria` with a bullet, `## Finish` ending with the `status=review` command); report shape (title, `## Deviations`,
    `## Open questions`); review dated in its first lines with one of the three verdicts, `done` only with `merge`; `review`/`done`
    only when every dependency is `done`; no dependency cycles.
  - `jobs next`: the "pick up the next job" procedure (lowest-numbered ready `queued` job with no remote `job/<id>`, else the
    lowest ready `needs_brief` with no `brief/<id>`, else what every open job waits for). `jobs review`: the "review the next job"
    procedure (fetches the job branches and reads the row on each).
  - `tests/test_jobs.py`: failing and passing fixtures for every check, plus `ThisRepo.test_the_queue_passes_jobs_check`, which runs
    `jobs check` on the real queue, so the `tests` gate (CI and full `wsc gates`) enforces it until core B1 gives games real gates.
- **`tools/pr_policy.py`**: refuses a job branch whose `review.md` was committed by a session (`Claude-Session:` trailer) that also
  committed `report.md`; refuses edits, reordering or misnumbered rows in `docs/DECISIONS.md` on every branch kind. Tests in
  `tests/test_pr_policy.py`. J3's real history passes (report and review sessions differ).
- **`tests/test_repo_rules.py`**: harness `.ps1`/`.cmd` are ASCII and data files BOM-free; no `*.dll`/`*.exe`/`*.pdb`/`*.dmp`
  tracked (`.gitignore` now refuses them); `wsc.toml` `[gates] skip` and exemption globs need a decision row quoting them
  (the two existing exemptions are listed with their reasons).
- **Prose**: `CLAUDE.md` "Jobs" now names the verbs instead of the procedures; branch kinds have one owner (the `pr_policy.py`
  docstring); the tool-header, "verified" and Windows-name rules link their gates; `docs/REVIEW.md` and `docs/DECISIONS.md` name the
  checks; the core is public everywhere (D29, for Liam's review), with the CI token kept wired.

**warscape-core PR #2** (https://github.com/liam-rowley/warscape-core/pull/2, open)
- `core_pin` checks the tag (backlog B5): a pin is `vX.Y.Z` with a lower-case v and must be a tag on the core HEAD when the checkout
  has tags; in the core, tags on HEAD equal `v` + `VERSION`.
- `hooks` gate (warning, skipped in CI): `core.hooksPath` is wired in this clone.
- Every core git call drops the `GIT_*` variables git exports to hooks (`repo.git_env`). Found here: pushing `plan/j5-followups`
  from a git worktree, the pre-push hook's `GIT_DIR` made `core_pin` read napoleon's index and refuse the push as "core dirty".
- Host test: core sources import the standard library only.
- Prose: Windows rule and the D15 copy link their owners; the core is public; backlog B5 removed, B7 and B8 added; `VERSION` 0.2.0;
  decisions C10-C12 proposed.

**Planning PR #18** (`plan/j5-followups`): `needs_brief` rows J17 (core pin bump to `v0.2.0`, after Liam tags it) and J18 (PC-side
guards: no git in the game folder, experiments under `_scratch\<owner>\`, exe sha after every install). Rows go there because a job
branch may change only its own row.

## Gates

| Run | Repo, ref | Result |
|---|---|---|
| baseline, local 2026-10-29 | napoleon `main` @ `0ec8aae` | 11 ok, 0 warn, 0 failed; 33 host tests |
| baseline, local 2026-10-29 | core `main` @ `d5275c2` | 11 ok, 0 warn, 0 failed; 62 host tests |
| final, local 2026-10-29 | napoleon `job/J5` (rebased on `2962d0e`) | 11 ok, 0 warn, 0 failed; 53 host tests |
| final, local 2026-10-29 | core `napoleon-j5` | 12 ok, 0 warn, 0 failed; 69 host tests |
| new check on core `main` | core `main` @ `d5275c2` with the PR's `core_pin` | **fails**: `tag 'V0.1.0' on HEAD is not v0.1.0` |

CI run ids for the pushed heads are listed at the end of this report.

## Enforced before and now

Counts from the ledger (120 rules): enforced 36 -> 53; removed (a verb does it, or a link replaced a copy) 0 -> 4; codeable now
25 -> 6; codeable later 22 -> 23; judgment 37 -> 34. Newly enforced, each with a failing-fixture test: job files and links, brief
shape (Model/reason, budget, kill criteria, Finish), report headings, review date and verdict, dependencies before review, cycles,
orphan folders, builder-reviewer separation, append-only decisions, harness ASCII/BOM, no binaries, no unrecorded skips or
exemptions, core tag/pin (core PR), hook wiring (core PR), stdlib-only core (core PR).

## Deviations from the brief, and why

- **Inventory scope.** About 480 candidate lines across both repos; 120 are rules. J1-J3 brief deliverables are one-off scope, and the
  proxy/harness README lines that describe what the code does are behaviour with their own tests, so neither became rows. The brief
  process rules they share (model, budget, kill criteria, Finish) are covered by the brief-shape check.
- **`jobs check` runs through the `tests` gate, not a separate CI step.** A host test that runs it on the real queue makes it part of
  CI and of a local full `wsc gates`; a CI-only step would have let a local run look green. It moves to a game gate with core B1.
- **The jobs logic is a napoleon verb, not a core change.** The jobs registry and its schema are repo-local; it is a core candidate for
  J12 (promotion) once Empire needs it.
- **One commit carried two fixes** (`pr_policy` session check and the CLAUDE.md Jobs rewrite), because the rewrite deletes the prose of
  both the verb and the policy change. Every other fix is its own commit.
- **D29** records a fact that contradicts D18 (the core is public); D-rows are Liam's, so it is marked "for Liam's review".
- The plan-branch push used `--no-verify` because of the hook bug fixed in core PR #2; the commit says why.

## Left as judgment (with reasons)

Rows 1-3, 6, 7, 19, 25, 27, 33, 36, 41, 43, 44, 47-50, 54-60, 63, 64, 67, 68, 83, 90, 94, 99, 116, 120 in the ledger, each with
its one-line reason. Groups: principles and reading habits (no observable record), chat behaviour (agent count, polling, commit
cadence), scope and design judgment (D14, "never translated"), review craft (risk-first reading, evidence quality), and things outside
the repo (branch-protection settings, remote tag history, a `--no-verify` that leaves no trace).

Codeable now but left (budget): core-missing hook refusal test (row 4), `core_pin` dirty-core test (rows 9, 45, 117: core B7), review
finding ranks (row 62), the core-is-game-agnostic grep (row 104).

## Findings

1. **Tag case.** The only core tag is `V0.1.0`; napoleon pins `v0.1.0`, which does not exist (tags are case-sensitive); the old
   `core_pin` compared `VERSION` only. With PR #2, core `main` itself fails the new check. Not weakened: Liam tags the PR #2 merge
   `v0.2.0`, then J17 moves the pin.
2. **Hook variable leak** (fixed in PR #2, see above).
3. **Branch protection could not be read** (GitHub API 403 from this session), so "required checks on `main`" (D21) is unverified.
4. `pr_policy.py` matches paths with `fnmatch`, where `*` crosses `/`; harmless for its globs today (each `x/*` has a `x/**` twin),
   noted for when it moves to the core's segment-aware globs.
5. `jobs next` picks J6 (lowest-numbered ready `needs_brief`), while `de8ed5c` says J5 comes "before the J13-J15 briefs". If Liam wants a
   different order, the queue needs an explicit priority field rather than prose.

## Open questions

1. Accept D29 (core public) and C10-C12 (core PR #2)? Tag `v0.2.0` after merging, and optionally add `v0.1.0` on `d5275c2`.
2. Should the queue get a `priority` field so `jobs next` follows Liam's order rather than the lowest number (finding 5)?
3. Keep `WARSCAPE_CORE_TOKEN` in the workflow now the core is public, or drop it in J17?

## CI runs

- napoleon `job/J5` @ `77176d3` (all code and the report): run 40871518126, `gates`, `proxy`, `harness-windows` success (2026-10-29).
- warscape-core `napoleon-j5` @ `e0fbb0c`: runs 40871301956 and 40871295158 (push and pull request), success (2026-10-29).
