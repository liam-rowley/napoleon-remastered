# J12 report: Promote phase 1 core candidates to warscape-core

Both parts are done. Part 1 (before the move): the fixes, the path wiring, the game-name lint, the PC proofs and the 20-pass run on
`job/J12`, and the core PR, liam-rowley/warscape-core#7, which Liam merged and tagged v0.4.0 (cf7c6e3). Part 2 (after the tag): the
switch to v0.4.0 and the proof that the move is pure (section "Part 2" below).

## What exists

### Fixes before the move (deliverable 1), each with a host test
| item | change | host test | PC proof |
|---|---|---|---|
| 1a (J13 should-fix 1) | `display_guard.h` `OwnMove` / `IsOwnMove`: the guard arms its target rect before each placement; `GuardProc` treats a move to exactly that rect within 2 s as its own on any thread, so the async move a non-owning thread queues is no longer dropped | `TestOwnMove`, and a simulation with Present on a worker thread: fixed ends uncloaked on the moved display; the J13 thread-id test stays cloaked | run `20261031_j12pc` 1a: with `headless.test_off_thread=1` the relocation ran on the guard thread (t20712, the window's thread is t33372), verified 62 ms after `-Origin 2560,0`, uncloaked after the 500 ms settle; again on `-Restore`. Window probe: 0 ms on a real monitor, 2 monitor changes |
| 1b (should-fix 2) | the guard thread sweeps every top-level window of the process every 62 polls (~250 ms), outside `s_cs` (`SweepDue`, `SweepHides`) | `TestSweep` (pure cases and a timeline: hidden after 232 ms) | 1b: the test hook showed a 640x480 window at 0,0 through the proxy's own import 15 s after start; the sweep hid it 101 ms later. Window probe: that window 109 ms on a real monitor, the game window 0 ms |
| 1c (J15 review 9, J3 review 5) | `shot.sh` takes the status file from the adapter (`job.sh adapter`); `job.sh ctl` writes to `dev.ctl_dir` from the game's mod ini, else the registered default | `test_ctl_dir_comes_from_the_mod_ini_not_the_watcher_root`, `..._uses_the_registered_default` | `job.sh ctl j12 ping` answered (launch `20261031T195333Z-p1776`); `shot.sh` wrote `harness/runs/20261031_j12pc/1c_shot.jpg` |
| 1d (J2 L3) | `job.sh lock` is an exclusive create (noclobber); a stale lock is moved aside first, a fresh one never | `test_lock_is_an_exclusive_create` (4 racers, 3 rounds: exactly one wins), `test_a_stale_lock_is_moved_aside...` | the sitting's lock taken and released through it |
| 1e (J2 L7, J2 q4) | `update.ps1` refuses a manifest whose `kit_id` is not its folder; nothing to replace is `NOTHING TO DO` (exit 4, no backup, no restart, never CONFIRMED) | two `Test-Integration.ps1` cases | a second `update kit=harness_20261031T194802Z_d5c606bb5661`: `NOTHING TO DO` (run_20261031T194909Z) |
| 1f (J13 q1) | a ps1 job whose last native or script call failed fails with `$LASTEXITCODE`; an explicit `exit N` still wins | `Test-Integration.ps1` queue case | `cmd /c exit 5` job: failed exit=5; with `exit 0` after it: ok |
| 1g (J44) | the watcher moves the adapter's `virtualstore_guard` copies to `_to_delete\` before every launch, from any caller, and says so (`virtualstore: moved ...`); `ctl.py` only records that line now. J47 can read the same line to see whether its fix removed the cause | `Test-Integration.ps1` launch case, `test_the_watchers_virtualstore_lines_are_recorded` | a planted `headless_status.json` copy was moved aside at launch `j12-20261031T195331Z` |
| J2 L1 | fixed: a `needs_reboot` flag the old watcher already had no longer blocks the update (a new one still fails it) | | |
| J2 L5 | fixed: the steam route fails when no game process appears within `steam_wait_s` | | |
| J2 L2 | **no**: mapping a script's exit code into a reserved range would change the codes scripts and callers rely on (`ctl.py` and `acceptance.py` test `rc == 0`, scripts return their own codes); the `[job ...: status exit=N]` line on stderr already tells refused (2, no exit line from the script) from a script's 2 | | |
| J2 L4 | **no, for now**: holding the game only for the start/kill inside a script needs the watcher to see the game start mid-script and re-arm the watchdog; scripts that start the game are refused by `job_script_guard=refuse` unless they name the lock owner, and the launch/kill job types are the supported route. Worth a row if a script ever needs to start the game | | |

Test hooks for the PC proofs, off by default and in release: `headless.test_off_thread`, `headless.test_dll_window_ms`
(registered, linted to default 0). Watcher 1.1.0 -> 1.2.0 (installed on the PC by update, CONFIRMED).

### Path wiring and the game-name lint (deliverable 2)
- `proxy/tools/layout.py` (new): the game root is `$WSP_GAME_ROOT`, else the superproject of the repo holding the tool, else that
  repo; the adapters are `wsc.toml` `[proxy] adapter` / `[harness] adapter` when set, else the one `proxy/*/adapter.cpp` /
  `harness/*/adapter.json`. Every moved tool uses it (python imports it, bash runs it); no moved file finds the game by its own path.
- `build.sh`: core sources, adapter and game root from `layout.py`; file names compiled into the DLL are fixed labels (`core/`,
  `adapter/`, `lua/`), so the bytes do not depend on the layout; the smoke's exe, mod folder and ini names come from `identity.json`.
- `build_id.py`: each role is looked up in the game repo, then through each submodule's gitlink
  (`git -C <sub> rev-parse <gitlink>:proxy/src`); `-dirty` covers a submodule checked out off its pin. Host test: a fixture moved into
  a submodule keeps the id, and a change there is seen.
- `gen_tables.py` emits `#include "adapter.h"` (found on the include path), not `../../core/adapter.h`.
- `pc_deploy.py`: adapters from `layout.py` (a kit copy still runs without a repo); the fixed-sky step became a generic `kit_packs`
  hook the game declares in its harness adapter; manifests and install records carry `packs`.
- Lint: `tests/test_core_candidates.py` (every moved file; provenance links to `empire-remastered` allowed). In the core,
  `tests/test_moved_tools.py` keeps it over `proxy/`, `harness/`, `saves/`.

### Rule 76 as code
`wsc jobs check` now fails an unlisted `*/core/` folder and one whose promotion job is done (`tools/verbs/jobs.py` `PROMOTIONS`, the
table lives in `jobs.py` because the pinned core 0.2.0 refuses unknown `wsc.toml` keys; tests in `tests/test_jobs.py`).

### The core pull request (deliverable 4)
Branch `napoleon-j12`: the move set as git objects from `job/J12` (so `proxy/src` has tree `2874c2ab1338` = Napoleon's
`proxy/core`), the null game (`proxy/tests/null_game`), CI jobs `proxy` (build, host tests, repro, wine smoke) and `harness-windows`,
`[proxy]`/`[harness]` keys in `warscape/repo.py`, 39 tools rows (path-slug ids per C8: `proxy.tools.*` keep their ids, `harness.*`
and `saves.*` are new), C13 (Pillow on the PC side only), C14, backlog B15-B19, `VERSION` 0.4.0, a CONSUMING section.
Locally: `wsc gates` 11 ok, 76 host tests; in the CI container the null DLL builds, 9 C++ host-test binaries pass, repro identical,
wine smoke passes (5 launches, 2 dumps).

## Part 2: the switch to core v0.4.0 (deliverables 5 and 6)
- `main` merged in first (J50, D37, J53 plan: no DLL input or harness file changed; the build id stayed `31094f6055c2`).
- **One commit** (core backlog B9) bumps `core` to v0.4.0, sets `wsc.toml` `[core] version = "v0.4.0"`, deletes the local copies
  (`proxy/core`, `proxy/tests`, the moved `proxy/tools`, `proxy/tools/wer`, `harness/core`, `harness/tests`, `saves/core`) and points
  everything at `core/`:
  - CI: `core/proxy/tools/build.sh` and `core/harness/tests/Run-HostTests.ps1`; the proxy and harness-windows jobs check out the core;
    `tools/changed_inputs.py` treats a `core` gitlink change as a proxy and harness input.
  - `tools/pr_policy.py`: reads `core/...` through the gitlink (the watcher version, the base's acceptance checker in either layout,
    the build id tool), and a pin change is in rule 79's scope.
  - The tests, `setup`, the hook, `ci_notify`, `saves/napoleon`, the discovery and viewer docs, `CLAUDE.md`, `proxy/README.md`,
    `harness/README.md` and `docs/CI_FAILURES.md`.
  - The J41 item: no proxy toolchain is now a plain skip (`tests/test_proxy_host.py`), shown as a warn by the core's tests gate.
- **Proof that the move is pure:**
  - `build.sh id`: `31094f6055c2` before and after. `build_id.py --inputs` after: `core core/proxy/src 2874c2ab1338...`,
    `build_sh core/proxy/tools/build.sh 82198d12...`, `fetch_lua core/proxy/tools/fetch_lua.py 5ed63198...`,
    `build_id core/proxy/tools/build_id.py 06865096...`, `adapter proxy/napoleon aa363225...`: the same object ids as before.
  - `core/proxy/tools/build.sh --docker all`: sha256 `3f5bc62e5575d9ef3546ea72eb2eac34a22edadfb26cb9240831443c8ae893fc`, byte-identical
    (`cmp`) to the DLL the 20 passes ran on; all host tests passed; `build.sh --docker repro`: identical from another path.
  - `pc_deploy.py kit` from the switched tree (`kit_20261031T215915Z_23cf2ff5aeec`) against the run's kit
    (`kit_20261031T194958Z_d5c606bb5661`): all 35 file sha256s equal. Harness kit (`harness_20261031T215916Z_23cf2ff5aeec` against
    `harness_20261031T194802Z_d5c606bb5661`): all 22 files and 5 kit files equal, watcher 1.2.0.
  - `acceptance.py streak --build 31094f6055c2 --watcher 1.2.0`: 20. `pr_policy.py --branch job/J12 --base origin/main`: no rule 79
    error (only the review and the `done` row, which the reviewer supplies).
  - `wsc gates`: 10 ok, 2 warn (the local hooksPath setting; 14 skips with reasons), 0 failed, 411 host tests. warscape-core CI on
    the merged PR: gates (Linux and Windows), proxy, harness-windows all green.

## Evidence
- `harness/runs/20261031_j12pc/`: 1a and 1b proxy log excerpts and window probes, the 1c shot.
- Build id of the run's DLL: `31094f6055c2` (kit `kit_20261031T194958Z_d5c606bb5661`, watcher 1.2.0).
- 20-pass run: `harness/runs/20261031_j12acc3`, 20 of 20 passed (20:07-21:33 UTC); `acceptance.py streak --build 31094f6055c2 --watcher 1.2.0` = 20. The ledger also holds the two failed first passes of `20261031_j12acc` and `20261031_j12acc2` (Deviations).

## Deviations from the brief, and why
- **`build_fixed_sky_pack.py` stays whole in Napoleon** (the brief moves its method). Its method reads the game's packs and db
  through `discovery/core` (`packfs`, `db`), which waits for the phase 2 promotion; a core module whose only readers live in a game
  folder would invert the dependency. `pc_deploy.py` now calls it through the adapter's `kit_packs` hook, so it moves with
  `discovery/core` without touching the core's kit code. `exe_info.py` stays too (its defaults are Napoleon's, as decided).
