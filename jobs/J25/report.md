# J25 report: Cascaded shadows spike

**Go with conditions.** A two-cascade prototype ran in `land_40`, `land_small` and `siege_small` with every caster duplicated, 24 of 28 receivers swappable, and a cost far inside the proposed budget, but one
criterion is met only in part: the pick's position is checked to about 10 screen pixels, not to the texel the brief asks for. Liam decides. The bigger question for J26 is what cascades buy at all: the J24 release map
already has more texels than a 2048 cascade, cascades do not remove imposter blobs, and a split measured from the camera misses the units at the deploy height.

## What was built
- **Route 1, variant (a)** on local warscape-core branch `spike/J25-cascades` (head 3b9134a, cut from v0.30.0, not pushed; series in `harness/runs/20261106_j25pc/patches/`). `cascade.cpp` draws each caster a second time
  into a near target, with the near matrix in that caster's own registers, then puts the registers, target, depth, viewport and scissor back. Casters are found from their own CTAB, so no table is needed.
- **Near cascade:** a bounding sphere of the frustum slice, snapped to whole texels, orthographic, the engine's map format and its linear depth. The engine's map stays as cascade 1, untouched.
- **Receivers:** swapped by hash at `CreatePixelShader`, compiled offline with the game's D3DX (`receivers.py`, `cascade.fx_fragment`). **Pixel shader only:** every sm3 receiver already has `world_position` there. The pick blends
  over 5 % of the map's width. All 24 that pass were swapped, not just terrain and units.
- **Tint:** `dev.cascade_tint` shows the pick as a scalar: dark inside the cascade, no shadow outside. It is not a colour tint, because the occlusion value is a scalar.
- **Host tests:** `test_cascade.cpp` (235 checks: CTAB reader, gate, splice, pass recogniser, fit, snap); `tests/test_run_helpers.py` for the density input.
- **On this branch:** the run folder, five new facts and an update to `napoleon.shadow.isolable`, the shadow section of `frame_anatomy.md` and `tools/shadow_density.py --cascade` with its row.
  No DLL input changed: `wsc policy` raises no rule 79.

## Evidence
All from run `20261106_j25pc` (`harness/runs/20261106_j25pc/README.md`), verified 2026-11-06.

### Questions 1 to 6
1. **The pass in `land_40`:** the shape of `napoleon.shadow.isolable` holds: first draw pass, one block, 61 draws at deploy and 55 turned (49 `land_small`, 47 `siege_small`), at 8192 with release values. Every caster is in the catalogue, with
   its registers in `napoleon.shadow.casters`. Receivers are listed in `passes_a_main.json`. Terrain is `grid.fx` `grid_far_sm3`, not `supertexturetile`. One shader is outside the catalogue: `5c9bd7a4bb31b068` (`decal.fx`, question 6).
2. **Buffers are not stable:** about 3.8 DISCARD and 56 NOOVERWRITE locks per pass, on the render thread, plus instancing and 60-75 state block applies. **Variant (b) is out.** Fact `napoleon.shadow.caster_buffers`.
3. **`0x114b440` draws nothing.** It builds matrices and uploads parameters. The pass is `0x1188b30`, and the casters come from the generic queue flush `0x1193db0`. So route 2 as written, a second call of slot 22, cannot work. Whether
   running `0x1193db0` twice is safe is **open**. Route 1 needed no help, so route 2 was not prototyped. Fact `napoleon.shadow.pass_call`.
4. **Light and camera:** the light direction is the casters' own linear-z row, read at the first caster draw of the same frame, so no earlier frame is involved. The camera is the mode's position (+8) and target (+0x14) through `CameraRead`, the current frame.
5. **Room in the receivers:** no constraint. All 28 are ps_3_0 (stock maximum c41 and s10). 24 pass, 3 call `shadow_map_occlusion` directly and stay stock (`cloth`, `navalsail`, `ocean`), `campaigntree` fails (9 constants move). Fact `napoleon.shadow.receivers`.
6. **There is no blob decal** in the main pass (below).

### Two findings the brief did not foresee
- **The CTAB gate is necessary but not sufficient.** With the gate passing, the first prototype looked right and did nothing: D3DX reads the constant table back from the shader and clears every name in it at each pass, so the cascade's registers
  were zero and every pixel fell through to the stock map. Clean shots did not show this; the tint did. Fix: gate the compiled table, then give the device the replacement under the **stock** CTAB. J26 must keep this.
