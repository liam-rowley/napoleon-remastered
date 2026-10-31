# J55: Registry views out of git; job rows one file per job

Phase 1, tooling (pipeline audit 2026-10-31, item 2). Concurrent jobs collide in the registries. Of the 27 job branches, 26 change
`registries/jobs.jsonl` and `jobs.md`, 24 change `tools.jsonl` and `tools.md`, 15 change `engine_facts.jsonl` and `engine_facts.md`
(counted 2026-10-31 against each branch's base on main). GitHub ignores `merge=union` on pull-request merges (community discussion
9288), so two jobs in flight conflict and auto-merge stalls: the branches carry 17 merge-main commits (10 after the merge verdict), each
touching 6 to 18 registry files, several citing a conflicted generated view or a union merge that kept both rows, each costing a session,
a hand de-duplication and a full slow-CI re-run. Two core changes remove the causes: generated views stop being committed, and a
registry can keep one file per row so two jobs never edit the same file. Then this repo switches over. Target: 0 merge-main commits per
job branch for registry reasons (17 over 27 branches today).

Model: Sonnet. Python tooling, schemas and tests in warscape-core and this repo; no engine, DLL or PC work. Budget about 150 tool calls
over both parts; at the cap, stop, commit, report what is left. Subagents are not needed.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J55`; "The core": a core change is made in a separate `warscape-core` clone beside this one, on a
  branch, as a pull request). Read `core/CLAUDE.md`, `core/docs/CONSUMING.md` (upgrading the pin), `core/docs/BACKLOG.md` (B4, B9),
  `core/warscape/registry.py` in full (its docstring is the storage contract), `core/warscape/gates.py` (`gate_registries`, the `json`
  gate), `core/warscape/verbs/reg.py`, `core/warscape/search.py` and `core/warscape/tools.py` (the `tools` registry is derived from file
  headers and written by the core).
- In this repo: `wsc.toml`, `.gitattributes` (the `merge=union` and `linguist-generated` lines), `.gitignore`, `tools/pr_policy.py`
  (`JOBS`, `PLAN`, `META`, the `brief/` and `job/` row rules), `tools/verbs/jobs.py` (`load_rows`, `branch_rows`, `run()`),
  `tools/changed_inputs.py` (the proxy set names `registries/(engine_sites|config_keys).jsonl`), and every direct reader of a registry file:
  `grep -rln "registries/\|\.jsonl" --include=*.py --include=*.yml --include=*.sh --include=*.ps1 . | grep -v "^./core/\|/runs/"` lists
  them (2026-10-31: `discovery/core/{assets,exe,sheets}.py`, `tools/verbs/{discovery,hotkeys,jobs}.py`, `upscale/napoleon/cli.py`,
  `tools/pr_policy.py`, `tools/changed_inputs.py` and ten test files).
- `jobs/J12/report.md`: the last job that changed the core and bumped the pin (one commit, B9). J54 and J56 also change
  `tools/verbs/jobs.py`; this job depends on J56 (one fetch in `branch_rows`), so start from a main that has it and change its one
  row-reading function.

## Target facts
Check each again before relying on it:
- The core pin is `v0.4.0` (`wsc.toml` `[core] version`, the `core` gitlink); the next core release is `v0.5.0`, `VERSION` says `0.5.0`.
- Registry rows today (2026-10-31): assets 12295, hotkeys 128, engine_facts 123, tools 82, jobs 56, config_keys 28, engine_sites 11,
  scenarios 10, ui_elements 0. Ids are dotted names (`discovery.core.api_inventory`, `napoleon.assets.image_headers`) or `J<n>`.
- 8 of the 9 registries use a core schema (`core:<name>` in `wsc.toml`); only `jobs` has a repo schema. A schema keyword would need the
  core schemas changed for one game's storage choice, and B2 (extending a core schema) is not built.
- Count the merge-main commits per job branch yourself (first-parent merges of `main` into `job/*`) and name, for each, the registry
  files that conflicted or were touched; the row's 17 is the baseline.

## Decisions already made for this job
- **Part 1, warscape-core (a pull request; Liam merges and tags `v0.5.0`).** Both changes are opt-in, so a repo that sets nothing keeps
  today's behaviour byte for byte (the core's own tests prove it):
  - (a) **Views not committed** (B4 extended). A `wsc.toml` switch in its own table (`[registries]` maps names to schemas, so not
    there; for example `[views] commit = false`) makes `wsc reg render` and `reg add|set` write views to a
    git-ignored directory (default `_scratch/registries/`, `--out DIR` on `reg render`), and `gate_registries` checks that every view
    renders without error instead of comparing it with a committed file; with the switch on, a committed `<registries_dir>/<name>.md`
    is an error (a stale copy cannot linger). `wsc find` must not depend on the views.
  - (b) **One file per row.** A per-registry storage choice declared by the repo, not the schema (see Target facts): for example a
    `wsc.toml` `[storage]` table `dir = ["jobs", ...]`. Rows of such a registry live in `<registries_dir>/<name>/<file>.json`, one row per
    file in canonical form (keys in schema order, one trailing newline; say whether one line or indented, and why), the file name derived
    from the id by a documented, reversible, Windows-safe rule (the `windows_paths` gate is the rule), the id still inside the file and
    checked against the name. `Registry` loads, validates, writes (`reg add|set`), renders and searches both storages through one API;
    duplicate ids are impossible by construction, a file whose name and id disagree is an error. `wsc reg migrate <name> --to dir|jsonl`
    moves a registry between storages in one step.
  - Core host tests for both, through the core's null game; the core's `docs/` and the `registry.py` docstring updated; B4 removed from
    `BACKLOG.md` (or narrowed to what is left), and a new backlog row for anything you leave.
  - Open the core pull request, ask Liam to merge it and tag `v0.5.0`, then stop and end the turn. Do not wait or poll. Resume when Liam
    says it is tagged. Commit and push this repo's `job/J55` before you stop (the report's Part 1 section and the core PR link).
- **Part 2, this repo, after the tag.**
  - One commit (B9) bumps `core` and `wsc.toml` `[core] version` to `v0.5.0` and turns the switches on; then the migration.
  - Views: delete every committed `registries/*.md`, git-ignore the render directory, drop the `registries/*.md linguist-generated` line.
  - One file per row for `jobs`, `tools` and `engine_facts` (the three most-collided registries above). The others stay JSONL: `assets`
    is 12295 game-derived rows touched by 4 branches, and the rest are small and rarely touched; say in the report what would move them.
    Drop the `merge=union` lines for the registries that moved; keep it for those that did not.
  - Every direct reader switches to the core's loader (or one helper in this repo that calls it), including `pr_policy.py` (it reads the
    jobs rows at the base and at the head: `git show <ref>:<path>` becomes a read of the per-id files at a ref; keep its rules unchanged),
    `jobs.py` (`load_rows` and the one row-reading function J56 left in `branch_rows`), `changed_inputs.py` (only if an input set's paths
    move; `engine_sites` and `config_keys` stay JSONL) and the tests. The `PLAN` and `META` path lists in `pr_policy.py` follow the new
    paths (a `brief/` branch may change `registries/jobs/J<n>.json` and nothing else under `registries/`).
  - `README.md` and `CLAUDE.md`: the job queue's status page is `python3 core/wsc.py jobs view` (no committed `jobs.md`); every doc or
    brief sentence that says to merge `main` before the pull request, or that names `registries/jobs.jsonl` or a committed view, is fixed
    (grep for them; earlier jobs' briefs and reports are history and stay as they are).
- **Out of scope:** moving `assets` or the small registries to one file per row; changing any schema's fields; Empire; branch protection.

## Deliverables
1. A warscape-core pull request with (a) and (b), their tests and docs, merged and tagged `v0.5.0` by Liam (its link in the report).
2. On `job/J55`: the pin bump with the switches on, the migration of `jobs`, `tools` and `engine_facts`, the committed views removed,
   `.gitattributes` and `.gitignore` updated, every direct reader moved to the loader, the docs fixed.
3. A test in this repo that two branches each adding a different job row and each changing a different tool header merge with no
   conflict (build both in a temporary repo from the real layout and `git merge` them; `merge=union` must not be what makes it pass).
4. The measurement: merge-main commits per job branch and their registry causes before (from the existing branches), and the conflict
   test's result after; the expected count per branch for registry reasons is 0.
5. `python3 core/wsc.py gates` green; `wsc jobs check`, `wsc find J55` and `wsc jobs view --no-open` work on the new layout.

## Kill criteria
- The core change cannot be made opt-in (Empire's or the null game's behaviour would change with nothing set): stop and ask Liam.
- Liam declines the core pull request or asks for changes you cannot make within the budget: stop, report, keep `job/J55` with Part 1
  only.
- `pr_policy.py`'s base-and-head row rules cannot be kept unchanged on per-id files: stop and ask before weakening any rule.
- Over about 150 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J55/report.md`: Part 1 (the core pull request, the tag, the switches and the file-name rule) and Part 2 (the migration, the
readers changed), the merge-main measurement and the conflict test, the test list and the gates result, deviations from this brief and
why, open questions (moving `assets` and the small registries; whether Empire wants the same switches). Then
`wsc reg set jobs J55 status=review report=jobs/J55/report.md`.
