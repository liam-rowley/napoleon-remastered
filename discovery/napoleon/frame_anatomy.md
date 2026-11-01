# Napoleon frame anatomy (J8)

The one owner of what Napoleon draws, pass by pass. Source: proxy frame captures (`dev.capture`, `proxy/README.md` "Frame capture") of the
acceptance scenes through `ctl.py scene` (fixed sky, settled), DXVK, 1920x1080, the PC's prefs as the acceptance baseline uses them
(`gfx_hdr`, `gfx_ssao`, `gfx_distortion`, `gfx_depth_of_field`, `gfx_hardware_shadows` false; `gfx_shadow_quality` 3; `gfx_unit_quality` 2).
Verified 2026-11-01, run `harness/runs/20261101_j8pc` (README there: captures, sizes, raw files). Tables between `gen` markers are written by
`python3 discovery/core/shader_catalog.py build` from the committed capture summaries (`harness/runs/*/captures/*.json`); never edit them by
hand. The catalogue is `shader_catalog.json` beside this file; facts `napoleon.render.*`, `napoleon.shadow.*`, `napoleon.shaders.*`.

## The frame, per scene kind
Every 3D scene (battle, naval, campaign) draws the same skeleton; with these prefs there is **no HDR chain, no SSAO,
no depth of field and no depth prepass** (no pass writes depth with colour writes off before the main pass):
1. (naval only) 17 `UpdateSurface` uploads of the sea's dynamic textures, read later by the main pass at s3/s4.
2. **Shadow map** (below): the frame's first draw pass, one block.
3. A full-resolution A8R8G8B8 target cleared and not drawn into on land (1 draw on naval); the main pass samples it at s7 on naval.
4. Two half-resolution A8R8G8B8 passes with the scene depth: water **reflection** and **refraction** (`grid.fx` `grid_reflection_sm3`,
   `grid_refraction_sm3`); the main pass samples both.
5. **Main pass**: A8R8G8B8 + D24S8 at the backbuffer size; terrain, units, vegetation, buildings, sky, sun, water.
6. **Sprites**: inside the engine's own D3DPERF event "Drawing sneaky sprites" (the only event the engine emits; `sprite.fx`).
7. **Composite** to the backbuffer (X8R8G8B8, 6 draws, reading the main target at s0): the scene/UI boundary.
8. **UI** on the backbuffer with a depth surface (clear z+stencil first).

The front end (`f1_frontend`, a fresh launch) runs the same skeleton with nothing in it (the shadow, water and main passes only clear),
then the composite and the UI (27 draws). The campaign adds, after the shadow map, a 2400x1350 A8R8G8B8 overlay target (1.25x the backbuffer, 267 draws, no depth) that the main
pass, the composite and the UI sample at s10, like Empire's political overlay; its shaders are `campaignterrain.fx`, `campaignoverlay.fx`,
`campaigntree.fx` and the like.

