# J94 report: Napoleon tools, tests and gates: small fixes

Written by the orchestrator from the builder subagent's hand-back (the harness refuses a subagent's write of a report file); the text is
the builder's own apart from this note. Branch `job/J94`: six of the seven items are built there, one commit each (hotkeys verb, repo-rule
tests, setup checks, Promotions fixtures, shot_sheet purpose, release/core promotion row J100, which policy sent to PR #194). Item 5 (`proxy.dxvk_path` description)
stopped under its kill criterion: the registry text alone makes the committed adapter ini stale (the `tests` gate fails), and regenerating
the ini changes the DLL build id (rule 79, a PC job). Python, tests and registry rows only; no game, PC, watcher or `core/` change.

## What was built
Each item was re-checked on `origin/main` at `e1cb6a8` (the J94 brief merge) before it was changed: all seven still applied.

1. **`tools/verbs/hotkeys.py`** (J21-L2, L3, L4), commit `f46c925`.
   - `GAME_DATA` comes from `discovery/napoleon/games.json` (`napoleon.root` joined with `napoleon.data`, as a Windows path on any host) via
     the new `game_data(path)`, which returns `(None, error line)` for a missing or broken file instead of a traceback. `--from-pack` with no
     folder uses it and prints the error line when it is missing; `--from-pack DATA_DIR` is unchanged. `load_loc` reads the same `GAMES_JSON`.
   - `KNOWN_OS_COMBO` and `KNOWN_VANILLA_CLASH` moved to **`tools/verbs/hotkeys_known.json`** (a data file beside the verb; the verb loader
     globs only `*.py`). The verb header (old lines 11 and 23) names it. `load_known()` reads it for the verb and for `tests/test_hotkeys.py`;
     `hotkeys check` no longer touches `sys.path` or imports from `tests/`.
   - `split()` uses `canon()` instead of `str.capitalize()`: one character upper-cased, else a case-insensitive lookup into the canonical
     names (`KEY_NAMES` values, `ORDER`, `KEY_ALIAS` keys and values, `MODS`, the Win modifiers, F1-F24, Numpad0-9), else the text as typed.
   - Tests (`tests/test_hotkeys.py`): `test_split_keeps_canonical_names` (`split('Ctrl+NumpadAdd') == (['Ctrl'], 'NumpadAdd')`, lower-case
     input, an unknown name kept as typed); `VerbInputs.test_game_data_is_the_games_json_value` (the module value against games.json, an
     injected games.json, a missing file); `VerbInputs.test_check_runs_without_tests_on_the_path` (a fresh `-I` interpreter whose import hook
     refuses `test_hotkeys` runs `wsc hotkeys check` and asserts no `tests` folder on `sys.path`). On the old verb the module fails to load
     (`load_known` missing); one by one, the split test gets `Numpadadd`, `game_data` does not exist and the old `check` imports `test_hotkeys`.
2. **`tests/test_repo_rules.py`** (J5-L3, J22-L1/L4), commit `0c2d1a5`.
   - `silenced()` uses `quoted_by_a_row()`: one decision table line (starting `|`) must name `wsc.toml`, quote the section in backticks
     (`` `[gates] skip` `` or `` `[gates]` ``) and quote the value. Fixtures (`Fixtures.test_silenced`): a value-only row, section and value
     in two rows, and the wrong section no longer clear the skip; a row with both does.
   - `BARE_BASH` runs over the whole text (comments cut per line, line breaks kept, so a hit maps to its line), which catches an argv list
     whose `'bash'` is on the next line, and now also hits `shutil.which('bash')` (and `'bash.exe'`). `BARE_BASH_ALLOWED` also takes
     `file::function` keys; one new entry with its reason, `tools/verbs/setup.py::check_git_bash` (it passes the PATH bash to `bash_check`
     only so setup can warn about the WSL launcher; it never runs it). That was the only new hit in the tree; `git_bash()` itself uses its
     injected `which('bash')`. Fixtures for every shape, failing and passing: `Fixtures.test_bare_bash_j94_shapes` (`shutil.which('bash')`
     left the old ok list).
   - **`.sh` files: not scanned (chosen).** No `harness/*.sh` or `tools/**/*.sh` exists outside `harness/runs/**`, and the tracked shell
     scripts (`harness/runs/**`, `saves/napoleon/load_save.sh`, `viewer/core/build.sh`, `upscale/runs/**`) hold no Python-style launch
     (`['bash'` / `"bash"]`): no real shape exists, so per the brief there is no scan. The comment above `BARE_BASH` says so.
