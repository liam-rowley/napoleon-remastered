# J30 report: RmlUi host in the proxy

The RmlUi host is in the proxy DLL (warscape-core W2, tag `v0.10.0`), with this repo's adapter, keys, test document and evidence. The final
build is `cb34c06baf42`. Rule 79 is met: run `20261103_j30acc6` holds 20 consecutive passes on `cb34c06baf42` with watcher 1.2.0, the host
enabled and no document shown (deliverable 7).

## What was built
- **Core (warscape-core W2, v0.10.0):** see `core/jobs/W2/report.md` and `core/docs/PROXY_UI.md`.
  - `ui_core.h`: the D19 scale model, input routing and the device lifecycle.
  - `ui_host.cpp`: the CreateDevice, Reset and Present hooks, the window subclass, DirectInput blanking, the frame pass in a `D3DSBT_ALL` state block,
    and `ui dump`.
  - `ui_render_d3d9.*`: Empire's render interface. Shaders compile at run time through d3dcompiler_47 or _43; a missing compiler logs "UI off".
  - A second Lua 5.1.1 (float) with RmlUi's Lua plugin.
  - `ctl ui ...`, `fetch_ui.py`, `kit_ui`, the `VtableHook` chain rule, and the host tests.
- **Here:**
  - The pin bump to v0.10.0 (1fcff35), after merging origin/main at 06b1002 (c129275). Later merges of main (6ee33bd, and 81a9d2a bringing
    J71, J72, D47 and D48) changed no DLL input apart from J24's tables and ini.
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
- **Build `af34b0c1f7d1`** (the PC checks):
  - 4,224,512 B, sha256 `9b4bad0c78117dacf1a5b49aa1713c7d5b2663d91389bf633b88c1a527630d54` (before the host: 973,312 B).
  - Imports system DLLs only.
  - `build.sh --docker all`: 212 s, host tests green (`test_ui_core` 212, `test_ui_rml` 25). `repro`: identical.
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
- **Final build `cb34c06baf42`** (after the main merge, core still `v0.10.0`):
  - 4,225,536 B, sha256 `b9c2bc2b7c381f501ecb5ee97b7885e66c6070c015c82e3080c72e2ed6903ac0`.
  - `build.sh --docker all`: 198 s, host tests green (`test_ui_core` 212, `test_ui_rml` 25). `repro`: identical.
  - Kit `kit_20261103T195609Z_6ee33bd89704`.
  - The host code is the same as on `af34b0c1f7d1`. The difference is main's J24 inputs (tables, ini), so the evidence above still describes
    the host. The last merge of main (81a9d2a) changed no DLL input: `build_id.py` still gives `cb34c06baf42`.
- **Rule 79** (idle host per deliverable 7: `ui.enabled=1`, `ui.show` empty):
  - Earlier runs, none counted:
    - `20261103_j30acc` (`af34b0c1f7d1`): pass 1 failed on a setup error; the test document was shown.
    - `20261103_j30acc2` (`af34b0c1f7d1`, release keys): 16 passes, then pass 17 failed at `campaign_start`. The launch and its retry both
      exited at DllMain (minidumps c0000374 and c0000005, `napoleon.proxy.init_heap_corruption`).
    - `20261103_j30acc3`, `acc4` and `acc5` (`cb34c06baf42`): 2, 3 and 1 passes. Each then failed on one scene's load just over its limit
      (`hist_lodi` 16.0 of 14.75 s, `naval_storm` 9.3 of 9.0 s, `siege_small` 14.3 of 14.0 s). The PC was overloaded: about 2 GB of 31.8 GB
      free, commit 50 of 56 GB, 31 `claude` processes, and a stray Git Bash `pgrep` busy loop.
  - **`harness/runs/20261103_j30acc6`, after a reboot: 21 of 21 passes** (2026-11-03 22:35 to 2026-11-04 00:42 UTC, about 6 minutes per pass).
    - Pass 1 carries the fresh-install kit label `6ee33bd89704`, because there was no proxy log yet. **Passes 2 to 21 are 20 consecutive passes
      on `cb34c06baf42`, watcher 1.2.0**, branch `job/J30`, with the evidence `pass_NN.json` committed (a327ab2).
    - Every scene load stayed at or under 52 % of its limit. The worst was `campaign_start` at 3.5 of 6.75 s in pass 1; `hist_lodi` ran 5.1 to
      6.1 s against 14.75 s. Every shot, camera, perf and settings check passed.
    - Two launches were retried by the runner and then passed:
      - pass 5 `hist_nile`: exit at DllMain, minidump c0000374 (`napoleon.proxy.init_heap_corruption`);
      - pass 18 `naval_small`: no `on_virtual` within 180 s (last status `starting DllMain`), the game using about two cores until the watcher
        killed it. The retry moved a stale VirtualStore `headless_status.json` aside.
      That is 2 retries in 21 passes, against 10 in 16 on `j30acc2` and 3 in J46's 20.
    - PC load (10 s samples, `proxy/runs/20261103_j30pc/acc6_pc_load.tsv`): free RAM 18.8 to 22.6 GB, commit at most 17.7 of 46.2 GB, CPU median
      23 % (mostly the game), 13 to 17 `claude` processes, no busy loop. So the three earlier load failures were most likely the PC's memory
      pressure, not the host.
