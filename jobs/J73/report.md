# J73 report: Napoleon's gates: rule 79 on every branch kind, narrower meta, derived proxy inputs

Written by the orchestrator from the builder subagent's hand-back (the harness refuses a subagent's write of a report file); the text is
the builder's own apart from this note. Branch `job/J73`, commits f9f15d7 (tests, red on the unchanged tree) and 6c6d004 (the change).
Files touched: `tools/jobs_hooks.py`, `wsc.toml`, `docs/REVIEW.md`, `registries/tools/tools.jobs_hooks.json`, `tests/test_jobs_hooks.py`,
`tests/test_discovery_gate.py`, `tests/test_proxy_host.py`, `tests/test_usage_reader.py`. Nothing under `core/`, `proxy/`, `harness/` or
`viewer/`.

## What was built
- **Rule 79 on every branch kind.**
  - `policy_problems` in `tools/jobs_hooks.py` no longer returns `[]` for kinds other than `job`.
  - A shortcut returns `[]` first when there is no recorded `facts['acceptance']` and no counted path: no `proxy/` or `harness/` path
    outside the exempt ones, and no `core` pin in `changed`. So `plan/` and `brief/` pull requests skip `dll_build_id` and the git
    reads.
  - Otherwise it calls `acceptance_problems(changed, acc or collect_acceptance(...))`; a recorded `acceptance` fact is used as given.
  - Rule 79 can only get stricter: every input that failed before still fails, and `brief`, `plan`, `meta` and the empty kind now fail
    as well. The module docstring says "on every branch kind".
- **Narrower meta.** `wsc.toml` `[policy] meta` drops exactly `"core"` and `"registries/*"`.
  - Tracked files matching meta, counted on this tree including the five files this job adds: 569 before, 230 after.
  - The brief's 564 to 225 is the same drop counted without those five files. `plan` was never affected.
- **Derived proxy inputs (P4).**
  - `[ci.inputs] proxy` gains `|^viewer/pins\.json$`. The comment above `[ci.inputs]` says the proxy set also holds the pin file J30 added
    to the build id.
  - New test `test_the_proxy_set_covers_every_input_of_the_dll_build_id` (`tests/test_proxy_host.py`):
    - it loads the checked-out core's `build_id.py` and walks `object_ids(ROOT, 'HEAD')`;
    - a `core/...` path counts as covered when `ci.classify(['core'])['proxy']` is true;
    - any other path, plus `path/probe` for a folder, counts as covered when its own classify is true;
    - it fails naming the role and the path;
    - it holds the INPUTS list nowhere, so it stays correct after the pin moves to v0.22.0.
  - `test_the_ui_pins_file_runs_the_proxy_and_viewer_jobs` pins `viewer/pins.json` to both the `proxy` and `viewer` sets.
- **Hook-module cleanup.**
  - `usage_state(..., rows=None)` and `pc_state(..., rows=None)` take the job rows, which `view_panel` supplies from
    `warscape.registry.load_all(ctx)['jobs'].rows`. The `registries/jobs/*.json` glob is gone.
  - `show` keeps its signature and its `core/` submodule fallback, but the plain read is now `warscape.policy.show(ref, path, cwd=...)`.
    `_core_policy` imports the core lazily, putting `<root>/core` on `sys.path` if `warscape` is not importable.
  - `PROMOTIONS`: `discovery/core` is `J64`; `upscale/core` and `viewer/core` are `J63`. `uiscale/core` and `release/core` stay `None`
    with their comments, because no row promotes them: J79 mentions `uiscale/core` only as a source file, and J67 is the stop-gap's
    second part.
- **Docs.** `docs/REVIEW.md`, rule 79 bullet:
  - rule 79 runs for every branch kind;
  - a core pin bump is a `job/` branch, never `meta/` or `plan/`, and meets rule 79 whenever the core's own `proxy/` or `harness/`
    changed between the two pins;
  - a registry edit outside `registries/jobs/*` is a `job/` branch too.

### Red, then green
Tests were committed first, in f9f15d7. On the unchanged code they gave 10 failures:
- **Rule 79 on every kind** (subTests `brief`, `plan`, `meta`, `''`): `AssertionError: False is not true : []`. The recorded-acceptance
  rule-79 error is absent for those kinds.
