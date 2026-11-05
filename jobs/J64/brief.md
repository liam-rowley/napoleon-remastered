# J64: Pin bump to core v0.22.0 and the discovery switch

Phase 1 pipeline job, one `needs_pc` job. Audit 2026-11-03 finding P5 (the bump is a PC job, not a commit), with C2 and C6 (the adapter), H10 (the watcher
kit with W5's display-restore fix) and G14 (the second copy of the discovery code). Napoleon is pinned at core v0.10.0 (J30 moved it there on 2026-11-04,
W2). This job moves the pin to v0.22.0 in one commit with everything the new core refuses or needs, deletes the two things the core now owns (the game
verb `discovery` and the folder `discovery/core`), and proves the new DLL and the new watcher kit with 20 acceptance passes on the PC (rule 79).
The old brief for this row (written for a v0.8 or v0.9 bump) is in history at 461b908; its step 4 (the switch) is reused below.

Model: Sonnet medium (D15). The host work is configuration, one C++ initialiser rewrite and a module move; the PC part is running the harness and writing
down what it says. No reverse engineering, shader, DLL design or crash work, and no independent check, so nothing here earns Opus. Budget about 170 tool
calls for the host part and about 40 for the PC part; at the cap, stop, commit, push, report what is left. No subagents. Waiting belongs to the harness:
nothing here polls CI, a merge or a pass run.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J64`; "Never change files inside `core/`" except moving the gitlink; "Reuse before you write"). Read `docs/DECISIONS.md`
  (D44 the pipeline in the core, D49 and D50 are new and do not touch this job), `docs/REVIEW.md` (rule 79 and what a reviewer checks), `core/docs/CONSUMING.md`
  at v0.22.0 (read it after the checkout in step 1: "Upgrading and releasing", "Game gates", "The proxy, the harness and the save tools", "Discovery
  (optional extras)"), and `docs/audits/AUDIT_2026-11-03.md` findings P5, C2, C6, H10, G14 and its section "Where each finding went".
- **Check the target tag first.** `git ls-remote --tags https://github.com/liam-rowley/warscape-core` (or `git -C core fetch --tags origin`). This brief was written
  with v0.22.0 the newest tag (core W21). If W20 (UI host and gesture driver hardening) or another core row has tagged something newer by the time you start,
  bump to the newest tag only if its diff since v0.22.0 leaves the facts below true (re-read `git -C core log --oneline v0.22.0..<tag>` and the CONSUMING.md
  diff, and say so in the report); otherwise stay on v0.22.0. A tag that appears after step 1 is not chased.