3. **`tools/verbs/setup.py`** (J70-L1, J41-L4, J45-L2), commit `92c3eea`.
   - `check_watcher` uses the new `watcher_detail(rc, out, now)`: it parses the `watcher.status` JSON in the `job.sh status` output and shows
     the watcher version, game state, heartbeat age (from `heartbeat_utc`), queue length and any lock owner; on a failing exit the line after
     the JSON is added; when no JSON parses, the first output line. A failing exit keeps its fix hint. Real run on the PC (read-only status):
     `ok   watcher: job.sh status exit 0: watcher 1.2.0, game not_running, heartbeat 1s old, queue 0`.
   - `git_bash()` no longer probes `%LOCALAPPDATA%/Git`; `%LOCALAPPDATA%/Programs/Git` is added only when `LOCALAPPDATA` is set (it used
     to give `/Programs/Git` when unset).
   - New `pillow` check (after `playwright` in `CHECKS`): `python3 -c 'import sys, PIL ...'`, the interpreter `core/harness/acceptance.py` runs
     under (`python3 core/harness/acceptance.py`, harness/README.md). The pure `pillow_result(rc, out)` is always ok; a missing PIL gives a
     `warn:` detail with `python3 -m pip install pillow`. On this PC: `ok   pillow: Pillow 13.0.0 for C:\Users\liamr\AppData\Local\Python\pythoncore-3.15-64\python.exe`.
   - The header purpose names both; the `wsc.setup` row is resynced (`wsc reg add tools tools/verbs/setup.py`).
   - Tests (`tests/test_setup.py`): `test_watcher_detail_reads_the_status_json` (multi-line JSON as the watcher writes its fields, lock,
     failing exit, no JSON), `test_watcher_check_failing_exit_keeps_its_fix`, `test_git_bash_roots_skip_localappdata_git` (injected
     `os.environ` and `isfile` recording every probed root), `test_pillow_result_warns_never_fails`.
4. **`tests/test_jobs_hooks.py`** (J70-L2), commit `f0d3b19`. The `Promotions.T` fixture table uses `area_a/core` and `area_b/core` (a
   docstring line says why). New `test_the_real_table_names_no_folder_that_is_gone`: a `PROMOTIONS` entry whose folder has no tracked files
   fails unless its promotion job is `done` (a done entry, the three J12 folders, is the record that the folder stays gone, which rule 76
   enforces). Today every open entry (`discovery`, `upscale`, `uiscale`, `viewer`, `release`) has tracked files. The rule-79 fixtures further
   down still use `proxy/core/dev.cpp` paths; they were outside the brief's lines and any `proxy/` path exercises them, so they stay.
