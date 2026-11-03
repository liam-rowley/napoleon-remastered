# J24 report: Shadow map resolution and fit

The orchestrator wrote this from the build agent's two hand-backs. The build ran as a subagent, and the harness refuses a subagent's Write of a
report file, so the parent writes it. The Claude-Session is the same as the build's.

## What was built
- **Sites and keys** (`registries/engine_sites.jsonl`, `registries/config_keys.jsonl`, owner J24; verified 2026-11-03, run `harness/runs/20261103_j24pc`).
  Eleven `shadow.*` rows, each behind one boolean `gfx.shadow_*` key (default off). The J9 proof keys `gfx.shadow_proof` and
  `gfx.shadow_sweep_proof` are replaced.
  - **Kept with new keys:** `shadow.map_size_q34` (2048 -> 8192, `gfx.shadow_map_large`), `shadow.far_cap_q3` (500 -> 1000 m,
    `gfx.shadow_far_cap`), `shadow.light_sweep` (extrusion -75 -> -150, `gfx.shadow_extrusion`).
  - **New fit rows:** `shadow.fit_height_cutoff` (100 -> 200, `gfx.shadow_height_cutoff`), `shadow.fit_crop_keep` (flag +0x66 1 -> 0),
    `shadow.fit_warp_ortho` (mode 1 -> 0), `shadow.fit_focus` (0.7 -> 0.3), `shadow.fit_near_scale` (1.0 -> 0.5).
  - **Hardware path:** `shadow.hw_force_setup` and `shadow.hw_force_define`, one diagnostic key `gfx.shadow_hw_force`.
  - **Proposed release values:** `gfx.shadow_map_large`, `gfx.shadow_height_cutoff` and `gfx.shadow_extrusion` on; everything else off.
  - With every key off, the start-up log shows all 64 rows "stock (key off)".
  - Docs updated: `proxy/README.md` "Shadow sites" and the shadow rows of `discovery/napoleon/engine_sites_routes.md`.
- **The player ini lists the three release keys:** `release/napoleon/release.json` `player_ini.keep_ids`, honoured by `omitted()` in
  `release/core/build_release.py`, with `tests/test_release.py` updated. The `gfx.` omit prefix had kept them out although their release
  value differs from the DLL default, which the release-value gate refuses. Neither file is a DLL input: the build id stayed 75739186b92e.
- **Route for configured values: no core change, one build per value.** Rows that share an RVA are refused by both
  `core/proxy/tools/gen_tables.py` (overlap check, whatever the keys) and the patch engine (`SiteState::Overlap`). So the ladder used one
  build per map size (4096 and 8192 kits), and each shipped row writes one fixed value. The numeric-key core change is in Open questions.
- **Fit code located (static):**
  - per-frame update 0x119ab50: farz from the camera height, far clip, min far and height cutoff at 0x119ad76;
  - frustum to light-space AABB 0x11552a0;
  - shadow pass 0x114b440: mode switch at 0x114b473 to ortho 0x1150390 or trapezoid 0x1152530;
  - crop 0x1176b10: its full-rect reset when +0x66 is set is at 0x1176ca9.
  - All 34 debug-property fields are mapped (getter 0x117ad20, names at 0x1468a50). Facts: `napoleon.shadow.fit_code`, `.fit_fields`.
- **Facts** (date 2026-11-03, evidence `harness/runs/20261103_j24pc/README.md`): `napoleon.shadow.fit_code`, `.fit_fields`, `.fit_controls`,
  `.size_route`, `.hardware_path`, `.kernel` (new or updated).