- **A constant can have an entry per register set** (`flat_shading`), so a gate must match on name and set. The name-only C++ gate wrongly refused the three `textured_rigid` receivers, which are the buildings. Fixed, with a test.

### Coverage
All 10 prototype launches: caster draws seen equal draws duplicated, 0 unknown shader, 0 without a fit (for example 8,532,501 in `e_on2k`). In `d_tint`, 19,715,616 receiver draws were swapped and 691,590 (3.4 %) stock, all of those `cloth`. 18 further receiver hashes are created
but never drawn in these scenes. Counts are per launch, not per frame. Casters are the engine's own list for the frame, so the cascade cannot lack one the control has; a caster the engine culled that only the cascade would need was not separately measured.

### Quality
Texels per metre at 20 m, map 2048, by the catalogue's metric (`tools/shadow_density.py`):

| setting | y0 | y45 | y90 | y135 | y180 | y225 | y270 | y315 | worst | best/worst |
|---|---|---|---|---|---|---|---|---|---|---|
| control (cutoff + extrusion) | 7.86 | 11.99 | 26.5 | 18.12 | 19.46 | 15.3 | 22.33 | 11.93 | 7.86 | 3.37 |
| cascade 0, split 25 | 21.08 | (all) | | | | | | | 21.08 | 1.0 |
| cascade 0, split 40 | 13.18 | (all) | | | | | | | 13.18 | 1.0 |
| cascade 0, split 60 | 8.78 | (all) | | | | | | | 8.78 | 1.0 |

The control reproduces J24's row. How to read this:
- **The 1.0 is by construction:** a fixed orthographic map has no yaw term. That is the point of it, but it is not a measured surprise.
- **The 20 m point is in the air** at this 59 m pose, as in J8 and J24. Ground in view starts about 68 m out.
- **Against the release map the picture changes:** J24's 8192 row has a worst yaw of 31.46, above every 2048 cascade here. A near cascade helps at release only at 4096 or more: 8192 at split 40 would be 52.7 by scale, not measured.
- **Cascade 1:** the engine's matrix differs from the control by at most 0.13 %. The prototype does not touch the fit, and my control differs from J24's by a similar amount, so I read it as launch noise, but no control-against-control pair exists at these poses.

### Cost
Median over 2 blocks of prototype minus same-sitting control, spread in brackets; cascade at 8192, release values on (`cost.md`, `ladder_tables.md`). Budget (PROPOSED): 1.5, 2.0, 50, 768.

| cell | control p50 / p99 | p50 | p99 | VA used | VRAM |
|---|---|---|---|---|---|
| 1080p `land_40` deploy | 2.3 / 3.67 | +0.07 (0.01) | +0.12 (0.0) | -1.25 (1.5) | +284 (208) |
| 1080p `land_40` turned | 2.23 / 3.51 | +0.12 (0.0) | +0.16 (0.07) | -1.25 (0.5) | +284 (208) |
| 4K `land_40` deploy | 2.3 / 3.7 | +0.1 (0.0) | +0.1 (0.02) | -7.25 (0.5) | +338 (124) |
| 4K `land_40` turned | 2.24 / 3.56 | +0.13 (0.01) | +0.23 (0.08) | -7.25 (0.5) | +338 (124) |
| 1080p `hist_dresden` deploy | 3.87 / 5.7 | +0.06 (0.01) | +0.13 (0.17) | -3.0 (30) | +314 (176) |
| 1080p `hist_dresden` turned | 3.67 / 5.47 | +0.06 (0.02) | +0.09 (0.1) | -2.0 (30) | +314 (176) |

- **Per cascade:** 47 to 61 more draws a frame and about 0.1 ms. VA peak is +11 to +22 MB, commit +0 to +9 MB.
- **VRAM:** the arithmetic is 384 MiB at 8192 (R16F and D24X8). Blocks read +180 to +400, and the counter drifts: the 1080p control alone moved 104 MB between blocks.
- **These scenes are CPU-bound on the 4090:** p50 is the same at 1080p and 4K, here and in `perf/baseline.json`. **The ms figures say little about a weaker GPU**, and none was tested. The scenes are also the deployment phase, not a fight.
- **Extrapolation, linear in cascades (not measured):** 3 cascades about +0.26 ms p50 and +0.46 ms p99; 4 about +0.39 and +0.69. VRAM at 8192 each: 768 MiB for 3, at the budget, and 1152 for 4, over it; at 4096 each, 96 MiB a cascade.
- The cost includes both maps being sampled at every pixel, with no branch.