## Render targets and the backbuffer
A `land_small` capture at 2560x1440 (`w1440_land_small`) against 1920x1080: **every target but the shadow map scales with the backbuffer**
(the reflection and refraction targets at exactly half); the shadow map's size depends only on `gfx_shadow_quality`. No target is MSAA (`gfx_aa` 0).
<!-- gen:targets -->
| size | format | msaa | texture | size rule | captures |
|---|---|---|---|---|---|
| 2048x2048 | D24X8 | 0 | no | fixed | b_d1000, b_d1400, b_d700, b_deploy, b_near, f1_frontend, q3_land_small, q4_land_small, r1_campaign_after_reset, r1_campaign_start, r1_hist_dresden, r1_hist_nile, r1_land_small, r1_naval_small, r1_siege_small, t1_land_small, w1440_land_small, y_0, y_135, y_180, y_225, y_270, y_315, y_45, y_90 |
| 2048x2048 | R16F | 0 | yes | fixed | b_d1000, b_d1400, b_d700, b_deploy, b_near, f1_frontend, q3_land_small, r1_campaign_after_reset, r1_campaign_start, r1_hist_dresden, r1_hist_nile, r1_land_small, r1_naval_small, r1_siege_small, t1_land_small, w1440_land_small, y_0, y_135, y_180, y_225, y_270, y_315, y_45, y_90 |
| 2048x2048 | R32F | 0 | yes | fixed | q4_land_small |
| 2560x1440 | A8R8G8B8 | 0 | yes | bb | w1440_land_small |
| 2560x1440 | D24S8 | 0 | no | bb | w1440_land_small |
| 2560x1440 | X8R8G8B8 | 0 | no | bb | w1440_land_small |
| 2400x1350 | A8R8G8B8 | 0 | yes | fixed | r1_campaign_after_reset, r1_campaign_start |
| 1920x1080 | A8R8G8B8 | 0 | yes | bb | b_d1000, b_d1400, b_d700, b_deploy, b_near, f1_frontend, q0_land_small, q1_land_small, q2_land_small, q3_land_small, q4_land_small, r1_campaign_after_reset, r1_campaign_start, r1_hist_dresden, r1_hist_nile, r1_land_small, r1_naval_small, r1_siege_small, t1_land_small, y_0, y_135, y_180, y_225, y_270, y_315, y_45, y_90 |
| 1920x1080 | D24S8 | 0 | no | bb | b_d1000, b_d1400, b_d700, b_deploy, b_near, f1_frontend, q0_land_small, q1_land_small, q2_land_small, q3_land_small, q4_land_small, r1_campaign_after_reset, r1_campaign_start, r1_hist_dresden, r1_hist_nile, r1_land_small, r1_naval_small, r1_siege_small, t1_land_small, y_0, y_135, y_180, y_225, y_270, y_315, y_45, y_90 |
| 1920x1080 | X8R8G8B8 | 0 | no | bb | b_d1000, b_d1400, b_d700, b_deploy, b_near, f1_frontend, q0_land_small, q1_land_small, q2_land_small, q3_land_small, q4_land_small, r1_campaign_after_reset, r1_campaign_start, r1_hist_dresden, r1_hist_nile, r1_land_small, r1_naval_small, r1_siege_small, t1_land_small, y_0, y_135, y_180, y_225, y_270, y_315, y_45, y_90 |
| 1024x1024 | D24X8 | 0 | no | fixed | q2_land_small |
| 1024x1024 | R16F | 0 | yes | fixed | q2_land_small |
| 1280x720 | A8R8G8B8 | 0 | yes | bb/2 | w1440_land_small |
| 960x540 | A8R8G8B8 | 0 | yes | bb/2 | b_d1000, b_d1400, b_d700, b_deploy, b_near, f1_frontend, q0_land_small, q1_land_small, q2_land_small, q3_land_small, q4_land_small, r1_campaign_after_reset, r1_campaign_start, r1_hist_dresden, r1_hist_nile, r1_land_small, r1_naval_small, r1_siege_small, t1_land_small, y_0, y_135, y_180, y_225, y_270, y_315, y_45, y_90 |
| 512x512 | D24X8 | 0 | no | fixed | q1_land_small |
| 512x512 | R16F | 0 | yes | fixed | q1_land_small |
<!-- /gen -->

## The shadow pass (J24, J25)
- **Path:** `SOFTWARE_SHADOWS` (the PC has `gfx_hardware_shadows` false): the casters write linear depth into an R16F (R32F at quality 4)
  colour target with a D24X8 depth surface; receivers filter it in the pixel shader (`shadow_map_texture_size` is used). The captured
  receivers reproduce byte for byte only with `SOFTWARE_SHADOWS`, never with `NVIDIA_HARDWARE_SHADOWS` or `ATI_HARDWARE_SHADOWS`.
- **Per quality** (`land_small`, deploy pose; captures `q0..q4_land_small`):

| `gfx_shadow_quality` | map | depth | casters (draws) | farz (m) | frame p50 (ms) |
|---|---|---|---|---|---|
| 0 | none | - | 0 | - | 1.76 |
| 1 | 512 R16F | 512 D24X8 | 36 | 72.3 | 2.04 |
| 2 | 1024 R16F | 1024 D24X8 | 44 | 139.1 | 2.26 |
| 3 | 2048 R16F | 2048 D24X8 | 48 | 250.5 | 2.18 |
| 4 | 2048 R32F | 2048 D24X8 | 54 | 473.3 | 2.35 |

- **Isolable:** in every capture it is the first draw pass and one contiguous block: it begins with `SetRenderTarget(0, <R16F|R32F map>)`,
  `SetDepthStencilSurface(<D24X8>)`, `Clear(target|z, 0xffffffff, 1.0)` and ends at the next `SetRenderTarget`. No D3DPERF event marks it.
