# J76 report: Agent hook hardening: per-segment exemptions, writers, git and game guards, merge rights

Written by the orchestrator from the builder subagent's hand-back (the harness refuses a subagent's write of a report file); the text is
the builder's own apart from this note. Branch `job/J76`, five commits:
- 084ee94 one shell parser and per-unit hook rules
- b33c2e7 the 247-row corpus and the git, launch, merge and branch rules
- 4d90748 the settings wrapper and the deny rows (its subject says six rows; there are five, see Deviations)
- 60a5c41 docs, registry rows and the short-name test
- 01a1a79 the corpus kept clear of bare bash, and the real 8.3 expander tested

## What was built
`tools/claude_hook.py` now judges every simple command of a shell call on its own. A new `tools/hook_parse.py`, with its own header and
a `tools.hook_parse` row, replaces the three regex entry points; `claude_hook.py` loads it by path.

### The parser (decisions 1 to 3)
- **What it unwraps:**
  - separators `&& || ; | & newline`, `if`/`then`/`for`/`while` blocks, `{ }` and `( )`;
  - `$( )`, backticks, `<( )`, heredoc bodies and here-strings;
  - `bash|sh -c`, `eval`, `cmd /c`, `powershell|pwsh -Command|-EncodedCommand`, `Start-Process -FilePath/-ArgumentList/-WorkingDirectory`,
    `start` and `call`;
  - the `nice`, `timeout`, `env`, `sudo`, `xargs`, `command`, `exec`, `nohup`, `time`, `stdbuf`, `setsid` and `ionice` wrappers.
- **Cwd and variables** flow left to right, with no subshell scoping.
  - Assignments are read as `V=x`, `export`, `$V = 'x'`, `$env:V` and `set V=x`.
  - They expand as `$V`, `${V}`, `$env:V` and `%V%`, falling back to the hook's `os.environ`.
- **Limits.** Nesting deeper than 4 sets `unparseable`. 8.3 short names go through an injectable `expand_short` (`GetLongPathNameW` via
  ctypes on Windows).

### Judging each command
- **The taint rule.** A command is tainted when its expanded text names a protected root, in any spelling or as an 8.3 form. An unresolved
  target or cwd is denied when the command is tainted and allowed when it is not, so `echo x > "$OUT"` still works.
- **Per-segment exemption (H1).** The whole-command `EXEMPT` switch is gone.
  - A unit is exempt only when its script is this checkout's `core/proxy/tools/pc_deploy.py` or `core/harness/job.sh`, and its redirections
    are still checked.
  - A look-alike (`/tmp/pc_deploy.py`) in a command that names a protected root is denied.
- **Writers (decision 5).**
  - Added: `install`, `rsync`, `dd of=`, `tar -C` and `-f`, `ln`, `robocopy` (`/MOVE` and `/MIR` count), `xcopy`, `copy`, `move`, `ren`,
    `rename`, `del`, `erase`, `rd`, `Rename-Item`, `Set-ItemProperty`, `Clear-Content`, `Tee-Object`, `truncate`, `chmod`, `chown`, `mklink`
    and `find -delete`.
  - Redirections come from a tokenizer: `> >> >| &> &>> >& file <> N> *>`. `>&2`, `2>&1` and `>&-` are not files.
  - Inline python, node, perl, ruby or powershell code (including heredocs and here-strings) is denied when it names a protected root
    together with a write verb.

### Git (decision 6)
- **Denied when any of these resolves into a protected root:**
  - the effective cwd, `-C`, `--git-dir`, `--work-tree`, `GIT_DIR` or `GIT_WORK_TREE`;
  - `-c core.worktree=` or `-c core.hooksPath=`, or `--separate-git-dir`;
  - the arguments of `init`, `clone`, `worktree add` and `submodule add`.
- Also denied when the cwd is unresolved while the command is tainted.
- **The trailer rule** moved into the same pass.
  - It finds the subcommand past git's global options.
  - It follows `-c alias.X=` and the `[alias]` sections of `~/.gitconfig`, the XDG config and the repo config. These are read as plain
    text, cached and size-capped.
  - It rewrites the call to a canonical `git commit ...` and calls the core's `commit_lacks_trailer`.
- `git config alias.X commit...` is denied.

### `--no-verify` (decision 10)
- Denied on `commit`, `push`, `merge`, `rebase`, `cherry-pick` and `am`.
- Also caught: `commit -n`, option clusters (`-an`, `-nm`), unique abbreviations, and `-c core.hooksPath=` on those subcommands. Clusters
  are scanned left to right, stopping at `m`, `F`, `C`, `c`, `t`, `u` or `S`.
- `git config core.hooksPath core/.githooks` stays allowed.

### Game launch and kill (decision 11)
- Image names come from `adapter.json`.
- **Denied:**
  - a command word equal to a game image, or a `steam://` URI;
  - `start`, `Start-Process`, `Invoke-Item`, `explorer`, `rundll32` or `xdg-open` on an image or a `steam://` URI;
  - `taskkill`, `Stop-Process`, `pkill`, `killall` or `wmic` naming an image, and `Get-Process X | Stop-Process`.
