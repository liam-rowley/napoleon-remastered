# J41 review: local gates run the proxy host tests

2026-10-29. Independent review of `job/J41` at `25577d6`, by a fresh session that did not build it (`docs/REVIEW.md`), session
`230d6e9c-87e8-4fcd-ba71-00da335d0330`.

**Verdict: merge.**

Every deliverable is present and matches the brief's decisions: one input-set tool used by both CI and the local test, the route
order (unchanged, CI, native, docker, none), the fail-closed no-toolchain branch with the `WSP_PROXY_TESTS=skip` opt-out and its
`# J41:` comment, `build.sh` run through Git Bash via a shared `setup.git_bash()` for J22, no `core/` change, no change to `build.sh`
or the CI `proxy` job's steps, and the warscape-core PR (#4, now merged; the pin bump is left to a later job as the brief says). The
deviations (Opus instead of Sonnet, proof c by PATH instead of stopping Docker, ~93 s instead of ~55 s) are named and reasonable.

## What I checked myself
- **Gates on the branch (PC, Git Bash):** `python3 core/wsc.py gates` -> `11 ok, 1 warn, 0 failed in 90.4 s`; `tests` took 89.6 s
  because this branch changes `gates.yml` and `proxy/README.md`, so the test took the Docker route and the real host suites passed.
  The one warn is `hooks` (this clone's `core.hooksPath` is an absolute path), unrelated to the branch.
- **Proof c reproduced:** with Docker's folder removed from PATH, `unittest ... -p test_proxy_host.py` -> `FAILED (failures=1)` naming
  all 8 suites, the fix and the opt-out; with `WSP_PROXY_TESTS=skip` -> `WARNING: proxy host tests NOT RUN ...` and `OK (skipped=1)`.
- **"Same CI output for the same diff":** I re-ran the comparison independently (old inline `grep -E` patterns vs `classify()`, parent
  vs commit over the last 80 non-merge commits of `origin/main`): 54 diffs compared, 0 differ.
- **CI on the head commit (run 40961617061):** `changes`, `gates` and `proxy` success; `harness-windows` was still running at the time
  of writing. Run 40960315465 (first commit) was green on every job. The report's run 40961258213 shows as `cancelled` (superseded by
  the next push), not still running.
- **Core PR #4:** `gate_tests` runs `-v`, a passing run with skips is `warn` with each skip's reason, a failing run stays `error` and
  lists skips too; tests use real `unittest -v` output. Small and as the brief asked.
- `tools/pr_policy.py --branch job/J41 --base origin/main` before this review: only the two expected refusals (no review, row not
  `done`).

## Risk-first reading
I read `tests/test_proxy_host.py`, `tools/changed_inputs.py` and `setup.git_bash()` in full, since a wrong input set or route makes
the gate silently pass (the failure this job exists to stop). The base logic is right (shallow, no `origin/main`, empty base or a
failing git call all mean "changed"); untracked files use `--exclude-standard`, and build output goes to the ignored `/build/`, so a
build does not make the next run look changed. `git_bash()` never returns the WSL launcher on Windows. A hung build fails at 540 s,
under the gate's 600 s.

## Reviewer fix (outside J41's scope, Liam's call 2026-10-29)
PR #55's first CI runs (40962483519, 40962535611) failed `core_pin` on every branch, not because of J41: warscape-core cut `v0.3.0`
at 21:56, and checkout's depth-1 submodule fetch then brings the core tip's tag but not the pinned `v0.2.0`, so the gate sees
"tags exist, none on HEAD". Reproduced on the PC with a depth-1 clone of `job/J41` plus `git submodule update --init --depth=1`:
`FAIL core_pin`; after fetching the pinned tag: `ok core_pin core 0.2.0 as pinned (tag v0.2.0)`. Fix: a `gates` job step in
`.github/workflows/gates.yml` that fetches the tag named in `wsc.toml` `[core] version` into the core submodule. Longer term the
core's `pin_problems` should not read a shallow submodule's foreign tags as "untagged" (later item 5).

## Findings
No blockers, no should-fix items.

**Later** (for this repo):
1. **The pin bump must not turn every run into a warn.** Once the core tag with PR #4 is pinned, the `unchanged` route (the common
   case on any branch that does not touch `proxy/`) and the CI route are `skipTest`s, so `wsc gates` would show `WARN tests` on almost
   every run, locally and in CI's `gates` job, and a warn that is always there gets ignored. The pin-bump job (open question 1) should
   make those two routes pass (return, with the reason printed) and keep a skip only for the opt-out and no-toolchain cases.
   See it: `tests/test_proxy_host.py:78-79` plus core PR #4's `gate_tests`.
2. **Run evidence counts as a proxy input.** `proxy/runs/<run>/` holds committed PC run logs (J13, J15, J20 added some), and
   `^proxy/` in `tools/changed_inputs.py:20` matches them, so an evidence-only commit runs the ~90 s Docker build locally and the CI
   `proxy` job. This was true of the inline CI pattern too (no regression); excluding `^proxy/runs/` changes CI output, so it belongs in
   a job (J42 is a natural home).
3. **The `Claude-Session` commit hook does not run when Claude Code starts outside the repo folder** (report open question 2). This
   review's session was started in `C:\Users\liamr\repos` as well; I added the trailer by hand. Agree it needs a guard: `wsc setup` or
   the hook resolving the repo from `git rev-parse --show-toplevel` instead of `CLAUDE_PROJECT_DIR`.
4. `setup.git_bash()` also probes `%LOCALAPPDATA%/Git`, which is not a Git for Windows install folder (the per-user one is
   `%LOCALAPPDATA%/Programs/Git`, also probed). Harmless; drop it when J22 touches the helper.
5. **Core:** `pin_problems` (`core/warscape/gates.py:159`) fails a shallow submodule that holds a newer tag but not the pinned one
   (see the reviewer fix above). For warscape-core `docs/BACKLOG.md`: compare against the pinned tag's commit, or treat tags not on
   HEAD as absent.

## Rules this merge changes for other branches
From this merge on, the full local `wsc gates` on any branch that touches a proxy input needs Docker Desktop (or native mingw) running,
or `WSP_PROXY_TESTS=skip`; `--fast` and the pre-push hook are unchanged. CI is unaffected (the test skips under `GITHUB_ACTIONS`).
