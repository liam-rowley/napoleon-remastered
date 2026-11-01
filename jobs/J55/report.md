# J55 report: Registry views out of git; job rows one file per job

Generated views are no longer committed. The three registries that collided most (`jobs`, `tools`, `engine_facts`) now keep one file
per row, so two jobs in flight never edit the same registry file. Part 1 is warscape-core 0.6.0
([liam-rowley/warscape-core#11](https://github.com/liam-rowley/warscape-core/pull/11), merged by Liam as `d4c2677` and tagged `v0.6.0`).
Part 2 switches this repo over. **It cannot merge yet:** rule 79 counts the core pin bump as a DLL or harness change and wants 20
acceptance passes on the PC (Open questions 1).

## Part 1: warscape-core

- Pull request: [liam-rowley/warscape-core#11](https://github.com/liam-rowley/warscape-core/pull/11), branch `registry-storage-j55`,
  `VERSION` 0.6.0. **Deviation:** the brief expected the pin at `v0.4.0` and this release to be `v0.5.0`. J40 had already bumped the
  pin to `v0.5.0` (main `40c639e`), so this release is **`v0.6.0`**.
- Both switches are opt-in. A repo that sets neither keeps the 0.5.0 layout byte for byte: the core's own registries and committed
  views pass the gates unchanged, and `tests/test_storage.py` `Defaults` covers it.
  - **`[views] commit = false`** (a new `wsc.toml` table, default `commit = true`, `dir = "_scratch/registries"`). `reg render` and
    `reg add|set` write views to that dir (`reg render --out DIR` too). The registries check renders each view and does not compare
    it, and a `<registries_dir>/<name>.md` on disk is an error. `wsc find` reads rows only.
  - **`[storage] dir = [...]`**: the registries listed keep one row per file, at `<registries_dir>/<name>/<id_to_file(id)>.json`.
    Each file is canonical: keys in schema order, **indented two spaces**, one trailing newline. Indented, not one line, so a field
    change shows as a one-line diff and two branches that change fields far apart in the same row still merge.
  - **File-name rule (`id_to_file`):** the id is percent-encoded as UTF-8. Every character except ASCII letters, digits and `_.-~`
    becomes `%XX` (`%` included). The first character is also encoded when the name would start with a Windows device name (`con` ->
    `%63on.json`). Then `.json` is appended. The rule is reversible (`file_to_id`) and passes the `windows_paths` rule. `J55` ->
    `J55.json`, `discovery.core.api_inventory` -> `discovery.core.api_inventory.json`.
  - **Errors:** a file whose name and id disagree; a stray non-`.json` file; a non-canonical file; a second copy in the storage the
    repo does not declare. `add` refuses ids that differ only in case. A duplicate id cannot be stored. An empty registry is no folder.
  - `wsc reg migrate <name> --to dir|jsonl` moves the rows and rewrites `[storage] dir` in `wsc.toml`.
- Docs: the `registry.py` docstring (the storage contract), a `CONSUMING.md` section "Registry storage and views", the README, C15.
  B4 is narrowed to repos that still commit views; B25 (`wsc reg remove`) is new.
- Tests: `tests/test_storage.py`, 14 tests, including a real `git merge` of two branches. Each branch adds one row and changes a
  different existing row, with no `.gitattributes`. Core `python3 wsc.py gates`: 11 ok, 1 warn (the existing POSIX-only hook-test
  skip), 90 host tests.
- Dry run on a copy of this repo's registries: `jobs` (57 rows), `tools` (84) and `engine_facts` (123) migrate and check clean.

## Measurement (before)

Every first-parent merge of `main` into the 30 `job/*` branches on origin (2026-11-01; measured by the throwaway script described below):
**17 merge-main commits on 15 branches, and all 17 change `registries/`.** This matches the brief's baseline. Every one touches
`jobs.jsonl` and `jobs.md`:

| Branch | Merge | Registry files the merge changed |
|---|---|---|
| J3 | 6e0d612 | jobs |
| J4 | dede003 | jobs, tools |
| J5 | c486565 | jobs |
| J6 | 600ee06 | jobs, tools |
| J7 | c7a5189 | jobs, tools, engine_facts, scenarios |
| J12 | 6ab3ccf | jobs, tools, engine_facts |
| J15 | f3e49d2 | jobs, tools, engine_facts, hotkeys |
| J18 | 35bd495 | jobs, tools, engine_facts, assets |
| J19 | 5740ece, df5de86 | jobs; jobs, tools |
| J21 | 0466ee5 | jobs, tools, engine_facts, config_keys |
| J31 | 98019da | jobs |
| J42 | 4fb6d30 | jobs |
| J44 | 83be4aa, 8d03a16 | jobs; jobs |
| J50 | 2a94296 | jobs, tools, engine_facts |
| J51 | 4a7f087 | jobs |

Each entry means `<name>.jsonl` and `<name>.md`. Several subjects name the cause, for example "regenerated jobs view" (J42) and
"registry views re-rendered from the merged rows" (J50). After Part 2, 13 of the 17 change only `jobs`, `tools`, `engine_facts` and
views, so they have no registry cause left. The other 4 (J7, J15, J18, J21) also touched a registry that stays JSONL: a conflict
there is possible only when two branches add rows to the same small JSONL.

Method: for each branch, the first-parent merges whose second parent is on `main`, and `git diff --name-only <first parent> <merge>
-- registries/` for each. The script lived in the session scratchpad and is not committed. Part 2's conflict test replaces it as the
lasting check.

## Part 2: this repo

- **The pin, in one commit (B9):** the `core` gitlink and `wsc.toml` `[core] version` both move to `v0.6.0`. The same commit sets
  `[views] commit = false`, deletes the nine committed `registries/*.md`, and drops the `registries/*.md linguist-generated` line.
  `_scratch/` was already git-ignored, so the render folder `_scratch/registries/` needed no new line.
- **The migration:** `wsc reg migrate <name> --to dir` for `jobs` (57 rows), `tools` (84) and `engine_facts` (123). `wsc.toml` now
  has `[storage] dir = ["jobs", "tools", "engine_facts"]`. The `registries/*.jsonl merge=union` line stays for the six JSONL
  registries; it never matches the per-row `.json` files.
- **Readers changed:**
  - `tools/pr_policy.py`: `rows_at(ref)` reads the per-id files at a ref with one `ls-tree` and one `cat-file --batch`. When the ref
    predates J55 it falls back to `jobs.jsonl`, so J55's own pull request and any branch cut before it are judged on the same dicts.
    The rules are unchanged.
  - The `PLAN` list now holds `registries/jobs/*`. A `brief/J<n>` branch may change `jobs/J<n>/brief.md` and
    `registries/jobs/J<n>.json` and nothing else. `META` (`registries/*`) already covers the folders, because `fnmatch` `*` spans `/`.
  - `tools/verbs/jobs.py`: `main_rows(ctx)` reads the working tree through the core's `load_all`. J56's one row-reading function,
    `branch_row_spec`, now returns the per-id spec first and the JSONL spec second. `branch_rows` reads both in its single
    `cat-file` batch and takes the first one present, so it is still one fetch and three git calls.
  - `tools/changed_inputs.py` is unchanged: its input sets name `engine_sites` and `config_keys`, which stay JSONL. The other direct
    readers (`discovery/core/{assets,exe,sheets}.py`, `tools/verbs/{discovery,hotkeys}.py`, `upscale/napoleon/cli.py`, the scenario,
    hotkey, ctl, acceptance and job_sh tests) read registries that did not move.
- **Docs:** `README.md` (the queue's status page is `python3 core/wsc.py jobs view`; how to get the views), `CLAUDE.md` (the queue's
  files; views not committed), `docs/plans/PLAN.md` section 3.2, and the `jobs` and `pr_policy` headers (their tool rows refreshed).
  No living doc or brief told anyone to merge `main` before the pull request: the grep found the step only in earlier jobs' briefs,
  reports and commit messages, which are history.

## Conflict test (after)

`tests/test_registry_merge.py` copies this repo's real `wsc.toml`, `.gitattributes`, `.gitignore`, `schemas/`, `registries/` and two
real tools into a temporary repository. Two branches each add a job row and change a different tool header (`reg add tools`), all
through the real `wsc`. The test checks that `git check-attr merge` is `unspecified` for every changed file, so `merge=union` plays no
part. Then `git merge` gives **exit 0, no conflict**, with both rows and both header changes present and no `registries/*.md`.
Expected merge-main commits per job branch for registry reasons: **0**, apart from the residual JSONL case in the measurement above.

## Tests and gates

- New: `tests/test_registry_merge.py`. In `test_pr_policy.py`: `rows_at` gives the same rows from either layout; a pre-J55 base with
  a per-id head passes, and still refuses a change to another row; brief branches may touch only their own row file; plan and meta
  scopes. In `test_jobs.py`: a pre-J55 branch's row is still read in the same single batch. Updated to the new paths:
  `test_jobs.py`, `test_pr_policy.py` and `test_proxy_host.py`.
- `python3 core/wsc.py gates` (2026-11-01, this branch): 11 ok, 1 warn (14 skips: no numpy or Pillow, no viewer build), 0 failed, 444 host tests. `wsc jobs check`, `wsc find J55` (the job row is a hit) and
  `wsc jobs view --no-open` (57 jobs) work on the new layout.
- `python3 tools/pr_policy.py --branch job/J55 --base origin/main` refuses for the expected reasons (no review yet, row not `done`)
  and for rule 79 (Open questions 1).

## Deviations

- The core release is `v0.6.0`, not `v0.5.0`: J40 had already pinned `v0.5.0`.
- Two commits on the branch, not one, for the switch: the pin bump with `[views] commit = false` (the B9 pair stays in one commit),
  then the migration. Turning `[storage] dir` on before the rows move would leave a commit whose gates fail.
- The readers of the six JSONL registries were not moved to the core loader. Their files did not move, and the brief scopes this to
  the readers of moved registries ("only if an input set's paths move").

## Open questions

1. **Rule 79 blocks this merge.** `acceptance_problems` counts any change to the `core` gitlink as DLL or harness code (since J12),
   so J55 needs 20 acceptance passes on the PC, which the brief excludes (`needs_pc` no). v0.6.0 changes only `warscape/` Python,
   tests and docs: `core/proxy/`, `core/harness/` and `core/saves/` are byte-identical to v0.5.0, and the DLL build id is unchanged
   (`f3e33f228416`, the same as J40's passes). I did not weaken the rule. Either run the 20 passes for `job/J55` on the PC, or file a
   rule change as its own job: exempt a pin change when the submodule diff between the two pins leaves `proxy/` and `harness/`
   untouched.
2. **Moving `assets` and the small registries.** `assets` (12295 game-derived rows, touched by 4 of the 30 branches) would be 12295
   files; it is worth moving only if branches start adding asset rows concurrently, or when discovery decides whether game-derived
   rows are committed at all (core B4). `scenarios`, `hotkeys`, `config_keys`, `engine_sites` and `ui_elements` each move with one
   `wsc reg migrate` once a measurement shows two jobs colliding on one of them (J7, J15, J18 and J21 each touched one).
3. **Empire.** The switches are opt-in, and Empire's layout is unchanged. Whether Empire wants them is for its own queue: the same
   collision measurement would tell.
4. A row cannot be deleted by a verb yet (core B25). With one file per row, `git rm` of the file works.