5. **`proxy.dxvk_path` description** (J23-L1, our half): **stopped, not changed**; see Deviations.
6. **`tools.shot_sheet` purpose** (J24-L2), commit `e760c72`. The header ends `a missing shot is a grey cell with "missing" in its label`
   (true to the code: `' | missing'` in the cell label); the row is resynced through the tools gate's own route (`wsc reg add tools
   tools/shot_sheet.py`). New guard `ThisRepo.test_tool_rows_keep_their_quotes`: a `registries/tools` row whose purpose has an odd number of
   double quotes fails (it failed on the old shot_sheet row). Grep of `tools/*.py` and `tools/**/*.py`: no other trailing quote. Repo-wide one
   more header has the shape, **`uikit/napoleon/changes.py`** (`flag a locked screen as "changed since lock"`): outside this job's files, so
   it is allow-listed in `PURPOSE_QUOTE_ALLOWED` with that reason (Open questions).
7. **`release/core` promotion** (J38-L3), commits `3aa3889` then `e8b6896`. Row **J100** "Promote release/core to warscape-core":
   `needs_brief`, phase 5, `depends_on` J63, model opus, `needs_pc` false; the description names the release builder, installer scripts and
   support bundle (J38), the adapter that stays (`release/napoleon`) and that it is held until a second game ships. The core policy refuses
   a job branch that changes another row, so the row now lives on **`plan/J100-release-core-row`, PR #194** (policy ok there; Liam merges,
   D50), and on `job/J94` `PROMOTIONS['release/core']` stays `None` with its comment naming J100 and PR #194 (see Deviations). Nothing
   else: **`uiscale/core` (J66) keeps `None` and has no row**.

## Evidence
- `python3 core/wsc.py gates --fast`: 13 ok, 0 failed after every commit (job-J94 worktree, 2026-11-04).
- `python3 core/wsc.py gates` (full, at `3aa3889`): 13 ok, 1 warn (tests: 641 host tests passed, 30 skipped for absent numpy/Pillow in that
  interpreter, viewer.wasm, capstone), 0 failed, 328 s. `gates --fast` after merging `origin/main` (`ce95c94`): 12 ok, 1 warn, the `hooks`
  gate, because the shared clone's `core.hooksPath` is now the absolute `C:\Users\liamr\repos\napoleon-remastered\core\.githooks`, which
  another session set (it was relative earlier in this run). I did not change it.
- `python3 core/wsc.py policy --branch job/J94 --base origin/main`: the only refusals left are the report (written by the orchestrator),
  `review.md` and row `done`, which belong to the reviewer. `plan/J100-release-core-row`: policy ok.
- `python3 -m unittest tests.test_hotkeys tests.test_repo_rules tests.test_setup tests.test_jobs_hooks`: 25, 13, 17, 44 tests OK.
- No game run, no watcher job, no PC write; the only PC contact was the read-only `job.sh status` inside `wsc setup`'s watcher check.

## Deviations from the brief and why
- **Item 5 stopped (kill criterion).** The brief's default was "change the registry text only". With the reworded description in
  `registries/config_keys.jsonl`, `python3 core/proxy/tools/gen_tables.py --check` reports `STALE ... proxy\napoleon\napoleon_remastered.ini`,
  which is `tests/test_proxy_tables.py` in the `tests` gate: the registry-only route fails the gates. `python3 core/proxy/tools/build_id.py
  --inputs` shows `adapter proxy/napoleon` hashed as a tree, so the ini is a DLL input: regenerating it changes the build id and rule 79
  (`tools/jobs_hooks.py acceptance_problems`, any `proxy/` change) would need 20 PC passes, which a `needs_pc: false` job cannot run. The
  registry edit was reverted; nothing of item 5 is on the branch.
- **Item 7 split.** The brief said to add the row with `wsc reg add jobs` on this branch and set the table entry. `wsc policy` refuses it
  ("a job branch may change only its own row; it also changes J100"), and a table entry naming a row that is absent fails rule 76. So the
  row went to `plan/J100-release-core-row` (PR #194, plan branches may change the jobs registry), and the entry stays `None` here. Once #194
  is on main, a one-line follow-up (or the reviewer's fix round, after merging main) sets `PROMOTIONS['release/core'] = 'J100'` and adds
  `('release/core', 'J100')` to `test_promotions_name_rows_that_exist`.
- Item 6 adds a test (the deliverables ask for tests per item) and allow-lists, rather than fixes, the second trailing-quote header
  `uikit/napoleon/changes.py`: outside the brief's files, with other jobs running in parallel.
- Item 2: `BARE_BASH_ALLOWED` gained the `file::function` form so `setup.check_git_bash` is allowed without exempting all of `setup.py`
  (the brief allowed an allow-list entry with a reason, without saying at which grain).

## Open questions
- **Item 5 (`proxy.dxvk_path`)** needs a job allowed to change `proxy/napoleon/`: the registry description and
  `proxy/napoleon/napoleon_remastered.ini` line 87 should both say "relative to the game folder or absolute; whatever this path is, DXVK's
  log, dxvk.conf and shader cache go to `<mod>\dxvk\` (the proxy's mod folder, never the game folder) unless a DXVK_* variable is already
  set" (`core/proxy/src/backend.cpp` `LoadDxvk`: `SetEnvDefault` on `rt.modDir + "dxvk\\"`), regenerated with `gen_tables.py`. The build id
  changes, so it rides on the next PC job that already changes `proxy/napoleon/` and runs the 20 passes. Move the triage row J23-L1 (our
  half) there? The generator half stays core B80.
- `uikit/napoleon/changes.py` header (`... as "changed since lock"`): a one-line reword for its next owner, then drop its
  `PURPOSE_QUOTE_ALLOWED` entry in `tests/test_repo_rules.py`. The root fix is the header-to-row extraction in `core/warscape/tools.py` not
  stripping a closing quote: a core backlog item (not filed here).
- `uiscale/core` (J66) still has no promotion row (`PROMOTIONS` `None`, "follows J67"): named here only, as briefed.
- J100's "held until a second game ships" is not enforced by anything; Liam decides when it is briefed.
