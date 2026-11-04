## Round 1 (2026-11-04, branch job/J74 at 24a2e6f)
**Verdict: merge.**

Checked independently (not from the report): `wsc gates` 13 ok / 0 failed on the branch; `tests.test_release tests.test_release_installer tests.test_play tests.test_install_packs` 69 tests OK locally;
CI on 24a2e6f all green (run 41801330689; `harness-windows` job 126477646779 log: the new step lists `CrashDumpTool.test_status_outside_the_repo_with_the_generated_arguments ... ok`
and `test_short_8_3_game_and_state_paths`, `Ran 27 tests`, no skips). Rule 79 does not apply: no `proxy/`, `harness/` or core-pin change. The diff touches only `release/`, `tests/`, `ci/`, the rendered workflow, `wsc.toml`, `jobs/J74/`, the J74 row and its tool row.

Risk-first reading: `value_problems`/`shipped_ini_problems` (the allow-list is exactly `dev.file_rules` with D46), `dll_problem`/`acceptance_streak` (12-hex id, whole-token regex, dirty-literal refusal, 20 consecutive passes with committed evidence; `--allow-dirty` skips only the count),
`crash_dump_cmd` (-ExeName/-DumpFolder, folder unexpanded) and its `check_folder` rule, and the `rr.ps1` `Long-Path` change (resolved once; a non-existent path resolves via its nearest parent). No defects found.

### Blocker
None.
### Should-fix
None.
### Later
- The `rr.ps1` 8.3 fix is outside the brief's stated files but is named in the report (deviation 7) and covered by a test that failed on the runner first; accepted.
- `acceptance_streak` ignores branch and watcher version (report open question 4); the brief leaves that to a later job.