- **`[harness]`/`[proxy]` cannot be in Napoleon's `wsc.toml` before the bump**: core 0.2.0 refuses unknown keys. `layout.py` finds the
  single adapter folder instead, so nothing needs the keys today; they are accepted from 0.4.0 for a game with more than one adapter.
- **Python host tests of the moved tools stay in Napoleon** (pc_deploy, ctl, acceptance, ESF, job.sh): they run against the real
  adapter and registries. The core carries `tests/test_moved_tools.py` (layout, the build id across the move, the lock, the lint) and
  the C++ and PowerShell suites; porting the rest to the null game is B17.
- **Two core proxy tests check this game's console and camera numbers** when the adapter has them; the null adapter skips them. Moving
  those checks into a game-side test is B15.
- **The core's CI passes `WSP_BUILD_ID`** for the null DLL: `build_id.py` hashes a game repo, and the null game is a folder inside the
  core (B16). `build.sh` and `build_id.py` were not changed for it, so the run's DLL inputs stayed fixed.
- **1b: the DLL's window was on a real monitor for 109 ms**, not zero: a sweep every ~250 ms cannot hide a foreign window before its
  first frame. The game's own windows stay at 0 ms. A show-time WinEvent hook would cut it (B19).
- **Two acceptance starts failed pass 1 on `settings_identical`** with every game step passing, for causes outside the fixes, each
  understood and turned into code before the restart (kill criterion 3): run `20261031_j12acc` began under the sitting's own lock and
  headless overlay (same owner), so its before-settings held the overlay (now `run_problems` refuses a run under a lock or an active
  profile); run `20261031_j12acc2` began on a freshly installed ini, and `ctl.py` writes the launch keys into the mod ini outside any
  snapshot, so pass 1 compared against an ini without them (now the run applies the keys once before pass 1). Their ledger lines stay.

