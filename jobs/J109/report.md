# J109 report: the local tests gate sits at the 600 s cap

The `tests` gate no longer sits at the cap: 350.1 s in a fresh worktree, 280.7 to 283.9 s after a proxy input changes, and 62 s on a repeat run, against 531 s, 470 s and 470 s before. `timeout_s` stays 600 and no test was skipped or deleted. `[tests] workers = 4` did the first target and a per-worktree stamp in `tests/test_proxy_host.py` did the second. No DLL input changed: the build id is `96722f4b8d52` before and after.

## What was built

- `wsc.toml`: `[tests] workers = 4` (CI's `cpu_count`) and `first = ["test_proxy_host", "test_release_installer", "test_job_sh", "test_build_id", "test_jobs_hooks", "test_play", "test_pc_deploy"]`.
- `tests/test_proxy_host.py`: deliverable 3 was needed, so the module remembers a pass in `build/proxy/host_tests.stamp`. The stamp holds a sha256 over the path and content of every proxy input on disk, uncommitted and untracked files included, with the core counted file by file. The hash is taken before the build, and the stamp is written only after both `all` and smoke pass, so a run with no smoke writes none. A hit is a pass with one line on stderr naming the stamp, never a skip. It is asked after the CI check, so CI never reads it. New unit tests cover hit, miss, a missing stamp, no hash, the route order, what moves the hash, and that the stamp path is ignored.
- Deliverable 4: the header and both timeout comments carry measured figures. `BUILD_TIMEOUT_S` 540 became 420 and `SMOKE_TIMEOUT_S` 300 became 150, 570 s together, and a new test holds their sum under `timeout_s`.
- `tests/ci_inputs.py`: `ci.git` and `ci.tests_timeout_s()`, so the module reuses the core's git call and config.
- `proxy/README.md`: the two old timings, and the stamp (see Deviations 1).

## Evidence

All local runs 2026-11-07, full `wsc gates`, Docker up, `job.sh status` no lock and `not_running`. Labels are this session's. "Changed" means an untracked `proxy/j109_probe.txt`, or from r1 on the branch's own `proxy/README.md` commit. Timestamps came from a `docker` shim outside the repo that added `date` lines around the package step; `build.sh` was not edited.

**Deliverable 1, `workers = 1`** (`tests` line; m3 has no build):

| Run | `tests` | `test_proxy_host` | `--docker all`: packages + compile and test | `--docker smoke`: packages + test |
| --- | --- | --- | --- | --- |
| m1 changed, fresh worktree | 531 s | 351.6 s | 277 s: 29 + 248 | 67 s: 53 + 14 |
| m2 changed, `build/` warm | 470 s | 288.7 s | 216 s: 33 + 183 | 65 s: 52 + 13 |
| m3 unchanged | 178.2 s | skipped | none | none |

Modules over 10 s, m1 and m2 and m3 within about 2 s of each other: `test_release_installer` 41.9, `test_job_sh` 37.0, `test_build_id` 20.8, `test_jobs_hooks` 19.8, `test_play` 12.5, `test_pc_deploy` 10.5.

**The `apt` share:** 82 s of m1's 351.6 s (23%), 85 s of m2's 288.7 s (29%). Most of it is the smoke's wine, about 52 s. The largest part is compile and test, 248 s cold and 183 s warm.

**Deliverable 2, the five runs in a row** at `workers = 4`, no failed test in any, 811 host tests, 43 skipped:

| Run | Route | `tests` | Target | Met |
| --- | --- | --- | --- | --- |
| r1 | real build, warm | 283.9 s | under 450 s | yes |
| r2 | stamp hit | 62.2 s | under 150 s | yes |
| r3 | real build, warm, probe content changed | 280.7 s | under 450 s | yes |
| r4 | stamp hit | 62.2 s | under 150 s | yes |
| r5 | stamp hit | 62.4 s | under 150 s | yes |

Without the stamp the second target was missed: `w4_changed_warm`, `workers = 4` before deliverable 3, took 287.7 s on the same inputs.

**Fresh worktree at `workers = 4`,** run after the five because they all had `build/` warm: `build/` deleted, 350.1 s (`w4_cold2`), under 450 s. The attempt before it failed, see Deviations 2.

**CI:** run 42406461879 on `3494da4b`: `gates`, `proxy`, `harness-windows` success. `timing: workers 4, cpu_count 4`, `tests` 20.2 s against 43.7 s at `workers = 1` on `main`'s `b98c7ded` (run 42403972478). Above 1 worker the per-module seconds do not compare, the `tests` totals do.

**Fixed paths or ports:** none needed fixing, and nothing was changed for this. No test uses `gettempdir`, a fixed port or a lock file. The fixed path the brief and `core/docs/CONSUMING_OPTIONS.md` name in `tests/test_acceptance.py` is gone: it uses `TemporaryDirectory`. `tests/test_uikit.py` and `tests/test_viewer.py` both read `build/viewer/out`; only `test_uikit` writes there (`uikit_gate`), so by reading they do not collide, but see Open questions 2.

**Build id:** `96722f4b8d52` before and after (`build_id.py --no-dirty`).

**`timing:` line of the last run (`w4_cold2`):** `timing: workers 4, cpu_count 16`; slowest: `test_proxy_host` 350.1 s, `test_release_installer` 48.2 s, `test_job_sh` 40.5 s, `test_harness_host` 28.1 s, `test_build_id` 26.0 s, `test_jobs_hooks` 22.9 s, `test_play` 18.7 s, `test_pc_deploy` 17.4 s, `test_registry_merge` 10.0 s, `test_claude_hook_corpus` 7.3 s.

Usage: 60 tool calls; models: opus; 1 session, the build only, counted by hand, about, 2026-11-07

## Deviations from the brief and why

1. **`proxy/README.md` changed,** though the brief names only `wsc.toml` and `tests/`. It held the same old timings as the module, and `CLAUDE.md` says to fix every living copy; it also has to say how to force a real run. It is not a build-id input (the id did not move), but it is in the CI `proxy` set, so this branch ran CI's `proxy` job, which passed.
2. **One gates run failed, outside the five.** The first fresh-worktree run at `workers = 4` (`w4_cold`) failed `test_proxy_host` at 173.5 s: `fetch_lua.py` got `Connection refused` from `www.lua.org` after its retries. It was not a collision: curl from the host timed out on the same site at that moment, and it answered 200 about six minutes later. For the rerun I copied `lua-5.1.1.tar.gz` from the main checkout's `build/downloads` into this worktree's, and its sha256 matched the pin. So `w4_cold2` is cold for every compile but skipped that one download. m1 is the fully cold figure, with the download. No stamp was left by the failed run.
3. **A sixth and seventh run beyond the five,** for the fresh-worktree case, which the five do not cover and which is what a reviewer gets.
4. **`first` has no `test_harness_host`.** It took 20 to 28 s here only because this branch changes its inputs, and it does not decide the total.

## Open questions

1. **A fresh worktree depends on `www.lua.org` being up (a core question, not fixed here).** `build/downloads` is per worktree, so every fresh worktree downloads the tarball, and an outage fails the gate with a named but unrelated error, as `w4_cold` did. It looks like a W row: let the fetchers read a shared download cache outside the worktree, still sha-checked. `fetch_lua.py` is a build-id input, so that change moves the id and needs a new 20 passes.
2. **The render tests were not exercised under workers.** `build/viewer/out/viewer.wasm` does not exist here, so `test_uikit` and `test_viewer`'s `Render` classes skipped in all runs, as did the numpy, Pillow and vanilla-game tests. A machine with those present runs them in parallel for the first time. The read says no collision; no run proves it.
3. **The `apt` share, W row text if wanted:** "`build.sh --docker` installs its packages on every run: about 30 s for `all`, about 52 s for `smoke`. Bake them into a local image keyed on `toolchain.py`." It would save about 80 s of a real build, so real builds would drop to about 200 s. `build.sh` and `toolchain.py` are both build-id inputs, so this is rule-79 exposed: a new 20 passes. Both targets are met without it, so I would not spend that run on this alone.
4. **`core/docs/CONSUMING_OPTIONS.md` still names the fixed path in `tests/test_acceptance.py`,** which is gone. A one-line core fix for the next core change.
5. **A stamp hit is hard to see in `wsc gates`.** The gate keeps a passing module's output to itself, so the printed line shows only when the module runs alone; in the gate a hit shows as `test_proxy_host` missing from the slowest ten. A core change could surface it.
