# J74: Release fixes before 0.1.0: crash-dump tool, ini_set gate, DLL marker, installer tests in CI

Phase 6. Four defects in the release machinery J38 built, found by the 2026-11-03 audit (`docs/audits/AUDIT_2026-11-03.md`: G1, G2, G3, G4, H9; C4 for the
allow-list). All four are in `release/`, `tests/`, `ci/` and `wsc.toml`: no DLL, no `proxy/`, no `harness/`, no `core/`. Nothing is published and no game is
launched. Fixed here, before the first release is built:
- **G1 (high).** The shipped `tools/Enable crash dumps.cmd` calls `wer_localdumps.ps1 -Mode enable` with no `-ExeName` or `-DumpFolder`; the script then searches
  upward for `wsc.toml` (`core/proxy/tools/wer/wer_localdumps.ps1:12-26`) and throws at line 23 anywhere outside the repo. `Install.cmd` offers this step to every
  player (`release/core/installer/rr.ps1:522-524`) and `README.txt` advertises it. J38 only passed because the release was built and tried inside the repo.
- **G2 (high).** `value_problems` runs before the components' `ini_set` keys are merged (`release/core/build_release.py:331` versus `:347-350`), so a component
  row can ship any dev key on. `dev.file_rules` already does (the UI scale component, D46), which starts DevInit, the file-rule hooks and `StateThread` in the shipped DLL (C4).
- **G4 (medium).** `dll_problem` (`build_release.py:196-203`) is a substring match: a DLL carrying `<id>-dirty` passes for `<id>`, an empty id passes, and nothing ties the
  DLL to the 20 acceptance passes.
- **G3 and H9 (high, medium).** `rr.ps1` and its tests never run in CI: `harness-windows` runs a fixed module list (`ci/gates.yml.in:164`) without
  `tests.test_release_installer`, `tests.test_play` or `tests.test_install_packs`, and `release/` is not in the `harness` input regex (`wsc.toml:91`), so a change to the
  installer does not even start the job.

Model: Sonnet medium (D15; the row says sonnet). Python, PowerShell text, a CI template and tests; no reverse engineering, shader, DLL or crash work, and no independent
check inside the job (the reviewer is the independent check), so nothing here earns Opus. Budget about 70 tool calls; at the cap, stop, commit, push, report what is left.
No subagents, no game launch. `needs_pc` is false: every test runs on the host (Windows PowerShell 5.1 is on this PC and on the CI runner).

## What exists (checked 2026-11-04 against main 5a76c0d, core v0.10.0; the audit read 8eec89a with core v0.9.0)
Every line number below was re-read on this tree: the audit's citations all still hold (the `wer_localdumps.ps1` default block starts at line 12, not 13).
- `release/core/build_release.py` (520 lines): `value_problems(keys, rel, dev_ini_text=None, dev_ini_expected=None)` at 138; `is_off_key` 132; `dll_problem` 196;
  `build()` 321 (the gate call at 331, `tree_dirty` 334, `build_id.py` and `dll_problem` 337-340, the `ini_set` merge 347-350, `player_ini(...)` 350, extras 371-385, `check_folder` 445).
  Extras are resolved by `resolve(...)` and written with `.read_bytes()` (line 380). `CMDS` (27) already generates `Install.cmd` and the four others from a template, which is the model for G1.
- `release/napoleon/components.json`: the `proxy` component's `extras` copy the core's two crash-dump `.cmd` files and `wer_localdumps.ps1` verbatim (`repo:core/proxy/tools/wer/...`).
  `ui_scale_2x` has `"ini_set": {"dev.file_rules": "napoleon_remastered\\ui\\ui_scale_2x.rules"}`.