- **Allowed:** `kill <pid>` and `sha1sum Napoleon.exe`.

### Merge rights, D50 (decision 8)
- **Denied:** `gh pr merge` of a `plan/` or `meta/` branch, after stripping `origin/`, `refs/heads/` and `owner:`.
- **Resolving the target.** A number, a URL or no target is resolved with `gh pr view`, or `git branch --show-current` (5 s timeout; the
  hook's only subprocess, injectable as `PR_HEAD`). A target that cannot be resolved is denied with "re-run naming the branch".
- **API merges.** `gh api` merge calls are denied (`pulls/N/merge`, `mergePullRequest`, `enablePullRequestAutoMerge`).
- `job/` and `brief/` merges stay allowed.

### Remote branch deletion (decision 9)
- Allowed for `scratch/*` and other names.
- Denied for `main`, `plan/`, `meta/`, `job/` and `brief/`, through `git push --delete|-d|:ref` and `gh api -X DELETE .../git/refs/heads/...`.

### Fail closed, not wedged (decision 12)
- **Roots unreadable:** a conservative `FALLBACK` pattern applies (program files*, steamapps, napoleon_remastered_pc, *total war*), with
  no scratch allowance, and the denial gains a note on restoring `adapter.json`.
- **`core/` missing:** `git commit` is denied with "git submodule update --init".
- **`decide()` raising:** `main()` falls to `panic()`, a text screen for a commit without a trailer, and for a protected-folder word together
  with a write, git, launch or kill word. It always exits 0.
- **The settings wrapper** reads stdin once and runs the hook under `timeout ${CLAUDE_HOOK_TIMEOUT:-10}`, trying `python3`, then `python`,
  then `py -3`. If python is missing, crashes or hangs, it applies the same screen with `grep -Eiq` and prints deny JSON. A missing hook
  file still exits 0.

### Settings deny rows (decision 13)
- Five new Edit rows: `ctl/**`, `play/**`, `saves/**`, the AppData `scripts/preferences.script.txt` and AppData `save_games/**`.
- The hook also treats the prefs file and `save_games` (from `adapter.json` `appdata_dir`, with `%APPDATA%` expanded) as write-protected
  paths. The denial says "use saves/napoleon/stage_save.py or pc_deploy.py set".

### Denial text and docs
- **Denial text (decision 14).** Each family's message names its route: pc_deploy.py, job.sh scratch, the trailer flag, the pre-push hook,
  core/harness/job.sh, D50 and Liam, scratch/, stage_save.py, or `git submodule update --init`. One test asserts each.
- **Docs.**
  - The file header covers purpose, usage and residuals.
  - The `tools.claude_hook` row is re-synced and the `tools.hook_parse` row added.
  - `CLAUDE.md`: the two Guard lines are rewritten, plus one line for launch and kill, `--no-verify` and D50.
  - `docs/REVIEW.md` "Merging" was already true and is unchanged.

### Counts
`tests/test_claude_hook_corpus.py` has 247 rows. "Red before" is the rows that fail against the unchanged hook (`HOOK_UNDER_TEST` runs the
corpus against an older file):

| Family | Rows | Red before |
|---|---|---|
| exempt | 10 | 7 |
| writers | 44 | 32 |
| git | 32 | 20 |
| launch | 16 | 11 |
| commit | 30 | 16 |
| merge | 19 | 13 |
| branches | 13 | 6 |
| roots | 11 | 5 |
| pipeline (36 commands, each from the repo and from a sibling worktree) | 72 | 0 |
| **Total** | **247** | **110** |

- **Red before: 110.** 107 are denials the old hook let through; 3 are allowed `roots` rows that need the new `FALLBACK` names.
- **Green after:** all 247.
- **The pipeline rows** were green before and stay green: no legitimate step is blocked.
- **Two more tests:**
  - one runs the real `decide()`, with the real roots and the real `core/`, on every pipeline command from the repo and from a worktree
    path;
  - one feeds in the commands `wsc jobs next` prints, and skips when the queue has nothing.
- The brief's required minimum is met in every family.

### Speed
| Measure | Measured | Target |
|---|---|---|
| `decide()` on a typical commit-and-push command | 0.12 to 0.13 ms | 5 ms |
| One hook process round trip (`echo '<event>' \| python3 tools/claude_hook.py`) | 52 to 54 ms | 150 ms |
| The 247-row corpus, in process | 0.03 s | 3 s |

### The one changed fixture (decision 7)
- **The change.** In `tests/test_claude_hook.py`, `test_reads_scratch_and_the_sanctioned_writers_pass` had
  `bash core/harness/job.sh j18 - <<< "launch owner=j18" > <state>/x.log`. Its redirect now goes to `/tmp/x.log`, and the original shape is
  in the denied list of `test_writes_into_a_protected_root_are_denied`.
- **Why.** That shape is exactly H1's bypass. No real job step prints a redirect into the state folder (checked against the step text in
  `core/warscape/jobq.py`), so the kill criterion did not fire.
