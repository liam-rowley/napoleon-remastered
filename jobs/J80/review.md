## Round 1 (2026-11-04, branch job/J80 at 2c540e8)

**Verdict: merge.**

Baseline accepted: 1db5e3979caf53745da431b473c0fcdca8385121

Checked: CI on the head is green (`gates`, `proxy`, `changes` pass; `viewer` and `harness-windows` skipped on an input tree that already passed in run 41929887320 at `cdfa0e8`). `wsc policy` run locally gives exactly the three standing lines before review (acceptance line, verdict, row `done`); this review and the row clear all three. `tests.test_uikit tests.test_viewer tests.test_jobs_hooks`: 124 tests OK, 10 skipped here (no viewer build), those render tests ran green in CI's `viewer` job.

**Baseline looked at (the accept line).** `git diff` of `baseline.json` against main adds only the `tolerance` block; every `rgba_sha256` and `wasm_sha256` is unchanged (Decision 7 and the kill criterion hold). I decoded all four reference PNGs with `pixeldiff.decode_png`: each pixel buffer hashes to the baseline's `rgba_sha256`. The PNGs add 530 KB (limit 8 MB). `git hash-object uikit/napoleon/baseline.json` = the sha above.

**Risk-first reading:** `ui_baseline_problems` / `ui_lock_problems` (a rule in the hook that judges its own branch) and `pixeldiff.judge` / `changes.judge` / `accept`. The sha in `accept()` is the git blob sha (LF write), the regex needs the line alone with the whole sha, a stale line fails, `plan/` and `meta/` are exempt, other branches refused, nothing is read when no baseline path changed. No existing assertion is weakened beyond the three named in Step 6, each with its replacement. `judge` fails on wasm difference, on `changed`/`new`/`removed`, and on any difference at all in a locked screen.

## Blockers
None.

## Should-fix
None.

## Later
1. **Merge order with J64 (report Open question 1), `viewer/pins.json`.** The new `playwright` key moves the DLL build id (`ui_pins` input). J64 (branch `job/J64` exists, needs 20 passes on the PC) would need a fresh 20-pass run if J80 lands first and J64 then merges `main`. J80 itself changes no `proxy/` or `harness/` path, so its own policy is fine. Liam may prefer to hold J80's merge until J64 lands. I did **not** queue auto-merge for that reason: see my reply. A lasting fix is a warscape-core item (hash only the keys `fetch_ui.py` reads). Backlog entry for warscape-core `docs/BACKLOG.md` still to be made by a core PR; not done in this review.
2. **No legal route for `LOCK.json` / baseline on `meta/`** (Open question 2): the core's globs refuse the file on `plan/` and `meta/`, so the hook's exemption is moot until `uikit/napoleon/LOCK.json` is added to `wsc.toml` `[policy] meta`. Liam's call; a `meta/` change.
3. **`channel_tolerance` 1** lets a uniform one-level shift pass as `within tolerance` (listed, not failing). Noise floor measured zero on PC and CI, so 0 would also have worked; a baseline change if Liam wants it.
4. **Eleven `TOKENS_ADDED` lengths with no LANGUAGE.md line** (Open question 4) and `min_on_ratio_all_77` 4.75 vs `min_ratio` 4.5 (Open question 3): Liam's choices; the test records them.
5. **Kill-criterion reading:** the builder continued after six refusals that named the accepted command form and used it, never `--no-verify`. Reasonable, no harm; noted.
6. The `tests` gate is near its 600 s limit (Open question 6); not caused by J80.
