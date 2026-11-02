# Phase 3 budgets: PROPOSED (J23, 2026-11-01)

**Status: PROPOSED.** Liam agrees or changes these in chat; until `perf/budgets.json` says `AGREED`, no job treats them as agreed.
The numbers are the machine-readable `perf/budgets.json`; `python3 tools/perf_baseline.py compare --run <dir> --feature <name>` flags a
breach of a feature's budget against `perf/baseline.json`. J59 re-agrees them once J46's larger battles are measured (D38).

## What the baseline says (run 20261101_j23pc, DXVK 3.1.1, RTX 4090, headless)
- **Frames are cheap and do not scale with resolution.** Worst p50 4.47 ms and worst p99 6.70 ms (hist_dresden, 1080p); 4K is no slower
  than 1080p in any scene (land_small p50 1.89 / 1.82 / 1.81 ms at 1080p / 1440p / 4K). The frame is bound by the CPU side (engine work and
  draw calls), not by pixels: features that add draw calls or engine work cost frame time; pixel work on this GPU is close to free.
- **Address space is the scarce resource.** The 32-bit process has 4096 MB; the highest peak is 2096 MB (hist_dresden); the smallest
  scene sits at 1750 MB. Address space is flat across sizes (land_small 1818 MB at every size) while VRAM grows (564 / 632 / 794 MB):
  under DXVK render targets and shadow maps live in VRAM, not in the process.
- **VRAM is not a constraint here** (at most 1076 MB of 24 GB at 4K). It is budgeted anyway, for a smaller card than this one.

## Targets
- **60 Hz with every feature on: p99 at or under 16.67 ms in every baseline cell at every size.** Today's worst p99 is 6.70 ms: 9.97 ms of
  headroom. The budgets below spend 7.5 ms at 4K (6.7 ms at 1080p) and keep about 2.5 ms for J46's larger battles, whose cost is unknown.
- **Address-space stop line for J27's memory gate: a peak of 3400 MB in any cell.** 696 MB under 4 GB is kept for fragmentation and
  load-time spikes (a 32-bit process fails a large allocation well before the last free byte). Headroom from today's 2096 MB peak: 1304 MB;
  the budgets spend 950 MB and keep 354 MB for J46's battles.

## Per feature (delta against the baseline cell, any scene)
| feature (job) | p50 ms (1080p / 1440p / 4K) | p99 ms | VA peak MB | commit MB | VRAM MB | why |
|---|---|---|---|---|---|---|
| shadows (J24): resolution and fit | 1.0 / 1.0 / 1.0 | 1.5 | 50 | 50 | 512 | a larger map is GPU work and VRAM (flat VA under DXVK); the fit runs on the CPU per frame |
| cascades (J26) | 1.5 / 1.5 / 1.5 | 2.0 | 50 | 50 | 768 | each cascade redraws the casters: draw calls, the cost that does show here |
| distances (J27): imposters and LOD | 1.0 / 1.0 / 1.0 | 2.0 | 600 | 500 | 1024 | more geometry and textures resident at once: the main address-space consumer, hence most of it |
| upscaler | 0.5 / 0.8 / 1.2 | 0.7 / 1.0 / 1.5 | 100 | 100 | 128 / 192 / 256 | a full-screen pass that scales with the output size; its DLL and shaders in the process |
| UI (J30): RmlUi | 0.3 / 0.3 / 0.3 | 0.5 | 150 | 150 | 128 | the library, fonts and atlases in the process; a few draw calls |
| **sum** | 4.3 / 4.6 / 5.0 | 6.7 / 7.0 / 7.5 | 950 | 850 | 2560 / 2624 / 2688 | against 9.97 ms p99 and 1304 MB VA of headroom |

The p99 sum at 4K is 7.5 ms with the upscaler's 1.5: 6.70 + 7.5 = 14.2 ms, inside 16.67 with 2.5 ms of reserve.

## Noise: what a breach must exceed
Within one sitting the repeats agree closely (largest spreads over the baseline: p50 0.14 ms, p99 1.47 ms, VA peak 19 MB, commit 20 MB,
VRAM 82 MB). Between sittings (separate launches) they agree less: land_small 1080p deploy, smoke run 20261101_j23smoke against the
baseline: VA peak +49 MB, VRAM +216 MB, p50 +0.06 ms. So a VA delta under about 50 MB and a VRAM delta under about 250 MB are inside
launch-to-launch noise. The 50 MB VA budgets of shadows and cascades sit at that noise: J24 and J26 should read `va_used_mb` (the scene's own
value, spread 1 MB) as well as the peak, and re-measure the baseline cells in the same sitting as their feature cells when a delta is close.

## Open for Liam
- Is 60 Hz the right target (the game's own `gfx_frame_rate` default is 60), or 120 Hz on this PC (p99 8.33 ms: today's 6.70 leaves 1.6 ms)?
- Is 3400 MB the right stop line, or should J27 measure where allocations start failing first?
- No system d3d9 number exists (fact `napoleon.render.system_backend`): these budgets are for DXVK, the shipped backend.
