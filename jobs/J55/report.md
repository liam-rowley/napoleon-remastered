# J55 report: Registry views out of git; job rows one file per job

**Status: Part 1 done; waiting for Liam to merge [warscape-core#11](https://github.com/liam-rowley/warscape-core/pull/11) and tag
`v0.6.0`. Part 2 (this repo) starts after the tag.**

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

Not started: it needs the `v0.6.0` tag.