- **Registers:** casters' vertex shaders take `shadow_map_projection_matrix` (4 rows) and `linear_z_shadow_map_projection_matrix`; their
  pixel shaders `shadow_map_slope_bias` (c0, 2.301). Receivers' vertex shaders take `shadow_projection_texture_transform_matrix` and
  `linear_z_shadow_projection_texture_transform_matrix`; their pixel shaders `shadow_map_farz`, `shadow_map_inv_farz`, `shadow_map_far_fade` (5),
  `shadow_map_texture_size` and `shadow_map_texture_sampler` at s0, s1 or s2. Registers differ per shader (table below). The projection's
  w row is not (0,0,0,1): a perspective warp, not an orthographic map.
- **Quality by view direction:** at one camera position (`y_0..y_315`, yaw in 45 degree steps, pitch -25, light direction (0, -0.54, 0.84))
  the shadow texels per metre on the view ray at 20 m are 13.9 side-on to the sun (yaw 90) and 5.1 with the sun behind the camera (yaw 0),
  2.5 at yaw 45; side-on the density falls with distance (13.9, 10.0, 6.4 at 20, 60, 140 m), with the sun behind it is flat (5.1, 5.1, 5.0):
  the warp degenerates when view and light line up, and farz (250.5) does not change. Yaw 45 and 315 (same sun angle) differ 3.6x, so the
  fit also depends on the scene (a caster crop, as on Empire). The code that computes the warp and crop is J9's to find. These poses look at
  open ground, so their shots do not show the drop; poses with casters near the camera are J24's.
- **Unit shadows by LOD:** close up every soldier is a skinned mesh and casts its own shadow (`variantmesh.fx`
  `variant_shadow_map_weighted_stream_instancing_sm3`, 306 draws with the camera at z 330); from the deploy pose (z 446, same line) out,
  units are imposters and cast `imposter.fx` `shadow_imposter_sm3`: the imposter's camera-angle frame on a light-facing quad, shrunk to
  0.96 and alpha-tested, a few texels at about 12 cm per texel (captures `b_near`, `b_deploy`, `b_d700`..`b_d1400`). The switch distance
  is an engine setting (J9).

## Captures
<!-- gen:captures -->
| capture | scene | draws | passes | backbuffer | shaders | events |
|---|---|---|---|---|---|---|
| 20261101_j8pc/b_d1000 | battle_deploy | 601 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/b_d1400 | battle_deploy | 593 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/b_d700 | battle_deploy | 608 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/b_deploy | battle_deploy | 674 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/b_near | battle_deploy | 1282 | 8 | 1920x1080 | 80 | 1 |
| 20261101_j8pc/f1_frontend | frontend | 33 | 6 | 1920x1080 | 16 | 1 |
| 20261101_j8pc/q0_land_small | battle_deploy | 626 | 7 | 1920x1080 | 66 | 1 |
| 20261101_j8pc/q1_land_small | battle_deploy | 660 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/q2_land_small | battle_deploy | 670 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/q3_land_small | battle_deploy | 673 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/q4_land_small | battle_deploy | 680 | 8 | 1920x1080 | 84 | 1 |
| 20261101_j8pc/r1_campaign_after_reset | campaign | 175 | 7 | 1920x1080 | 35 | 1 |
| 20261101_j8pc/r1_campaign_start | campaign | 1084 | 7 | 1920x1080 | 58 | 1 |
| 20261101_j8pc/r1_hist_dresden | battle | 1446 | 8 | 1920x1080 | 86 | 1 |
| 20261101_j8pc/r1_hist_nile | naval | 653 | 8 | 1920x1080 | 59 | 1 |
| 20261101_j8pc/r1_land_small | battle_deploy | 675 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/r1_naval_small | naval | 248 | 8 | 1920x1080 | 56 | 1 |
| 20261101_j8pc/r1_siege_small | battle_deploy | 626 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/t1_land_small | battle_deploy | 675 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/w1440_land_small | battle_deploy | 671 | 8 | 2560x1440 | 83 | 1 |
| 20261101_j8pc/y_0 | battle_deploy | 572 | 7 | 1920x1080 | 64 | 1 |
| 20261101_j8pc/y_135 | battle_deploy | 544 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/y_180 | battle_deploy | 670 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/y_225 | battle_deploy | 642 | 8 | 1920x1080 | 83 | 1 |
| 20261101_j8pc/y_270 | battle_deploy | 691 | 8 | 1920x1080 | 74 | 1 |
| 20261101_j8pc/y_315 | battle_deploy | 587 | 8 | 1920x1080 | 68 | 1 |
| 20261101_j8pc/y_45 | battle_deploy | 503 | 8 | 1920x1080 | 53 | 1 |
| 20261101_j8pc/y_90 | battle_deploy | 532 | 8 | 1920x1080 | 67 | 1 |
<!-- /gen -->

