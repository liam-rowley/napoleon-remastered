# Engine sites and routes: shadow, unit imposter (sprite), LOD, grass (J9)

Owner of this topic: which route governs each graphics setting on Napoleon.exe (sha1 `9aebcd21...`), the stock value, its encoding
and how many places change together. J24 (shadow) and J27 (distances, sprites) read this table. Rows: `registries/engine_sites.jsonl`
(ids below), proof keys `registries/config_keys.jsonl` (`gfx.*_proof`, default and release off), facts `registries/engine_facts/`
(`napoleon.shadow.*`, `napoleon.lod.*`, `napoleon.sprite.*`, `napoleon.exe.options_object`, `napoleon.tweakers.table`).
VAs at ImageBase 0x400000, RVA = VA - 0x400000. Proofs: run `harness/runs/20261101_j9pc` (README: one line per proof), 2026-11-01,
on DLL builds 286b3fa123e4, d3196b3a8424 and 46f52d356ce8 (the proven rows are byte-identical in all three; the final build's start-up
check passes all 45 rows). Strings: `python3 discovery/core/exe_strings.py find <regex>`.

## Routes

| setting | governing route | stock | encoding, places | rows | proof (capture, key off -> on) |
|---|---|---|---|---|---|
| shadow map edge, quality 3 and 4 | site: shadow setup 0x11868f0, `mov ebx, 0x800` (one instruction for both; colour map and depth buffer take `ebx`) | 2048 | imm32, 1 place | `shadow.map_size_q34` (key `gfx.shadow_map_large`, 8192) | 2048 R16F -> 8192 R16F (J24; 4096 in J9); density x4 at every pose |
| shadow map edge, quality 1 / 2 | site: same function, `mov esi, ecx; mov ebx, 0x200` at 0x11868fa / `mov ebx, 0x400` at 0x1186965 | 512 / 1024 | imm32 | not registered (same pattern) | - |
| shadow far clip per quality | site: same function, `mov dword [esi+0x7c], <float>` (esi = the shadow renderer, [+0x7c] its `shadow_far_clip`) at 0x118695c / 0x118696a / 0x1186973 / 0x118697c: 100 / 250 / 500 / 1000 m (q1..q4) | 500 at q3 | float, 1 place per quality | `shadow.far_cap_q3` (key `gfx.shadow_far_cap`, 1000) | fitted farz 250.5 -> 473.3, density about half |
| shadow extrusion (light sweep) | site: shadow renderer ctor 0x1127580 (Empire 0x103f160, fields +0x14): `mov dword [edi+0x9c], -75.0`, `shadow_extrusion_length` | -75 m | float after `c7 87 9c 00 00 00` | `shadow.light_sweep` (key `gfx.shadow_extrusion`, -150) | yaw 45 at 20 m 3.65 -> 8.48 texels/m |
| shadow fit: height cutoff | site: same ctor, `mov dword [edi+0x98], 100.0` (`far_distance_scale_with_height_cutoff`; farz lerps from `[+0x84]` 50 to the far clip by camera height / cutoff, 0x119ad76) | 100 m | float after `c7 87 98 00 00 00` | `shadow.fit_height_cutoff` (key `gfx.shadow_height_cutoff`, 200) | farz 250.5 -> 150.3 at the deploy height; yaw 0 5.24 -> 13.16 |
| shadow fit: mode, crop, trapezoid | site: same ctor: `shadow_map_mode` `[+0x5c]` 1 (`c7 47 5c`), crop flags `[+0x64..0x67]` one imm32 (`c7 47 64`, +0x66 `unit_cube_clip_bug_out`), `focus_distance` `[+0xc0]` 0.7, `near_trapezoid_scale` `[+0xdc]` 1.0; all 34 fields: fact `napoleon.shadow.fit_fields` | see left | imm32 / float | `shadow.fit_warp_ortho`, `shadow.fit_crop_keep`, `shadow.fit_focus`, `shadow.fit_near_scale` (measurement keys, release off) | ortho: worse everywhere; crop keep: no change; focus / near scale: side-on up to 2x, sun-behind unchanged (fact `napoleon.shadow.fit_controls`) |
| shadow format, hardware path | site: 0x11868f0 picks the format from caps bytes and `gfx_hardware_shadows` (options +0x69d09, read at 0x11869a4); the receivers' define follows at 0x11a7e60 (pref read at 0x11a7e75) | software R16F (R32F at q4) | branches | `shadow.hw_force_setup` + `shadow.hw_force_define` (key `gfx.shadow_hw_force`, diagnostic) | NVIDIA path under DXVK: A8R8G8B8 dummy + D24X8 depth texture (fact `napoleon.shadow.hardware_path`) |
| shadow quality | preference `gfx_shadow_quality` (0 off .. 4), options +0x69d18 | 3 on this PC | int | - | J8 (`napoleon.shadow.map`) |
| unit imposter atlas | site: 0x1240010 switch on `gfx_texture_quality` (options +0x69d00): cell `mov dword [esi+0x5c], <float>`: 512 at quality 0, 1024 at 1 / 2 / 3; the atlas (stage 2 of `imposter.fx`, one-level dynamic DXT1) is twice the cell; a budget loop steps the case down | atlas 2048 (quality 2) | float, 4 places | `sprite.page_q0..q3` | atlas 1024 / 2048 / 2048 / 2048 -> 4096 at texture quality 0 / 1 / 2 / 3; load 4.2 -> 4.0 s |
| unit imposter frame time | site: same switch, `mov dword [0x14692e8], <float>`: 0.5 / 0.25 / 0.2 / 0.5 s | 0.25 s (quality 2) | float after an absolute address: needs a core `value_offset` | open fact `napoleon.sprite.frame_time` | - |
| unit LOD distances | site: 0x756e80 per `gfx_unit_quality`, five distances from shared .rdata floats (q3: imposter 100 m); tweaker `ENTITY_LOD_OVERRIDE` on swaps in five tweakers; the shared floats are not patchable (100.0 has 303 users), so the route is the override plus tweaker defaults (CRT initialiser immediates) | 100 m imposter switch at q3 | byte + float imm32, 3 places (override, imposter, large imposter) | `unit_lod.*` | 8 imposter draws -> 0; shadow pass 48 -> 90 draws |
| unit mesh LOD (per model) | db `warscape_animated_lod` (1307 rows, a switch distance per mesh, e.g. 15 / 40 / 50 m) | per row | db | data route | - |
| building and rigid LOD | db `warscape_rigid_lod_range` (2 LODs 600; 3: 600/1200; 4: 200/400/750; 5: 200/400/750/1500 m) per `warscape_rigid_lod` row; tweakers `lod_distance_scaler` 1.0 (reader 0x1146b20), `rigid_lod_distance_scaler` 10.0 (reader 0x1146e30) | see left | db / tweaker float | data route preferred; tweakers not registered | - |
| ship rope and knot distances | site: CRT initialisers of tweakers `ROPE_DISTANCE`, `ROPE_DISTANCE_FADEOUT`, `KNOT_DISTANCE`, read unconditionally by the ship draw 0x782210 (squared, against the camera distance squared) | 200, 150, 50 m | float imm32, 1 place each | `ship_lod.*` | 400 m behind the deploy pose: rope.fx 0 -> 7 draws (12,104 prims), textured_rigid 92 -> 2,208 prims; 800 m: no change |
| ship mast distance | tweaker `MAST_LOD_DISTANCE` 250 (RVA 0x15711) | 250 m | float imm32 | none: no observable effect (open fact `napoleon.lod.mast`) | - |
| ship model LOD | db `warscape_naval_lod` (26 rows, all 0 in vanilla) | 0 | db | data route | - |
| flag size | tweakers `flag_max_size` 2.75, `flag_min_apparent_size` 0.03 (reader 0x770450), `naval_flag_size` 0.5, `naval_flag_distance_scale` 200 (reader 0x790910) | see left | float imm32 | not registered | - |
| tree far distance | site: tree display init 0x11e1220 switches on `gfx_tree_quality` (options +0x69d1c) and overwrites tweaker `tree_far_distance` through its setter 0x5aa4a0: 100 / 150 / 200 m at quality 1 / 2 / 3, 50 m otherwise (the tweaker default 200 never survives) | 150 m (quality 2) | float imm32 after `c7 44 24 14` or `c7 44 24 18`, 1 place per case | `trees.far_other`, `trees.far_q1..q3` | 3D tree (branch/frond) draws 5/5 -> 8/9 at quality 1, 6/6 -> 9/10 at 2, 3 and 4 |
| tree near distance | tweaker `tree_near_distance` 30 (RVA 0x42ae1), read at 0x11e1417 and 0x124a8e6 | 30 m | float imm32 | not registered | - |
| grass range | site: .rdata table 0x1419ab4, one row per `gfx_grass_quality` (options +0x69d20): (grid N, cell 16, density 1/16/24/28/32), N 5 everywhere (80 m); 0x11d0c90 steps the quality down when N^2 x density is over budget | N 5 | int32 in data, 1 place per quality | `grass.grid_q3`, `grass.grid_q4` | grass 97/117,958 -> 213/260,694 draws/prims at quality 3; 97/154,074 -> 213/340,400 at 4 |

