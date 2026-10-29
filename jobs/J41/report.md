# J41 report: Local gates run the proxy host tests

Built on `job/J41` from Claude Code on Liam's PC (Git Bash), session `1353b89f-568f-4c28-a816-8f3e6505e2cf`, 2026-10-29.

## What changed and why
1. **One source for the input sets: `tools/changed_inputs.py`** (header, `tools.changed_inputs` row). `classify(files)` holds the
   `proxy` and `harness` patterns that used to be inline in `gates.yml`. `--base <sha>` prints `proxy=`/`harness=` for base..HEAD (an
   empty or unknown base means everything changed, as before); `--local` uses `git merge-base origin/main HEAD` plus `git diff HEAD`
   (staged and unstaged) and untracked files, and a shallow clone or no `origin/main` counts as changed. The changed files go to
   stderr, the key=value lines to stdout. `gates.yml` `changes` keeps its event-specific base selection and now runs
   `python3 tools/changed_inputs.py --base "$base" >> "$GITHUB_OUTPUT"`.
2. **`tests/test_proxy_host.py`**, run by the full `tests` gate (not `--fast`, so not pre-push). Routes in the brief's order:
   unchanged -> skip `proxy inputs unchanged against <base>`; `GITHUB_ACTIONS` -> skip `covered by the `proxy` job`; native
   `i686-w64-mingw32-g++[-win32]` and `g++` -> `build.sh all`; `docker info` answers -> `build.sh --docker all`; otherwise fail, naming
   the `proxy/tests/test_*.cpp` stems, the fix (Docker Desktop, `wsc setup`) and the opt-out `WSP_PROXY_TESTS=skip`, which turns it
   into a skip and prints the same message as a WARNING on stderr. The `# J41:` comment at that branch says it becomes a plain skip
   once a core tag with warscape-core PR #4 is pinned. A failed build names the failed suites (`build.sh: test_x FAILED`, or a
   compile error that names `proxy/tests/test_x.cpp`) and the last 30 lines. Docker is probed only after the cheaper routes.
3. **Git Bash helper for J22: `git_bash()` in `tools/verbs/setup.py`**, next to `bash_kind`. Off Windows it returns `bash` on PATH;
   on Windows it returns `bash` on PATH only when `bash_kind` says `git`, then the install that `git --exec-path` names
   (`<root>/bin/bash.exe`, then `usr/bin/bash.exe`), then `%ProgramFiles%`, `%ProgramW6432%` and `%LOCALAPPDATA%` Git folders;
   None when none is found. Probes are injectable (`which`, `git_exec_path`, `isfile`). `test_proxy_host.py` runs `build.sh` with it.
4. **Unit tests** (in `tests/test_proxy_host.py`, 20 besides the real run): routes unchanged (no probes called), CI, native (both
   mingw names), docker, none -> fail naming suites, none + opt-out -> skip, unknown base -> changed; input set: untracked `proxy/`
   file, uncommitted edit, `registries/config_keys.jsonl` and `engine_sites.jsonl`, docs/jobs only -> unchanged, workflow -> both,
   harness set, shallow / no `origin/main` / empty base -> changed; `failed_suites`; `git_bash` for posix, Git on PATH, WSL on PATH
   with the Git install found from `--exec-path`, and none.
5. **warscape-core PR #4** (https://github.com/liam-rowley/warscape-core/pull/4, branch `tests-gate-warns-on-skips`): `gate_tests`
   runs `unittest discover -v`. When a run passes with skips it returns `warn` with one `<dir>: skipped <Class.test>: <reason>` line per
   skip; a failing run stays `error` and lists the skips too. `gates.unittest_skips` handles both test-id formats and tests that have a
   docstring (the id is then on the line before). Host tests use real `unittest -v` output. The core's own gates with it: 11 ok, 1
   warn. The warn is `PrePush.test_hook_runs_the_fast_gates_from_a_game_repo`, which has been skipping silently on Windows. No
   version bump or tag (that follows the merge).
6. `proxy/README.md` "Build": the local gates run the host tests, the routes, and the opt-out. `CLAUDE.md` unchanged (no rule changed).