## Passes: land_small (battle)
<!-- gen:passes_r1_land_small -->
| # | render targets | depth | draws | prims | classes (clear) | reads passes | events |
|---|---|---|---|---|---|---|---|
| 0 | rt1 2048x2048 R16F | rt2 2048x2048 D24X8 | 49 | 12478 | navalship 18, vegetation 18, sprite 9 (clear 3) |  |  |
| 1 | rt3 1920x1080 A8R8G8B8 | - | 0 | 0 |  (clear 1) |  |  |
| 2 | rt4 960x540 A8R8G8B8 | rt5 1920x1080 D24S8 | 75 | 141630 | grid 68, vegetation 5, sky 2 (clear 3) | 0 |  |
| 3 | rt6 960x540 A8R8G8B8 | rt5 1920x1080 D24S8 | 7 | 7416 | cloth 4, grid 3 (clear 3) | 0 |  |
| 4 | rt7 1920x1080 A8R8G8B8 | rt8 1920x1080 D24S8 | 454 | 321360 | vegetation 342, grid 69, unit 12 (clear 7) | 0,2,3 |  |
| 5 | rt7 1920x1080 A8R8G8B8 | rt8 1920x1080 D24S8 | 19 | 110 | sprite 19 |  | Drawing sneaky sprites |
| 6 | rt9 1920x1080 X8R8G8B8 bb | - | 6 | 12 | post 6 | 5 |  |
| 7 | rt9 1920x1080 X8R8G8B8 bb | rt5 1920x1080 D24S8 | 65 | 822 | sprite 65 (clear 6) |  |  |
<!-- /gen -->

## Passes: naval_small
<!-- gen:passes_r1_naval_small -->
| # | render targets | depth | draws | prims | classes (clear) | reads passes | events |
|---|---|---|---|---|---|---|---|
| 0 | updsurf | rt1 -> rt2 |  |  |  |  |  |
| 1 | updsurf | rt3 -> rt4 |  |  |  |  |  |
| 2 | updsurf | rt5 -> rt6 |  |  |  |  |  |
| 3 | updsurf | rt7 -> rt8 |  |  |  |  |  |
| 4 | updsurf | rt9 -> rt10 |  |  |  |  |  |
| 5 | updsurf | rt11 -> rt12 |  |  |  |  |  |
| 6 | updsurf | rt13 -> rt14 |  |  |  |  |  |
| 7 | updsurf | rt15 -> rt16 |  |  |  |  |  |
| 8 | updsurf | rt17 -> rt18 |  |  |  |  |  |
| 9 | updsurf | rt19 -> rt20 |  |  |  |  |  |
| 10 | updsurf | rt21 -> rt22 |  |  |  |  |  |
| 11 | updsurf | rt23 -> rt24 |  |  |  |  |  |
| 12 | updsurf | rt25 -> rt26 |  |  |  |  |  |
| 13 | updsurf | rt27 -> rt28 |  |  |  |  |  |
| 14 | updsurf | rt29 -> rt30 |  |  |  |  |  |
| 15 | updsurf | rt31 -> rt32 |  |  |  |  |  |
| 16 | updsurf | rt33 -> rt34 |  |  |  |  |  |
| 17 | rt35 2048x2048 R16F | rt36 2048x2048 D24X8 | 39 | 26608 | navalship 24, icons 6, navalsail 6 (clear 3) |  |  |
| 18 | rt37 1920x1080 A8R8G8B8 | - | 1 | 216 | shipbowwave 1 (clear 1) |  |  |
| 19 | rt38 960x540 A8R8G8B8 | rt39 1920x1080 D24S8 | 55 | 47041 | navalship 44, navalsail 9, sky 2 (clear 3) | 17 |  |
| 20 | rt40 960x540 A8R8G8B8 | rt39 1920x1080 D24S8 | 44 | 33245 | navalship 44 (clear 3) | 17 |  |
| 21 | rt41 1920x1080 A8R8G8B8 | rt42 1920x1080 D24S8 | 74 | 101036 | navalship 47, navalsail 9, grid_spline 6 (clear 7) | 17,18,19,20 |  |
| 22 | rt41 1920x1080 A8R8G8B8 | rt42 1920x1080 D24S8 | 1 | 44 | sprite 1 | 18,19,20 | Drawing sneaky sprites |
| 23 | rt43 1920x1080 X8R8G8B8 bb | - | 6 | 12 | post 6 | 18,19,20,22 |  |
| 24 | rt43 1920x1080 X8R8G8B8 bb | rt39 1920x1080 D24S8 | 28 | 1128 | sprite 26, textured_rigid 2 (clear 6) | 17 |  |
<!-- /gen -->