- `release/napoleon/release.json`: `release_values` (`off_prefixes` has `dev.`, `required`, `inert_parameters`), `player_ini` (D46: omits `dev.`, `headless.`, `gfx.`, `ui.`).
- The core's `Enable crash dumps.cmd` and `Disable crash dumps.cmd` (`core/proxy/tools/wer/`, never edited here) run `wer_localdumps.ps1 -Mode enable|disable` elevated through
  `Start-Process -Verb RunAs`, writing the output to `%TEMP%`. The script takes `-ExeName` and `-DumpFolder`; without them it needs the repo. The values it would find are
  `exe_name` and `mod_dir` in `proxy/napoleon/identity.json` (`Napoleon.exe`, `napoleon_remastered`); its default folder is the **unexpanded** string
  `%LOCALAPPDATA%\CrashDumps\<mod_dir>` (stored as REG_EXPAND_SZ so WER expands it for the crashing user, outside the game folder: the byte-exact uninstall depends on that).
- `harness/acceptance/ledger.jsonl` (311 rows; read-only here): one JSON object per run with `pass` (1, 2, ...), `result` (`pass` or `fail`), `build_id`, `run` and `evidence`.
  Main's DLL id is `cb34c06baf42` (`core/proxy/tools/build_id.py`); its rows end in exactly 20 consecutive `pass` lines (pass 2 to 21, after a `fail`), so a build of main today clears the new gate.
  `-dirty` ids exist in the ledger (three `pass` rows): the gate must not count them.
- The DLL carries its build id as the C string literal passed by `-DWSP_BUILD_ID` (`core/proxy/tools/build.sh:127`), used by `"... build %s ..."` formats and the Lua `version()`; so in the binary the id
  is a stand-alone NUL-terminated string. `tests/test_release.py::Folder.test_dll_build_id` uses `b'MZ..build 715e9dfc0727 ..'`.
- `.github/workflows/gates.yml` is generated from `ci/gates.yml.in` (`python3 core/wsc.py ci render`; the `ci_render` gate fails on a difference). The template is this repo's, not the core's:
  J38's review (Later 2) wrongly called the CI hookup a core change. `wsc.toml` `[ci.inputs] harness` (line 91) decides when `harness-windows` runs and which input tree its pass marker hashes.
- On this PC (Windows, Git Bash): `python -m unittest tests.test_release_installer tests.test_play tests.test_install_packs` runs 25 tests in about 37 s, all pass, none skipped (checked while writing this brief). So adding them
  fits the job's 25-minute limit (the harness step has 18).

## Constraints (read before you start)
- **Never edit `core/`.** `wer_localdumps.ps1` and the two `.cmd` files live in the core. G1 is fixed on napoleon's release side. If the core should also change (for example an error that names
  the missing `-ExeName` and `-DumpFolder` instead of "no proxy adapter identity.json"), write it under `## Open questions` as a one-line warscape-core backlog item for the orchestrator to file; it is not part of this job.
- **Do not touch `proxy/`, `harness/`, `registries/config_keys.jsonl`'s release values or anything under `../empire-remastered`** (rule 79 counts `proxy/` and `harness/`; this job needs no acceptance run).
- **Out of scope, owned by later jobs that also edit `build_release.py` and `rr.ps1`:** J77 (`approved_by` on release values, refusing a PROPOSED budget), J81 (owned set as a union of installed sets, backups on every install,
  `Clean.cmd`, Steam-update classification on uninstall, the external-output sidecar check, `--record`, `key_text`), J83 (a real install on the PC). Do not start any of them; keep your edits to
  `build_release.py` to the functions named below so the three merges stay small. Also out: comparing the DLL's sha with the CI artifact (the audit's S-M extra; needs `gh` and a run id).
- `allowed_dev_keys` lists `dev.file_rules` and cites D46, until core W33's player key arrives (then J78 deletes the entry). Do not add any other key.
- The PowerShell installer tests run only on Windows. They must run in the `harness-windows` CI job, and you must prove from the job log that they ran there (step 9).
- Python on this PC: if `python3` hangs, use `C:\Users\liamr\AppData\Local\Python\pythoncore-3.15-64\python.exe` directly (do not use RunAs). Make file edits with Edit or Write, not shell heredocs that carry backslashes.

