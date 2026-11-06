# J96 PC run 2026-11-06_j96

Session `685b4182-f0e0-46ca-9fb2-32e135a940ef`, branch `job/J96`, lock owner `j96` (the watcher's owner rule is lower case), watcher 1.4.0, headless on the virtual display.
Kit `kit_20261105T191805Z_86900aa937bf`, J67's: its `d3d9.dll` has sha `0f8209c5647f`, J67's record for build `a005f6cccc17`, which `build_id.py` gives this branch. No kit is named after the DLL build, and the newest kit was another job's.
Scripts: `build_probes.py` (scratch packs under `<state>\_scratch\j96\packs`, never committed), `sit.sh` (one sitting), `grab.ps1` (read-only frames at about 4 a second), `classify.py` (reads probe 1). Picked evidence: `raw/evidence/`.
Display: `foreign_windows.ps1 -X 3839 -Y 2160` watched the virtual display from 08:55 UTC: only Explorer's desktop and taskbar (`raw/evidence/foreign_windows.log`).

## Cells
| Cell | Size | Packs | What it showed |
|---|---|---|---|
| `art` | 1080p | `zz_j96_art` | Unreadable alone: no in-pack control, no load caught. Superseded by `art2`. |
| `art2` | 1080p | `zz_j96_art` + TGA controls | Probes 1 and 3 |
| `load` | 1080p | `zz_j96_load` | The loading-screen DXT files are not on that screen |
| `r1` | 1080p | `zz_j96_tpl_r1`, `zz_j96_pics` | Probe 2; first template marker: no marker |
| `r2` | 1080p | `zz_j96_tpl_tex`, `dev.file_rules` | First template marker failed its control |
| `t1` | 1080p | `zz_j96_tpl2x_r1` | Route 1: vanilla tabs |
| `t2` | 1080p | none, `dev.file_rules` | Route 2: 2x tabs |

An earlier sitting attempt ran with no lock or kit, because the call that takes them was refused; every scene refused cleanly and the pack came back out. Its results were overwritten by `art`.

## Probe 1: DXT5 at a 4-aligned TGA path: not drawn
`art2`: 376 DXT5 files, vanilla size, both sides multiples of 4, full mips, solid orange. In the same pack, 393 TGA controls on paths J50 saw drawn: the magenta logo, the green end-turn disc and the cyan battle HUD all draw, so the pack was read.
- **Steam button** (`button_steam_store*.tga`, 148x24, all 9 state files): the gold art is gone and the text stays. `raw/evidence/steam_vanilla_tga_dxt5.png`, left to right: vanilla (J50 `s2r`), TGA magenta (J50 `s2m2`), DXT5 (here).
- **Battle HUD**, against J50's all-cyan `s2r3_land.jpg`: of 86437 pixels those files draw, 39.1 % control cyan, 0 orange, 29.5 % unchanged from vanilla, 31.3 % other, mainly the Start Battle panel, the minimap border and the flag discs (`raw/evidence/classify_land.png`, red). Orange anywhere in the shot: 7 pixels.

J50's confound is gone: blank at 500x153 and at 148x24. `napoleon.ui_art.dds_at_tga_paths` stays refuted.

## Probe 2: DXT off the 4 grid: draws
`r1`: every DXT loading picture solid in its own colour at 4802x3002, full mips (`raw/evidence/pics_colours.txt`).
- `land_small` load: solid `0x8010` = `default_landbattle.dds`, DXT5 (`raw/evidence/r1_load_land_4802x3002_dxt5.jpg`).
- `campaign_start` load: solid `0x001f` = `6.dds`, DXT1 (`raw/evidence/r1_load_camp_4802x3002_dxt1.jpg`).

Limit: the other five affected files stay unproven. `load` gave all seven DXT files of `ui\frontend ui\loadingscreen` their own colour, six at aligned sizes and the heading at 1154x382, and none showed (`raw/evidence/load_land_markers_absent.jpg`), so they are not on that screen. The 82 flags' `large.dds` at 1282x642 were not seen in any shot. Fact `napoleon.ui_art.dxt_target_multiple_of_4`.

## Probe 3: 4800 px loading pictures: drawn
`art2`: all 23 of J51's 4800 px outputs with a magenta band at every mip. The band fills the screen in the land load and the campaign load (`raw/evidence/art2_load_land_4800.jpg`, `art2_load_camp_4800.jpg`), with no crash. A shot through the watcher takes about 3 s and missed the load in `art`; `grab.ps1` caught it. At 1920x1080 only. Fact `napoleon.ui_art.loading_screen_4800px`.

## Probe 4: templates by a pack entry: refused
Marker 1 (`r1`, `r2`): every `data\UI\*.tga` path in the file renamed, at the same length, to a file only the pack holds. No magenta on either route though the redirect hit, so it decides nothing: this is why the control launch exists.
Marker 2 (`t1`, `t2`): J67's 2x templates file on vanilla layouts, field army selected. Route 2 (`proxy.log`: 1 redirect hit) draws the Army and Recruitment tabs at about twice their size; route 1 leaves them vanilla (`raw/evidence/t2_route2_camp_field.jpg`, `t1_route1_camp_field.jpg`). Fact `napoleon.ui.templates_route`.

## Crashes
Two first-launch deaths, `20261106T090629Z-p23456` and `20261106T090810Z-p25364`, both `c0000374` with last status `starting DllMain`, before any pack is read; `ctl` relaunched each and the scene passed (`raw/load`, `raw/r1` `ctl_scene_land_small.json`). The known `napoleon.proxy.init_heap_corruption`, with different packs each time. No hang. `ui_cache` stayed empty after every launch.
