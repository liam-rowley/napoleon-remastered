# J30 report draft (not yet `jobs/J30/report.md`)

The orchestrator wrote this from the finishing agent's hand-back on 2026-11-03. It becomes `jobs/J30/report.md` once rule 79 is met. Until then,
the job is not done: the streak on build `af34b0c1f7d1` is 0.

## Next step
- **Merge main.** `origin/main` now has J24, J70 and the J25 brief. J24 changes DLL inputs (`proxy/napoleon/generated/tables.h`, the shipped ini,
  `config_keys`, `engine_sites`), so a streak on `af34b0c1f7d1` would not be on the build that merges.
  - Keep the core at `v0.10.0` (main pins v0.9.0).
  - `git merge-tree` shows two conflicts: keep both sides of `harness/acceptance/ledger.jsonl`, and regenerate `generated/tables.h` with `gen_tables`.
- **Build and install fresh.**
- **Check the installed ini, with no lock held.** Every `ui.*` key must be at its release value; see "Worth remembering".
- **Run the passes:** `acceptance.py run --passes 21 --branch job/J30`. The 21st makes up for pass 1, which a fresh install labels with the kit id
  (core B26/B31).
- **Liam decides which keys this run uses:** release values (`ui.enabled=0`, as run so far), or the brief's deliverable 7 (host enabled and idle,
  no document shown).

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
- **PC end state:**
  - The uninstall is identical to the snapshot (1565 files).
  - Exe sha1 `9aebcd21...`; prefs sha256 `83b9b32b...`.
  - `job.sh status` shows no lock (the orchestrator re-checked).

## Deviations from the brief and why
- **The acceptance runs use release values, not the brief's idle host.** That was the orchestrator's instruction. The frame-cost cells cover the
  idle host.
- **The system d3d9 backend is not measured,** because of the headless failure (J61).
- **`release.json` leaves out `ui.*`.** That became necessary once J38 merged. The `ui.*` keys' defaults equal their release values.
- **The evidence comes in two stages.** The first PC run used a pre-review W2 commit, so the checks were re-run in full on the tagged core.

## Open questions
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