- **The docs-only shortcut:** `AssertionError: collect_acceptance ran for a change rule 79 does not count`.
- **`test_the_pin_and_the_registries_are_not_meta_or_plan`:** `'core' unexpectedly found in [..., '.gitmodules', 'core', 'registries/*']`.
- **The meta globs, fnmatch against segment-wise matching:** `Items in the first set but not the second:
  'registries/engine_facts/napoleon.ui.hud_placeholder_attach.json', 'registries/tools/proxy.napoleon.lua.probes.maps_matrix.json', ...`.
- **Derived proxy inputs:** `Lists differ: ['ui_pins viewer/pins.json'] != []`, and `ci.classify(['viewer/pins.json'])` gave
  `{'proxy': False, 'harness': False, 'viewer': True}`.
- **`test_promotions_name_rows_that_exist`:** `None != 'J64' : discovery/core`.

Green after 6c6d004: `python3 -m unittest tests.test_jobs_hooks tests.test_usage_reader tests.test_discovery_gate tests.test_proxy_host
tests.test_build_id tests.test_repo_rules` ran 144 tests, OK, 1 skipped. The baseline before the change was 112 tests in the four modules,
OK, 1 skipped.

Where a new test could not be red first:
- **`test_collect_acceptance_reads_the_pin_diff_from_the_merge_base`** pins existing behaviour, so it passes on the unchanged code. It was
  shown to bite by mutating `core_pin_diff(mb, 'HEAD', root)` to use `'HEAD'` as the base: it went red. The mutation was then restored.
- **The legacy-hash constants** were computed from the current `jobs/legacy.json`, after checking that they equal the git-derived sets:
  22 `round_rules` ids from `39eab5e`, and 54 `brief_hooks` ids from `c674fb1` plus J24 and J37. A hash test cannot go red while the
  file is unchanged.

### Scratch `meta/x` demonstration
In a throwaway worktree of this branch: a commit touching `proxy/napoleon/adapter.cpp`, then
`python3 core/wsc.py policy --branch meta/x --base origin/main`:
```
policy: rule 79: this branch changes proxy/napoleon/adapter.cpp but harness/acceptance/ledger.jsonl holds 0 consecutive acceptance passes on build de4486f0a36a, watcher 1.2.0 (need 20): run `python3 core/harness/acceptance.py run` on the final build
policy: a meta/ branch may only touch repo infrastructure; it also changes: proxy/napoleon/adapter.cpp, registries/tools/tools.jobs_hooks.json (game code goes through a job)
policy: meta/x: REFUSED (9 files changed)
```
The scratch worktree and its branch were deleted, and nothing was pushed.

### Gates and policy
- `python3 core/wsc.py ci render --check`: ok.
- `python3 core/wsc.py jobs check`: 88 rows, ok, 0 registry gaps in briefs.
- `python3 core/wsc.py gates`: 13 ok, 1 warn, 0 failed in 149.2 s. The warn is `tests`: 594 host tests passed and 30 skipped. The skips
  are Playwright and `viewer.wasm`, numpy, Pillow and freetype, and capstone, none of them missing for files this job changed.
- `python3 core/wsc.py policy --branch job/J73 --base origin/main` refused for only three reasons: the report, the review and the `done`
  status. There was no rule 79 line, because the diff holds no `proxy/` or `harness/` file.

### Hand check: no rule loosened (`git diff origin/main -- tools/jobs_hooks.py`)
- **The kind check.** `if facts.get('kind') != 'job': return []` is replaced by the shortcut. The shortcut returns `[]` only when
  `acceptance_problems` would for that input: no acceptance fact, no counted path, and no `core` in `changed`.
- **The acceptance call.** `acc = facts.get('acceptance') or collect_acceptance(...)` is unchanged in effect, and
  `return acceptance_problems(facts['changed'], acc)` is unchanged.
- **The row glob.** The `registries/jobs/*.json` glob in `usage_state` became the `rows` parameter, supplied by `view_panel` from the core's
  registry loader.
- **`show`.** The plain `git show` in `show` is now `warscape.policy.show`, which does the same `git show ref:path` and returns None on
  failure.