### Shots
- **Sheets:** `sheets/all_2048.jpg`, `all_8192.jpg` (control, cascade, tint at every pose), `low_2048_crop.jpg` (near crops), `decal_skip.jpg`. **Liam judges these.**
- **Acceptance metric, cascade against control:** 0.67 to 1.05 at the `land_40` poses, p5, p6 and s1 (threshold 4.0; control against control 0.81 to 2.26).
- **p1 to p4 are 5.9 to 16.4, over the threshold**, but the `c_on` build, whose receivers read nothing, differs from the control just as much (6.5 to 16.7): formations and grass differ between launches. So this metric **cannot verify the stock look at low poses.**
- By eye, tree shadows in the cascade sit where the control has them, and horse shadows at p4 are present. I saw no seam at the poses I viewed, at the size I viewed them, in the frames captured: not checked in motion, so shimmer is unjudged.
- **Unexplained:** a thin pale vertical line in the p2 tint crop, around x 1600 of `low_2048_crop.jpg`. It does not separate two regions, so it does not look like a seam. I do not know what it is.

### Blob shadows
- **No decal:** the main pass has 12 blended draws at every pose, none tied to units. At low poses a 13th, `decal.fx`, is one batched draw of 240 triangles. I first ruled decals out by draw count, which was wrong for a batch; skipping that one shader removed the blue formation outline and nothing else (`sheets/decal_skip.jpg`). `sprite.fx` in the main pass is opaque and alpha tested.
- **Imposter caster past the LOD switch:** cascades do **not** remove it. The same quad is drawn at more texels, and the units at the deploy poses are outside a 40 m cascade anyway. J27's LOD distance would remove it, at a cost not measured here (J9: 90 shadow draws against 48 with the switch at 1000 m).
- **Sun-behind collapse of near mesh shadows:** the near cascade removes it (best/worst 1.0 against 3.37).

Fact `napoleon.shadow.blob`.

## Go or no-go
| # | criterion | result | evidence |
|---|---|---|---|
| 1 | Isolable and complete | **Met** | 0 unknown and seen equal to duplicated in `land_40` (both poses), `land_small`, `siege_small` |
| 2 | Receivers replaceable | **Met in part** | Every swap passes the gate, 0 refused; terrain and units swapped; every other receiver has a route. **Position: 7 of 8 edges within 11 px at deploy and 5 of 6 within 27 px turned** (`pick_check.py`, one fitted ground height), **not within a texel**: 5.6 cm cannot be read from a 1280-wide shot on uneven ground. No seam seen at the viewed poses |
| 3 | Quality | **Met** | Worst yaw 8.78 to 21.08 against 7.86; best/worst 1.0; cascade 1 unchanged within noise |
| 4 | Cost | **Met**, on the proposed budget | Largest medians: p50 +0.13, p99 +0.23, VA used -1, VRAM +338 (one block +400). Variant (c) not needed |
| 5 | Stable | **Met** | No crash or hang in 14 launches and 8 cost runs; 0 DXVK `err:` in every log read. `c_on`'s log is lost, so that one launch has no device-error evidence |

**Verdict: go with conditions**, the conditions being:
1. J26 proves the pick to a texel in map space, not by shots: read back the cascade's uv at known world points.
2. Liam agrees the budget, which is still PROPOSED.
3. Liam judges the sheets; shimmer needs a moving check.