## Proof
All on the PC in Git Bash, Docker Desktop 29.6.2 running, no native mingw on PATH (so the PC takes the Docker route).
- **a) A failing proxy test fails the gate.** The J15 case: `// Napoleon console ...` added as line 1 of `proxy/core/console.cpp`.
  `time python3 core/wsc.py gates --only tests` -> `FAIL /src/proxy/tests/test_console.cpp:135: !named`, `build.sh: test_console
  FAILED`, `AssertionError: proxy host tests failed (docker): test_console`, `gates: 0 ok, 0 warn, 1 failed in 94.1 s` (real 1m34s).
  Reverted (`git checkout proxy/core/console.cpp`), the same command: `ok tests 188 host tests passed (tests) (93.0 s)`.
- **b) No proxy change skips in under 2 s.** A detached scratch worktree on `origin/main` (dc014e0) with only the three new non-proxy
  files copied in: `changed_inputs.py --local` -> `proxy=false harness=false`; `time python3 -m unittest discover -v -s tests -t tests
  -p test_proxy_host.py` -> `skipped 'proxy inputs unchanged against dc014e0d3312'`, `Ran 21 tests in 0.323s`, real 0.50 s.
- **c) No toolchain.** I did not stop Docker Desktop. Instead the run used a PATH without Docker's folder (`command -v docker` -> none):
  `FAILED (failures=1)` in 0.38 s with `proxy host tests NOT RUN (no toolchain): test_config, test_console, test_crash, test_dev,
  test_display_guard, test_guard, test_patch_engine, test_sha1. Fix: start Docker Desktop ... or run python3 core/wsc.py setup ...
  One-off opt-out: WSP_PROXY_TESTS=skip`. With `WSP_PROXY_TESTS=skip`: `WARNING: proxy host tests NOT RUN ...` on stderr, `OK
  (skipped=1)`. Through the gate under the pinned core v0.2.0 the opt-out shows only `ok tests 188 host tests passed`: the silent pass
  that core PR #4 removes, and the reason no-toolchain fails by default.
- **d) CI on `job/J41`.** Run 40960315465 (head of the first J41 commit): `changes` printed `proxy=true harness=true` through the new
  tool; `gates` success (the test skips there: `GITHUB_ACTIONS`); `proxy` success (`build.sh: host tests passed`); `harness-windows`
  success. Run 40961258213 (README commit): `changes`, `gates` and `proxy` success; `harness-windows` was still running when this was written.
- **Same CI output for the same diff:** I compared the old inline grep patterns with `classify()` over the parent..commit diffs of
  the last 60 non-merge commits on `origin/main`: 54 diffs compared, 0 differ.
- Local `python3 -m unittest ... test_proxy_host.py` with the branch's changes: 21 tests OK in 58.9 s (Docker route ran the real suites).

## Deviations
- **Timing:** `build.sh --docker all` through the gate took about 93 s on the PC (the J20 figure was ~55 s; apt in a fresh container
  each run is most of the difference). That is well under the 600 s gate timeout. The test's own build timeout is 540 s, so a hung
  build fails with a message before the gate's timeout kills the run.
- **c) without stopping Docker:** the brief allowed a PATH without `docker`. I used that and did not ask to stop Docker Desktop.
- **Commit hook:** this session was started in `C:\Users\liamr\repos`, not the repo folder, so `CLAUDE_PROJECT_DIR` did not contain
  `tools/claude_hook.py` and the hook let a commit through without the trailer. I amended that commit before pushing, and every
  pushed commit carries `Claude-Session`. Worth a guard (open question 2).
- Model: this job ran on Opus, not the brief's Sonnet (the session's model when Liam asked for J41).

## Open questions
1. **Pin bump (file as `needs_brief`):** "Bump the core pin to the tag that carries warscape-core PR #4 (tests gate warns on skips);
   then make the no-toolchain branch of `tests/test_proxy_host.py` a plain skip (the `# J41:` comment) and drop the default failure."
   Depends on PR #4 being merged and tagged by Liam.
2. The `Claude-Session` hook does nothing when Claude Code starts outside the repo folder (it resolves `tools/claude_hook.py` from
   `CLAUDE_PROJECT_DIR`). `pr_policy.py` still catches it in CI. A user-level hook, or `wsc setup` warning about the start folder,
   would catch it locally.
3. J22 can use `setup.git_bash()` for `test_job_sh` and `test_pc_deploy`. I did not touch those tests.