## Decisions already made (do not re-open; the reason is next to each)
1. **G1: the builder generates the two crash-dump `.cmd` files; `wer_localdumps.ps1` is still copied from the core.** A generated file cannot drift from `identity.json`, and the other five `.cmd` files are generated the same way
   (`cmd_text`). No napoleon-side `.ps1` wrapper: it would be a second elevation hop with its own quoting. A new pure function in `build_release.py` (for example `crash_dump_cmd(mode, ident)`) returns the ASCII, CRLF text; a new
   extras source kind (for example `crash_cmd:enable` and `crash_cmd:disable` in `components.json`) calls it; `resolve` may return `bytes` for an extra, so the line-380 `.read_bytes()` must accept bytes. The shape (one line, same
   elevation and `%TEMP%` output as the core's, with the two arguments added; `%%` is how a batch file writes a literal `%`, and the doubled `''` is the existing nested-quote form):
   `powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -Verb RunAs -Wait -FilePath powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command','& ''%~dp0wer_localdumps.ps1'' -Mode enable -ExeName ''Napoleon.exe'' -DumpFolder ''%%LOCALAPPDATA%%\CrashDumps\napoleon_remastered'' *> ''%TEMP%\rr_wer_enable.txt'''"`
   with `Napoleon.exe` from `exe_name` and `napoleon_remastered` from `mod_dir`. The folder must reach the script **unexpanded** (`%LOCALAPPDATA%`), never as the builder's or the player's expanded path (see What exists). Keep the core's `rem` header, the "Enabling crash dumps..." echo, `type` of the output file and `pause`.
   Verify the nesting by running the inner command string yourself in `-Mode status` (non-elevated, read-only; step 3); never run the generated `.cmd` (it raises a UAC prompt and writes HKLM).
2. **G1's proof has two layers.** A pure rule in `check_folder` (so `--check` works on any unzipped release, on any OS): every shipped `*.cmd` or `*.ps1` under `tools/` that names `wer_localdumps.ps1` also passes `-ExeName` and
   `-DumpFolder`, and the script sits beside it. Plus a Windows-only test that copies `wer_localdumps.ps1` and the generated `.cmd` into a fresh temp folder **outside the repo** (no `wsc.toml` above it), takes the arguments out of the
   generated text, and runs `powershell -File wer_localdumps.ps1 -Mode status -ExeName <...> -DumpFolder <...>`: exit 0 and a `WER LOCALDUMPS:` line. The same test shows the control: the same call without the two arguments exits non-zero
   (`no -ExeName and no proxy adapter identity.json`), so the test fails if the arguments are ever dropped. Status needs no admin rights and writes nothing.
3. **G2: `allowed_dev_keys` is a map from key id to the decision that allows it,** inside `release.json` `release_values`: `{"dev.file_rules": "D46: the UI scale stop-gap (J66) needs it until core W33 gives it a player key"}`. A map (not a list) because each entry
   must cite a `D<n>` (the gate checks the text matches `\bD\d+\b`), which is what keeps the list from growing by habit. The allow-list excuses only a component's `ini_set` of that key; it does not excuse a non-off `release_value` in the registry.
4. **G2: one function owns "what the components set".** Add `component_ini_set(comps)` (the loop now at 347-349), used by `build()` and by the tests. `value_problems` gains an `ini_set=None` argument (keep the existing positional arguments, so the tests that call it still work) and checks the **effective** value of every key:
   `ini_set` overrides the registry's `release_value`. New errors: an `ini_set` key that is not in the registry; an `ini_set` value that is not off for an off key (`is_off_key`) unless the key is in `allowed_dev_keys`; an `ini_set` that changes a `required` key's value; an
   `allowed_dev_keys` entry that no component sets (stale), that is not a registry key, or whose reason has no decision id. In `build()`, compute `ini_set` first and pass it to the gate on line 331. After `player_ini(...)` renders, a second pure check
   (`shipped_ini_problems(ini_text, rel)`) parses the **rendered text** and fails on any key under `[dev]`, `[headless]` or a test key that is not allow-listed: the gate on the output, not only on the inputs.
5. **G4: a delimited marker, a clean id, and 20 passes from the ledger.** `dll_problem(dll, want_id, ...)`: (a) an empty `want_id`, one that does not match `^[0-9a-f]{12}$`, or one ending `-dirty` is refused; (b) the id must appear as a whole token, i.e. a regex over the bytes
   `(?<![0-9A-Za-z_-])<id>(?![0-9A-Za-z_-])` (it matches the NUL-delimited literal and the old space-delimited test bytes, and it does not match `<id>-dirty` or a longer hex run); (c) a DLL that also contains `<id>-dirty` is refused (the build mixed a dirty literal in); (d) the ledger gate:
   in `harness/acceptance/ledger.jsonl` the rows with this `build_id`, in file order, must end in at least 20 consecutive `result == "pass"` rows, each with `run` and an `evidence` file that exists in the tree (the same streak rule as rule 79, `tools/jobs_hooks.py` `acceptance_problems`, without the branch and
   watcher conditions: a release may be built from `main` for a DLL proven on a job branch). Read the ledger path and the count from `release.json` (`"acceptance": {"ledger": "harness/acceptance/ledger.jsonl", "passes": 20}`), because `release/core` is a core candidate (rule 76) and must not name game paths or import `tools/`. Rows whose id is `<id>-dirty` never count. `--allow-dirty`
   (a throwaway build, already marked `"dirty": true` in the manifest) skips (d) only and prints a warning; (a) to (c) always apply. The refusal text names the id, the count found and the count needed.
6. **G3 and H9: three modules into `harness-windows`, as their own step, and no silent skip.** A new step after "Python host tests that run bash" runs `python -m unittest -v tests.test_release_installer tests.test_play tests.test_install_packs` under `shell: powershell` with its own `timeout-minutes: 8` and the same `$LASTEXITCODE` check; `-v` makes the log
   name every test and say `ok` or `skipped`. No stderr redirect (`2>&1` on a native command is a Windows PowerShell 5.1 trap; the existing step does not redirect either). The three modules' `skipUnless(PS ...)` would make a runner without PowerShell pass silently, so when `os.name == 'nt'` and `CI` is `true` and PowerShell is missing
   the class must **fail** (a `setUpClass` that raises), not skip; elsewhere behaviour is unchanged. This is the guard that makes "skipped" impossible on the job that exists to run them.
7. **Inputs.** `wsc.toml` `[ci.inputs] harness` gains `^release/(?!runs/)` (like `proxy/runs`, committed run evidence is not an input), `^upscale/pc/` (`install_packs.ps1` and `play.py` are what two of the modules run) and the three tests in the existing test list:
   `^tests/test_(job_sh|pc_deploy|claude_hook|setup|proxy_host|release_installer|play|install_packs)\.py$`. Update the comment above `[ci.inputs]`. Then `python3 core/wsc.py ci render` and commit `ci/gates.yml.in` and `.github/workflows/gates.yml` together.
8. **No new decision row.** D46 already says the player ini omits the dev keys and names the `dev.file_rules` exception; D45 says the installer is held by `tests/test_release_installer.py`. The new rules are documented in `release/README.md` (a short "Release gates" paragraph: the allow-list, the DLL marker, the 20 passes, the crash-dump `.cmd` files are generated), not in `DECISIONS.md`.

## Steps
1. **Start.** `git pull`, read `CLAUDE.md` (Jobs: branch `job/J74`), `docs/DECISIONS.md` D45, D46, D49, D50, `release/README.md`, `jobs/J38/report.md` ("Deviations" 3, 4 and 6) and the code listed in "What exists". Run
   `python -m unittest tests.test_release tests.test_release_installer tests.test_play tests.test_install_packs` once and note it is green (and its time).
2. **Tests first, in `tests/test_release.py`** (and the PowerShell one in `tests/test_release_installer.py`), written and run against the unchanged code before any fix; each must fail there, and you paste the failures in the report:
   - G4: `dll_problem` refuses a DLL whose only match is `<id>-dirty`; refuses an empty id; refuses an id that is a prefix of a longer hex run; accepts `\0<id>\0`; refuses 19 passes, accepts 20, and a `fail` after them (a fake ledger text; rows for another id and a `-dirty` id do not count; a missing evidence file ends the streak).
   - G2: a fake component with `ini_set {"dev.<some key>": "1"}` is refused; the same key in `allowed_dev_keys` with a `D46` reason passes; an `ini_set` of `proxy.exe_guard` to 0 is refused; a stale or reasonless `allowed_dev_keys` entry is refused; `shipped_ini_problems` catches a `[dev]` line that is not allow-listed; and the real `release.json` + `components.json` + registry is clean through `component_ini_set`.
   - G1: the generated `Enable` and `Disable` text for the real `identity.json` contains `-ExeName ''Napoleon.exe''` and `%%LOCALAPPDATA%%\CrashDumps\napoleon_remastered`, is ASCII with CRLF, and changes when the identity changes; `check_folder` flags a folder whose `tools/Enable crash dumps.cmd` is today's argument-less core copy; and the Windows-only outside-the-repo test of decision 2.
3. **G1.** Build the generator, the new source kind and the `check_folder` rule; change the two `extras` rows in `components.json`. Run the Windows test; also run the inner command string by hand once in `-Mode status` to see the nesting is right, and paste the `WER LOCALDUMPS:` line.
   `README.txt` text (`readme_text`) and `release/README.md` keep saying the step is optional and asks for administrator rights; correct them only if a sentence is no longer true.
4. **G2.** `component_ini_set`, the `ini_set` argument, `allowed_dev_keys` in `release.json`, the ordering fix in `build()`, `shipped_ini_problems`. Update `release.json`'s `player_ini._note` (it says "a component's ini_set keys are added"; add that they are gated and where the allow-list is).
5. **G4.** `dll_problem` and the ledger function, the `acceptance` block in `release.json`, the `--allow-dirty` rule, a one-line `print` of the passes found. Run the new `dll_problem` against **real bytes** read-only: the proxy DLL in the game folder or the CI artifact if one is already on disk (for example `C:\napoleon_remastered_pc` or the game folder's `d3d9.dll`;
   reading is allowed, copying into the repo is not, downloading is not). Report which file, which id it carried, and that the delimited regex matched it; if no real DLL is on disk, say so (the test bytes stand in) and do not fetch one.
6. **G3/H9 wiring.** The `setUpClass` guards in the three test modules, the CI step in `ci/gates.yml.in`, the `[ci.inputs]` change in `wsc.toml`, `python3 core/wsc.py ci render`, and the `harness-windows` hint check (`docs/CI_FAILURES.md` needs no row unless a run fails).
7. **Docs.** `release/README.md` "Release gates" paragraph (decision 8); the header comment of `build_release.py` (`usage`, `purpose`) if flags or refusals changed.
8. **Gates.** `python3 core/wsc.py gates` green; `python -m unittest tests.test_release tests.test_release_installer tests.test_play tests.test_install_packs tests.test_repo_rules` passing; `python3 core/wsc.py policy --branch job/J74 --base origin/main` clean apart from the missing report and review.
   Run `python3 release/core/build_release.py --check` is not needed (no folder is built); do not build a release.
9. **Push and read the log.** Push `job/J74` (every commit carries the `Claude-Session` trailer). In the CI run for the pushed head: (a) the `changes` job must say `harness` changed (the job is not skipped; if it is skipped, the input regex is wrong); (b) read the `harness-windows` job log
   (`gh run view <run id> --log --job <harness-windows job id>`, grep `Installer\|test_play\|InstallPacks\|Ran \|skipped`): the new step lists the installer tests (`Installer` and `Scripts` classes) and the crash-dump status test, each `ok`, ends `Ran 25 tests` or more, and contains no `skipped`. Paste the run id, the job id, the `Ran N tests` line and the count of `... ok` lines for the three modules in the report. If a test
   passes on this PC and fails on the runner, the runner is the truth: fix the test or the code, never mark it skipped or `expectedFailure`.
10. **Report and row** (Finish).

## Proof and what done looks like
- Every new test failed on the unchanged code (failures pasted), then passes; the suite named in step 8 passes; `wsc gates` is green.
- The crash-dump status test passes from a folder outside the repo, and fails without the two arguments (control).
- Two refusals shown by a real run of the function on a fixture: a component row with a dev key on, and a `<id>-dirty` DLL; and one acceptance, the real `release.json` + `components.json` through `value_problems` with no errors.
- The CI run id and `harness-windows` job id on the pushed head, and the log lines of step 9 (the three modules ran, none skipped). A green `harness-windows` that did not list the tests is **not** done.
- Done = the four fixes in, the three modules and `^release/` in CI, the allow-list holding `dev.file_rules` and nothing else, the report written, the row `review`. Nothing else changes: `git diff --stat origin/main` touches only `release/`, `tests/`, `ci/`, `.github/workflows/gates.yml`, `wsc.toml`, `jobs/J74/`, `registries/jobs/J74.json`.

## Out of scope
- Anything under `core/`, `proxy/`, `harness/`, `registries/config_keys.jsonl`, `../empire-remastered`, or the PC state folder; building a release; `releases.json`; publishing.
- J77, J81, J83 and J78 items (see Constraints); the CI-artifact sha comparison; changing which keys the player ini omits (D46).
- Weakening a test, adding a skip, or widening `allowed_dev_keys` to make a gate pass.

## Kill criteria
- A fix would need an edit inside `core/`, `proxy/` or `harness/`: stop, change nothing there, and write what the core would need as a one-line warscape-core backlog item under `## Open questions`.
- Any of the three modules fails on the `harness-windows` runner for a reason the PC does not show, and two honest fix attempts (each pushed and read from the log) leave it red: stop, commit, report the log lines; do not skip or loosen the test.
- A new test passes on the unchanged code: it does not test the bug; rewrite it before touching the fix.
- The delimited regex fails to match a real DLL's id (step 5): stop and report the bytes around the id; do not widen the pattern to a substring.
- About 70 tool calls reached, or a tool call is refused by a deny rule or the hook: stop, commit, report the call; do not retry another way.

## Open questions
No question needs Liam before the job starts. For the report, write the conservative reading and flag it:
1. Should `--allow-dirty` keep skipping the 20-pass check (a throwaway build)? **Recommended: yes**, as decided above: such a build is marked dirty in its manifest and is not releasable, and a PC sitting should still be able to build a test release from a DLL still being proven.
2. Should the 20-pass rule later also demand the passes' watcher version and the CI artifact sha? **Recommended: leave to a later job** (the audit's S-M part needs `gh`); this job does the id and the streak.
3. Warscape-core backlog item to file (the builder only states it): `wer_localdumps.ps1` should fail with "pass -ExeName and -DumpFolder" outside a repo, and `status` should accept the unexpanded folder. Recommended: file it with the next core batch; napoleon does not depend on it.

## Finish
Write `jobs/J74/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`): the red-then-green test runs, the generated `.cmd` text and the `WER LOCALDUMPS:` line, the allow-list as shipped, the real-DLL check of step 5, the CI run id, job id and log lines of step 9, the gates output, and the backlog item.
Then `wsc reg set jobs J74 status=review report=jobs/J74/report.md`.