- **Gates and policy** (2026-11-04): `python3 core/wsc.py gates`: 13 ok, 1 warn (tests: 585 passed, 30 skipped for optional dependencies),
  0 failed. `python3 core/wsc.py policy --branch job/J30 --base origin/main`: only the report, the review and the done status, no rule 79 complaint.
- **PC end state:**
  - The uninstall is identical to the snapshot (1565 files); `pc_deploy.py status` is clean.
  - Exe sha1 `9aebcd21...` (vanilla); prefs sha256 `83b9b32b...` (unchanged).
  - `job.sh status` shows no lock, no active profile, and the game not running.

## Deviations from the brief and why
- **The acceptance runs `j30acc` and `j30acc2` used release values, not the brief's idle host.** That was the orchestrator's instruction. The
  runs on the final build (`j30acc3` to `j30acc6`) use the brief's idle host (deliverable 7).
- **The passing run has 21 passes, not 20.** On a fresh install, pass 1 records the kit label as its build id, so it does not count. 21 passes
  give 20 on the build id.
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
- **Report and row:** the builders ran as subagents, which cannot write report files, so the orchestrator wrote this report from the last
  builder's text, removed the stale `proxy/runs/20261103_j30pc/REPORT_DRAFT.md`, and set the row to review (same Claude-Session as the builds).

## Open questions
- **Load-time limits and PC load:** scene loads on this PC have heavy tails when it is short of memory. Three runs on this build broke on one
  load each at about 2 GB free; the same build passed 21 of 21 at about 20 GB free.
  - A guard for the core: the acceptance runner could refuse to start (or pause) below a free-RAM floor, or re-measure one load outlier once.
  - The stray J46 `pgrep` busy loop was gone after the reboot. Its pattern (`until pgrep ... && sleep 15 || false; do :; done`, which never
    sleeps while pgrep fails) is one to avoid in agent waits.
- **Start-up flake:** `napoleon.proxy.init_heap_corruption` (c0000374 at DllMain) hit again once in `j30acc6`. It still needs a fix.
- **A new start-up stall:** pass 18's launch sat at `starting DllMain` for 180 s while using CPU, and the retry cleared a stale VirtualStore
  `headless_status.json`. Whether the stale file caused the stall is not proven; it is near the fact `napoleon.harness.uac_virtualstore`.
- **Warscape-core backlog:** `build.sh smoke` step 6 should accept a game without a `GestureAdapter` (it is inert by contract), so a game can
  move past v0.13.0 before its gesture half lands.
- **Scale edges:** 1 dp hairlines at dp below 1, and 14 dp text at dp 2.5. The crispness verdict is Liam's, from `crops/`.
- **The `viewer/core` promotion row (rule 76):** proposed, not made.
- **`napoleon.ui.depth_stencil` is still open.** The GPU time of the UI draw is not measured on its own.
- **Review point:** `release.json` is J38's file.