- **Run helpers** in the run folder (run evidence like J9's `proof.sh`, not registered tools): `fit.sh` and its sweep scripts, `ladder.sh`,
  `shots.sh`, `final.sh`, `final2.sh`, `final3.sh`, `summ.py`, `dens.py`, `sheet.py`, `ladder_table.py`, `accsum.py`.

## Evidence
### Fit
Texels per metre at 20 m from `shader_catalog.py` shadow_density, on the J8 yaw sweep at 2048, runs in `harness/runs/20261103_j24pc`. The full
table is `density.tsv`.

| setting | y0 | y45 | y90 | y135 | y180 | y225 | y270 | y315 | worst | best/worst |
|---|---|---|---|---|---|---|---|---|---|---|
| stock (f2_stock) | 5.24 | 3.65 | 20.88 | 11.98 | 12.44 | 8.69 | 15.48 | 10.08 | 3.65 | 5.72 |
| height cutoff 200 | 13.16 | 5.85 | 26.5 | 18.21 | 19.45 | 15.3 | 22.61 | 13.96 | 5.85 | 4.53 |
| extrusion -150 | 4.5 | 8.48 | 20.88 | 11.49 | 12.44 | 8.79 | 14.36 | 8.24 | 4.5 | 4.64 |
| cutoff + extrusion | 7.86 | 11.99 | 26.5 | 18.12 | 19.45 | 15.3 | 22.33 | 11.93 | 7.86 | 3.37 |
| focus 0.3 | 5.3 | 3.56 | 41.01 | 30.32 | 29.78 | 22.72 | 35.33 | 11.31 | 3.56 | 11.52 |
| near scale 0.5 | 5.75 | 3.87 | 28.71 | 20.1 | 21.07 | 15.29 | 23.96 | 10.82 | 3.87 | 7.42 |
| ortho (mode 0) | 0.31 | 0.0 | 0.56 | 3.04 | 3.45 | 3.04 | 1.37 | 0.3 | 0.0 | - |
| crop keep (+0x66 off) | same as stock at every yaw and pose | | | | | | | | | |
| far cap 1000 | 2.14 | 4.62 | 8.63 | 5.01 | 6.43 | 5.13 | 7.71 | 4.05 | 2.14 | 4.03 |
| 8192 | 20.97 | 14.6 | 83.54 | 47.92 | 49.78 | 34.76 | 61.91 | 40.3 | 14.6 | 5.72 |
| 8192 + cutoff + extrusion (release) | 31.46 | 47.96 | 106.02 | 72.5 | 77.82 | 61.18 | 89.34 | 47.71 | 31.46 | 3.37 |

- **Target 1, met at 2048 by cutoff + extrusion:** the worst yaw at 20 m at least doubles (3.65 -> 7.86, 2.15x).
- **Target 2, not met by any control:** best/worst within 2 (it went from 5.72 to 3.37). The sun-behind yaws (0 and 45) follow farz and the
  extrusion, not the warp: the trapezoid knobs (focus, near scale) raise only the side-on and sun-in-front yaws.
- **Shot poses:** cutoff + extrusion is at or above stock at every pose (p3 18.24 against 18.36). Focus lowers the low side-on poses
  (p2 32.9 -> 17.8), so it stays off.
- **Costs:**
  - The height cutoff shortens the fitted farz at a 45 m camera from 250 to 150 m. Shadows end nearer, and above 100 m of height farz is
    lower than stock's 500 m cap: 275 m at 100 m.
  - The extrusion gathers casters further towards the sun.
  - The Empire crop fix (crop keep) never triggered here.

### Map-size ladder
Quality 3; 4096, 8192 and 8192 at quality 4, each against a same-sitting control (every key off). Runs `harness/runs/20261103_j24ladder_ctl`,
`_4k`, `_8k`, `_8k_q4`; table in `harness/runs/20261103_j24pc/ladder_table.md`; land_small, siege_small and hist_dresden at 1080p and 4K, 2 repeats.
- **Frame time:** no cost at any step. p50 is within -0.6 to +0.04 ms of the control and p99 inside noise. `compare --feature shadows`
  against the control finds 0 breaches.
- **VRAM:** 4096 +33 to +125 MB; 8192 +338 to +386 MB; 8192 at quality 4 (R32F) +455 to +514 MB, at the 512 MB budget. The arithmetic for
  8192 R16F + D24X8 is 384 MiB.
- **Address space:** VA used within ±15 MB; VA peak at most +16 MB. Load time at most +0.5 s.
- **DXVK at 8192:** DXVK 3.1.1 creates the 8192 R16F map and the 8192 D24X8 depth buffer on the RTX 4090 (capture j24_f_8k_*, viewport 8192).
  Density is exactly 4x the 2048 value at every pose.
- **Smaller card:** the 8192 map needs about 384 MB of VRAM (512 MB at quality 4). That is the figure for a smaller card; none was tested (D13).
- **Against J23's baseline:** the control itself "breaches" p99 at 4K by about 1.5 ms. So between sittings, p99 noise is as large as the
  1.5 ms budget, and the comparisons here are against the same-sitting control.

### Release values
8192 + cutoff + extrusion against a same-sitting control on build 75739186b92e. Runs `harness/runs/20261103_j24rel_ctl` and `_rel`; table
`release_table.md`; scenes include J46's land_40.
- VRAM +178 to +481 MB; p50 -0.34 to +0.40 ms; VA used within ±9 MB.
- Two p99 breaches, both on 1080p "turned" cells: land_small +4.69 ms (spread 12.5 ms, 120 %, one spike with max 44.8 ms) and land_40
  +3.49 ms (spread 7.8 ms). These are spikes in one of two passes. The same scenes' deploy cells and the 4K turned cells are faster than the control.
- No breach in hist_dresden or siege_small, so the ">2x budget" kill criterion is not triggered.
- land_small deploy load at 1080p was +1.2 s (once; the ladder's 8192 load was +0.0 s).

### Filtering
1. **Stock software kernel:** one fetch4, i.e. 2x2 point taps with bilinear weights (`pcf_filter`), so the footprint is one texel (about 8 cm
   at 12 texels/m). USE_MULTI_TAP is not defined: the receivers map byte for byte with base defines that lack it (J8). A larger map shrinks
   the penumbra in metres in proportion; the 8192 map gives about 2 cm. Fact `napoleon.shadow.kernel`.
2. **Hardware path:** captured by forcing it with the two-site key, since the prefs duplicate (B30) blocks the preference (run 20261103_j24pc,
   `raw/f_hw2`, 2026-11-03). Under DXVK the NVIDIA branch is taken: a 2048 A8R8G8B8 dummy target with a D24X8 depth texture, z-only clear,
   27 shaders not in the catalogue. The density metric does not read the hardware receivers' registers. Fact `napoleon.shadow.hardware_path`.
3. **Shimmer or aliasing at 8K:** not judged. The shots are still frames; Liam judges from the sheets. Grass hides most ground shadow at the low poses.

### Shots
In `harness/runs/20261103_j24pc/sheets/` (JPEG):
- `land_before_after.jpg`: p1..p6 at stock 2048, 4096, 8192 and the release;
- `land_before_after_crop.jpg`: centre-bottom crops at full resolution;
- `siege_before_after.jpg`: s1 at five settings;
- `fit_2048_land.jpg`: stock, cutoff + extrusion, focus.

Poses are in the run README. The yaw 270 readback is outside tolerance in every launch, as in J8. The distant pose is the engine's clamped readback.

### Acceptance
- **Idle check** (every shadow key off, build 75739186b92e): one pass, passed (`harness/runs/20261103_j24idle/pass_01.json`, 2026-11-03). The
  ledger labels it `679422b9443a-dirty`, read from the previous install's log (core B26/B31).
- **20 consecutive passes on build 75739186b92e, watcher 1.2.0, with the release values on** (`gfx.shadow_map_large`,
  `gfx.shadow_height_cutoff`, `gfx.shadow_extrusion`), verified 2026-11-03.
  - Run `harness/runs/20261103_j24acc3`: passes 1 to 20 all passed. Its pass 1 is labelled with the kit id `6bab276b0030` (B26/B31: first
    pass after a fresh install) and is not counted.
  - Run `harness/runs/20261103_j24acc3b`: pass 1 passed, the 20th counted pass.
  - `acceptance.py streak --build 75739186b92e --watcher 1.2.0`: "20 consecutive passes ... (need 20)". The orchestrator re-ran
    `wsc policy --branch job/J24` on d97b43e: rule 79 no longer refuses.
  - The shots match the baseline within their thresholds, for example land_small 1.48 to 1.60 against 4.0 and siege_small 1.33 against 4.0.
- **Earlier runs on the same build were broken by the hist_nile headless-launch flake, not shadow code:**
  - `20261103_j24acc`: 9 passes, then pass 10 failed with "HEADLESS FAILED ... exited before reporting on_virtual (last status: starting DllMain)".
  - `20261103_j24acc2`: 16 passes, then pass 17 failed with "no on_virtual status within 180 s".
  - The same exit happened on a launch with every key off (`raw/f2_focus_fail1`), and the message appears in J8, J23, J44 and J46 runs.
- **PC end state** (2026-11-03, about 14:35 UTC): `pc_deploy uninstall` reported the game folder identical to the pre-install snapshot
  (1565 files); exe sha1 9aebcd2172f2878d781b079f7feb45b0e12e0250; `preferences.script.txt` sha256
  83b9b32b2b738ebcafa4910a9b3b6f0c69b9a06e3e6270fb55d6e51bdee2cea7, as before the job; `job.sh status` shows the game not running and no lock.
- **Gates:** `wsc gates` 13 ok, 1 warn, 0 failed on 650ec50 (the commit before the acceptance runs, which add only run files and ledger lines).

## Deviations from the brief and why
- **No same-RVA ladder:** the generator and the engine both refuse overlapping rows, so the ladder used one build per size.
- **Rows are named by key, not stepped:** each row writes one fixed value until the core has a numeric key.
- **Fit candidates changed:** quantize_scene_bounds (+0x6c), move_clip_planes_with_landscape (+0x64) and +0x94 have no reader, so they were
  not tried. The trapezoid focus and near-scale rows were added because the warp is the suspected cause. Max range is +0x7c, the far clip
  that the per-quality setup overwrites, so the ctor value is dead; the far clip row stands in for it.
- **Release proposes 8192:** VRAM is within budget and there is no frame cost. 4096 is the alternative.
- **Release packaging touched:** `keep_ids` in `release.json` and `build_release.py`, so the player ini lists the three release keys (above).
- **Run helpers live in the run folder** (as J9's `proof.sh`), not `tools/`.
- **Worked from a clone in the session scratchpad:** the dispatch put the agent in a warscape-core worktree, and the harness refused git
  commands aimed at the napoleon checkout.
- **The acceptance needed three runs:** two broken by the hist_nile launch flake, then a fresh 20 (plus one, for B26/B31).
- **One incident:** `raw/f_hw` is 8192 + crop keep, not the hardware path. The driver was edited while it ran; the run README explains.

## Open questions
- **Liam:**
  - The release values: 8192 + height cutoff 200 + extrusion -150, or 8192 alone (keeps the 250 m farz), or 4096 to save VRAM.
  - Is the cut-off line nearer (150 m at deploy height) acceptable?
  - From the sheets, is 4096 visibly sharper than 2048 (the kill criterion)? And does 8K shimmer?
  - Quality 4 at 8192 is at the 512 MB budget.
- **J25 and J26:** cascades are the real fix for the sun-behind case; no single-map control gets best/worst within 2. Mapping the hardware
  path's 27 shaders and any softer kernel need receiver shaders (J26).
- **J27:** the extrusion and unit LOD both change the caster set; it was not tuned here.
- **Core (for the orchestrator to file):**
  - Numeric patch values from config keys: a `patch` row may name an int or float `config_keys` key (`value_key`) instead of a boolean, and
    the proxy writes the key's value as the immediate (int32 or float32, the length of `stock_bytes`), only when it differs from stock, and
    logs it. Files: the engine_sites schema, `gen_tables.py`, `patch_engine.h` and `patch_driver.cpp`, `config.h` (a float key type) and
    the patch engine host test. Why: shared-RVA rows are refused, so each value is a separate build today; J24's size, cutoff and extrusion
    and J27's distances need one shipped value a player can change. Optionally combine with `value_offset` (B41).
  - B26/B31: the first pass after a fresh install is labelled with the wrong build (the previous install's id, or the kit id).
  - The hist_nile relaunch headless flake, seen in J8, J23, J44, J46 and here (about one 20-pass run in ten).
  - B30 (the duplicated prefs key) no longer blocks J24: the `gfx.shadow_hw_force` sites go round it.

## Worth remembering
- Bash reads a script as it runs: editing a running driver broke a launch and left the game open, and the next launch reused that process.
  Never edit a running `.sh`.
- `TaskStop` on a background bash leaves its child `bash`/`python` processes running; kill them by command line.
- `shader_catalog.py import --run` takes the run id, not a path. Import fails entirely if one named capture is missing. `density` takes
  about 40 paths at most per Windows command line.
- p99 noise between sittings is about 1.5 ms, the same as the shadow budget: compare against a same-sitting control.
- `ctl cam` heights are clamped to 2.5 to 44.6 m above terrain. In land_small, yaw 0 faces +z with the sun behind the camera.
- After a fresh install, plan for 21 passes: pass 1 is labelled with the kit id (B26/B31) and the streak does not count it.
- A multi-hour watcher run spends many tool calls on wait loops; keep each wait under 10 minutes and do not send them in parallel.
