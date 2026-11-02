# J62: Promote the job pipeline to warscape-core

Phase 1, the promotion job for the queue itself (PLAN section 4, "Promotion rows"; core backlog B35, plus B8 on the way). The job
pipeline is the most reusable thing built on this game and is still game-side: `tools/verbs/jobs.py` (1200 lines: `next`, `review`, `fix`,
`check`, `view`, the launch server and the `--auto` loop), `tools/pr_policy.py`, `tools/ci_notify.py`, `tools/changed_inputs.py`,
`tools/ci_failures.py`, the session-trailer rule in `tools/claude_hook.py`, `schemas/jobs.schema.json`, `docs/REVIEW.md`, their tests and
the two workflows. Empire restarts on the core only after this job (PLAN section 4, "Next games"), and every core change still waits for a
hand merge while its backlog grows faster than it drains. This job moves the generic machinery to `liam-rowley/warscape-core` as core
v0.9.0, keeps every game-specific rule in this repo as `wsc.toml` config and one hook module, and makes the core a consumer of its own
queue. **The move is invisible here: the same outputs, byte for byte.** Nothing in the DLL, the watcher or the game changes.

Model: Sonnet. Python, YAML and tests in two repos; no engine, DLL or PC work. Budget about 320 tool calls over both parts (about 190 for
the core PR, about 130 for the switch); at the cap, stop, commit, push both repos, report what is left. Subagents are not needed. Waiting
belongs to the harness: never poll CI, a merge or a tag.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J62`; "The core": a core change is a pull request from a separate `warscape-core` clone,
  `/c/Users/liamr/repos/warscape-core`, branch `napoleon-j62`, `git pull` first). Never edit inside `core/` here. Read `core/CLAUDE.md`,
  `core/docs/CONSUMING.md` (upgrading the pin; the B9 one-commit rule), `core/docs/DECISIONS.md` (C2, C5, C8, C15), `core/docs/BACKLOG.md`
  (B1, B8, B9, B35), `core/warscape/repo.py` (DEFAULTS: the loader refuses a `wsc.toml` key it does not know, so every new table ships in
  the core release before this repo uses it), `core/warscape/verbs/__init__.py` (the verb contract) and `core/warscape/registry.py`.
- Read the code being moved, in full: `tools/verbs/jobs.py`, `tools/pr_policy.py`, `tools/ci_notify.py`, `tools/changed_inputs.py`,
  `tools/ci_failures.py`, `tools/claude_hook.py` (the trailer rule only), `schemas/jobs.schema.json`, `docs/REVIEW.md`,
  `.github/workflows/gates.yml`, `.github/workflows/policy.yml`, `.claude/settings.json`, `wsc.toml`.
- Read the reports and reviews that shaped it: `jobs/J52/report.md` (rounds, the autopilot), `jobs/J54/report.md` (pass markers, draft
  pull requests, `branch_checks`), `jobs/J55/report.md` (per-row files, `branch_row_spec`; the last core release and pin bump, v0.6.0),
  `jobs/J56/report.md` (one fetch), `jobs/J57/report.md` (the ready-before-push order, the `changes` fail-safe), `jobs/J11/report.md` item 5
  and deviation 8, `jobs/J58/report.md` (a core pin bump that leaves the core's proxy and harness untouched needs no acceptance run),
  `jobs/J12/report.md` (how the previous promotion retired local copies and tools rows).
- Search before writing: `python3 core/wsc.py find jobs policy trailer decisions`.
- **Other branches on the same files.** `git branch -r` at the start and just before the switch; any open `job/*` branch that changes a moved
  file (J54 to J57 and J11 are merged) has to merge `main` after you. Name each in the report.

## Target facts
Check each again before relying on it:
- The core pin is `v0.8.0` (`wsc.toml` `[core] version`, the `core` gitlink); tags v0.5.0 to v0.8.0 exist; the next release is `v0.9.0`
  (`VERSION` says `0.9.0`) unless the core has moved on since.
- Required checks on `main` here: `gates`, `proxy`, `harness-windows`, `policy` (docs/REVIEW.md, "Merging"). **A reusable `workflow_call`
  workflow would rename them** (GitHub shows `<caller job> / <called job>`), so auto-merge would wait for checks that never report; see Decisions.
- Rule 79 counts a core pin change only when the core's own `proxy/` or `harness/` changed between the two pins (J58). So the v0.9.0 diff
  against v0.8.0 must leave both folders alone (READMEs and `runs/` aside); `needs_pc` is `false` and no acceptance run is available.
- The slow CI jobs treat a `core` gitlink change as a change of all three input sets, so the pin bump runs `proxy`, `viewer` and
  `harness-windows` once. Expected, not a failure.
- Game-specific content in the code today: the `LEGACY_REVIEWS`, `LEGACY_BRIEFS` and `LATE_LEGACY` sets and the found-path call (J11);
  `PROMOTIONS` (rule 76); `pc_state` and `pc_block` (the view's PC line, reading `harness/napoleon/adapter.json` and the acceptance ledger);
  `ACC_*`, `acceptance_active`, `acceptance_problems`, `core_pin_diff`, `dll_build_id` (rule 79); `PLAN`/`META` branch globs and the
  `D<n>` rule in `pr_policy.py`; the `INPUTS` regexes and `SALT` in `changed_inputs.py`; `class_hint` in `ci_notify.py`; `CLASSES` and
  `GUARDS` in `ci_failures.py`; D-numbers, `docs/plans/PLAN.md`, `tools/pr_policy.py` and `python3 core/wsc.py` inside the step texts.

## Decisions already made for this job
- **Capture first.** Before any change, on `origin/main` at the job's start sha, write the golden outputs below to `_scratch/j62/before/`
  (git-ignored; the capture script stays in the session scratchpad and is not committed). The proof compares against them.
- **The generic half moves; the game half stays as config and one hook module.** The core gets, as verbs and library code under `warscape/`
  (stdlib only, C2): `jobs` (all subcommands, unchanged behaviour), `policy` (the pull-request policy as `wsc policy --branch B [--base REF]`),
  and a `ci` verb with `inputs` (the input sets and tree hashes), `notify` and `render` (below); `failures` joins them if the split is cheap
  (see Open questions). It also gets the `core:jobs` schema and the trailer-rule function (a library function; the hook entry point and the
  game-folder rules stay in this repo's `tools/claude_hook.py`, whose settings wiring does not change).
- **Config, in `wsc.toml` tables the core release adds** (defaults make a repo with none of them behave as a plain queue):
  - `[jobs]`: `id_prefix` (`J` here), `models`, `dir` (`jobs`), `legacy` (a data file, below), `hooks` (a list of repo-relative Python files),
    and a `[jobs.text]` table for every game-specific string in the step texts and prompts (the D-numbers, the plan and review doc paths, the
    policy command line). The values here are today's wording, so the rendered text is identical; the core's defaults are generic. The
    command prefix is `python3 core/wsc.py` in a game and `python3 wsc.py` inside the core itself.
  - `[policy]`: `decisions` (path) and `decision_prefix` (`D` here, `C` in the core) for the append-only rows check, which also closes core
    backlog B8; `session_trailer` (`Claude-Session`; empty switches the own-review rule off); `plan` and `meta` (the glob lists `PLAN` and `META`
    are today).
  - `[ci]`: `inputs` (set name to regex, the current `proxy`, `harness` and `viewer`), `salt`, and `hints` (job name to the text `class_hint`
    prints).
  - The jobs schema moves as `core:jobs`. Allowed differences from today's file: the `$id`, the wording of its description, and `phase`
    losing its maximum of 6 (a static schema cannot take one game's phase count; core backlog B2 is not built).
- **Three hook points, not B1.** A module listed in `[jobs] hooks` may define any of: `brief_problems(ctx, jid, row, text)`,
  `queue_problems(ctx, rows, files)`, `policy_problems(ctx, facts)` and `view_panel(ctx)`, plus an optional `summary(ctx, rows, read)` that
  `jobs check` appends to its last line. This is the verb contract the row asks for. It is not general game gates (B1 stays open; the list is
  its first consumer). If the contract needs more than these five names, stop (kill criteria).
- **This repo's hook module is `tools/jobs_hooks.py`** (header and tools row as for any tool). It holds: the found-path rule and its
  `jobs check` summary (the J11 hook, calling `discovery/core/briefpaths.py` as now; that file moves with `discovery/core` in J64, not here),
  rule 76 (`PROMOTIONS` and `promotion_problems`), rule 79 (everything `ACC_*` and `core_pin_diff`, `dll_build_id`) and the PC line of the view.
  `jobs/legacy.json` replaces the three frozen sets: `round_rules` (today's `LEGACY_REVIEWS`: exempt from the round rules only) and
  `brief_hooks` (`LEGACY_BRIEFS` plus `LATE_LEGACY`: exempt from the brief hooks only; the shape rules still apply). Same ids, same effect.
  The two tests that pin these sets to commits stay here and read the data file.
- **Workflows are rendered templates, not `workflow_call`.** The core ships the generic parts (the `changes` job with its pass-marker
  restore, the pass-marker save steps, the `policy` job, the `notify` job, the J57 `if:` expressions) as templates read from `[ci]`;
  `wsc ci render` writes them into the repo's `.github/workflows/` and a core gate (`ci_render`, active only when `[ci]` exists) fails when
  a committed workflow differs from its render. The slow job bodies (`proxy`, `viewer`, `harness-windows`) stay in this repo's `gates.yml`
  outside the generated blocks. Job ids and names stay `changes`, `gates`, `policy`, `notify` and the three slow ones, so the required checks
  keep their names. The `changes` and `notify` jobs now need the core checked out (they ran without it): check out the submodule shallowly
  and keep the `changes` job as fast as today (report the time before and after). Keep `WARSCAPE_CORE_TOKEN` in the checkout steps (D29).
- **The core runs its own queue.** In the same core PR: `registries/jobs/`, `jobs/`, `[registries] jobs = "core:jobs"`, `[storage] dir`
  including `jobs`, `[jobs] id_prefix = "W"`, `[policy] decision_prefix = "C"`, the two rendered workflows (`policy.yml`, plus `notify` in
  `gates.yml`; the core's `gates.yml` triggers and slow jobs are left alone), a generic `docs/REVIEW.md`, the "Jobs" section of the core's
  `CLAUDE.md`, a "The job pipeline" section in `docs/CONSUMING.md` (the tables, the hook points, the render step and the check names Liam must
  require), and one first row, `W1` "Triage the core backlog into queue rows" (`needs_brief`, `sonnet`, `needs_pc` false, no dependencies),
  so the next core change is the first to travel the pipeline. A decision line `C18` (proposed; Liam's merge accepts it): the core's `main`
  changes through the queue and a reviewer merges on green CI, replacing "a merge Liam approves" in the core's `CLAUDE.md`. Backlog: B35 and
  B8 removed, the leftovers added as rows. Required checks, auto-merge and branch protection on warscape-core are repository settings:
  Liam's, listed in the report (this job changes no repository setting).
- **A second consumer, in the core's tests.** `tests/fixture_game/` is a minimal game repo (its own `wsc.toml` with `id_prefix = "F"`,
  `decision_prefix = "X"`, a different trailer name, one input set, one hook module) copied into a throwaway git repo by the host tests. It
  must run `jobs check`, `jobs next|review|fix --offline`, `policy` on a brief, job and plan branch, `jobs view --offline` and one dry
  autopilot tick (fake `claude` and `gh`, as `tests/test_jobs.py` does today), and `ci render --check`. Real `git` throughout, no network.
- **Tests move with the code.** `tests/test_jobs.py`, `test_pr_policy.py`, `test_ci_notify.py`, `test_changed_inputs.py`, `test_workflows.py`
  (the template's `if:` logic) and, if `ci_failures` moves, `test_ci_failures.py` go to the core with the game wording replaced by fixture
  values; the "this repo's own queue passes" cases become the core's own queue and the fixture game. Left here, as tests of the hook module:
  rule 79 (`acceptance_*`), rule 76, the found-path hook, the legacy data and the PC line. `tests/test_claude_hook.py` keeps the guards and
  calls the core's trailer function. `tests/test_registry_merge.py`, `test_proxy_host.py` and `test_harness_host.py` load the moved tools
  from `core/`. No test in either repo may depend on the real game or a running `Napoleon.exe`.
- **No shim.** The local copies are deleted in the switch commit, as in J12; `tools/pr_policy.py` does not stay as a forwarder. Every living
  text that names an old path or command is fixed (grep `pr_policy`, `verbs/jobs`, `ci_notify`, `changed_inputs`, `ci_failures`, `jobs.schema`
  outside `core/`, `jobs/` and `_scratch/`): at least `CLAUDE.md`, `README.md`, `docs/REVIEW.md`, `docs/plans/PLAN.md` section 4,
  `harness/README.md`, `proxy/README.md`, `docs/CI_FAILURES.md`, `.claude/settings.json` if it names one, and the two workflows' comments.
  `docs/REVIEW.md` becomes this game's short addendum (the check names, the "Empire repeats" step, rule 79) over `core/docs/REVIEW.md`
  (one owner per topic). `docs/DECISIONS.md` rows are history and stay; a new row `D43` records the move and the new commands.
- **Release and pin.** Liam merges and tags the core (core `CLAUDE.md`). Open the core PR, ask Liam to merge it and tag `v0.9.0`, then
  stop and end the turn. Do not wait or poll. Resume when Liam says it is tagged. The switch is one commit for the pin: the `core` gitlink and
  `wsc.toml` `[core] version` together (B9), with the config tables; the deletions and the hook module may be separate commits.
- **No real sessions in the proof.** The autopilot is only ever run with `--dry-run`; this job never starts a `claude --bg` session.

## Deliverables
1. **Golden outputs** (before anything changes), stdout, stderr and exit code of each, with timestamps and ports masked:
   - `jobs check`; `jobs next --offline`; `jobs next --id J62 --offline` and `--id J11 --offline` (the refusal); `jobs review --offline`;
     `jobs fix --id J57 --offline`; `jobs review --id J57 --offline`;
   - `jobs view --offline --no-open --out <file>` (the page) and with `--all`;
   - one dry autopilot tick: `jobs view --serve --offline --auto --interval 30 --dry-run --no-open`, stopped after the first tick; the lines
     of `_scratch/jobs_auto.log` and stderr;
   - the policy: the old `check()` run on recorded inputs (the changed files, both row dicts, the file texts, the trailer sets and the rule 79
     facts as one JSON file) for 12 real pull requests (the heads of `origin/job/J52`, `J54` to `J58`, `J11` and `J66`, and four brief or plan
     branches from `gh pr list --state merged`) plus the five branch names `job/J62`, `brief/J62`, `plan/x`, `meta/x` and `foo/bar`; the output
     is the error list of each. The CLI itself is checked by hand on the job branch (item 4); HEAD moves, so it has no golden;
   - `python3 tools/changed_inputs.py --base <sha>` for four fixed shas (a workflow-only change, a `proxy/` change, a pin bump, a docs change);
   - `ci_notify.py --dry-run` for a recorded failed-run fixture, and the step texts (`brief_steps`, `build_steps`, `review_steps` and
     `fix_steps` for `J62`, `review_steps` with a merge and a non-merge verdict).
   Record the sha256 of each in the report.
2. **The core PR** (`warscape-core`, branch `napoleon-j62`): the verbs and libraries, the config tables and their defaults, `core:jobs`, the
   templates and `ci_render` gate, the hook contract and its host tests, the fixture game, the core's own queue and docs (above), tools rows for
   every new file, `VERSION` 0.9.0, the `C18` line, the backlog update. Core `python3 wsc.py gates` green on Linux and Windows CI, and the core
   PR touches no file under the core's `proxy/` or `harness/`.
3. **The switch** (after the tag, on `job/J62`): the pin and config commit; `tools/jobs_hooks.py` and `jobs/legacy.json`; the rendered
   workflows; the deletions and superseded or removed tools rows (follow `jobs/J12/report.md`); the moved tests; the grep fixes; `D43`.
   `[cli] verb_dirs` keeps `tools/verbs` for the other verbs; `[registries] jobs = "core:jobs"`.
4. **Proof of an invisible move**, run after the switch against the Part 1 captures:
   - every golden output from item 1 has an identical sha256, except the allowed differences, each listed with its diff in the report: the
     schema description, and nothing else expected. A step text or a view that changed is a bug, not a difference;
   - the rendered `gates.yml` and `policy.yml` equal today's files outside a header comment line; `tests/test_workflows.py` (or its core
     successor) passes against them; the required checks keep their names;
   - `python3 core/wsc.py gates` green here, `python3 core/wsc.py jobs check` ok with the same row count and "0 registry gaps in briefs";
   - `python3 core/wsc.py policy --branch job/J62 --base origin/main` refuses only on the reviewer's part (no `review.md`, row not `done`),
     with no rule 79 error (the core diff leaves `proxy/` and `harness/` alone); the recorded policy inputs from item 1, fed to the new
     `check` with this repo's config and hook module, give the same error lists (the old script no longer exists, so the command in the steps
     and in `policy.yml` is the new one);
   - the fixture game's host tests pass in the core's CI (give the run id), and `changes` runs in about the time it did.
5. **The report** also lists, for Liam: the repository settings the core now needs (required checks `gates`-style names, auto-merge, branch
   protection, whatever the core's CI actually reports), the job branches still open on old paths, and the backlog rows `W1` should open.

## Kill criteria
- Any of the Part 1 captures differs after the switch for a reason other than the allowed differences, and two attempts to find the cause
  fail: stop. Report the diff and the commands; do not widen the allowed list.
- The core change needs an edit under the core's `proxy/` or `harness/`: stop before merging anything and report. Rule 79 would demand 20
  acceptance passes this job cannot run.
- The workflow render cannot keep the required check names, or the `changes` job gets slower by more than 30 seconds: stop and report the
  numbers with the alternative (a `workflow_call` workflow plus a branch-protection change that only Liam can make).
- The hook contract needs more than the five names above, or the `jobs` verb needs game code that cannot be expressed as config or a hook:
  stop. That is B1 (general game gates); report the proposal rather than building it.
- Budget: at the cap after Part 1, push the core branch and the report stub and stop; the switch is a second sitting.

## Open questions
Settled as recommended unless Liam answers before the builder reaches them; a `D` line records any change.
1. **Rendered templates or `workflow_call`?** Recommended: rendered templates with a core gate, because a reusable workflow renames the
   required checks and changing branch protection is Liam's. A `workflow_call` workflow is the alternative once he is willing to re-point
   the checks.
2. **Core job ids.** Recommended `W<n>` (branches `job/W1`, `brief/W1`), so a core job never collides with a game's `J<n>`, with `X` the fixture's
   prefix. The alternative is `K<n>`. The first row is `W1`, the backlog triage; the builder does not convert backlog rows itself.
3. **`ci_failures.py`.** Recommended: it moves with its classes as game data (`ci/failure_classes.json` here), as long as that costs about 15
   calls; if the classes are woven through the code, it stays here as a tool and the report says so. `docs/CI_FAILURES.md` stays (a dated
   record).
4. **Hook points or B1?** Recommended: the five-name hook contract now. B1 later replaces it with the general `[gates]` modules; the hook
   modules then become gate modules.
5. **In-flight sessions.** Recommended: no shim. A review or fix session started before the switch and still running will find
   `tools/pr_policy.py` gone after it pulls; `wsc jobs review|fix` prints the new command to a session that reads it again. The report names
   any job in `review` or `fix` at the switch.
6. **Repository settings on warscape-core** (required checks, auto-merge, branch protection) are Liam's; until he sets them, a core
   `job/` branch's `gh pr merge --auto` has nothing to wait for and merges at once. Recommended: he sets them before the first core job runs
   (`W1`); this job's report lists the check names.
7. **The core's own slow jobs.** Recommended: leave the core's `gates.yml` triggers and its proxy and harness jobs alone here (J42's
   push-only trigger and J54's skip are worth adopting there, as a core backlog row), so that this job's CI risk stays in the pipeline.

## Finish
Write `jobs/J62/report.md`. Cover:
- what moved, as a table of old path and core path, and what stayed and why (the hook module, the legacy file, the guards)
- the core PR and the tag, the core's CI run id, and the fixture-game tests
- the before and after sha256 table of every golden output, with each allowed difference and its diff
- the `changes` job time before and after, and the check names
- deviations from this brief and why, the Open questions as settled, and the repository settings Liam must change
- open job branches on old paths, and what each needs
- the core backlog rows now closed (B8, B35) and added

Then `wsc reg set jobs J62 status=review report=jobs/J62/report.md`.
