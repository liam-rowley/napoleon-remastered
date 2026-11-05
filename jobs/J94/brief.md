# J94: Napoleon tools, tests and gates: small fixes

Phase 1, a sweep of small Python, test, registry and doc fixes from the Later triage (`docs/audits/LATER_TRIAGE_2026-11-04.md`, rows J5-L3, J21-L2/3/4,
J22-L1/L4, J23-L1 (our half), J24-L2, J38-L3, J41-L4, J45-L2, J70-L1/L2). Each item is small and none had an owner. No game, no PC, no watcher.

Model: Opus, reason: D52 (Opus for builds; Sonnet for its reviews).
Budget about 120 tool calls; at the cap, stop, commit, report what is left. No subagents needed. Waiting belongs to the harness: no polling.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J94`). Read `docs/DECISIONS.md` and the triage rows above (`grep -n "row J94" docs/audits/LATER_TRIAGE_2026-11-04.md`).
- Checked on main at `0271d10` (J73, J74, J76 merged): every item below still applies; none was fixed by them. Re-check each before you change it
  and say in the report if one was fixed since.
- Search first: `python3 core/wsc.py find hotkeys setup git_bash promotion shot_sheet`.

## Decisions already made for this job
1. **`tools/verbs/hotkeys.py`** (J21-L2, L3, L4; tests in `tests/test_hotkeys.py`).
   - `GAME_DATA` (line 33) is hard-coded. Read it from `discovery/napoleon/games.json` (`napoleon.root` joined with `napoleon.data`), keeping the
     `--from-pack [DATA_DIR]` override. A missing file is a clear error line, not a traceback.
   - `run()` for `check` does `sys.path.insert` and imports `KNOWN_OS_COMBO` and `KNOWN_VANILLA_CLASH` from `tests/test_hotkeys.py` (line 247). Move
     both lists to a data file (beside the verb or under `registries/`: pick one and say so in the verb header, whose lines 11 and 23 name the test
     file today); the verb and the test both read it; the verb no longer imports from `tests/`.
   - `split()` (line 132) uses `str.capitalize()`, which turns `NumpadAdd` into `Numpadadd` in messages and in the OS-combo match. Normalise with a
     case-insensitive lookup into the canonical names (`KEY_NAMES` values, `ORDER`, `KEY_ALIAS`, `MODS`), falling back to the text as typed.
   - Tests: `split('Ctrl+NumpadAdd')` returns key `NumpadAdd`; `GAME_DATA` equals the games.json value; the verb's `check` runs with no `tests/` on
     `sys.path`. Each must fail on the old code.
2. **`tests/test_repo_rules.py`** (J5-L3, J22-L1/L4).
   - `silenced()` (line 150) clears a skip when `` `v` `` appears anywhere in `docs/DECISIONS.md`, so any row that mentions `tests` clears
     `[gates] skip = ["tests"]`. Require one decision row (one table line) to quote both the `wsc.toml` section and the value. Fixtures: a row
     quoting only the value no longer clears it; a row quoting both does.
   - `BARE_BASH` (lines 56-60) misses `shutil.which('bash')` as an argv element, an argv list whose `'bash'` starts on the next line, and `.sh`
     files. Match over the whole text (not line by line) for the multi-line list, add `shutil.which` of bash as a hit (the sanctioned users are
     `setup.git_bash()` and `bash_for_tests()`), and scan `harness/*.sh` and `tools/**/*.sh` for Python-style bare launches only if a real
     shape exists there (shell `bash -c` inside a script is fine); say what you chose in the report. Fixtures for each shape, passing and failing,
     as in `Fixtures.test_bare_bash`. A new hit in the tree is fixed at the caller; allowlist only with a reason in `BARE_BASH_ALLOWED`.
3. **`tools/verbs/setup.py`** (J70-L1, J41-L4, J45-L2; tests: `grep -ln check_watcher tests/*.py`).
   - `check_watcher` (line 207) shows only the last line of `job.sh status` output, so the ok line can be a stray `}`. Parse the status JSON and show
     the state and heartbeat age; fall back to the first line on a parse failure. A failing exit keeps its fix hint.
   - `git_bash()` roots (line 58) include `%LOCALAPPDATA%/Git`, which is not an install folder. Drop it; keep `%LOCALAPPDATA%/Programs/Git` (line 59).
     Test with an injected environment.
   - Add a `pillow` check: the interpreter that runs the acceptance script imports PIL (find the interpreter with
     `grep -n "PIL\|Pillow" harness/*.py tools/*.py`). Warn, not fail, fix hint `pip install pillow`. Test the pure result function.
4. **`tests/test_jobs_hooks.py`** (J70-L2, lines 38-44): the `Promotions` class injects its own table `T` naming `proxy/core` and `discovery/core`,
   from before J12 moved the proxy into the core. They are fixtures (`T` is passed to `promotion_problems`), so the paths are not wrong, only
   misleading: rename them to neutral folders (`area_a/core`, `area_b/core`), and add one test that the real `PROMOTIONS` table in
   `tools/jobs_hooks.py` has no entry for a folder that no longer exists in the tree, which catches the real drift.
5. **`proxy.dxvk_path` description** (J23-L1, our half; `registries/config_keys.jsonl` line 39, echoed in `proxy/napoleon/napoleon_remastered.ini`
   line 87). It says DXVK's log, config and caches go "next to it" (the DLL). `core/proxy/src/backend.cpp` `LoadDxvk` puts them in `<mod>\dxvk\`
   (the proxy's mod folder) whatever `dxvk_path` is, and resolves a relative path against the game folder. Reword the description to say that.
   The core generator half (`gen_tables.py` skips other owners) is core backlog B80, not here. **Rule 79:** `proxy/napoleon/` is a DLL input
   (`core/proxy/tools/build_id.py`, role `adapter`), so editing the committed ini changes the build id. Default: change the registry text only
   and list the ini line under open questions. Touch the ini only if `python3 core/proxy/tools/build_id.py` shows it is not hashed; if you do,
   regenerate it with the repo's generator and say in the report that the build id changed and no passes are claimed.
6. **`tools.shot_sheet` purpose** (J24-L2): the `purpose:` line in the header of `tools/shot_sheet.py` (line 4) ends with a quoted word, and the
   header-to-row extraction strips the trailing quote, so `registries/tools/tools.shot_sheet.json` ends in `marked \"missing`. Reword the header
   so it does not end in a quote, bring the row in line (`wsc reg set tools tools.shot_sheet purpose=...` or the tools gate's own route), and
   grep the other `tools/*.py` headers for a trailing quote on `purpose:` (fix any, name them).
7. **`release/core` promotion** (J38-L3): `PROMOTIONS['release/core']` in `tools/jobs_hooks.py` is `None` ("no row yet"). Add a `needs_brief` row
   (`python3 core/wsc.py reg add jobs ...`, next free id, `depends_on` J63, model opus, `needs_pc` false) titled "Promote release/core to
   warscape-core", its description naming the release builder, installer scripts and support bundle (J38) and that it is held until a second game
   ships, then set the table entry to that id and update the comment. Do the same for nothing else: `uiscale/core` (J66, no row) is named in the
   report only.

## Deliverables
Items 1 to 7, each with its tests, one commit per item on `job/J94`, `python3 core/wsc.py gates` green (`--fast` per commit), and
`python3 core/wsc.py policy --branch job/J94 --base origin/main` ok.

## Kill criteria
- An item needs a `core/` change or a game-side file: stop that item, leave it under open questions, finish the rest.
- Item 5 would change `tables.h` or any DLL source: stop, take the registry-only route and report the build-id consequence.
- The gates fail twice on the same cause after your fix: stop, report the cause.

## Finish
Write `jobs/J94/report.md` (what was built per item with the test that proves it, evidence, deviations, `## Open questions`), then
`wsc reg set jobs J94 status=review report=jobs/J94/report.md`.
