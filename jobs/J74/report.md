# J74 report: Release fixes before 0.1.0: crash-dump tool, ini_set gate, DLL marker, installer tests in CI

Written by the orchestrator from the builder subagent's hand-back (the harness refuses a subagent's write of a report file). The text is
the builder's own apart from this note and the CI run ids, which the orchestrator read. Branch `job/J74`:
- 1d8b01e: the release builder (crash-dump cmds, the `ini_set` gate, the whole-token DLL marker, the 20-pass ledger check)
- 4ea5109: the CI step, the harness inputs and the docs
- 1b73965: `rr.ps1` and 8.3 short paths, found by the first CI run
- a merge of `main` (J73's proxy input line and J74's harness line, both kept)

Nothing in `core/`, `proxy/` or `harness/` changed.

## What was built
### G1: crash dumps
- `crash_dump_cmd(mode, ident)` in `release/core/build_release.py` generates `tools/Enable crash dumps.cmd` and
  `tools/Disable crash dumps.cmd`, ASCII with CRLF, from `identity.json`.
- They keep the core's elevation, `rem` header, echo, `type` and `pause`, and add `-ExeName` and `-DumpFolder`, with the folder left
  unexpanded.
- `components.json` uses two new extras sources, `crash_cmd:enable` and `crash_cmd:disable`. `wer_localdumps.ps1` is still copied from
  the core.
- `check_folder` gains a rule: any `tools/*.cmd` or `*.ps1` that names `wer_localdumps.ps1` must pass `-ExeName` and `-DumpFolder` and
  have the script beside it.

### G2: the ini_set gate
- `component_ini_set(comps)` is now the only place that merges `ini_set`. `build()` computes it first and passes it to the gate.
- `value_problems(..., ini_set=None)` checks the effective values and refuses:
  - a key not in the registry;
  - a required key whose value is changed;
  - an off key that is on and not in `allowed_dev_keys`;
  - an allow-list entry that is stale, is not a registry key, or has a reason without a `D<n>`.
- Keys in `ini_set` skip the "omitted, default must equal release value" check.
- `shipped_ini_problems(ini_text, rel)` then checks the rendered ini.
- `release.json` carries the allow-list as shipped: `"allowed_dev_keys": {"dev.file_rules": "D46: the UI scale stop-gap (J66) needs it
  until core W33 gives it a player key"}`.

### G4: the DLL marker
`dll_problem(dll, want_id, acceptance=None)`:
- refuses an empty id, an id that is not 12 hex characters, or a `-dirty` id;
- requires the id as a whole token, matched by `(?<![0-9A-Za-z_-])id(?![0-9A-Za-z_-])`;
- refuses a DLL that also contains `id-dirty`;
- with `acceptance={'text','passes','exists'}`, requires 20 consecutive pass rows of exactly that build id. Other ids and `-dirty` ids
  neither count nor break the streak, and each row needs a `run` and an evidence file that exists.

`release.json` gains `acceptance: {ledger: harness/acceptance/ledger.jsonl, passes: 20}`. `build()` prints the passes it found, and
`--allow-dirty` skips only the count, with a warning.

### G3 and H9: the installer tests in CI
- A new step in `ci/gates.yml.in`, "PowerShell installer, play and pack-installer tests":
  - it runs `python -m unittest -v tests.test_release_installer tests.test_play tests.test_install_packs` under `shell: powershell`;
  - it has `timeout-minutes: 8` and checks `$LASTEXITCODE`;
  - `.github/workflows/gates.yml` was re-rendered.
- `skipUnless` on `Installer`, `Play` and `InstallPacks` became a `setUpClass` guard: on Windows CI (`CI=true`) without PowerShell it
  fails; elsewhere it skips as before.
- `wsc.toml` `[ci.inputs] harness` gains `^release/(?!runs/)`, `^upscale/pc/` and the three test modules.

### 8.3 short paths in the installer (found by the first CI run)
- **Fix.** `release/core/installer/rr.ps1` resolves the game and state folders to their long, full form once at start: a new
  `Long-Path` function calls `GetLongPathNameW` through `Add-Type`, and for a path that does not exist yet resolves the nearest existing
  parent and joins the leaf. `Take-Snapshot` uses the long form as its root.
- **Cause.** Before the fix, relative paths were cut with `Substring($root.Length)` from file names that .NET enumerates in the long
  form. With a short-name TEMP or game path the lengths differ: `changed ame/data/vanilla.pack`. A player whose TEMP or game path is in
  short form would hit this.
- **Tests.**
  - `tests/test_release_installer.py` gains the `long_path` and `short_path` helpers (ctypes), and `Installer` resolves its temp dir to
    the long form.
  - A new test, `test_short_8_3_game_and_state_paths`, runs install, check and uninstall with `-GamePath` and `-StateDir` in 8.3 form. It
    expects exit 0, the printed long form and an unchanged game folder, and skips only when the volume has 8.3 names off.

### Docs
A "Release gates (J74)" section in `release/README.md` and an updated header in `build_release.py`.