## Design for J26
- **First decide whether it is wanted.** At 8192 the engine's map is already 31 to 106 texels per metre at 20 m. What a cascade adds is an even density, not more of it unless it is also large. Liam may prefer J24's map alone.
- **Route and variant:** route 1, variant (a), inline duplication: the only correct one with these buffers, and cheap at 47 to 61 draws. Variant (c) is unnecessary on this evidence.
- **Cascade count and splits:** start with two, keys `gfx.cascade_count`, `gfx.cascade_split`. **Do not fit to camera distance alone:** at the deploy height a 40 m slice lies mostly in the air, and the units, about 180 m away, are outside it. Fit to the ground in view, for example around where the view ray meets the terrain. Proposed release value: none until that fit exists.
- **Size and format:** the engine's format. 4096 is the likely choice for a near cascade: 96 MiB, about 26 texels per metre at split 40 by scale, not measured. 8192 is 384 MiB.
- **The engine's map stays the last cascade,** with J24's height cutoff and extrusion. Its fit is untouched here.
- **Receiver route:** bytecode swap by hash for now, table in `receivers/receivers.json`: `grid`, `grass`, `imposter`, `variantmesh`, `weighted`, `textured_rigid`, the vegetation shaders, `navalship`, `supertexturetile`, `campaignbuilding`. An fx pack override would reach all at once and needs `napoleon.files.loose_override` settled first. Change `cloth`, `navalsail` and `ocean` in their fx. `campaigntree` needs its registers pinned. The hardware path's 27 receivers are not covered.
- **Keep:** stock CTAB under every replacement, gate on name and set, the bound shader read at each draw, casters found by CTAB.
- **Split of the work:** core job `W<n>`: the device module, CTAB reader, gate, splice and swap loader. Napoleon: the hash table and bytecode, the camera offsets, the 70 degree fov (hardcoded here, as is 16:9), and engine addresses as `engine_sites` rows.
- **Expected cost:** about 0.1 ms and 50 to 60 draws per cascade on this PC; unknown on a smaller card.
- **Risks:** GPU cost on weaker cards; shimmer in motion; the 3.4 % of `cloth` draws staying stock; R16F depth precision over a long light range, untested at grazing sun; the 18 undrawn receivers appearing in another scene.
- **J26's kill criteria:** a smaller card over budget in `land_40`; shimmer Liam rejects; any stock register moved by a compile that has no pinning route; VRAM above 768 MB at the chosen sizes.

## Deviations
- **Spike cut from v0.30.0, not v0.9.0:** the brief's tag predates the current pin.
- **`shader_catalog.py` is now in `core/` (J64), so it could not be extended.** `tools/shadow_density.py` feeds the unchanged metric instead, which also changed its registry row.
- **Pixel shaders only, and all 24 swappable receivers,** where the brief expected more shader work and fewer receivers.
- **Added `SpliceCtab`,** not in the brief, because the gate alone left the cascade unread.
- **Cost sizes grouped,** all 1080p then all 4K, so the display changes size once; arms still interleave within a size.
- **Cost arms ran the cascade at 8192,** the "same size as the engine's map" under release values.
- **A scalar tint,** not a colour one.
- **Extra spike key** `dev.cascade_skip_ps`, for question 6; **raw captures stayed in `<state>\captures`,** not `_scratch\j25`.
- **`c_on`'s DXVK log is lost, and no raw DXVK log is committed:** a copy out of the game folder was denied, so later launches record an error summary instead.
- **`napoleon.shadow.pass_call` is `verified`, not `open` as the brief allowed:** what it claims is verified, and the discovery ratchet refuses a new open fact. The unsettled second flush is stated as untested in it, and is an open question below.
- **No assets row for `shadowmap.fx_fragment`,** which the brief asked for: `registries/assets.jsonl` is generated from the discovery index, a hand row fails its test, and the route (`asset_roles.json`, `wsc discovery assets`) is outside this branch's paths. J26 adds it, as the job that ships the fragment.
- **Spike clone in the job's temporary folder,** not beside this repo; the patch series is the durable copy.
- The window-observer offsets (`-X 3839 -Y 2160`) were not needed: nothing here used a foreign-window observer.

## Open questions
- **Liam:** Is the cascades budget agreed? Do you want cascades at all, given 8192 alone (Design for J26)? What did D12 mean by "slicing artefacts" and "blob shadows": imposters are not fixed by cascades; the sun-behind collapse is. Should the spike branch be pushed as a draft? The sheets are yours to judge, including the p2 tint mark.
- **J26:** the map-space pick check; a ground-based fit; route 2 only if something needs it, with `0x1193db0` still open.
- **J27:** imposter blobs are yours: only the LOD distance removes them.
- **Core, for the orchestrator:** `test_capture`'s stress failed once in six builds with its code unchanged. `shader_catalog.py import` takes every shader in the capture folder, not just those a capture uses. The installer prints the repo commit as "build", which reads like the DLL's identity.
