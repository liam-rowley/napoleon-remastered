# J41: Local gates run the proxy host tests

Phase 1. `python3 core/wsc.py gates` on the PC never builds or runs the proxy's C++ host tests (`proxy/tests/test_*.cpp`), so a
change under `proxy/` passes locally and fails only in CI's `proxy` job. J15's review commit 6316cb9 did exactly that: a comment in
`proxy/core/console.cpp` named the game and broke `test_console`'s no-game-in-core lint, seen only in CI (PR #50). Make the local
run cover them, fast when `proxy/` is untouched, and never a silent pass when it cannot build.

Model: Sonnet (D15 default: build plumbing and a Python test, no reverse engineering). Budget about 80 tool calls; at the cap, stop,
commit, report what is left. No subagents.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J41`). Read `docs/DECISIONS.md` D22, D31, D32 and `jobs/J20/report.md` (the `--docker` route,
  ~55 s per build, Docker Desktop is a per-user install that may not be running).
- Read, don't rediscover: `proxy/tools/build.sh` (targets `all`, `tests`, `--docker`; the `tests` target compiles each
  `proxy/tests/test_*.cpp` with the host `g++` and runs it with `--root`), `proxy/README.md` "Build", `.github/workflows/gates.yml`
  (job `changes`: the proxy input set is `^\.github/workflows/|^proxy/|^registries/(engine_sites|config_keys)\.jsonl$`),
  `core/warscape/gates.py` `gate_tests` (runs `unittest discover` on `tests/`, reports only `Ran N` on success: skips and stderr are
  invisible), `tools/verbs/setup.py` `bash_kind` and `check_docker`.
- Overlap with J22 (Windows host tests find Git Bash, not built yet): this job must call `build.sh` through Git Bash explicitly,
  never through `bash` on PATH (the WSL launcher on the PC). Write the finder once as a small shared helper next to `bash_kind`
  (or reuse `bash_kind`), so J22 can use it; do not fix J22's tests (`test_job_sh`, `test_pc_deploy`) here. Name the helper in the
  report for J22.

## Decisions already made for this job
- **One source for the proxy input set.** Move the `changes` file patterns out of `gates.yml` into one repo tool (header and
  `tools` row) that prints `proxy=` / `harness=` for a base; `gates.yml` calls it and the local check calls it. Locally the base is
  `git merge-base origin/main HEAD` and the set also includes staged, unstaged and untracked files (a local edit must trigger the
  run). Base unknown (no `origin/main`, shallow) means "changed", the same as CI.
- **Where it runs:** a repo test, `tests/test_proxy_host.py`, so the `tests` gate (full `wsc gates`, not `--fast`) runs it. Not the
  pre-push hook: it is the core's (`core/.githooks/pre-push`) and runs `--fast`, which excludes `tests`.
- **Routes, in order:** inputs unchanged → skip in under 2 s with the reason "proxy inputs unchanged against <base sha>". In CI
  (`GITHUB_ACTIONS` set) → skip, "covered by the `proxy` job". Native toolchain on PATH (`i686-w64-mingw32-g++` and `g++`) →
  `proxy/tools/build.sh all`. Else Docker answering (`docker info`) → `proxy/tools/build.sh --docker all`. Else no toolchain.
  A failing build or host test fails the test with the failing suite names and the last lines of the output.
- **No toolchain must not pass silently.** `gate_tests` cannot show a skip today, so a skip there is a silent pass. Do both:
  1. Core: a warscape-core PR that makes `gate_tests` return `warn` (never `error`) when unittest reports `skipped=N`, with the skip
     reasons in the details (`-v` output or a result class). Open it and stop there for the core part (`core/docs/CONSUMING.md`);
     the pin bump that brings it in is a later job: file it as a `needs_brief` row in the report's open questions, not here.
  2. Until that tag is pinned, the no-toolchain case **fails** the test with a message naming the skipped suites (the
     `proxy/tests/test_*.cpp` stems), how to fix it (start Docker Desktop, or `wsc setup`), and the one-off opt-out
     `WSP_PROXY_TESTS=skip`, which turns it into a skip with the same message on stderr. Leave a `# J41:` comment at that branch
     saying which core tag lets it become a plain skip.
- Never change files inside `core/` (the `core_pin` gate). Do not change `build.sh`'s targets or the CI `proxy` job's steps; a
  `build.sh` fix that the routes need is allowed and goes in the report.
- The `tests` gate's timeout is 600 s; `--docker all` is ~55 s plus apt. If it ever nears the timeout, say so in the report rather
  than raising the core default.

## Deliverables
1. The input-set tool, used by `gates.yml` `changes` and by the test; CI output for `proxy=` / `harness=` unchanged for the same diff.
2. `tests/test_proxy_host.py` with the routes above, calling `build.sh` through Git Bash on Windows.
3. Unit tests (in the same file or a sibling) for the route choice and the input set, with the toolchain probes and git injected:
   unchanged → skip; CI → skip; native; docker; none → fail with the suite names; none + `WSP_PROXY_TESTS=skip` → skip; untracked
   `proxy/` file → changed; `registries/config_keys.jsonl` → changed; `docs/` only → unchanged.
4. The warscape-core PR (link in the report).
5. `proxy/README.md` "Build" and `CLAUDE.md` (only if a rule changes) say the local gates now run the host tests and how to opt out.

## Proof (on the PC, Git Bash, each with the command and its output in the report)
a) A deliberately failing proxy test (e.g. a temporary `CHECK(false)` in one `test_*.cpp`, or the J15 lint case: the game's name in
   a `proxy/core/` comment) fails `python3 core/wsc.py gates --only tests`; revert it, and the same command passes.
b) No change under `proxy/`: the test skips in under 2 s (time it).
c) Docker Desktop stopped (ask Liam before stopping it, or use a PATH without `docker`): the run fails with the named suites and the
   fix; with `WSP_PROXY_TESTS=skip` it passes and prints the warning.
d) CI on the job branch: `gates` green (the test skips there), `proxy` green (`gates.yml` changed, so it runs).

## Kill criteria
- The `--docker` route cannot run the host tests from Git Bash after 3 attempts (paths, mounts, CRLF): stop, report the errors,
  propose the CI-artifact fallback route instead.
- Making the gate surface a warning needs more than a small change to `gate_tests` in the core: stop after opening the core PR as a
  proposal (draft) and keep the fail-closed behaviour; do not work around the core from the repo.
- Any step would need the game: it does not; stop and ask if one seems to.

## Finish
Write `jobs/J41/report.md`: what was built, the proof runs a) to d) with commands, times and CI run ids, the core PR link, the Git
Bash helper for J22, deviations from this brief and why, open questions (the pin-bump row to file). Then
`wsc reg set jobs J41 status=review report=jobs/J41/report.md`.
