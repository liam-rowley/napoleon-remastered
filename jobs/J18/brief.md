# J18: PC-side rule guards

Phase 1 follow-up from the J5 audit. Three PC rules are still prose only, J5 ledger rows 28, 31 and 32 (`jobs/J5/rules.md`). Each one
becomes a guard that refuses the step, plus a check that finds the damage afterwards, each with a host test that fails on a fixture:
- **row 32:** never run git in a game folder
- **row 31:** PC experiments live under `_scratch\<owner>\`
- **row 28:** the exe stays vanilla on disk, so its sha is checked after every install or sync

Model: Sonnet (guards on existing code paths: a Python hook, a Python deploy script, the PowerShell watcher, all with test suites). Budget about
100 tool calls; at the cap, stop, commit, report what is left. No subagents.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J18`). Read `docs/DECISIONS.md` (D2, D21, D30), `harness/README.md`, `jobs/J5/rules.md` rows
  28, 31 and 32, and `jobs/J20/report.md` items 5 and 6 (the hook and the deny rules this job extends).
- Since D30, agents run Git Bash on the PC directly, so `job.sh` only sees what is sent through it. The ledger says "a `job.sh` guard", but
  the place every agent shell call passes is the Claude Code PreToolUse hook. Build on what exists and do not add near-duplicates:
  - `tools/claude_hook.py` (`decide(event)`, the commit-trailer rule; must never exit non-zero) and `tests/test_claude_hook.py`
  - `.claude/settings.json` (`permissions.deny`: Edit rules cover Write)
  - `harness/core/watcher.ps1`: `Guard-Regexes`, `Script-TouchesGame`, `Script-TouchesConfig`, the `job_script_guard` setting and the
    `launch` path. Tests: `harness/tests/Test-Unit.ps1` and `Test-Integration.ps1`, run in CI as `harness-windows`.
  - `harness/core/job.sh` and `tests/test_job_sh.py`
  - `proxy/tools/pc_deploy.py`: `install`, `uninstall`, `set`, `status`, `snapshot`/`diff_snapshots`, and the kit builders.
    Tests: `tests/test_pc_deploy.py`.
  - `tools/verbs/setup.py` (`wsc setup`, `CHECKS`) and `tests/test_setup.py`
- The two game folders come from `harness/napoleon/adapter.json` (`game_dir`) and `discovery/napoleon/games.json` (`napoleon.root`,
  `empire.root`). The exe identity has one owner: `proxy/napoleon/identity.json` (`sha1`, `size_of_image`, `time_date_stamp`). The
  state folder is the adapter's `state_dir` (`C:\napoleon_remastered_pc`). Read these values from those files. Never hard-code a copy.