- **`PROMOTIONS`.** The `None` entries became job ids; rule 76 is unchanged.
- **Untouched:** `acc_exempt`, `acceptance_active`, the `acceptance_problems` counting loop and the ledger format.
- **`wsc.toml`** lost only the two meta globs and gained one proxy alternative. `.gitmodules`, `tools/*`, `tests/*` and `wsc.toml` stay in
  meta.

### Replaced assertions
- **`test_check_wires_it_into_job_branches`:** its `brief` -> `[]` assertion is replaced by two tests. Its `job` assertion stays.
  - `test_failing_fixture_rule_79_runs_on_every_branch_kind` covers the kinds `brief`, `plan`, `meta`, `''` and `job`, each against a
    proxy path, a docs-only change, a pin with a proxy core diff and a pin with a docs-only core diff.
  - `test_docs_only_branches_skip_the_git_reads_and_the_shortcut_equals_the_full_path` covers the shortcut.
- **`test_main_passes_the_merge_bases_pin_diff`** (a source-line grep) is replaced by `test_collect_acceptance_reads_the_pin_diff_from_the_merge_base`,
  a behaviour test with `dll_build_id` patched.
- **The legacy-set tests keep their git comparison**, still skipping when the base commit is absent: the two `LegacyData` tests (the
  `round_rules` and `brief_hooks` sets) and `tests/test_discovery_gate.py::test_the_legacy_set_is_every_brief_on_main_at_j11s_base`. Each
  gains a sha256 constant test that always runs: `test_the_frozen_sets_still_hash_to_their_constants` and
  `test_the_legacy_set_still_hashes_to_its_constant`.
- **`tests/test_usage_reader.py`:** the call sites gained `rows=[{'id': 'J7'}]`. `PcState` needed no change, because `rows=None` means no
  rows.
- **Left alone:** `tests/test_build_id.py:206-211` (`test_neither_computes_its_own_id`), a deliberate source guard that the hook does not
  compute its own build id.
- No other assertion was removed or relaxed.

## Deviations from the brief and why
1. **The meta-glob equality test compares per kind (the union of that kind's globs), not per glob.**
   - Per glob it fails on `docs/*`, `tools/*`, `tests/*` and `schemas/*`. Under fnmatch these cross `/`, but each has its `**` form
     beside it in the same list.
   - The brief's own "225 under both" count is a union.
   - The per-kind test is red today (`registries/*`, `core`) and green after the drop.
   - Cost: it would not catch a single over-wide glob whose reach another glob already covers.
2. **Test placement.** The brief left it open. The meta-glob and promotion tests are in `tests/test_jobs_hooks.py` (classes `MetaGlobs`
   and `Promotions`). The derived-inputs test is in `tests/test_proxy_host.py`, where `ci` is imported.
3. **`registries/tools/tools.jobs_hooks.json` was regenerated.** The brief does not name it, but the docstring change made the `tools`
   row stale, and `reg check` failed until `reg add`.
4. **`view_panel` puts `<root>/core` on `sys.path`** when `warscape` is not yet imported, before importing the registry loader. The hook
   then works even when the core has not put its package on the path.

## Open questions
1. Should `tools/jobs_hooks.py`, `tools/claude_hook.py`, `wsc.toml` and `.gitmodules` leave the meta globs? They stay, as the brief
   recommends. A `meta/` branch can still rewrite a rule and pass its own check until warscape-core W23 (judged with the base) reaches
   napoleon; W23 and J76 are the intended guards.
2. Should a `plan/` pull request be allowed to carry a pin bump for the J78 train? After this job it cannot, because `core` is in neither
   list. The build went ahead on "no": J64 and J78 are `job/` branches already.
3. Items left to other rows:
   - J75: the evidence checks (unique evidence, an append-only ledger, exempting only `ledger.jsonl`, the shas) and `acc_exempt`.
   - W23: `policy.allowed` (segment matching) and loading the hooks from the base rather than the head.
   - J76: the `gh pr merge` deny.
   - J80: the baseline rule.
   - J64 and J78: the pin bumps, which from now on are `job/` branches that meet rule 79.
4. Until W23 reaches this repo, CI's `policy` check judges this branch with this branch's own hooks. The reviewer should check the diff
   by hand against the mapping of each removed line under "Hand check" above.