- Other work that touches the same ground (check `git branch -r` at the start and before the final push):
  - `job/J29`, `job/J37`, `job/J60` and `job/J67` sit on job branches waiting for a PC slot (another session's work; do not touch them). J29 and J60 now depend on
    J64, and `job/J29` carries its own v0.9.0 to v0.13.0 bump that this job makes redundant. **J64 takes the next PC slot.** Those branches rebase onto `main`
    after J64 merges; that is not part of this job. J27 and J48 also depend on J64 and plan their own bump, which this job likewise makes unnecessary.
  - J73 (rule 79 on every kind, proxy CI inputs) and J77 and J78 are queued plan rows that edit `tools/jobs_hooks.py` and `wsc.toml`. If one has merged when you
    start, rebase onto it before step 3; the file you move in step 3 is whatever `main` holds then.
- Look things up with `python3 core/wsc.py find <words>`. Rows you will touch: `tools.jobs_hooks`, `wsc.discovery`, `proxy.tools.exe_info`, and 32 `discovery.core.*`.
- `needs_pc` is true: the DLL build id and the watcher version both change, so rule 79 needs 20 consecutive acceptance passes on the final build and watcher.

## What exists (verified 2026-11-04 on main 61174f5; re-check each with the command shown)
- `git -C core describe --tags` is v0.10.0; `wsc.toml` `[core] version = "v0.10.0"`. The newest core tag is v0.22.0 (`git ls-remote --tags`).
- **Every verb refuses to load on the new core.** The core's `CORE_VERBS` gained `discovery` (v0.15.0), and `tools/verbs/discovery.py` is a game verb of the same
  name: `wsc` exits with "verb 'discovery' already exists". Proved on a scratch copy of this repo against the v0.22.0 archive, 2026-11-04.
- **The core refuses `[jobs] hooks`** (removed in v0.20.0, no shim): "`[jobs] hooks` was replaced by `[gates] dirs` in 0.20.0 (C22)". `wsc.toml` line 40 sets it for
  `tools/jobs_hooks.py`. The brief of this row said only "update PROMOTIONS"; the real work is moving the hook module to a gate module (step 3).
- `GameAdapter` gained a seventh member `gesture` (core `proxy/src/adapter.h`, v0.13.0, W6). `proxy/napoleon/adapter.cpp` builds `GameAdapter` with a positional
  aggregate initialiser at the end of the file (`Adapter()`), and `kConsole`, `kCamera`, `kOrders` and `kDev` are positional too (C6). The proxy build uses
  `-std=c++17 -Wall -Wextra -Werror` (`core/proxy/tools/build.sh`), so the missing member fails as `-Werror=missing-field-initializers`.
- `ci/gates.yml.in` line 75: the `proxy` job has `timeout-minutes: 15`; the core needed 30 once RmlUi compiled (J30, core `ci/gates.yml.in` has 30). The workflows are
  rendered from `ci/*.in` (`python3 core/wsc.py ci render`; the core's `ci_render` gate fails on a difference).
- The core's discovery module is flat (`core/discovery/*.py`, host tests in `core/discovery/tests/`) and driven by the core verb `wsc discovery` through
  `wsc.toml` `[discovery] adapter = "discovery/napoleon"`. Napoleon holds `discovery/core/` (32 modules, 30 of 31 shared files differ from the core's) and
  `tools/verbs/discovery.py`. Tested 2026-11-04 on the scratch copy with the v0.22.0 core, `[discovery] adapter` set, the verb deleted: `wsc discovery check` passes on
  every committed result file **only after `discovery/napoleon/games.json` gains `"target": "napoleon"` and `"reference": "empire"`** (without them the core writes and
  expects row fields named `reference` and `target`, and every row of `discovery/diff/*.json` is reported as having the wrong keys). With them, `discovery render` leaves
  every generated README byte-identical **except `discovery/diff/README.md`**, which loses its `effects` section (see below).
- **`discovery/core/effects.py` has no home in the core.** J72 (merged 2026-11-03) added the effects pass after the core's W4 took its copy. The core v0.22.0 has no
  `effects.py` and its `discovery render` does not know the `effects` area, so the committed `discovery/diff/effects.json` and the effects rows of the diff README
  have no tool in the core. No core row promotes it (checked: the core's queue and BACKLOG). Decided below.
- `discovery/requirements.txt` (Pillow pin) is the core's now (`core/discovery/requirements.txt`). `proxy/tools/exe_info.py` is the core's (`core/proxy/tools/exe_info.py`).
- The watcher on the PC is 1.2.0; the kit in `core/harness/` at v0.22.0 is 1.3.0 (core W5, v0.14.0: a pending virtual-display restore whose saved position can no longer
  apply restores the mode at the display's current origin; a missing virtual display drops the record, D38). `tools/jobs_hooks.py` reads the watcher version from
  `$Version` in the kit's `watcher.ps1` and compares it with each ledger line (rule 79).

## The consumer-facing changes between v0.10.0 and v0.22.0 (core diff read 2026-11-04) and what this job does with each
| Core change | What it means here | Handled in |
|---|---|---|
| 0.13.0 W6 gesture layer: `GameAdapter::gesture`, config key `controls.gestures`, ctl `gesture` verb | adapter must build; Napoleon passes `nullptr` (J29 fills it later) | step 4 |
| 0.13.1 W3: `jobs next` survives unset `[jobs] ledgers` | nothing | none |
| 0.14.0 W5: watcher 1.3.0 display-restore fix | kit reinstall on the PC, new watcher version on every ledger line | step 8 |
| 0.15.0 W4: discovery in the core, verb `discovery`, `[discovery] adapter`, `exe_info.py` | verb collision, folder switch, `games.json` names, extras paths | steps 2 and 5 |
| 0.16.0 W7: engine-site `value_key`, `value_scale`, `value_floor_stock`; config keys gain `type`, `min`, `max` | existing rows unchanged; generated tables byte-identical | step 6 (`gen_tables --check`) |
| 0.17.0 W14: `x-extends` schemas, modifier-agnostic hotkeys | no schema change needed; the registries gate must stay green | step 6 |
| 0.17.1 W11: `core_pin` testable, worktree-safe, shallow-safe | the pinned tag is compared by commit when present; CI's depth-1 submodule falls back to `VERSION` | step 6 |
| 0.18.0 W17: ctl requests written before the game process started are refused as `stale` (job.sh exit 2: resend); read-only `peek` | acceptance and any ctl user sees exit 2 as a resend, not a failure | step 8 |
| 0.19.0 W8: harness host tests in the core; `warscape/gitbash.py` (the Git Bash finder) | Napoleon's `tools/verbs/setup.py` has its own copy; J70 owns that file; filed, not changed | Out of scope |
| 0.20.0 W13: game gates (`[gates] dirs`); `[jobs] hooks` removed | `tools/jobs_hooks.py` becomes `tools/gates/pipeline.py` in this commit | step 3 |
| 0.21.0 W19: capture hooks 37 device slots and 2 state-block slots, new `frame.txt` lines | proxy source only; no Napoleon capture doc claims the old slot count (grep to confirm) | step 6 |
| 0.22.0 W21: `{{wsc fetch_cache}}`, fetch retry (`netfetch.py`), `[ci] required_checks`, `wsc ci check-settings` | workflow gains the cache step; settings checked once | step 7 |
| `adapter.h`, `build.sh`, `gen_tables.py`, `layout.py`, `fetch_dxvk.py`, `ui_host.cpp`, `patch_driver.cpp`: DLL inputs | the DLL build id changes whatever else is true | step 8 |

## Decisions already made for this job
Settled by the audit, the core's CONSUMING.md and the scratch test of 2026-11-04; Liam can overrule in the review.
- **One commit for the pin (B9).** The `core` gitlink, `wsc.toml` (`[core] version`, `[discovery] adapter`, `[gates] dirs`, `[jobs] hooks` removed, `[ci] required_checks`),
  the deletions of `tools/verbs/discovery.py` and `discovery/core/`, and the `games.json` names land in one commit, because the pinned core refuses the old keys and the
  old verb and a split leaves no commit on which `wsc` runs. Everything else (adapter, workflows, tests, docs) may be separate commits on the branch.
- **`tools/jobs_hooks.py` moves to `tools/gates/pipeline.py`** exactly as `core/docs/CONSUMING.md` "Moving off `[jobs] hooks`" lists it (rehearsed there on a copy of this repo by
  core W13): `git mv`, `NAME = 'pipeline'`, `STAGES = ('jobs', 'policy', 'view')`, a `run(ctx)` that dispatches on `ctx.stage`, `view_panel` becomes the `view` result, the
  folder is `tools/gates` (every `*.py` in it is loaded, so nothing else goes there), paths relative to the file move one folder down, the tools row keeps its id
  `tools.jobs_hooks`. Behaviour must not change: `wsc jobs check`, `wsc policy` and the status page's PC line read as before, and `tests/test_jobs_hooks.py` keeps every assertion
  (it gains only the new module path and function names). `PROMOTIONS['discovery/core']` is set to `'J64'` in the same file (rule 76: the folder is then gone, as it must be).
- **`games.json` gains the two names**, `"target": "napoleon"` and `"reference": "empire"`, and nothing else changes in it. Rewrite it with the Edit tool (keep its layout; do not
  dump it through `json.dump`, which reflowed every list in the scratch test).
- **Effects stays Napoleon's for now (open question 1, recommended).** `effects.py` moves out of the doomed folder to `discovery/napoleon/effects.py` (a game tool that imports the
  core's modules from `core/discovery`, with its header, its tools row keeping the id `discovery.core.effects`, and `tests/test_discovery_effects.py` repointed). Its output
  `discovery/diff/effects.json`, the facts `napoleon.diff.effects*` and its host tests stay untouched. The one accepted difference in the proof of step 5 is that the generated
  `discovery/diff/README.md` no longer lists the 12 effects rows or the effects line of its count table (the core's `discovery render` does not know that area); everything
  else must be byte-identical. A core row to promote the pass and the area is proposed in the report (not made here: a core change is a warscape-core pull request).
- **Tests.** Napoleon's unit tests of the moved modules (`tests/test_discovery.py`, `test_discovery_assets.py`, `test_discovery_gate.py`, `test_discovery_lua.py`, `test_discovery_ui.py`,
  `test_engine_api.py`, `test_exe_strings.py`, `test_x86re.py`) are the core's now (`core/discovery/tests/`, run in the core's CI). Delete them and add one thin file,
  `tests/test_discovery_repo.py`, that runs on this repo's real data: `wsc discovery check` and `wsc discovery gate` pass, the committed diff files pass the schema, the engine API,
  probe-safe, exe-strings and shader-catalog tables are current (their `--check` modes), the generated READMEs are current, and the brief found-path rule passes on every brief.
  Read each old test before deleting it: a test that reads the real index or real registries (the 88,415-row index test in `test_discovery_gate.py`, the committed-files tests in
  `test_discovery.py`) is moved into the thin file, not dropped. Compare the counts: old tests minus deleted plus thin file, nothing silently lost. `test_discovery_effects.py`, `test_mod_packs.py`,
  `test_play_pack.py`, `test_uiscale.py`, `test_uiscale_fonts.py`, `test_upscale.py`, `test_jobs_hooks.py` stay and are repointed.
- **Napoleon's duplicate tests of the other moved tools** (`tests/test_pc_deploy.py`, `test_job_sh.py`, `test_claude_hook.py`, the Git Bash finder in `tools/verbs/setup.py`) are left alone:
  they test Napoleon's own wiring, `wsc.toml` `[ci] inputs` names them, and J70 owns `setup.py`. The report lists the overlap with the core's `tests/test_pc_deploy.py`, `test_job_sh.py` and `warscape/gitbash.py` for a later trim.
- **Designated initialisers for every adapter struct (C6).** `GameAdapter`, `ConsoleAdapter`, `CameraAdapter`, `OrdersAdapter` and `DevAdapter` use `.member = value` in declaration order, with
  `.gesture = nullptr` on the `GameAdapter`. g++ with `-std=c++17` accepts in-order designators and rejects out-of-order ones, which is the check C6 wants. The values are copied across
  unchanged. If a struct has a member the positional form silently left out, say so in the report. The `static_assert` on size and field count is W34's (core); do not add one here.
- **Workflows.** Add `{{wsc fetch_cache}}` to the `proxy` job in `ci/gates.yml.in` after its checkout and before `core/proxy/tools/build.sh all` (CONSUMING.md 0.22.0), raise that job's
  `timeout-minutes` to 30, then `python3 core/wsc.py ci render` and commit the template and the rendered workflow together. Triggers (`push` and `pull_request`) stay as they are: the core's
  push-only change is its own, and `policy` needs the pull request.
- **Required checks.** `wsc.toml` `[ci] required_checks = ["gates", "policy", "proxy", "harness-windows"]` (what `main` requires, D32), then `python3 core/wsc.py ci check-settings`
  once (`gh api` GETs only). Changing a repository setting is Liam's: if it names a missing check, report it and do not touch settings.
- **PC order and rebase.** J64 takes the next PC slot. The job branches J29, J37, J60 and J67 rebase onto `main` afterwards (not this job's work; J29's own bump is dropped when it does).
- **The newest tag is the target** unless the check in Start says otherwise; the report names the tag and the commit it points at.

## Deliverables
1. **Baseline and checkout.** `git pull`; `python3 core/wsc.py gates` green; record the test counts (`python3 -m unittest discover tests` summary) and write
   `_scratch/j64/before.sha256` (git-ignored, outputs listed in step 5) so the proof is a diff. `git -C core fetch --tags origin`, `git -C core checkout v0.22.0`, and read the
   CONSUMING.md sections named in Start. Confirm the facts above with the commands given (the verb collision: `python3 core/wsc.py reg check` after the checkout fails to load).
2. **The pin commit** (one commit, B9): gitlink at the tag, `wsc.toml` as in Decisions, `git rm tools/verbs/discovery.py`, `git rm -r discovery/core` (after step 3 moved `effects.py` out
   and step 5's module list is checked), `discovery/requirements.txt` removed (Pillow pin is `core/discovery/requirements.txt`; fix the places that name it, `discovery/README.md`), the
   32 `discovery.core.*` rows removed except `discovery.core.effects` (repointed to `discovery/napoleon/effects.py`), `wsc.discovery` and `proxy.tools.exe_info` removed (the file
   `proxy/tools/exe_info.py` is deleted; the tools gate takes a superseded target only inside the same registry, so remove, do not supersede), `games.json` names, and `tools/jobs_hooks.py`
   moved (step 3). Use `python3 core/wsc.py reg` verbs for rows; never edit a row file by hand. Run `python3 core/wsc.py gates --fast` on the commit: it must at least load.
3. **The hook module becomes a gate module** (inside the pin commit, per Decisions): `tools/gates/pipeline.py`; `tests/test_jobs_hooks.py`, `tests/test_build_id.py`, `tests/test_registry_merge.py`,
   `tests/test_repo_rules.py` (`MOVED_ALLOWED` key and the loader), `tests/test_usage_reader.py` (`sys.path`, `import pipeline as hk`) and `tests/test_proxy_host.py` follow the new path;
   `tools/usage_reader.py`'s header, `docs/REVIEW.md`, `harness/README.md`, `docs/plans/PLAN.md`, `CLAUDE.md` and the `wsc.toml` comments are fixed (`git grep -n "jobs_hooks\|hook module\|policy_problems"`
   outside dated job folders). Merged history (briefs, reports, reviews, run folders, `registries/jobs/*.json` descriptions) is left alone.
4. **The adapter** (`proxy/napoleon/adapter.cpp`): designated initialisers and `.gesture = nullptr` as in Decisions. Build it first with the core's own route:
   `core/proxy/tools/build.sh --docker all` (or the host route when the PC has one; D31), which runs the host tests; it must pass with no warning-as-error. This is a rule 79 input.
5. **The discovery switch and its proof of a pure move.** Repoint the importers of the folder: `tools/verbs/hotkeys.py`, `proxy/tools/build_fixed_sky_pack.py`, `uiscale/core/cuf_encode.py`,
   `uiscale/core/scale.py`, `uiscale/napoleon/cli.py`, `upscale/napoleon/cli.py`, `tools/shadow_density.py` (its `CATALOG` constant), `tests/test_mod_packs.py`, `tests/test_play_pack.py`, `tests/test_uiscale.py`,
   `tests/test_uiscale_fonts.py`, `tests/test_upscale.py` and `tests/test_discovery_effects.py` to `core/discovery` (`from paths import REPO` style as the core's modules do). `git grep -n "discovery/core"`
   over the living files (`CLAUDE.md`, `README.md`, `docs/`, `discovery/README.md`, `uiscale/`, `upscale/`, `viewer/`, `proxy/README.md`, tool headers and the generated-file sources) is then empty; where a generator writes
   the old path into a committed file (`discovery/napoleon/*.json` notes, `proxy/napoleon/console_sources.json` and the generated `proxy/napoleon/generated/console_table.h`, `proxy/napoleon/lua/probes/api_surface.lua`,
   `discovery/ui/*.json`), change the generator's source or note and regenerate through the tool, never by hand in the output. Anything under `proxy/` changes the DLL inputs, which step 8 covers anyway. `discovery/README.md`
   gets a "Where things moved" table (old path, new path) and the extras sentence. Then, with the baseline from step 1:
   - `sha256sum -c _scratch/j64/before.sha256`: every file listed equal after the switch, except `discovery/diff/README.md` (effects rows, the one accepted difference) and the files whose only change is the old path in a comment or note (list each with its diff);
   - `python3 core/wsc.py discovery render` then `git status`: no change beyond those;
   - `python3 core/wsc.py discovery check` and `discovery gate`: ok with the same lines and findings as before; the ratchet figures in `discovery/napoleon/gate.json` unchanged;
   - the `--check` modes that read only committed files, through the core's tools: `engine_api.py build --check`, `engine_api.py probe-safe --check`, `shader_catalog.py build --check`, `exe_strings.py build --check` where it needs no extras;
   - the passes that read the game (`discovery assets|db|loc|sheets|ui`, `effects.py --check`): when the install and the extract store are on this machine, re-run them read-only (no launch, nothing written in a game folder, never git there)
     and show `git status` clean for `discovery/` and the registries; when they are not, say so and rely on the host tests. Pillow and the RE environment are PC-side extras (`core/docs/CONSUMING.md`, "Discovery (optional extras)").
6. **Gates, CI inputs and generated tables.** `python3 core/proxy/tools/gen_tables.py --check` (the tables must be byte-identical to the committed ones; if a core change makes them differ, stop: kill criterion),
   `python3 core/wsc.py gates` green, `python3 -m unittest discover tests` compared with the step 1 counts, `git grep -n -i "slot" docs proxy/README.md` for any capture claim the 0.21.0 slot counts make false (fix or note), and
   the `core_pin` gate green in a fresh clone (`git clone --recurse-submodules` into `_scratch/j64/clone`, `python3 core/wsc.py gates --only core_pin`).
7. **Workflows and settings.** As in Decisions: `ci/gates.yml.in` (fetch cache, 30 minutes), `python3 core/wsc.py ci render`, `[ci] required_checks`, `python3 core/wsc.py ci check-settings` output pasted in the report.
   Push the branch early once the host gates are green so CI's `proxy` job (RmlUi, cold cache) runs while you work on step 8; its time goes in the report.
8. **The PC sitting (rule 79; start only when the host gates and CI's `gates` and `proxy` are green).**
   - Confirm the slot: no other job holds the game lock (`python3 core/harness/job.sh status` through the watcher, read-only) and Liam has not said the PC is busy. If it is held, stop and report who holds it.
   - Build the final DLL and the watcher kit from this branch: `core/proxy/tools/build.sh --docker all`, `python3 core/proxy/tools/pc_deploy.py kit --what harness`, then `send --kit build/kits/<id> --state 'C:\napoleon_remastered_pc'` (harness/README "Install"),
     then the job `update kit=<id>` (back up, replace sha-checked, restart, new pid, version 1.3.0, healthy heartbeat, stable window; a failure rolls back by itself). Record the watcher version the status then reports. Install the DLL with
     `pc_deploy.py` (sha-checked) as the harness README says; never copy into the game folder by hand.
   - `python3 core/harness/acceptance.py run --passes 20 --run <date>_j64pc` against the committed baseline (rule 74), in the background (the harness waits, you do not poll). Ledger lines and `harness/runs/<run>/pass_NN.json` are committed; the ledger lines must name
     the DLL build id of the final inputs and watcher 1.3.0. Ctl requests refused as `stale` (exit 2, v0.18.0) are resent by the tool; a stale refusal that persists is a finding.
   - One documented flake class is allowed one relaunch inside a pass (core BACKLOG B60, the `hist_nile` headless relaunch); any other failure stops the run: keep its evidence, do not edit the baseline or a tolerance to pass.
   - After the 20 passes: `python3 core/wsc.py policy --branch job/J64 --base origin/main` and confirm it reports rule 79 satisfied. If `main` moved and brought a DLL-input change since the passes, the branch needs a new run (CLAUDE.md, rule 79 and history edits); merge or rebase only when the inputs are unchanged.
9. **Living copies.** The `CLAUDE.md` bullet "Since J12 the core carries ..." gets the discovery and gates sentence; PLAN section 4's promotion note says discovery was J64 (core v0.15.0) and the hook module became `tools/gates/pipeline.py`; `docs/CI_FAILURES.md` is checked for the `proxy` timeout; one line `D51`
   in `docs/DECISIONS.md` (append only): the pin moved to v0.22.0, the effects pass stays Napoleon's until a core row promotes it, the new watcher version 1.3.0 is the acceptance baseline; Reversible yes.

## Proof and what done looks like
- One pull request from `job/J64` whose pin commit has the gitlink at the tag, `[core] version` equal to it and the old verb and folder gone; `python3 core/wsc.py reg check` loads every verb.
- `gates` green locally and in CI; `proxy` green in CI under the 30-minute limit; `gen_tables --check` clean; the host tests of the proxy pass in `build.sh all`.
- The proof of a pure move (step 5) pasted in the report: `sha256sum -c` result, the one accepted difference with its diff, `discovery check` and `gate` lines, the test counts before and after.
- 20 consecutive passes in `harness/acceptance/ledger.jsonl` on the final build id and watcher 1.3.0, each with committed evidence, and `wsc policy` satisfied on the final head.
- `python3 core/wsc.py jobs check` ok, and the other three queued PC jobs unaffected (their rows are not edited here).

## Out of scope
- Anything inside `core/` other than the gitlink; a warscape-core change of any kind (the effects promotion is a proposed row, not made here); `empire-remastered`.
- Rebasing, editing or running `job/J29`, `job/J37`, `job/J60`, `job/J67`, or any other job's branch; the briefs of J27, J29, J48 and J60 (they keep their own bump text until they are rebased).
- Enabling the gesture layer or any new proxy feature (`gesture` is `nullptr`), the 0.18.0 `peek` verb, a `static_assert` on the adapter structs (W34), changing Napoleon's Git Bash finder (J70), trimming Napoleon's duplicate host tests, the audit's other pins (W22 and later: J78).
- Re-measuring the acceptance baseline or changing a tolerance; any change to `.claude/settings.json` or repository settings; touching the PC state folder other than through `pc_deploy.py`, `job.sh` and `acceptance.py`.

## Kill criteria
- `wsc` still fails to load after step 2 on a reason this brief does not list: stop, change nothing more, report the full error and the first commit it appears on.
- A committed discovery output (other than `discovery/diff/README.md`'s effects rows) differs after the switch and two attempts to find the cause: stop, report the diff and the first diverging step; never regenerate and commit a "new" output to pass the proof.
- `gen_tables --check` differs, the proxy host tests fail, or the adapter needs a change beyond initialisers and `.gesture = nullptr` (the core changed a table, a signature or a field Napoleon fills): stop and report; no workaround in `core/`.
- The `proxy` CI job exceeds 30 minutes on a cold cache or fails on a fetch (not on the code): rerun once; a second failure is a finding, stop and report the run id.
- An acceptance pass fails (other than the one allowed B60 relaunch), the kit update rolls back, the watcher does not report 1.3.0, or a load time or shot is outside the baseline's tolerance: stop at the first failure, keep its evidence, report; do not edit the baseline or retry the streak with different settings.
- The PC game lock is held by someone else, or the game or watcher would have to be started outside `job.sh` and the watcher: stop; the slot is not yours.
- `main` brings a DLL-input change after the 20 passes that a rebase cannot carry without a new run: report and leave the branch; do not claim the passes.
- The budget is reached: stop, commit, push, report what is left.
- Any tool call is refused by a deny rule or the hook: stop and report the call; do not retry another way.

## Open questions (for Liam; each has a recommendation this brief follows)
Answered 2026-11-04: Liam, "Follow recommendation" (question 1 put to him; 2 and 3 follow their recommendations too).

1. **Effects pass.** The core has no `effects.py` (J72 landed after the core's copy). Recommended (followed): bump now and keep the pass in `discovery/napoleon/effects.py`, accepting that the generated `discovery/diff/README.md`
   loses its effects section until a warscape-core row promotes the pass and the area; the committed data (`effects.json`, the facts) is untouched. Alternative: hold J64 until a new core tag carries the effects area; that delays the PC slot for J29, J48 and J60 and the audit's "bump now"
   plan for no data loss. Say which; the builder's default is the recommendation.
2. **Required checks.** The brief sets `[ci] required_checks` to the four checks `main` requires today. If Liam wants the list to stay empty (every workflow job but `changes` and `notify`), say so; the result is the same four.
3. **Newest tag.** If W20 tags before this job starts, the builder takes it when the diff since v0.22.0 leaves this brief true (Start). Recommended; the alternative is v0.22.0 regardless, with J78 carrying the rest.

## Finish
Write `jobs/J64/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`): the tag and its commit, the pin commit's contents, the verb collision and `[jobs] hooks` evidence (the `wsc` error lines before), the hook-to-gate move and its unchanged `jobs check` / `policy` / page lines,
the designated-initialiser diff, the proof of a pure move (every result, the accepted effects-README difference with its diff), the test counts before and after, CI run ids and the `proxy` job time, the `ci check-settings` output, the kit update (version before and after, build id), the 20-pass run id, ledger range and the `policy` output,
the overlap list of Napoleon tests the core now has, the proposed core row for the effects pass, and what rebase J29, J37, J60 and J67 and the briefs of J27 and J48 now need. Then `wsc reg set jobs J64 status=review report=jobs/J64/report.md`.

## Re-scope (Liam, 2026-11-04)
The target is the **newest warscape-core tag** at the start of the build (v0.30.0, commit 4d69d11, on 2026-11-04), not v0.22.0. Why: on v0.22.0 CI's
`proxy` job fails in the core's `build.sh` smoke ("gesture: on: drag 6 px" not in the log, runs 41801657509 and 41804261931; the first session stopped
at df7339a). The fix, core W37, is first in v0.28.0, and every tag from v0.24.0 on also brings W12 (`run_refs`), W23 (base-judged policy:
`pull_request_target`, the policy stage reads the head by sha), W24 (the build id names one DLL; the pinned toolchain) and W10 (the lock is the
session's; watcher 1.4.0). A local trial of v0.28.0 failed `ci_render` and `run_refs` (12 references). Liam chose the newest tag over a v0.22.1
patch tag: J64 absorbs what that tag forces; the rest of J78 stays J78's. Every step above stands, read with the new tag: the CONSUMING.md notes
from v0.10.0 to the target, 20 passes on the final build and the kit's watcher version, and a D line after D57 naming the new pin.
