# J9 PC run 20261101_j9pc: engine-site proofs, API surface probes, case coverage

PC (RTX 4090, Windows 11), watcher 1.2.0, 2026-11-01 15:50 to 17:12 UTC, game lock `j9`, session `4127895c-6413-43ca-81ff-480348089c8a`.
Every launch through `ctl.py scene` (adapter `ctl.launch.keys`: fixed sky, DXVK, headless 1920x1080) plus `dev.capture=1`, driven by
`proof.sh` (this folder; one launch per call: keys with `pc_deploy.py set` after the previous launch's profile restore, lock, optional
watcher profile, scene, a 1-frame capture per pose, shot, perf, kill, the proxy log copied to `raw/j9_<tag>_proxy.log`). Prefs: the
PC's as the acceptance baseline has them (`gfx_texture_quality 2`, `gfx_unit_quality 2`, `gfx_shadow_quality 3`, `gfx_tree_quality 2`,
`gfx_grass_quality 3`) unless a profile is named. Proof keys `gfx.*_proof` (all default and release off).

Builds: 286b3fa123e4 (kit `kit_20261101T162204Z_1e7d97d4f24c`, 37 sites) for chain 4; d3196b3a8424 (`kit_20261101T165736Z_08fdb0e85596`,
46 sites incl. the J28 hook rows) for the far-pose naval pair; 46f52d356ce8 (`kit_20261101T170343Z_6f201de1f8b2`, 45 sites: the mast row
removed) for the case-coverage launches and the 20 passes (run `20261101_j9acc`). The proven rows are byte-identical in all three.

## Files
- `raw/`: ctl results, shots (`j9_<tag>_*.jpg`), proxy logs, the driver logs `proofs4.log` .. `proofs6.log`; `raw/chain1..3/` the
  discarded attempts (below), kept as the evidence for the two harness facts.
- `captures/<name>.json`: the committed summary of each capture (`discovery/core/shader_catalog.py import`), with the raw file's sha256;
  the raw `frame.txt` files stay in `C:\napoleon_remastered_pc\captures\j9c_*`, `j9d_*`, `j9e_*`.
- `summaries/sum_<tag>.txt`: `capsum.py` (this folder) on each raw capture: draws and primitives per fx technique, render targets,
  draws per target, `shadow_map_farz` and `shadow_map_texture_size`.
- `tweakers.tsv`: all 802 tweaker initialisers (name, ctor, object, default, the default immediate's RVA): `re/tweak_table.py`.
- `j28_candidates.md`, `re/`: the static RE notes and scripts (J28's functions; the Lua bindings and their argument counts).

## Proofs (one line per proof; pose = the land_small or naval_small deploy pose unless named)
| key / profile | launch (stock -> on) | result |
|---|---|---|
| `gfx.shadow_proof` | 20261101T162338Z-p15020 -> 20261101T162527Z-p37428 | shadow map 2048 R16F -> 4096 R16F (depth buffer too), `shadow_map_texture_size` 2048 -> 4096, farz 250.5 -> 473.3, caster draws 48 -> 53 |
| `gfx.grass_proof` (same launch) | idem | grass 97 draws / 117,958 prims -> 213 / 260,694 |
| `gfx.shadow_sweep_proof` | -> 20261101T162647Z-p39568 | caster draws 48 -> 53, farz unchanged 250.5 |
| `gfx.sprite_page_proof` | -> 20261101T162758Z-p40108 | imposter atlas (stage 2 of imposter.fx, dynamic DXT1) 2048 -> 4096; scene load 4.2 -> 4.0 s |
| `gfx.unit_lod_proof` | -> 20261101T162923Z-p27880 | imposter_sm3 draws 8 -> 0, shadow-pass draws 48 -> 90 (units stay meshes) |
| `gfx.tree_lod_proof` | -> 20261101T163039Z-p38772 | vegetation branch / frond draws 6 / 6 -> 9 / 10 (prims 860 / 1,146 -> 1,196 / 2,030) |
| `gfx.ship_lod_proof` | 20261101T163629Z-p7468 -> 20261101T163755Z-p40040 | rope.fx 0 -> 7 draws (12,104 prims; shaders new to the catalogue), textured_rigid 180 -> 4,444 prims |
| `gfx.ship_lod_proof`, cam 400 / 800 m back | 20261101T165804Z-p34820 -> 20261101T165946Z-p34980 | 400 m: rope.fx 0 -> 7 draws, textured_rigid 92 -> 2,208 prims; 800 m: no change; navalship / navalsail identical at every pose (no mast effect: row removed) |
| profiles `j9-uq3`, `j9-tq3`, `j9-uq0` (stock) | 20261101T163208Z-p26912, 163344Z-p31448, 163507Z-p28396 | atlas 2048 in all three (unit quality is not the route); texture quality 3 doubles the environment cube 512 -> 1024 and terrain textures |
| `j9-mixa` (texture 0, tree 1, grass 4), sprite + tree + grass keys | 20261101T170419Z-p18280 -> 170540Z-p37256 | atlas 1024 -> 4096; branch / frond 5 / 5 -> 8 / 9; grass 97 / 154,074 -> 213 / 340,400 |
| `j9-mixb` (texture 1, tree 3) | 20261101T170704Z-p35108 -> 170827Z-p32020 | atlas 2048 -> 4096; branch / frond 6 / 6 -> 9 / 10 |
| `j9-mixc` (texture 3, tree 4) | 20261101T170947Z-p25816 -> 171109Z-p39900 | atlas 2048 -> 4096; branch / frond 6 / 6 -> 9 / 10 |
Every launch's start-up check: all sites ok, 0 bad (37 / 46 / 45 by build); hooks verified 17 (11 earlier rows + the 6 guard rows) on
286b3fa123e4, 26 (+ the 9 J28 rows) on d3196b3a8424 and 46f52d356ce8. Key-on launches wrote exactly their family's sites.

## API surface probes (`proxy/napoleon/lua/probes/api_surface.lua`)
| state | launch | names |
|---|---|---|
| front end (main menu) | 20261101T162452Z-p5592 | 720 |
| land (deploy) | 20261101T162338Z-p15020 | 1,784 |
| naval | 20261101T163629Z-p7468 | 1,788 |
| siege | 20261101T163909Z-p30564 | 1,784 |
| campaign, nothing selected / a character selected | 20261101T164037Z-p34068 | 3,435 / 3,751 |
Table: `discovery/napoleon/engine_api.json` (`discovery/core/engine_api.py build --run harness/runs/20261101_j9pc`). The land launch's log
holds a second probe block (16:23:46, 721 names, front-end context): a stale request from the killed chain 3, dropped by the generator
(`dropped_blocks`; fact `napoleon.harness.stale_ctl_request`).

## Discarded attempts
- Idle check before the proofs: run `20261101_j9idle`, one acceptance pass on 1088ccb1016a with every new key off: pass.
- Chain 1 (15:57 to 16:06): every key-on launch logged its keys at 0: the previous launch's deferred profile restore overwrote the
  ini after `pc_deploy set` (fact `napoleon.harness.profile_restore_race`); its stock captures matched chain 4. The probe then walked
  only the script environment (fixed: it follows the environment's `__index` chain and `_G`).
- Chain 2 (16:06 to 16:14): capture names reused (names are never reused); stopped.
- Chain 3 (16:15): a child process of the stopped chain 2 sent kill and unlock to its first launch; stopped and killed.
