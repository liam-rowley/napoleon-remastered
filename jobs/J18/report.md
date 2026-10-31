# J18 report: PC-side rule guards

The three PC rules that were prose only (J5 ledger rows 28, 31 and 32, `jobs/J5/rules.md`) now each have a guard that refuses the step and a
check that finds the damage afterwards, each with host tests that fail on a fixture. Live on the PC in run `proxy/runs/20261030_j18pc`.

## What was built, rule by rule

### Row 32: never run git in a game folder
- **Guard (hook):** `tools/claude_hook.py` `git_reason` denies a Bash or PowerShell call that runs git in a protected root: the event's `cwd`, a
  `cd`/`pushd`/`Set-Location` into one earlier in the same command, `git -C <root>`, `--git-dir`/`--work-tree`, `GIT_DIR=`/`GIT_WORK_TREE=`
  (also `$env:GIT_DIR =`). Protected roots: both game folders and the state folder, read from `harness/napoleon/adapter.json` (`game_dir`,
  `state_dir`) and `discovery/napoleon/games.json` (`napoleon.root`, `empire.root`); every path is matched case-insensitively in the `C:\`,
  `C:/` and `/c/` spellings (`norm`). The reason says to work in the repo checkout and sync with `pc_deploy.py`.
- **Guard (watcher):** `Script-RunsGit` refuses any `cmd` or `ps1` job whose script runs git, lock or not, whatever `job_script_guard` says.
- **Damage check:** `pc_deploy.py` `git_dirs` (a `.git` in the game folder or any parent up to the drive root) fails `status`; `wsc setup`
  `pc_rules` checks both game folders.
- **Tests:** `tests/test_claude_hook.py` `test_git_in_a_protected_root_is_denied` (11 shapes), `test_git_elsewhere_passes`,
  `test_norm_reads_all_three_spellings`, `test_roots_come_from_their_owners`; `harness/tests/Test-Unit.ps1` "guards: a script that runs git is
  refused ..."; `Test-Integration.ps1` "a script that runs git is refused even with the lock held (J18)"; `tests/test_pc_deploy.py`
  `test_a_git_folder_in_a_parent_fails_status`; `tests/test_setup.py` `test_pc_rules_present_absent_and_failing`.

### Row 31: PC experiments live under `_scratch\<owner>\`
- **The default:** `job.sh scratch <owner>` creates `<state>/_scratch/<owner>/` and prints its Git Bash path; owner `^[a-z0-9][a-z0-9_-]{0,31}$`.
- **Guard (hook):** `write_reason` denies a shell call that writes into a protected root outside `<state>\_scratch\<owner>\`: `>`/`>>` targets,
  `cp` (destination, `-t`), `mv`, `mkdir`, `touch`, `rm`, `tee`, `sed -i`, `unzip -d`, `Copy-Item`/`Expand-Archive` (`-Destination[Path]` or
  the second positional), `Move-Item`, `New-Item`, `Set-Content`, `Add-Content`, `Out-File`, `Remove-Item` and their short aliases. A call that
  runs `pc_deploy.py` or `job.sh` is exempt; reads pass.
- **Settings:** `.claude/settings.json` denies Edit (and so Write) in the Empire game folder and the state folder's `watcher/**`, `kits/**`,
  `backup/**`, `snapshots/**`, `_to_delete/**` and `install.json`; the test derives the expected rules from games.json and adapter.json.
- **Damage check:** `pc_deploy.py status` diffs the Napoleon folder against the pre-install snapshot (`foreign_files`); an added or changed
  path outside the install's `owned` set and the adapter's game-anchored `config_files` is listed as foreign and fails (removed vanilla paths are
  listed apart, not failing). The kit manifest and the install record carry `game_config_files`.
- **Tests:** `test_writes_into_a_protected_root_are_denied` (23 shapes), `test_reads_scratch_and_the_sanctioned_writers_pass` (19 look-alikes,
  including writes under `_scratch\j18\`, `pc_deploy.py install` and `job.sh`), `test_settings_deny_edits_in_the_other_game_and_the_managed_state`;
  `tests/test_job_sh.py` `test_scratch_creates_the_owner_folder_and_refuses_bad_owners`; `tests/test_pc_deploy.py`
  `test_a_foreign_file_fails_status_and_config_files_do_not`.

### Row 28: the exe stays vanilla on disk
- **One value:** the sha1 in `proxy/napoleon/identity.json`. The proxy kit stages it as `exe_identity.json` (sha256 in the manifest,
  `verify_kit` checks it; a kit without it is refused as pre-J18), the harness kit as `src/exe_identity.json` beside `adapter.json`.
- **pc_deploy:** `install` hashes the exe before any change and refuses a mismatch (not the vanilla build the proxy knows, nothing installed,
  next step a new identity.json from `exe_info.py`, Liam's call); the identity goes into `install.json` before the first change, and the exe is
  hashed again after the copy and recorded (`exe_sha1`, `exe_verdict`) in the history. `uninstall` and `set` (new optional `--state`) never
  refuse: they check after, record, print a loud line and exit non-zero on a mismatch. `status` prints an `exe` line and fails on a mismatch
  or when it cannot check.
- **Watcher 1.1.0:** `Exe-Gate` at the top of `Launch-Job`, before any display or config change: sha1 cached by size and mtime, refused (-2) on a
  mismatch or a missing identity; `watcher.ini` `exe_check=refuse|warn` (default refuse; warn launches with a WARNING line). `watcher.status`
  has `exe` {sha1, ok, checked_utc, expected, detail}, refreshed by every launch and `status` job; an `update` job's output names the verdict.
- **wsc setup:** `pc_rules` reports the exe verdict, `.git` in or above both game folders and the foreign-file count; skipped with a clear line
  when the game or state folder is absent; prints only (`--fix` fixes nothing here).
- **Tests:** fixtures use a fake exe and a fixture identity passed in (`build_kit(identity=...)`), never the real sha:
  `test_kit_carries_the_identity_copy`, `test_harness_kit_carries_the_identity_copy`, `test_a_mismatched_exe_refuses_the_install_and_changes_nothing`,
  `test_install_records_the_exe_verdict`, `test_set_and_uninstall_never_refuse_but_fail_loudly_on_a_changed_exe`,
  `test_status_without_an_install_still_checks_the_exe`; `Test-Unit.ps1` "exe check: ..."; `Test-Integration.ps1` "exe check (J18): a fake game
  whose sha1 is not the identity is refused (-2), exe_check=warn launches it with a warning, watcher.status has the verdict" (the integration
  watcher gets a fixture identity with the fake game's sha1, so every other launch case still runs).

### Prose
CLAUDE.md: the three rules are one line each naming their guard. `harness/README.md`: `scratch`, `exe_identity.json`, the git refusal, the
exe check and `exe_check`. `jobs/J5/rules.md` is untouched (dated ledger): rows 28, 31 and 32 are the ones now enforced.

## What the write heuristic misses
- Writes by a program rather than a shell builtin or the listed commands: `python3 -c "open(r'C:\...', 'w')"`, a script file, `robocopy`,
  `xcopy`, `curl -o`, `tar -C`, `7z`, `rsync`, `install`, `ln`, `[IO.File]::WriteAllText`, `Rename-Item`, `Clear-Content`.
- Paths it cannot know: anything through a variable (`$GAME`, `$env:X`, `%X%`), `~`, command substitution, globs it does not expand; a `cd $X`
  makes the cwd unknown, so later relative writes are not judged.
- Quoting it does not model: a redirect inside a quoted string is taken as a redirect (only matters with a protected cwd), separators inside
  quotes split a command early.
- The exemption is by name: any call that mentions `pc_deploy.py` or `job.sh` skips the write rule entirely (not the git rule).
- The git rule looks at the first word of each simple command (and after `sudo`, `xargs`, `env`, `command`, `exec`, `time`, `nohup`): git run
  from a script, an alias or `bash -c "..."` with the cwd inside the string is not seen. The watcher's `Script-RunsGit` is a word match per line.
- The hook only runs when Claude Code loads this repo's `.claude/settings.json`, that is when the session starts in the repo folder (D30).

## Evidence
- Commits on `job/J18`: `035671a` + `6f45bca` (hook, settings), `5f86202` (job.sh scratch), `6b0b368` (pc_deploy), `d5ee0a5` (watcher, setup,
  docs), `119004d` (run folder), and this report.
- CI (`gates`): 41145570796 success (`6f45bca`); 41146123674 success (`7b8bd96`, the stray commit as pushed to `job/J36`, see Deviations);
  41146895956 (`d5ee0a5`) was **cancelled** by the next push, not a pass; the run that counts is **41147641941 on `4daf44e`**: `gates`,
  `proxy` and `harness-windows` all success (review round 1, finding 6).
- Local: `wsc gates` 12 ok (204 s); `Test-Unit.ps1` 46 passed; `Test-Integration.ps1` 27 passed, 0 failed (full suite, Windows PowerShell 5.1).
- Live run `proxy/runs/20261030_j18pc` (2026-10-30 23:51-23:56 UTC): watcher update to 1.1.0 CONFIRMED; status job `exe.ok true` sha1
  `9aebcd2172f2878d781b079f7feb45b0e12e0250`; install `exe: ok` before and after; `status` exe ok, git ok, foreign 0 (also after the launch);
  `wsc setup` `ok pc_rules`, 11 ok; `launch` under dev-dxvk: `exe check: ok ...`, on_virtual, kill clean, profile restored byte-identical;
  uninstall identical to the pre-install snapshot (1564 files).

## Deviations
- **The in-session hook demo is a replay.** This session started in `C:\Users\liamr\repos`, so Claude Code never loaded the repo's settings and
  the hook did not run on its own calls (the commit-trailer rule did not fire either: every commit here carries the trailer by hand). Running
  `git status` in the Napoleon folder would then have run git there for real, so the run feeds the PreToolUse event to the exact settings
  command instead (`raw/hook.txt`: denied in the game folder, allowed in the repo). A session started in the repo folder sees it live.
- **Uninstalled at the end.** The proxy was not installed when the run began, so after the launch check it was uninstalled again (which also
  exercised the uninstall exe check); the brief allowed a re-install through `pc_deploy.py`.
- **Proxy DLL from the main checkout's build folder** (`build/proxy/napoleon/d3d9.dll`, built by another session) rather than a fresh build:
  the run checks the exe gate and the launch path, not the DLL.
- **Removed vanilla paths do not fail `status`.** The brief names added or changed paths; removed ones are printed apart so a Steam verify
  problem is visible without turning every partial install red.
- **`cp` and `Copy-Item` judge only the destination** (the source is a read), and `mv`/`Move-Item` every path (the source is deleted).
- **A shared checkout cost one stray commit.** Another session switched the shared main checkout to `job/J36` while this job was mid-step, so
  the pc_deploy commit landed on `job/J36` and was pushed to `origin/job/J36` (`7b8bd96`). It was cherry-picked onto `job/J18` (`6b0b368`) and
  the job moved to its own worktree. **`origin/job/J36` still carries that J18 commit** on top of `32c0b9a`: J36's owner should drop it (see
  Open questions). The same event left `core.hooksPath` set to an absolute path in the shared config (the `hooks` gate warns there).
- **Model:** run on Opus, not the brief's Sonnet (the session was started on Opus).

## Open questions
- `origin/job/J36` has the stray J18 commit `7b8bd96`; removing it needs a force-push on a branch another session owns, which is Liam's call
  (or J36's session, which has that worktree locked). J18 does not depend on it.
- Should the hook also cover `robocopy`/`xcopy`/`Rename-Item` and Python one-liners? Each widens the false-positive surface; left out for now.
- Should the D30 rule "start Claude Code in the repo folder" itself get a guard (for example `wsc setup` checking `CLAUDE_PROJECT_DIR`), since
  a session started one folder up runs without either hook rule?