## Passes: campaign_start
<!-- gen:passes_r1_campaign_start -->
| # | render targets | depth | draws | prims | classes (clear) | reads passes | events |
|---|---|---|---|---|---|---|---|
| 0 | rt1 2048x2048 R16F | rt2 2048x2048 D24X8 | 142 | 54445 | campaigntree 72, campaignbuilding 38, navalship 32 (clear 3) |  |  |
| 1 | rt3 2400x1350 A8R8G8B8 | - | 267 | 51718 | campaignoverlay 134, supertexturetile 133 (clear 1) |  |  |
| 2 | rt4 960x540 A8R8G8B8 | rt5 1920x1080 D24S8 | 187 | 56876 | campaignflag 111, textured_rigid 34, strengthbar 27 (clear 3) | 0 |  |
| 3 | rt6 960x540 A8R8G8B8 | rt5 1920x1080 D24S8 | 37 | 28896 | textured_rigid 22, unit 10, campaignbuilding 5 (clear 3) | 0 |  |
| 4 | rt7 1920x1080 A8R8G8B8 | rt8 1920x1080 D24S8 | 396 | 448370 | campaignflag 111, supertexturetile 76, campaigntree 67 (clear 7) | 0,1,2 |  |
| 5 | rt9 1920x1080 X8R8G8B8 bb | - | 6 | 12 | post 6 | 1,4 |  |
| 6 | rt9 1920x1080 X8R8G8B8 bb | rt5 1920x1080 D24S8 | 49 | 2598 | sprite 49 (clear 6) | 1 |  |
<!-- /gen -->

## Passes: front end
<!-- gen:passes_f1_frontend -->
| # | render targets | depth | draws | prims | classes (clear) | reads passes | events |
|---|---|---|---|---|---|---|---|
| 0 | rt1 2048x2048 R16F | rt2 2048x2048 D24X8 | 0 | 0 |  (clear 3) |  |  |
| 1 | rt3 960x540 A8R8G8B8 | rt4 1920x1080 D24S8 | 0 | 0 |  (clear 3) |  |  |
| 2 | rt5 960x540 A8R8G8B8 | rt4 1920x1080 D24S8 | 0 | 0 |  (clear 3) |  |  |
| 3 | rt6 1920x1080 A8R8G8B8 | rt7 1920x1080 D24S8 | 0 | 0 |  (clear 7) |  |  |
| 4 | rt8 1920x1080 X8R8G8B8 bb | - | 6 | 12 | post 6 | 3 |  |
| 5 | rt8 1920x1080 X8R8G8B8 bb | rt4 1920x1080 D24S8 | 27 | 824 | sprite 27 (clear 6) |  |  |
<!-- /gen -->

