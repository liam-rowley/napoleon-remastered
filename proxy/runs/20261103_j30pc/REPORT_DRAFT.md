# J30 report draft (not yet `jobs/J30/report.md`)

The orchestrator wrote this from the finishing agent's hand-back on 2026-11-03, and the second finishing session (Claude-Session a3c823fa)
updated it the same evening. It becomes `jobs/J30/report.md` once rule 79 is met. Until then, the job is not done. The final build is
`cb34c06baf42`, and its streak is 0 (see "Rule 79").

## Next step
- **Done (session a3c823fa):**
  - Merged origin/main (6ee33bd: J24, J70, the J25 brief, plan 290ac86). Conflicts: the ledger and `release.json` keep both sides (J24's
    `keep_ids` and J30's `ui.` omit prefix); `generated/tables.h` was regenerated.
  - Rebuilt: `build.sh --docker all` green, `repro` identical. The core stays at `v0.10.0` (see "Deviations").
  - Three idle-host acceptance runs (`ui.enabled=1`, no document), each stopped by a scene load time just over its limit (see "Rule 79").
- **To do:**
  - Re-run `acceptance.py run --passes 20 --branch job/J30` on build `cb34c06baf42` when the PC is quiet. This build's pass 1 already
    carries the right build id; the kit-label case is only for a fresh install.
  - Before that run:
    - Install the kit (`pc_deploy.py kit`, then `install`).
    - With no lock held, run `pc_deploy.py set ui.enabled=1`.
    - Check that `[ui] show=` is empty.
    - Stop the stray J46 busy loop (Open questions).

## What was built
- **Core (warscape-core W2, v0.10.0):** see `core/jobs/W2/report.md` and `core/docs/PROXY_UI.md`.
  - `ui_core.h`: the D19 scale model, input routing and the device lifecycle.
  - `ui_host.cpp`: the CreateDevice, Reset and Present hooks, the window subclass, DirectInput blanking, the frame pass in a `D3DSBT_ALL` state block,
    and `ui dump`.
  - `ui_render_d3d9.*`, Empire's render interface. Shaders compile at run time through d3dcompiler_47 or _43.
  - A second Lua 5.1.1 (float) with RmlUi's Lua plugin.
  - `ctl ui ...`, `fetch_ui.py`, `kit_ui`, the `VtableHook` chain rule, and the host tests.
- **Here:**
  - The pin bump to v0.10.0 (1fcff35), after merging origin/main at 06b1002 (c129275).
  - The `ui.enabled`, `ui.scale`, `ui.dir`, `ui.show` and `ui.dump_dir` keys.
  - `kit_ui`; the test document `viewer/napoleon/hosttest/` and its checks `tools/ui_hosttest.py`; the `stb_image_write` pin.
  - `tests/test_viewer.py`, which holds the core's compat header and fetcher equal to the viewer's copies.
  - The facts `napoleon.ui.{main_device, input_path, depth_stencil, lua_state, present_thread, loading_and_video, saved_state, helper_device_rehook}`
    and `rmlui63.sub_pixel_rule`.
  - The player ini leaves out `ui.*` (`release/napoleon/release.json`, e1083ef). The fixtures carry the new build-id roles (e1083ef).
- **Lua:** the host has its own state (`napoleon.ui.lua_state`).
- **Input:** the mouse arrives through the window procedure; DirectInput carries the keyboard only (`napoleon.ui.input_path`).
- **Licences for J38:** RmlUi 6.3 (MIT), FreeType 2.13.3 (FTL, which needs an acknowledgement), Lua 5.1.1 (MIT), stb `f0569113` (MIT or public domain).

## Evidence
- **Build `af34b0c1f7d1`:**
  - 4,224,512 B, sha256 `9b4bad0c78117dacf1a5b49aa1713c7d5b2663d91389bf633b88c1a527630d54`.
  - Imports system DLLs only.
  - `build.sh --docker all`: host tests green (`test_ui_core` 212, `test_ui_rml` 25). `repro`: identical.
  - Kit `kit_20261103T145025Z_1fcff35f261b`.
- **PC run `proxy/runs/20261103_j30pc/`** (2026-11-03; DXVK; headless at 1080p, 1440p and 4K):
  - **Checks:** everything ok at 100% in the front end, the campaign, the battle and after a warm reset. Two fails, the same as on 2026-11-02:
    - 1080p at 85%: `rules_solid` (`rmlui63.sub_pixel_rule`);
    - 4K at 125%: `text_height` fails for 1 of 4 sizes.
  - **Routing:** 9 of 9 checks pass in all 12 cells. RmlUi logs 0 warnings and 0 errors.
  - **Host cost:** update + render p50 is 0.062 to 0.094 ms with the document, at most 0.096 ms for the whole hook (D38 budget 1 ms). The idle host
    is 0.000 ms (budget 0.1 ms).
  - **Frame time:** document minus off -0.01 to +0.28 ms; idle minus off -0.06 to +0.20 ms (spread about 0.3 ms).
  - **Memory, document over off:** address space +5 to +16 MB, commit +0 to +6 MB.
  - **System d3d9:** the headless launch fails before the front end with the host off. That is J61.
- **Rule 79:**
  - `harness/runs/20261103_j30acc`: pass 1 failed on a setup error, because the test document was shown.
  - `harness/runs/20261103_j30acc2`: 16 passes, then pass 17 failed at `campaign_start`. The launch and its retry both exited at DllMain, with
    minidumps c0000374 and c0000005 (`napoleon.proxy.init_heap_corruption`).
  - The streak is 0.
- **Final build `cb34c06baf42`** (after the main merge, core still `v0.10.0`):
  - 4,225,536 B, sha256 `b9c2bc2b7c381f501ecb5ee97b7885e66c6070c015c82e3080c72e2ed6903ac0`.
  - `build.sh --docker all`: 198 s, host tests green (`test_ui_core` 212, `test_ui_rml` 25). `repro`: identical.
  - Kit `kit_20261103T195609Z_6ee33bd89704`.
  - The host code is the same as on `af34b0c1f7d1`. The difference is main's J24 inputs (tables, ini), so the b) to e) evidence above still
    describes the host.
- **Rule 79 on `cb34c06baf42`** (idle host per deliverable 7: `ui.enabled=1`, `ui.show` empty; the log shows `ui: enabled` and the window subclassed):
  - `harness/runs/20261103_j30acc3`:
    - 2 passes (pass 1 carries the fresh-install kit label `6ee33bd89704`).
    - Pass 3 failed at `hist_lodi:load` (16.0 s; baseline 5.9 s, limit 14.75 s).
  - `harness/runs/20261103_j30acc4`:
    - 3 passes; then pass 4 failed at `naval_storm:load` (9.3 s, limit 9.0 s).
    - Pass 3 had `hist_lodi` at 13.9 s.
  - `harness/runs/20261103_j30acc5`:
    - 1 pass, with every load raised (`hist_lodi` 9.3 s, `land_40` 8.9 s).
    - Pass 2 failed at `siege_small:load` (14.3 s, limit 14.0 s).
  - **Each failure is one scene's load, in a different scene each time.** Every shot, camera, perf and settings check passed.
  - **The host is not the likely cause:**
    - The host draws nothing on a load screen, and its idle hook costs 0.000 ms p50 (run 20261103_j30pc).
    - Host-free builds on this PC hit the same outliers. J24's `75739186b92e` reached `hist_lodi` 14.5 s (j24acc2 pass 3). J30's own
      host-off run j30acc2 drifted to 8.0, 9.2, 10.2 and 11.9 s in passes 14 to 17.
  - **The PC was loaded throughout the runs:**
    - About 2 GB of RAM available out of 31.8 GB; commit 49.9 of 55.9 GB.
    - 31 `claude` processes (9.5 GB private); the WSL and Docker VMs (about 9 GB private).
    - A stray Git Bash busy loop (below).
  - Streak: 0. Stopped after three runs in a row on the same cause (the orchestrator's stop rule).
- **PC end state:**
  - The uninstall is identical to the snapshot (1565 files).
  - Exe sha1 `9aebcd21...`; prefs sha256 `83b9b32b...`.
  - `job.sh status` shows no lock (the orchestrator re-checked).

## Deviations from the brief and why
- **The acceptance runs j30acc and j30acc2 used release values, not the brief's idle host.** That was the orchestrator's instruction. The
  runs on the final build (j30acc3 to j30acc5) use the brief's idle host (deliverable 7).
- **The core stays at `v0.10.0`.** The orchestrator asked for the latest tag that works without another job's Napoleon half:
  - **v0.15.0 (W4 discovery) is out.** It makes the game verb `tools/verbs/discovery.py` a load error, and deleting that verb is J64's half.
  - **v0.14.0 (W5) is out.** It ships watcher 1.3.0. Rule 79 compares against the pinned `watcher.ps1`, so a watcher redeploy on the shared
    PC would be needed (J48's half).
  - **v0.13.0 and v0.13.1 (W6 gestures) are out.** They were tried: `wsc gates` fails `build.sh --docker smoke` step 6
    (`'gesture: on: drag 6 px' not in the log`). That smoke step needs the game to have a `GestureAdapter` and a `controls.gestures` key,
    which is J29's half. Apart from that, the one change v0.13.x needs is a trailing `nullptr` in the `GameAdapter` initialiser (`-Wextra -Werror`).
- **The system d3d9 backend is not measured,** because of the headless failure (J61).
- **`release.json` leaves out `ui.*`.** That became necessary once J38 merged. The `ui.*` keys' defaults equal their release values.
- **The evidence comes in two stages.** The first PC run used a pre-review W2 commit, so the checks were re-run in full on the tagged core.

## Open questions
- **PC load during acceptance:**
  - Scene load times on this PC have heavy tails when it is busy. Three 20-pass runs on the idle host were stopped by single-scene load
    outliers 2 % to 9 % over their limits.
  - A stray Git Bash loop is spinning on the PC: pid 28292, started 2026-11-02 23:31 by the J46 session (claude pid 38400).
    - The loop is `until pgrep -f "acceptance.py measure" && sleep 15 || false; do :; done`. With no measure running, pgrep fails, so the
      sleep never runs and the loop forks pgrep forever (about 49,000 CPU-seconds so far).
    - Stopping it was refused (auto mode, "interfere with workloads"); Liam or the J46 session should stop it.
  - **Warscape-core backlog items:**
    - The acceptance load limits could allow for PC contention, or the runner could re-measure one outlier load once.
    - `build.sh smoke` step 6 should accept a game without a `GestureAdapter` (it is inert by contract), so a game can move past v0.13.0
      before its gesture half lands.
- **Start-up flake:** `napoleon.proxy.init_heap_corruption` hit 12 launches in 17 passes, against 3 retries in J46's 20. It needs a fix, or a wider
  acceptance retry.
- **Scale edges:** 1 dp hairlines at dp below 1, and 14 dp text at dp 2.5. The crispness verdict is Liam's, from `crops/`.
- **The `viewer/core` promotion row (rule 76):** proposed, not made.
- **`napoleon.ui.depth_stencil` is still open.** The GPU time of the UI draw is not measured on its own.
- **Review point:** `release.json` is J38's file.

## Worth remembering
- **A lock release undoes ini edits made during the sitting.** The watcher's headless snapshot is taken at the sitting's first launch, and releasing
  the lock restores it. Set release values after the release, then check the ini.
- **A guard for the core:** `acceptance.py run_problems` should refuse a run when any installed-ini key outside the launch keys differs from its
  `release_value`.
- **The battle loader's 1x1 helper device shares the main device's vtable,** so a re-hook must be idempotent.
- **RmlUi 6.3 rounds box edges:** a 1 dp box vanishes at dp below 1, while a 1 dp border keeps one pixel.
