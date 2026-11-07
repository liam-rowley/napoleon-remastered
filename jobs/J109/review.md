# J109 review

## Round 1 (2026-11-07, branch job/J109 at 3d251bcdc449)

**Verdict: merge after fixes.**

The speed-up is real and the stamp is sound, but deliverable 4 is not met on the PC's own route: the timeouts do not fire on time while Docker runs, so a hung build still dies on the gate's deadline with no named failure. The report's fresh-worktree figure also did not reproduce. No file outside this folder and the row was changed in this round; both fixes are left to the fix session.

### Machines
- Three full `wsc gates` in this review's fresh worktree at `3d251bc`, Docker up, `job.sh status` no lock, no failed test in any: 811 host tests, 43 skipped, the report's counts. The PC was not quiet: 4 `claude` processes were up, sampled between runs 1 and 3 at 18 % CPU, and run 1 shared the PC with this review's few short Docker probes.

| Run | State | `tests` | Target | Met |
| --- | --- | --- | --- | --- |
| 1 | fresh worktree, `lua` downloaded | 467.1 s (gate says "near the time limit") | under 450 s | no |
| 2 | same inputs, stamp hit | 63.5 s | under 150 s | yes |
| 3 | `build/` deleted, `lua` downloaded | 402.2 s | under 450 s | yes |

- `policy`: only the two refusals a branch has before its review (no verdict, row not `done`). It does not name rule 79, though `proxy/README.md` changed; the build id is `96722f4b8d52`, the report's figure, after all three runs.
- CI: all 9 checks passed or skipped on `3d251bc`. Run 42406461879 on `3494da4b` says `tests` 20.2 s, `timing: workers 4, cpu_count 4`; run 42403972478 on `main` says 43.7 s at `workers 1`. Both as reported.

### Findings

**should-fix 1. Deliverable 4 is not met: `BUILD_TIMEOUT_S` and `SMOKE_TIMEOUT_S` do not fire on time on Windows.** `tests/test_proxy_host.py:157` runs Git Bash through `subprocess.run(..., capture_output=True, timeout=...)`. On Windows, on expiry, `subprocess.run` kills the direct child and then calls `communicate()` with no timeout, which waits for the pipes to close, and the `docker` child still holds them. So the timeout lands when Docker ends, not when it expires. A hung or slow build runs on to the gate's 600 s kill, and the result is the gate's `timed out`, the unnamed failure the brief's deliverable 4 exists to remove. The comment at line 40 and the report's "so a slow build fails with its own message" claim otherwise, and `Budget` only proves the arithmetic.
- See it fail: `subprocess.run([git_bash, '-c', 'docker run --rm <pinned image> sleep 15; echo x'], capture_output=True, timeout=3)` raised `TimeoutExpired` after 15.6 s, and after 15.0 s with a plain `sleep 15`.
- The core's `gates.kill_tree` alone does not cure it: `Popen`, `communicate(timeout=3)`, `kill_tree`, and the pipes were still open 5 s later with the container up.
- What worked here: output to a temporary file instead of a pipe, `p.wait(timeout=...)`, then `kill_tree(p)`: `timed out` after 3.1 s with the output kept. Add a host test that uses a shell child outliving the timeout, since the fix is otherwise unproved.
- The container outlives this kill, and `build.sh` does not name it, so nothing here can stop it (a core question; see Later). The report should say so.

**should-fix 2. `BUILD_TIMEOUT_S` 420 is too tight for what a fresh worktree really takes, and the report's fresh figure is its best case.** The report gives 350.1 s fresh at `workers = 4`, and that run skipped the `lua` download (its Deviation 2). This review got 467.1 s and 402.2 s on the same route with the download, on a PC with other sessions up. Smoke is about 67 s, so run 1's `--docker all` was near 400 s, about 20 s under the 420 limit, while `tests/test_proxy_host.py:41` still justifies it with 277 s and 330 s. Every fresh worktree meets this case, including every reviewer's first run, and once finding 1 is fixed a slow build there fails outright. The time was not split inside the module in this review, so the 400 s is an estimate.
- Fix: rebalance inside the same sum (for example 460 and 120: smoke is 67 s, so 120 is still nearly double), and put the fresh range into the comment and the report: 350 s without the download, 402 to 467 s with it on a shared PC. `timeout_s` stays 600.
- The brief's first target is read on a quiet PC, and the warm figures the report gives for "after a proxy input changed" are well inside it, so run 1's 467.1 s is not a missed target by itself. The report should still not read as if 350 s is what a fresh worktree gets.

**later 3. The local runs have no evidence to open.** m1 to m3, r1 to r5 and the `w4_*` runs exist only as figures in the report; the labels are the session's and no log is committed, and the Docker shim's timings cannot be rerun from the branch. This review's runs 2 and 3 agree in kind for repeat and fresh runs, and the CI figures check out. A future job with a measurement deliverable should commit the `timing:` lines.

**later 4. Core items, for a W row when the core next moves:** the report's open questions 1, 3, 4 and 5 stand (shared download cache, baked image, the stale `tests/test_acceptance.py` path in `core/docs/CONSUMING_OPTIONS.md`, surfacing a stamp hit in the gate), plus naming the `--docker` container in `build.sh` so that a timeout can stop it. Not filed yet: `core/docs/REVIEW.md` puts these in a `later` row through a `plan/` pull request in warscape-core, and this session is confined to its napoleon worktree, so that row is still to do.

### Checked and found sound
- **Risk-first read, the stamp** (a false pass would hide a broken DLL build). The real `[ci] inputs` regex keeps the `core` gitlink, so the core is hashed file by file; the unit test's injected predicate does not prove that, this review checked it with `ci.classify`. The hash is taken before the build, written only after both `all` and smoke pass, not written on the no-wine route, and never read in CI (it is asked after that check). `ci._git` turns `core.quotepath` off, so odd paths are not hashed as missing. A stamp left from older inputs can only match those same inputs. After run 1 the stamp was present and run 2 hit it; `build/` is ignored and the tree stayed clean.
- **Collisions under `workers`.** No `gettempdir`, fixed port or lock file shared by two modules. On the report's open question 2: `render_corners` and `stage` take a temporary site and `build/viewer/out` is only read, so `test_uikit` and `test_viewer` do not collide by reading the code. Not exercised here either: no `viewer.wasm`.
- **Scope.** Deviation 1 (`proxy/README.md`) is named and justified. No stale copy of the old timings left in `docs/`. Decisions 2, 4 and 5 are followed: `timeout_s` 600, per-worktree stamp, nothing under `core/`.

The `hooks` warn in this review's gates is this worktree's own (hook not wired), not the branch's.