## Matrix and constant registers per shader class
From the CTABs; the uploaded values (first draw per shader) are in each capture summary's `shaders.<hash>.consts`.
<!-- gen:registers -->
| class | constant | registers (stage, range) |
|---|---|---|
| campaignbuilding | camera_position | ps c8, vs c17 |
| campaignbuilding | light_direction | vs c18 |
| campaignbuilding | linear_z_shadow_projection_texture_transform_matrix | vs c8-c10 |
| campaignbuilding | shadow_map_texture_size | ps c12 |
| campaignbuilding | shadow_projection_texture_transform_matrix | vs c4-c7 |
| campaignbuilding | view_projection | vs c0-c3 |
| campaignflag | camera_position | ps c5 |
| campaignflag | view_matrix | vs c11-c14 |
| campaignflag | view_projection | vs c7-c10 |
| campaignflag | world | vs c15-c18 |
| campaignoverlay | view_projection | vs c0-c3 |
| campaignoverlay | world | vs c4-c7 |
| campaignriver | linear_z_shadow_projection_texture_transform_matrix | vs c12-c14 |
| campaignriver | shadow_projection_texture_transform_matrix | vs c4-c7 |
| campaignriver | view_projection | vs c0-c3 |
| campaignriver | world | vs c8-c11 |
| campaignterrain | camera_position | ps c5 |
| campaignterrain | linear_z_shadow_projection_texture_transform_matrix | vs c12-c14, vs c13-c15 |
| campaignterrain | shadow_projection_texture_transform_matrix | vs c4-c7, vs c9-c12 |
| campaignterrain | view_projection | vs c0-c3, vs c5-c8 |
| campaignterrain | world | vs c8-c11 |
| campaigntree | camera_position | ps c8, vs c17 |
| campaigntree | light_direction | vs c19 |
| campaigntree | linear_z_shadow_projection_texture_transform_matrix | vs c8-c10 |
| campaigntree | shadow_map_texture_size | ps c12 |
| campaigntree | shadow_projection_texture_transform_matrix | vs c4-c7 |
| campaigntree | view_projection | vs c0-c3 |
| cloth | camera_position | ps c16, vs c15 |
| cloth | light_direction | ps c17 |
| cloth | linear_z_shadow_projection_texture_transform_matrix | vs c12-c14 |
| cloth | shadow_map_texture_size | ps c21 |
| cloth | shadow_projection_texture_transform_matrix | vs c4-c7 |
| cloth | view_projection | vs c0-c3 |
| cloth | world | vs c8-c11 |
| grid | camera_position | ps c6, ps c8, ps c9, ps c10, ps c11, vs c17, vs c19 |
| grid | light_direction | ps c7, ps c9, ps c10, ps c11, ps c12 |
| grid | linear_z_shadow_projection_texture_transform_matrix | vs c14-c16, vs c16-c18 |
| grid | shadow_map_texture_size | ps c12, ps c17 |
| grid | shadow_projection_texture_transform_matrix | vs c4-c7, vs c10-c13 |
| grid | view_projection | vs c0-c3, vs c6-c9 |
| grid | world | vs c8-c11 |
| grid_spline | camera_position | ps c0, vs c8 |
| grid_spline | view_projection | vs c0-c3 |
| grid_spline | world | vs c4-c7 |
| navalsail | camera_position | ps c16, vs c15 |
| navalsail | light_direction | ps c6, ps c17 |
| navalsail | linear_z_shadow_projection_texture_transform_matrix | vs c12-c14 |
| navalsail | shadow_map_texture_size | ps c22 |
| navalsail | shadow_projection_texture_transform_matrix | vs c4-c7 |
| navalsail | view_projection | vs c0-c3 |
| navalsail | world | vs c8-c11 |
| navalship | camera_position | ps c13, vs c11, vs c115 |
| navalship | light_direction | ps c14 |
| navalship | linear_z_shadow_projection_texture_transform_matrix | vs c8-c10, vs c112-c114 |
| navalship | shadow_map_texture_size | ps c20 |
| navalship | shadow_projection_texture_transform_matrix | vs c4-c7, vs c104-c107 |
| navalship | view_projection | vs c0-c3, vs c100-c103 |
| navalship | world | vs c108-c111 |
| ocean | camera_position | ps c19, vs c11 |
| ocean | g_decal_projection_normal | vs c16 |
| ocean | g_decal_projection_plane | vs c15 |
| ocean | light_direction | ps c20 |
| ocean | linear_z_shadow_projection_texture_transform_matrix | ps c16-c18, vs c8-c10 |
| ocean | shadow_map_texture_size | ps c31 |
| ocean | shadow_projection_texture_transform_matrix | ps c12-c15, vs c4-c7 |
| ocean | view_projection | vs c0-c3 |
| outline | view_projection | vs c0-c3 |
| outline | world | vs c4-c6 |
| particle | camera_position | ps c4, vs c16 |
| particle | light_direction | ps c5 |
| particle | view_matrix | vs c13-c15 |
| particle | view_projection | vs c9-c12 |
| post | colour_matrix | ps c0-c2 |
| post | half_texel_offset | ps c0, ps c1, ps c2, ps c4 |
| post | projection_matrix | vs c0-c3 |
| shadow_caster | animation_matrix_stack | vs c0-c122 |
| shadow_caster | camera_position | vs c34, vs c40 |
| shadow_caster | g_imposter_size | vs c8 |
| shadow_caster | g_wind_matrices | vs c0-c23 |
| shadow_caster | light_direction | vs c35, vs c41, vs c43 |
| shadow_caster | linear_z_shadow_map_projection_matrix | vs c4-c7, vs c17-c20, vs c28-c31, vs c32-c35, vs c36-c39, vs c127-c130 |
| shadow_caster | shadow_map_projection_matrix | vs c0-c3, vs c13-c16, vs c24-c27, vs c28-c31, vs c32-c35, vs c123-c126 |
| shadow_caster | vs20_instance_data | vs c0-c27 |
| shadow_caster | world | vs c8-c10, vs c8-c11 |
| shipbowwave | g_decal_projection_normal | vs c5 |
| shipbowwave | g_decal_projection_plane | vs c4 |
| shipbowwave | view_projection | vs c0-c3 |
| sky | camera_position | ps c0, ps c3, vs c4, vs c6 |
| sky | projection_matrix | vs c4-c7 |
| sky | view_matrix | vs c0-c3 |
| sky | view_projection | vs c0-c3 |
| sky | vs10_instance_data | ps c0-c5 |
| sprite | camera_position | ps c8, ps c10, ps c11, ps c12, vs c17 |
| sprite | g_imposter_size | vs c20 |
| sprite | inv_view_projection | ps c0-c3, ps c6-c9 |
| sprite | light_direction | ps c12, ps c13, vs c18 |
| sprite | linear_z_shadow_projection_texture_transform_matrix | vs c8-c10 |
| sprite | shadow_map_texture_size | ps c19 |
| sprite | shadow_projection_texture_transform_matrix | vs c4-c7 |
| sprite | view_projection | vs c0-c3 |
| strengthbar | camera_position | ps c7, vs c11 |
| strengthbar | view_projection | vs c0-c3 |
| strengthbar | world | vs c4-c7 |
| sun | g_world_view | vs c4-c7 |
| sun | projection_matrix | vs c0-c3 |
| supertexturetile | camera_position | ps c9, ps c15, vs c15, vs c19 |
| supertexturetile | g_decal_projection_normal | vs c24 |
| supertexturetile | g_decal_projection_plane | vs c23 |
| supertexturetile | light_direction | ps c10, ps c16, vs c20 |
| supertexturetile | linear_z_shadow_projection_texture_transform_matrix | vs c12-c14, vs c13-c15 |
| supertexturetile | shadow_map_texture_size | ps c17, ps c21 |
| supertexturetile | shadow_projection_texture_transform_matrix | vs c4-c7, vs c9-c12 |
| supertexturetile | view_projection | vs c0-c3, vs c5-c8 |
| supertexturetile | world | vs c8-c11, vs c16-c18 |
| textured_rigid | camera_position | ps c8, ps c12, ps c13, vs c20 |
| textured_rigid | light_direction | ps c14, ps c15, vs c21 |
| textured_rigid | linear_z_shadow_projection_texture_transform_matrix | vs c8-c10 |
| textured_rigid | screen_size | ps c13, ps c14 |
| textured_rigid | shadow_map_texture_size | ps c12, ps c21 |
| textured_rigid | shadow_projection_texture_transform_matrix | vs c4-c7 |
| textured_rigid | view_projection | vs c0-c3 |
| unit | animation_matrix_stack | vs c0-c122 |
| unit | camera_position | ps c12, ps c13, ps c15, ps c24, ps c25, vs c11, vs c134, vs c140 |
| unit | light_direction | ps c13, ps c14, ps c16, ps c25, ps c26, vs c141 |
| unit | linear_z_shadow_projection_texture_transform_matrix | vs c8-c10, vs c131-c133 |
| unit | shadow_map_texture_size | ps c20, ps c22, ps c32 |
| unit | shadow_projection_texture_transform_matrix | vs c4-c7, vs c127-c130 |
| unit | view_projection | vs c0-c3, vs c123-c126 |
| unmapped | camera_position | ps c6, ps c10, ps c11 |
| unmapped | light_direction | ps c7, ps c11, ps c12 |
| vegetation | camera_position | ps c4, ps c8, ps c10, ps c11, ps c12, vs c9, vs c17, vs c24, vs c43, vs c46, vs c48, vs c51 |
| vegetation | g_wind_matrices | vs c0-c23 |
| vegetation | light_direction | ps c9, ps c11, ps c12, ps c13, vs c44, vs c47, vs c49, vs c52 |
| vegetation | linear_z_shadow_projection_texture_transform_matrix | vs c14-c16, vs c32-c34, vs c39-c41, vs c40-c42 |
| vegetation | shadow_map_texture_size | ps c14, ps c17, ps c18 |
| vegetation | shadow_projection_texture_transform_matrix | vs c10-c13, vs c28-c31, vs c35-c38, vs c36-c39 |
| vegetation | view_projection | vs c0-c3, vs c6-c9, vs c15-c18, vs c24-c27, vs c31-c34, vs c32-c35 |
| water | camera_position | ps c5, vs c11 |
| water | g_decal_projection_normal | vs c13 |
| water | g_decal_projection_plane | vs c12 |
| water | linear_z_shadow_projection_texture_transform_matrix | vs c8-c10 |
| water | shadow_projection_texture_transform_matrix | vs c4-c7 |
| water | view_projection | vs c0-c3 |
| weather | box_size | vs c25 |
| weather | camera_position | vs c23 |
| weather | view_projection | vs c19-c22 |
<!-- /gen -->