## Evidence
- **Red first.**
  - Against the unchanged code, 20 of the new tests failed: 6 assertion failures and 14 errors (missing functions, new keyword
    arguments, the new `release.json` key). The red output was kept in the builder's scratch.
  - The six assertion failures:
    - `test_dirty_neighbour_is_not_the_id`
    - `test_empty_or_malformed_id_is_refused`
    - `test_prefix_of_a_longer_run_is_not_the_id`
    - `test_a_dll_that_also_carries_the_dirty_literal_is_refused`
    - `test_crash_dump_cmd_without_its_arguments_is_flagged`
    - `test_proxy_component_ships_the_generated_files`
  - The short-path test against the old `rr.ps1` failed with
    `AssertionError: 1 != 0 : rr: ... game folder C:\Users\liamr\AppData\Local\Temp\TMPLRP~1\ALONGG~1`, then a `New-Item` error.
- **The generated Enable text,** from the real identity, passes `-ExeName ''Napoleon.exe''` and
  `-DumpFolder ''%%LOCALAPPDATA%%\CrashDumps\napoleon_remastered''`.
  - The Windows test `CrashDumpTool` copies the script and the generated `.cmd` into a temp folder outside any repo and undoes the
    quoting. It runs the inner command in `status` mode and gets exit 0, a `WER LOCALDUMPS:` line and `Napoleon.exe`.
  - The control call without the two arguments exits non-zero with "no -ExeName".
- **The real DLL check.** The only real DLL on disk is the J38 rehearsal copy (id `715e9dfc0727`, 973312 bytes). Its id appears three
  times, each delimited by NULs, and `dll_problem` without the ledger returns '' for it. `test_real_ledger_clears_main` shows that main's
  `cb34c06baf42` has at least 20 consecutive passes with evidence.
- **Two refusals and one acceptance** from real runs of the code:
  - refused: `test_a_dev_key_on_is_refused` (`dev.ctl` on);
  - refused: `test_dirty_neighbour_is_not_the_id`;
  - accepted: `test_real_release_is_clean`, which runs the real `release.json`, `components.json` and registry with no errors. The
    allow-list is exactly `["dev.file_rules"]`.
- **Local runs.**
  - The three installer modules: 27 tests OK, none skipped.
  - `tests.test_release` and `tests.test_release_installer`: 56 tests OK.
  - After the merge of `main`, `tests.test_proxy_host`, `tests.test_jobs_hooks` and `tests.test_release`: 110 tests OK, 1 skipped.
  - `python3 core/wsc.py gates`: 13 ok, 1 warn (skipped tests), 0 failed.
- **CI proof** (read by the orchestrator):
  - **First pushed head, 4ea5109:** run 41796839289, `harness-windows` job 126462941913. The new step ran the three modules on the runner
    with no skips: `Ran 26 tests ... FAILED (failures=3)`. All three failures came from 8.3 short paths (the runner's TEMP is
    `C:\Users\RUNNER~1\...`, while files enumerate as `C:\Users\runneradmin\...`):
    - `test_check_repair_and_foreign_files`: `Check` returned 1;
    - `test_finds_the_game_from_the_scripts_own_location`: the long form was printed;
    - `test_uninstall_reports_a_difference`: `changed ame/data/vanilla.pack`.
  - **After the fix, 1b73965:** run 41798644209, `harness-windows` job 126468788406, green. The new step: `Ran 27 tests in 43.067s` OK,
    including `test_short_8_3_game_and_state_paths`. The job's earlier step: `Ran 80 tests` OK.

## Deviations from the brief and why
1. **`dll_problem`'s third argument** is an `acceptance=None` dict (`text`, `passes`, `exists`), not ledger path arguments, which keeps
   `release/core` free of game paths. `build()` reads the path from `release.json`, and two-argument callers still work.
2. **The generated `.cmd` writes its output to `%TEMP%\rr_wer_<mode>.txt`.** The core's uses `wsp_wer_*.txt`. The `rem` header is reworded
   for a player release.
3. **`check_folder` also fails when `tools/wer_localdumps.ps1` is not beside the `.cmd`.** This follows decision 2: "the script sits beside
   it".
4. **`shipped_ini_problems`** also fails any key that `is_off_key` matches, proof and test keys included, unless it is allow-listed. That
   is a superset of the brief's wording.
5. **`registries/tools/release.core.build_release.json` was re-added** (`wsc reg add tools`), because the `tools` gate needs the row to
   match the changed header.
6. **Edits around the shell.** Heredocs mangled backslashes in the builder's shell, so the code and tests were written with Edit and
   Write, and the JSON and CI edits with small patch scripts checked by diff.
7. **The brief did not expect an `rr.ps1` change.** The runner's short TEMP showed a real installer bug (G5 and G7 territory), so it was
   fixed at the root in `release/core/installer/rr.ps1`, on the orchestrator's direction, in the lines named above only.

## Open questions
1. `--allow-dirty` keeps skipping the 20-pass check, as the brief recommends. Such a build is marked dirty in its manifest and is not
   releasable.
2. Should a release also require the passes' watcher version and the CI artifact's sha? Recommended: leave that to a later job, since
   it needs `gh`.
3. A core backlog item, now filed as warscape-core B85: `wer_localdumps.ps1` should say "pass -ExeName and -DumpFolder" outside a repo,
   and `status` should accept the unexpanded folder.
4. By design, `acceptance_streak` ignores the branch and the watcher: a release may be built from main for a DLL proven on a job branch.