## How to read the sites
- Every proof row writes fixed `patch_bytes` (one non-stock value). J24 and J27 own the stepping and any proxy feature that writes a
  configured number; the encoding column says what it writes. J24 (run `harness/runs/20261103_j24pc`, 2026-11-03): rows that share an
  RVA are refused by both `gen_tables.py` and the patch engine (overlap, whatever their keys), so a ladder of values is one build per
  value; the shadow rows ship one fixed value each behind a boolean key, and a configured number waits for the core's numeric key. All 45 rows pass the proxy's start-up check on the final build.
- A tweaker default patched in its CRT initialiser takes effect because the proxy patches in DllMain, before the exe's CRT runs the
  static initialisers (d3d9.dll is a static import). A tweaker can also be changed at run time by name through the console executor's
  tweak stage (`console_exec_string` 0x106c370 -> tweaks 0x106c980, `proxy/runs/20261029_j15re/README.md`): a route without an exe write
  that needs the console path. Tweaker layout and all 802 defaults: fact `napoleon.tweakers.table`, `harness/runs/20261101_j9pc/tweakers.tsv`.
- Graphics options: `*[0x182eb14]`; setter index i stores at +0x69c84 + 4i and +0x69cfc + 4i; index 1 texture quality, 7 shadow
  quality, 8 tree quality, 9 grass quality (fact `napoleon.exe.options_object`).
- Captures: the 512 or 1024 A8R8G8B8 cube at stage 0 of most draws is the environment cube (it follows texture quality 3), not the
  imposter atlas; `harness/runs/20261101_j9pc/capsum.py` and the imported summaries in `harness/runs/20261101_j9pc/captures/`.