- **Two other edits to that file:**
  - `assertNotIn('git ', cmd)` became `assertNotIn('git rev-parse', cmd)`, because the new wrapper's text screen legitimately contains
    "git commit" in its grep patterns;
  - the settings tests were extended: the five deny rows, and the wrapper cases where python is missing, crashes or hangs.

### Residuals (as the file header states them)
- `python3 script.py`, and any program that writes where the shell cannot see.
- A write through a shell variable that is set neither in the same command nor in the hook's environment.
- A path assembled inside inline code.
- A weakening of rule 79 or of `watcher.ini` done by a sanctioned script (that is core W25).
- `xargs rm < list`, whose target comes from stdin.

### What the core could add (warscape-core backlog)
- A `COMMIT` regex in `warscape/trailer.py` that knows git's global options (`git --no-pager commit`, `-P`, `--git-dir=`, `-c alias.X=`,
  aliases), so the trailer rule stops depending on the game repo's normalisation.
- A shared shell parser, so every game's hook could reuse `hook_parse`.

### Gates and policy
- `python3 core/wsc.py gates`: 13 ok, 1 warn, 0 failed in 157.2 s. The warn is skipped tests: no viewer wasm, Pillow, capstone or freetype
  on this host.
- `python3 -m unittest tests.test_claude_hook tests.test_claude_hook_corpus tests.test_jobs_hooks tests.test_repo_rules`: 78 tests, OK.
- `python3 core/wsc.py policy --branch job/J76 --base origin/main` refuses only for the missing report, review and `done` row (8 files
  changed).

## Deviations from the brief and why
1. **The exemption path rule is broader than "relative to cwd or absolute under ROOT".**
   - A script counts as sanctioned when it resolves under this checkout, or under a sibling checkout beside it (`ROOT.parent/<dir>/...`),
     and ends in `core/proxy/tools/pc_deploy.py`, `proxy/tools/pc_deploy.py`, `core/harness/job.sh` or `harness/job.sh`.
   - Why: worktrees (`nap-job-*`) and the main clone are all valid checkouts, and the existing fixtures use a separate repo path.
   - The exemption has little power: it only skips the launch and inline-code rules for that unit, and the script's own writes are
     invisible to a hook that reads command text anyway. The look-alike deny is what gives it meaning.
2. **The look-alike deny** applies only when the command names a protected root, because a python script is not a writer. That is how
   `/tmp/pc_deploy.py install --game "<root>"` is denied.
3. **Five deny rows, not six.** The brief says six but lists five (ctl, play, saves, the prefs file, save_games).
4. **More module-level names than the brief asked for.** `PR_HEAD`, `alias_files`, `expand_short` and `FALLBACK` are all module-level so
   tests can inject them. The brief asked for an injectable resolver and `expand_short`; the others follow the same pattern.
5. **`decide()` accepts a `Roots` object, or a 2- or 3-tuple** (games, state, write-protected paths). `protected_roots()` still returns the
   2-tuple, so the existing tests are unchanged.
6. **`-c alias.X=commit` is not itself denied**; only `git config alias.X commit...` is. The brief's commit family requires
   `git -c alias.ci=commit ci` to be denied without a trailer and allowed with one, so the alias is judged by what it runs.
7. **`hook_parse.py` is a separate file** from the start, since a single file would have passed 700 lines. Both have headers and `tools`
   rows, and the gate is green.
8. **The open questions are built to the brief's defaults** ("the brief's defaults; open for Liam"). They are not Liam's answers.

## Open questions
All four are still open for Liam. The build uses the brief's defaults, and each is a small change to revert.
1. **An unresolvable target that is not tainted.** Built: deny only when the command also names a protected root. The alternative, denying
   every unresolvable write, breaks `echo x > "$OUT"`.
2. **AppData in the hook.** Built: the hook also denies shell writes to the AppData prefs file and to `save_games`, as well as the Edit rows.
3. **Remote branch deletion.** Built: deleting `main`, `plan/`, `meta/`, `job/` or `brief/` remote branches is denied, while `scratch/*` and
   other names stay allowed. If the answer is no, the denials go and the allowed cases stay.
4. **`--no-verify` scope.** Built: denied on `push`, `merge`, `rebase`, `cherry-pick` and `am` as well as `commit`. If the answer is no, the
   other five subcommands drop out.

## Fix round 1

1. **Blocker, hard-coded path** (fixed, d2c5999): `REPO` in `tests/test_claude_hook.py` is now `ch.norm(ch.ROOT)` and the fixture uses `core/proxy/tools/pc_deploy.py`, so it no longer depends on the author's machine.
2. **Sibling exemption** (fixed, d2c5999): a script is exempt only under this checkout or one of its `git worktree list` entries, and only in the `core/` form (bare `proxy/tools/` and `harness/job.sh` suffixes dropped). Both review commands are in the corpus as `deny`.
3. **Writers** (fixed, d2c5999): curl/wget `-o/-O/--output/--output-document/-P`, and `perl -i`, now count as writes; corpus rows added. Other flags (`-K` config, `aria2c`) are listed as residuals in the hook header.
4. **Later item** (left): `gh pr merge job/<id>` stays allowed by design; CI's `policy` owns the own-review rule.
