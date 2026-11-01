# Engine sites and routes: shadow, unit imposter (sprite), LOD, grass (J9)

Owner of this topic: which route governs each graphics setting on Napoleon.exe (sha1 `9aebcd21...`), the stock value, its encoding
and how many places change together. J24 (shadow) and J27 (distances, sprites) read this table; the rows are `registries/engine_sites.jsonl`
(ids below), the proof keys `registries/config_keys.jsonl` (`gfx.*_proof`, default and release off). VAs at ImageBase 0x400000, RVA = VA - 0x400000.
Proof run: `harness/runs/20261101_j9pc` (README: one line per proof). Strings: `python3 discovery/core/exe_strings.py find <regex>`.

## Routes

| setting | route | stock | encoding, places | rows | proof |
|---|---|---|---|---|---|
| shadow map edge, quality 3 and 4 | site: shadow setup 0x11868f0, `mov ebx, 0x800` (one instruction for both) | 2048 | imm32, 1 place (colour map and depth buffer both take `ebx`) | `shadow.map_size_q34` | PROOF_SHADOW |
| shadow map edge, quality 1 / 2 | site: same function, `ebx` = 0x200 at entry / `mov ebx, 0x400` at 0x1186965 | 512 / 1024 | imm32 | not registered (same pattern) | - |
| shadow map format | site: same function; quality 4 sets `dl=1` (R32F, engine format 9, if caps byte +0x711), else R16F (8, caps +0x710), else 0xe; hardware path (`gfx_hardware_shadows`, options +0x69d09) picks a depth format 0x17 (NV, caps +0x707) or 0x16 (ATI, +0x706) with a NULL colour target (0x13, caps +0x71b) or a dummy (2/4/5) | R16F | imm8/branches | open fact `napoleon.shadow.format_route` | - |
| shadow distance cap per quality | site: same function, `mov dword [esi+0x7c], <float>` per case | 100 / 250 / 500 / 1000 m (q1..q4) | float, 1 place per quality | `shadow.far_cap_q3` (q3) | PROOF_SHADOW |
| shadow light sweep, ranges, crop flags | site: shadow renderer ctor 0x1127580 (Empire 0x103f160 with every field +0x14): sweep `[+0x9c]` -75, max range `[+0x7c]` 400, min range `[+0x84]` 50, height factor `[+0x98]` 100, crop flags `[+0x64..0x67]` 01 01 01 01 | see left | float imm32 after `c7 87 <disp32>` (anchor = 6 opcode bytes) | open fact `napoleon.shadow.fit_code` (narrowed) | - |
| shadow quality itself | preference `gfx_shadow_quality` (0 off .. 4), copied to options field +0x69d18 (setter index 7) | 3 on this PC | int | - | J8 |
| unit imposter page edge | site: 0x1240010 switch on options field +0x69d00 (setter index 1; which `gfx_*` key feeds index 1 is open) and a budget loop that steps the case down while the page cost is over budget: case 1/2/3 `mov dword [esi+0x5c], 1024.0`, case 0 and other 512.0 | 512 seen in J8's captures (A8R8G8B8) | float, 4 places | `sprite.page_q0..q3` | PROOF_SPRITE |
| unit imposter frame time | site: same switch, `mov dword [0x14692e8], <float>`: 0.5 / 0.25 / 0.2 / 0.5 | 0.5 s | float after an absolute address (anchor would hold a relocated dword): needs a core `value_offset` or an anchor after the value | open fact `napoleon.sprite.frame_time` | - |
| unit LOD distances (imposter, large imposter, no variant, shared pose, feathered range) | site: 0x756e80 (thiscall(out, quality, a3, a4)): quality = `gfx_unit_quality` from the battle settings (vfunc +0xf8); per quality five floats from shared .rdata constants (q3: 100, 100, 150, 50 or 70, 0); with tweaker `ENTITY_LOD_OVERRIDE` on, the five tweakers instead | q3 ultra 100 m imposter | tweaker defaults: float imm32 in CRT initialisers, 1 place each (+ the override byte); the per-quality constants are shared (100.0 has 303 users): not patchable in place | `unit_lod.*` (override + 2 distances) | PROOF_UNITLOD |
| unit mesh LOD (per model) | db `warscape_animated_lod` (1307 rows, a switch distance per mesh, e.g. 15 / 40 / 50 m) | per row | db | data route (no exe write) | - |
| building and rigid LOD | db `warscape_rigid_lod_range` (2 LODs: 600; 3: 600/1200; 4: 200/400/750; 5: 200/400/750/1500 m) per `warscape_rigid_lod` row; tweakers `lod_distance_scaler` 1.0 (reader 0x1146b20) and `rigid_lod_distance_scaler` 10.0 (reader 0x1146e30) | see left | db / tweaker float | data route preferred; tweakers not registered | - |
| ship mast, rope, knot distances | site: CRT initialisers of tweakers `MAST_LOD_DISTANCE`, `ROPE_DISTANCE`, `ROPE_DISTANCE_FADEOUT`, `KNOT_DISTANCE`, read unconditionally by the ship draw 0x782210 (squared, against the camera distance squared) | 250, 200, 150, 50 m | float imm32, 1 place each | `ship_lod.*` | PROOF_SHIP |
| ship model LOD | db `warscape_naval_lod` (26 rows, all 0 in vanilla) | 0 | db | data route | - |
| flag size | tweakers `flag_max_size` 2.75, `flag_min_apparent_size` 0.03 (reader 0x770450), `naval_flag_size` 0.5, `naval_flag_distance_scale` 200 (reader 0x790910) | see left | float imm32 | not registered | - |
| trees near / far | tweakers `tree_near_distance` 30, `tree_far_distance` 200 (readers 0x11e1220, 0x124a8e0); `gfx_tree_quality` | 30 / 200 m | float imm32 | open fact `napoleon.lod.trees` | - |
| grass range | site: .rdata table 0x1419ab4, one row per `gfx_grass_quality` (options +0x69d20): (grid N, cell 16, density 1/16/24/28/32), N = 5 in every row (range N x 16 = 80 m); a budget loop in 0x11d0c90 steps the quality down when N^2 x density is over budget | N 5 | int32 in data, 1 place per quality | `grass.grid_q3`, `grass.grid_q4` | PROOF_GRASS |

## How to read the sites
- Every proof row writes fixed `patch_bytes` (one non-stock value). J24 and J27 own the stepping and any proxy feature that writes a
  configured number; the encoding column says what such a feature writes.
- A tweaker default patched in its CRT initialiser takes effect because the proxy patches in DllMain, before the exe's CRT runs the
  static initialisers (d3d9.dll is a static import). The same tweaker can also be changed at run time by name through the console
  executor's tweak stage (`console_exec_string` 0x106c370 -> tweaks 0x106c980, `proxy/runs/20261029_j15re/README.md`), a route without
  an exe write that needs the console path.
- Options fields: the graphics options object is `*[0x182eb14]`; setter index i stores at +0x69c84 + 4i and +0x69cfc + 4i (max at
  +0x69d74 + 4i), setters in the vtable at 0x140cd60. Index 1 = the imposter page switch, 7 = shadow quality, 9 = grass quality.
