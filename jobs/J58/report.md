# J58 report: a core pin bump that leaves the DLL and harness unchanged needs no acceptance run

Rule 79 (`tools/pr_policy.py`) now judges a move of the `core` gitlink on the core's own diff: it reads the pins at the merge base and
at HEAD, lists `git -C core diff --name-only <base pin> <head pin>`, and counts the pin change only when a listed path is a proxy/ or
harness/ path that is not `acc_exempt`. When the pins cannot be compared it counts the change, as before, and says why and how to fetch
them (fail closed). On J55's branch the rule-79 refusal is gone; J55's remaining refusals are its own (no review, row not `done`).

## What exists
- `tools/pr_policy.py`:
  - `rule79_path(path)`: the one test for "proxy/ or harness/ and not `acc_exempt`", used for this repo's paths and the core's.
  - `core_pin_diff(base, head='HEAD', root=None)`: the core's changed paths between the two pins, or a str
    `cannot compare core pins <a>..<b>: <git error> (fetch both: git -C core fetch origin <a> <b>)` (a missing gitlink names the ref).
    It reads only git objects (the gitlinks and the core's commits), so the branch under review cannot steer it with a file.
  - `acceptance_problems`: when `core` is in `changed`, adds `core/<path>` for each counted core path, or `core (<why>)` when
    `acc['core_diff']` is a str or missing. Everything else (streak, build id, watcher, foreign passes, evidence, `acceptance_active`)
    is untouched. `build_id.py`'s `INPUTS` is not restated: every core input lives under `proxy/`, which the prefix covers.
  - `main()`: `'core_diff': core_pin_diff(mb) if 'core' in changed else None` (the merge base's pin, matching `changed`).
  - Docstring: the rule-79 paragraph says what a pin change needs and what fail-closed means.
- `.github/workflows/policy.yml`: a step before the check that fetches the merge base's core pin when the checkout lacks it.

## Evidence
`policy.yml` question (target fact 3): `actions/checkout` passes `--depth` to `git submodule update` only when `fetch-depth` > 0, so
with `fetch-depth: 0` the core is cloned in full and the base pin is present whenever a core branch or tag reaches it (the pins are
tags: the `core_pin` gate requires it). I could not prove that on a CI run before this pull request leaves draft, so I added the
explicit fetch anyway (`cat-file -e` first, so it costs nothing when the commit is there); it ends in `|| echo`, leaving a real gap to
pr_policy's fail-closed message. No token or branch-protection change was needed (the core is public, D29; checkout's token is kept).

J55 (job/J55 at 2fb0c93: head pin d4c2677 `v0.6.0`, base pin e7893fe `v0.5.0`, 2026-11-01), on a scratch worktree, not committed there. J55 rewrites
`pr_policy.py` itself (per-row jobs registry), so J58's diff was applied on top of J55's own copy (one trivial conflict in `main()`):

    policy: jobs/J55/review.md is missing or has no "Verdict:" line: every job is reviewed before merge (docs/REVIEW.md)
    policy: row J55 must be `done` on the branch (the reviewer sets it with a merge verdict)
    policy: job/J55: REFUSED (289 files changed)

J55's own copy, for contrast, also printed `rule 79: this branch changes core but harness/acceptance/ledger.jsonl holds 0 consecutive
acceptance passes on build f3e33f228416 ...`.

## Tests
`tests/test_pr_policy.py`, new class `CorePin`: a fixture game repo with a real core submodule (a file:// clone) and two core commits.
- `test_a_bump_of_docs_and_python_only_needs_no_passes`: docs/ and warscape/ only, empty ledger: no error.
- `test_failing_fixture_a_bump_that_changes_the_cores_proxy_is_refused`: `proxy/src/a.cpp` changed: refused, names `core/proxy/src/a.cpp`.
- `test_failing_fixture_a_bump_that_changes_the_cores_harness_is_refused`.
- `test_exempt_paths_inside_the_core_do_not_count`: `harness/runs/...`, `proxy/README.md` and `saves/` do not count.
- `test_failing_fixture_a_base_pin_missing_from_the_core_fails_closed`: a gitlink to a commit the core lacks: the message and the fetch
  hint; a missing `core_diff` counts too.
- `test_a_branch_that_also_changes_this_repos_proxy_is_judged_as_before`.
- `test_main_passes_the_merge_bases_pin_diff`: the wiring in `main()`.

The existing rule-79 tests are unchanged and green: 35 tests in `tests.test_pr_policy` OK. `python3 core/wsc.py gates`: 11 ok, 1 warn
(the usual local skips: no numpy/Pillow, no viewer.wasm), 0 failed.

## Deviations
- `policy.yml` changed although the base pin is very likely already present; the reason is above (it could not be checked on CI from a
  draft, and the step is free when the commit is there).
- The end-to-end case is tested through `core_pin_diff` and `acceptance_problems` on the fixture plus a source check of `main()`, not by
  running `main()` on the fixture: `main()` also needs an active acceptance baseline on the fixture base, which other tests cover.

## Open questions
- J55 and J58 both edit the `acc = {...}` lines in `main()`: J55's merge after this one will conflict there. The resolution keeps J55's
  `rows_at(...)` and this job's `'core_diff'` entry (done once on the scratch worktree; it is mechanical).
- `show()` reads `core/...` paths through the repo the script lives in, while `core_pin_diff` uses the current checkout. They are the
  same in CI and locally; a later cleanup could make `show()` use the checkout too.