## Decisions already made for this job
- **Protected roots.** Both game folders (Napoleon and Empire) and the state folder. Writes in the state folder are allowed only under
  `_scratch\<owner>\` and through the sanctioned writers (`job.sh`, `pc_deploy.py`, the watcher). Match paths case-insensitively in
  all three spellings: `C:\...`, `C:/...` and `/c/...`.
- **Row 32, no git in a game folder:**
  - Hook: deny a Bash or PowerShell call that runs `git` while it is in a protected root. That covers the event's `cwd`, a `cd` into
    one earlier in the same command, `git -C <root>`, `--git-dir`/`--work-tree` and `GIT_DIR=`/`GIT_WORK_TREE=` pointing at one. The
    reason names the rule and says to work in the repo checkout and sync with `pc_deploy.py`.
  - Watcher: refuse any `cmd` or `ps1` job whose script runs `git`. Watcher jobs have no reason to use git, and agents have Git Bash.
    This is a new regex next to `Guard-Regexes`, refused whatever `job_script_guard` says.
  - Damage check: a `.git` in a game folder or in any of its parents up to the drive root is a failure (`pc_deploy.py status` and
    `wsc setup`).
- **Row 31, experiments under `_scratch\<owner>\`:**
  - The default: `job.sh scratch <owner>` creates `<state>\_scratch\<owner>\` and prints its Git Bash path. Owner pattern:
    `^[a-z0-9][a-z0-9_-]{0,31}$` (J2 to J6 used `j2`, `j3s2`, `j6`). `harness/README.md` and the CLAUDE.md line point at it.
  - Hook: deny a shell call that writes into a protected root outside `_scratch\<name>\`. Writes here mean:
    - a `>` or `>>` target
    - `cp`, `mv`, `mkdir`, `touch`, `rm`, `tee`, `sed -i`, `unzip -d`
    - `Copy-Item`, `Move-Item`, `New-Item`, `Set-Content`, `Out-File`, `Remove-Item`, `Expand-Archive`

    whenever a path argument lies under a protected root. A call that runs `pc_deploy.py` or `job.sh` is exempt, and so are reads.
    The regex is a heuristic: the tests fix what it catches, and the report lists what it misses.
  - Settings: add deny rules for the Empire game folder and the state folder's managed parts: `watcher/**`, `kits/**`, `backup/**`,
    `snapshots/**`, `_to_delete/**` and `install.json`.
  - Damage check: `pc_deploy.py status` diffs the Napoleon folder against the pre-install snapshot. Any added or changed path outside
    the install record's `owned` set (and outside the adapter's game-anchored `config_files`) is listed as foreign and fails.
- **Row 28, exe sha after every install or sync:**
  - One value: the sha1 in `identity.json`. Both kits (proxy and harness) stage a sha-checked copy as `exe_identity.json`, and a test
    proves the copy equals the source. The watcher reads its copy beside `adapter.json`.
  - `pc_deploy.py install`: hash the exe before any change and refuse when it does not match. Say it is not the vanilla build the
    proxy knows (Steam update or modified exe), that nothing was installed, and that the next step is a new `identity.json` from
    `proxy/tools/exe_info.py`, which is Liam's call. After the copy, hash it again and record `exe_sha1` and the verdict in the
    install history.
  - `uninstall` and `set`: never refuse on the exe. Check after, record, and exit non-zero with a loud line on a mismatch.
  - `status`: prints an `exe` line and fails on a mismatch.
  - Watcher: hash the exe before every `launch` (cached by size and mtime) and refuse the launch on a mismatch (exit -2).
    `watcher.ini` `exe_check=refuse|warn` (default `refuse`). `watcher.status` gets an `exe` field (sha1, ok, checked_utc), and an
    `update` job's result names the exe verdict.
  - Tests use a fake exe and a fixture identity, passed in. Never the real sha.
- **`wsc setup`** gains one check, `pc_rules`. It reports the exe verdict, `.git` absent from both game folders and their parents,
  and the foreign-file count from the snapshot diff. It is skipped with a clear line when the game or state folder is absent
  (CI, other hosts). The check prints, and `--fix` fixes nothing here.
- **Prose:** in CLAUDE.md, the three rules become one line each that names the guard. Do not edit `jobs/J5/rules.md`: it is a dated
  ledger, so the report names the rows now enforced. `harness/README.md` documents `scratch`, `exe_check` and the git refusal.
- **Fail-open stays.** The hook never exits non-zero (J20 review), and a hook error lets the call through. A check that cannot read
  the game folder reports that instead of passing.

## Deliverables
1. Extended `tools/claude_hook.py` with the git and write rules. The `tests/test_claude_hook.py` fixtures each deny one command
   shape, and allowed look-alikes pass: git in the repo, reads in the game folder, writes under `_scratch\j18\`, `pc_deploy.py install`.
2. `.claude/settings.json` deny rules, covered by the existing settings test.
3. The watcher: git refusal and the pre-launch exe check, with unit and integration tests (a fake game whose exe sha does not match
   is refused; `exe_check=warn` launches it with a warning). The `exe` field in `watcher.status`.
4. `job.sh scratch <owner>`, tested in `tests/test_job_sh.py` (good and bad owners).
5. `pc_deploy.py`: the exe checks around `install`, `uninstall` and `set`, the `status` lines (exe, `.git`, foreign files), and
   `exe_identity.json` in both kits. Tests in `tests/test_pc_deploy.py`: a mismatched fixture exe refuses an install, a foreign file
   fails `status`, a `.git` in a parent fails `status`.
6. The `wsc setup` `pc_rules` check with tests (present, absent, failing fixtures).
7. A live run on the PC, under `proxy/runs/<utc>_j18pc/README.md`:
   - harness kit `send`, then `update kit=<id>`, then a `status` job showing the exe verdict
   - `pc_deploy.py status` and `wsc setup`
   - in this Claude Code session, `git status` with the Napoleon folder as cwd is denied by the hook
   - one `launch`/`kill` through `job.sh` (with the dev skip-intro profile), showing that the pre-launch check passes on the
     vanilla exe

   Paste the verdict lines. Make no change in the game folder beyond a proxy re-install through `pc_deploy.py`, if one is needed.
8. Tools rows and headers for anything new (`wsc gates` green). CLAUDE.md and `harness/README.md` updated as above.

## Kill criteria
- The live Napoleon.exe does not match `identity.json`: stop the PC part, install nothing, and ask Liam. The host work still lands.
- The hook's write rule denies an ordinary repo command in normal use (a false positive you cannot remove in about 5 calls):
  ship the git rule and the damage checks, drop the write rule from the hook, and report the command shape.
- `harness-windows` fails twice on the watcher change for a reason outside this job: stop and report the run ids.
- Anything would need a change in `core/`, in `empire-remastered` or in either game folder by hand: stop and ask Liam.
- The watcher `update` fails its dead-man check and rolls back: do not retry more than once. Report the rollback lines.

## Finish
Write `jobs/J18/report.md`. Cover:
- what was built, rule by rule (rows 28, 31 and 32, each with its guard, its damage check and the failing-fixture test names)
- what the write heuristic misses
- evidence: commits, CI run ids and the `_j18pc` run folder
- deviations from this brief and why
- open questions

Then `wsc reg set jobs J18 status=review report=jobs/J18/report.md`.