## Shader classes
<!-- gen:classes -->
| class | shaders |
|---|---|
| sprite | 21 |
| vegetation | 17 |
| shadow_caster | 16 |
| post | 11 |
| grid | 10 |
| unit | 10 |
| outline | 10 |
| supertexturetile | 8 |
| textured_rigid | 6 |
| sky | 6 |
| navalship | 6 |
| unmapped | 5 |
| navalsail | 5 |
| campaignterrain | 4 |
| campaigntree | 3 |
| campaignbuilding | 3 |
| cloth | 3 |
| grid_spline | 3 |
| campaignoverlay | 2 |
| campaignflag | 2 |
| water | 2 |
| weather | 2 |
| strengthbar | 2 |
| sun | 2 |
| particle | 2 |
| ocean | 2 |
| campaignriver | 2 |
| shipbowwave | 2 |
| icons | 1 |
<!-- /gen -->

## Flagged sources (`napoleon.diff.shaders.j8_flags`)
A file that another source includes counts the mapped shaders of that source: `extendedsprite.fx` is a macro template included by
`sprite.fx` (it does not compile on its own), the fragments are included by most effects. Macro profiles: 386 of the mapped records
reproduce with the base set; 44 `rigid.fx` and `textured_rigid.fx` records (no shadow receiver among them) only with `SOFTWARE_SHADOWS`
undefined, and some effects only with `DEPTH_PRE_PASS` or `ENABLE_SHADOWS` undefined: the engine does not pass every macro to every effect.
5 pixel shaders seen only with shadows off stay unmapped (not even with `ENABLE_SHADOWS` and `SOFTWARE_SHADOWS` both undefined).
<!-- gen:flagged -->
| flagged source | captured shaders mapped |
|---|---|
| sprite.fx | 11 |
| variantmesh.fx | 9 |
| weighted.fx | 9 |
| vegetation_billboard.fx | 6 |
| custom_sprite.fx | 6 |
| extendedsprite.fx | 11 |
| imposter.fx | 5 |
| rigid_imposter.fx_fragment | 12 |
| shadowmap.fx_fragment | 117 |
<!-- /gen -->

## What the capture cannot see
- The system d3d9 backend: with Windows' own d3d9 the hooked device vtables see no `Present` (frame 0 after both devices were hooked),
  and the headless launch never reaches the virtual display; nothing was captured there (open, owner J16).
- State set through state blocks: `CreateStateBlock` (device slot 59) and `IDirect3DStateBlock9::Apply`/`Capture` are not hooked, so a
  block made before the capture (or by `CreateStateBlock`) and applied during it changes render, sampler and texture state and constants
  unseen. No `SBBEGIN` in a capture says only that no block was recorded with Begin/End during it. D3DX effects save and restore state
  through state blocks unless created with `D3DXFX_DONOTSAVESTATE`, so per-draw render/sampler state and textures after an effect's
  `End` may be stale here; render targets, depth surfaces and shader binds inside `BeginPass` are not affected (open: J8 review round 1).
- GPU time per pass: `perf` gives the frame time only.
