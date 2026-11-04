# Run report 2026-10-31: UI art packs load in game (J50)

Session `0afa23ee-dbcb-40f4-a69e-7a223f2f7a65`, branch `job/J50`. PC: Windows 11, RTX 4090, watcher 1.1.0, headless 1920x1080 on the virtual
display, game lock `J50` from 16:47:55 to 17:05:49 UTC. Every launch through `harness/core/ctl.py` (`scene`, `shot`) with the adapter's
`ctl.launch.keys` (dev.skip_intro=1 among them). Raw results and shots: `raw/` (`<probe>_<scene>.json|jpg`). Scripts used for the probes,
kept as evidence: `build_probes.py` (scratch packs), `probe_run.sh` (the per-probe sequence), `crops.py` (the crop sheet).

## a) Game folder and proxy
- Start: J22's kit `kit_20261031T144321Z_13d00a1d4302` was still installed (the brief expected no proxy); its ini carried J44's ctl keys.
  `pc_deploy uninstall`: identical to its pre-install snapshot (1564 files). `pc_deploy snapshot` -> `_scratch\j50\snap_start.json`, `diff`
  against J36's post-uninstall `upscale\snap_after.json`: **identical** (no stray file).
- Kit `kit_20261031T164614Z_f6850d9fe914` (`pc_deploy kit --dll`, the build `41cde4716ac7` DLL, sha256 `b1ff76a0b7f6...`, the same id
  `proxy/tools/build_id.py` gives this branch), `send` (38 files sha-checked), `install` (sha-checked, exe vanilla).

## b) Stage 1: the four J36 packs, no crash
`upscale/pc/install_packs.ps1` (new, the J36 flow) through job `J50-20261031T164812Z-1327310857`: `ui_art_2x5_{ui_art,icon,panel_frame,button_state}.pack`
(709 MB) into `data\`, sha256 of source = `.pack.json` manifest = copy for all four.

| step | result | evidence |
|---|---|---|
| `scene land_small` | ok, battle_deploy, load 4.2 s; **first launch died** (below), `ctl` retried, pid 32720 | `raw/s1_land_scene.json`, `s1_land.jpg` |
| `reset frontend` + shot | ok (main menu) | `raw/s1_reset_frontend.json`, `s1_frontend.jpg` |
| `scene campaign_start` | ok, campaign | `raw/s1_campaign_scene.json`, `s1_campaign.jpg` |
| repeat `scene land_small` | ok on the first launch, pid 28788, no dump | `raw/s1b_land_scene.json` |

The crash: launch `20261031T164846Z-p33332`, first-chance `0xc0000374` (heap corruption) at `ntdll.dll+0xfd71f`, 156 ms after process start and
33 ms after the proxy's `init done`, before the first d3d9 call and before the engine reads any data pack (`raw` has the scene JSON with
`retried_after`; dump `napoleon_remastered\dumps\20261031T164846Z-p33332_c0000374.dmp`, moved to `_to_delete` by the uninstall). J44 saw the same
at init with no UI packs at all. The repeat run was clean, so per the kill criterion it is not the packs' crash: fact `napoleon.proxy.init_heap_corruption` (open).
WER: one report in the J50 window, `AppCrash_Napoleon.exe_39553a96...` at 16:48:49 (that launch); the same bucket hash has a report at 12:17 the same day,
during J45's run with no UI packs. Watcher hang folder: none since 2026-10-29. Every shot shows the vanilla UI (the `ui_art_2x5\` entries replace nothing).

## c) Stage 2: read proof, real outputs, DDS at a TGA path
Packs out (job `J50-20261031T165613Z-1751523609`), then one scratch pack set per launch, built by `build_probes.py` with `upscale/core/pack.py`
(movie type 4, vanilla paths, under `_scratch\j50\packs`, never committed), in and out by `install_packs.ps1` jobs. Each probe: battle, main
menu, campaign, shot each, kill, pack out.

| probe | pack (entries) | what was put where | front end | campaign | battle |
|---|---|---|---|---|---|
| s2r (control) | none | vanilla | vanilla | vanilla | vanilla |
| s2m marker | `zz_j50_marker` (37) | magenta `simple_button_center_up` (front end, common), green `button_end_turn_*`, cyan `battle ui\skins\button_*_unselected` | no change | **end-turn button green** | no change |
| s2m2 marker | `zz_j50_marker2` (796) | every TGA in `ui\frontend ui\skins` magenta, `ui\battle ui\buttons` cyan | **logo and Steam button magenta** | n/a | no change |
| s2r3 real + marker | `zz_j50_real` (4) + `zz_j50_marker3` (752) | J36 outputs at the vanilla paths of `logo`, `button_steam_store`, `button_end_turn_active`, `_unselect`; every TGA in `ui\battle ui\skins` cyan | logo, Steam button: same place and size | end turn: same place and size | **whole battle HUD cyan** |
| s2d DDS | `zz_j50_dds` (2) | DXT5 DDS with full mips (orange) at `logo.tga` (500x153, 9 levels) and `button_steam_store.tga` (148x24, 8 levels) | **logo blank**, Steam button vanilla | n/a | n/a |

Verdicts:
- **Read proof: yes in all three scenes.** A movie pack's entry at a vanilla UI art path wins over `data.pack` (fact `napoleon.ui_art.movie_pack_overrides`;
  related `napoleon.packs.dev_pack_precedence`). Some guessed files are not what the screen draws (the red menu buttons are not
  `simple_button_center_up`; the battle bar is not `ui\battle ui\buttons`).
- **Real 2.5x outputs:** drawn into the vanilla rect, layout unchanged, no crash (`napoleon.ui_art.hires_same_rect`). Not visibly sharper at 1080p:
  `real_vs_vanilla_crops.jpg` (vanilla run s2r left, s2r3 right) gives mean abs diffs of 4.6 (logo) and 5.0 (end turn) against 3.3 on an untouched
  menu button (the control); the sharper art pays off only once a UI host draws it at a scale above 1. No layout finding for the UI host jobs.
- **DDS at a TGA path: no** (`napoleon.ui_art.dds_at_tga_paths` refuted): the logo is not drawn at all; no crash and no log line (the proxy has no
  texture hook). The Steam button stayed vanilla, which says nothing: s2m2 tinted all eight of its state files and the one on screen may be another.
  J36's TGA outputs stay TGA.
- No launch in stage 2 crashed (no new dump, `probe_run.sh` lists the dumps folder after each).

## d) Uninstall
Lock released 17:05:49; the watcher restored the `headless` profile byte for byte (prefs, keys, battle prefs: 0 mismatches) and the virtual display mode.
`pc_deploy uninstall`: identical to the pre-install snapshot (1564 files), exe vanilla. `snap_end.json` against `snap_start.json`: **identical**.
`save_games`: newest file 2026-10-29T20:32:30, untouched. Packs moved, never deleted: `watcher\_to_delete\J50_*`.
