# J109: The local tests gate sits at the 600 s cap

Phase 1, tooling, ahead of the game-facing jobs on purpose. Liam, 2026-11-07: game-facing work next, and "the gates and whatnot can't be slow". Every job that touches the DLL runs full `wsc gates` several times with Docker up, and that is the case this gate is slowest in: J78's sessions and J88's review all sat at or over the cap with no test failing. This job makes the gate fast without raising the cap, and then gets out of the way.

Model: Opus, reason: Liam's "Opus across the board" (2026-11-06), and telling a real test collision from a flake under parallel workers needs an independent read of what each module shares.
Budget about 80 tool calls (J88 used 36 of 90, J95 100; most of this job's time is the harness running, not calls). Subagents are not needed. Waiting belongs to the shell's background runs, not to repeated calls.

**No DLL or harness input changes: this job carries no 20 passes (rule 79).** It changes `wsc.toml` `[tests]` and files under `tests/`. `needs_pc` stays false: the game is not launched. It does need Docker and a PC with no acceptance run on it, see Start.

## Start
- If this session's model is not the row's, stop and say so.
- Follow `CLAUDE.md` (Jobs: branch `job/J109`). After any pull that moves the pin, run `git submodule update --init core`: a plain pull leaves the old core checked out, and `gates --fast` then refuses the push.
- Read `jobs/J78/report.md` (Evidence and Deviations on the gates), `jobs/J78/review.md` finding 9, `jobs/J88/review.md` (Later, item 2), and `core/docs/CONSUMING_OPTIONS.md` "The `tests` gate".
- Docker must answer (`docker info`). If it does not, ask Liam: this job has no measurement without it.
- `bash core/harness/job.sh status` must show no lock and `not_running`, and no acceptance run may be going. This job's full runs load the PC and would spoil a run's numbers.

## Target facts
Check each again before relying on it.
- **The figures so far**, all full local runs: 542 s and 577.7 s (J78's builder and reviewer), 602.8 s and 545.1 s (J78's fix round and review), 580.8 s (J88's review, which shared the PC with other work, so an upper figure), 187.5 s (J88's builder, Docker down, so `test_proxy_host` did not run). `test_proxy_host` was 382.7 s of J88's review run. The row's "suspect, unproved" is therefore nearly proved, but not where inside the module the time goes.
- **`[tests] workers` and `first` exist in the pin and the game has not opted in:** `core/docs/CONSUMING_OPTIONS.md` is the owner, including the rule that tests may share nothing fixed, and that `tests/test_acceptance.py` has a fixed temp path. J88 left `workers` at 1 for this job. `wsc gates` and CI read the same keys, and `workers` must stay at or under the runner's `cpu_count`: every run logs it on the `timing:` line, so read it from a CI `gates` log as well as locally.
- **`timeout_s` is one deadline across all workers,** and above one worker the seconds on the `timing:` line are each process's wall time, so they do not compare with a `workers = 1` run.
- **`tests/test_proxy_host.py` runs two container builds:** `build.sh --docker all`, then `--docker smoke`, when `ci.local_changes` says a proxy input changed. Its comments say about 93 s and 70 s, and those are old: J85's proof took about 5.5 minutes for one `--docker all` on 2026-11-07 (run 20261107_j85auto1, `tick.log`). Each `--docker` run starts from the base image and installs its packages, so part of that is probably `apt`. Measure it, do not assume it.
- **`BUILD_TIMEOUT_S` 540 plus `SMOKE_TIMEOUT_S` 300 is over the 600 s deadline,** so a slow build dies on the gate's timeout, with no named failure.
- **A skip in that module is a warn** in the core's `tests` gate (J41).
- **The toolchain is a build-id input** (`core/proxy/tools/toolchain.py`, W24): a change to what `build.sh` installs is a core change, and it can move the build id.

## Decisions already made for this job
1. **The targets, read off the `tests` line of `wsc gates`, Docker up, quiet PC.** First run after a proxy input changed: under 450 s, which is the gate's own `warn_at` line. Second run on the same inputs: under 150 s. Liam's reason is that a builder runs gates repeatedly on the same head.
2. **`timeout_s` stays 600.** The row says so. No `[gates] skip`, and no test is deleted or skipped to reach a target.
3. **Measure before changing anything.** Deliverable 1 comes first, and its table decides how far 2 and 3 go.
4. **Any result reuse is per worktree.** A fresh worktree runs the host tests for real, so a reviewer's independent run stays independent, and CI's `proxy` job always runs them.
5. **No core change here.** If the time is in `build.sh` or its `apt` step, write what the core change would be under `## Open questions`, with its rule-79 exposure, for a W row. Do not edit `core/`.

## Deliverables
1. **The measurement.** One full `wsc gates` at `workers = 1`, Docker up, proxy inputs seen as changed, then the same with them unchanged. A table in the report: the whole `tests` gate, every module over 10 s, and inside `test_proxy_host` the seconds for `--docker all` and for `--docker smoke`, each split into package install and compile plus test, from timestamps around the steps.
2. **`[tests] workers` and `first` in `wsc.toml`.** Slowest modules in `first`, and the highest `workers` that is at or under CI's `cpu_count` and holds. Fix any fixed path, port or lock file two modules share, in `tests/`. It holds when **five full `wsc gates` runs in a row** have no failed test, and CI's `gates` check is green on the branch with a time no worse than `main`'s.
3. **Repeat runs, only if decision 1's second target is still missed after 2.** `test_proxy_host` remembers a pass: a stamp in the worktree's ignored `build/proxy/`, keyed on the content of the proxy inputs. The stamp holds the hash of those inputs, so a changed input cannot match it. A hit is a pass with one printed line naming the stamp, never a skip (a skip is a warn). CI never reads it. Host unit tests for hit, miss and a missing stamp, with the route's probes injected as the module's tests already do.
4. **The module tells the truth.** Its header and the two timeout comments carry the measured figures with the run they came from, and `BUILD_TIMEOUT_S` plus `SMOKE_TIMEOUT_S` fit inside `timeout_s`, so a slow build fails with its own message.

## Out of scope
- Anything under `core/`, including `build.sh`, `toolchain.py`, an image with the packages baked in, and the gate's own code (decision 5).
- `gates --fast`, which takes seconds; the CI workflow files; the proxy's C++ tests themselves.
- Game-facing jobs, J85's run, and any other tooling row. A slow test that is not on the way to the targets stays as it is.

## Open questions
None: decisions 1 to 5 settle what the row left open.

## Kill criteria
- `job.sh status` shows a lock or a running game at the start: stop and say so, do not wait in the session.
- `python3 core/proxy/tools/build_id.py --no-dirty` prints a different id from `main`'s, or `python3 core/wsc.py policy --branch job/J109 --base origin/main` names rule 79: stop and report the line.
- A collision under `workers` cannot be fixed in `tests/`: keep the highest `workers` that held, report the module pair.
- A flake in the five runs, twice for the same `workers` after a fix: drop one step and report it. At `workers = 2` still flaking: put `workers` back to 1, stop, report.
- CI's `gates` fails or runs slower than `main` with `workers` set: lower it to what CI holds, and report both figures.
- Both targets still missed after deliverables 2 and 3: stop, commit what helped, report the table. Do not raise `timeout_s`.
- Over about 80 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J109/report.md`: `## What was built`, `## Evidence`, `## Deviations from the brief and why`, `## Open questions`, with a `Usage:` line. It must also say: deliverable 1's table; the `workers` and `first` values and CI's `cpu_count`; the `tests` figure of each of the five runs against both targets; every fixed path or port found and what was done; whether deliverable 3 was needed; the build id before and after; the `timing:` line of the last run; the `apt` share and, if it is large, the W row text. Then `wsc reg set jobs J109 status=review report=jobs/J109/report.md`, push, and open the draft pull request `wsc jobs next` printed.