- **The 39 moved tools' rows are removed from Napoleon's registry, not superseded.** The tools gate only takes a superseded target that
  is a row in the same registry, and the core's rows live in the core's registry (`proxy.tools.*` keep their ids there; `harness.*`
  and `saves.*` are path slugs, C8). The gate's own message allows removal; git keeps the history.
- **The adapter's files still name old paths in comments** (`proxy/napoleon/adapter.cpp`, `generated/tables.h`, `lua/`): they are DLL
  inputs, so editing them would change the build id the 20 passes ran on. They get fixed with the next real adapter change.

## Open branches on old paths
- `job/J16` (queued, changes `proxy/core`): not carried. Once J12 merges, its `proxy/core` change becomes a warscape-core PR against
  `proxy/src` plus a pin bump in Napoleon; its brief and evidence stay in Napoleon.
- J47 (VirtualStore) and J48 (watcher) have no branch; their briefs should cite `core/harness/watcher.ps1` and the `virtualstore:`
  line (1g).

## Promotion rows still needed (needs_brief, not added here)
- `discovery/core` with `build_fixed_sky_pack.py`'s method: phase 2, after J11.
- `upscale/core`: after J50 and J51.
- `viewer/core` (J31's review viewer): with the RmlUi host work.

## Open questions
1. v0.3.0 (the J41 tests-gate release) has `VERSION` 0.2.0, so `core_pin` refuses a game that pins v0.3.0 ("pins v0.3.0 but the core
   checkout is 0.2.0"): that is why Napoleon still pins v0.2.0. v0.4.0 carries `VERSION` 0.4.0 and supersedes it; v0.3.0 is best left
   unused. Liam may want a note on the v0.3.0 release.
2. The acceptance launch keys stay in the mod ini after a run (the watcher restores the headless overlay, not the keys `ctl.py` sets
   before the snapshot). That was already so; is the end state Liam wants an ini with the dev keys on?
3. `headless_status.json` is written once, at `on_virtual`: after a relocation it still names the old rect (seen in 1a). A rewrite after
   each verified relocation would keep `shot.sh` right after a display move.
4. Cross-repo retirement: should the core's tools gate accept `superseded:core:<id>` (checked against the pinned core's registry), so a
   game can retire a row in favour of a core tool instead of deleting it? A small core change for the next tag.
