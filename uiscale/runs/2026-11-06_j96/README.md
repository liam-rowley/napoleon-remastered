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
| `load` | 1080p | `zz_j96_load` | The loading-screen DXT files are on that screen, but the markers did not reach it (corrected in review) |
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

Limit: the other five affected files stay unproven. `load` gave all seven DXT files of `ui\frontend ui\loadingscreen` their own colour, six at aligned sizes and the heading at 1154x382, and none showed (`raw/evidence/load_land_markers_absent.jpg`). Corrected in review (J96 round 1): the art is on that screen, because the plaque, the blue and red boxes and the bar in the shot are these vanilla files, whose only copy in any pack is `boot.pack` (header type 0). `raw/load/proxy.log` indexes the pack (87002 entries against 86995 with no pack, so all seven), yet the engine drew vanilla: a movie-pack entry did not replace them. Why is not proven. The 82 flags' `large.dds` at 1282x642 were not seen in any shot. Fact `napoleon.ui_art.dxt_target_multiple_of_4`.

## Probe 3: 4800 px loading pictures: drawn
`art2`: all 23 of J51's 4800 px outputs with a magenta band at every mip. The band fills the screen in the land load and the campaign load (`raw/evidence/art2_load_land_4800.jpg`, `art2_load_camp_4800.jpg`), with no crash. A shot through the watcher takes about 3 s and missed the load in `art`; `grab.ps1` caught it. At 1920x1080 only. Fact `napoleon.ui_art.loading_screen_4800px`.

## Probe 4: templates by a pack entry: refused
Marker 1 (`r1`, `r2`): every `data\UI\*.tga` path in the file renamed, at the same length, to a file only the pack holds. No magenta on either route though the redirect hit, so it decides nothing: this is why the control launch exists.
Marker 2 (`t1`, `t2`): J67's 2x templates file on vanilla layouts, field army selected. Route 2 (`proxy.log`: 1 redirect hit) draws the Army and Recruitment tabs at about twice their size; route 1 leaves them vanilla (`raw/evidence/t2_route2_camp_field.jpg`, `t1_route1_camp_field.jpg`). The pack was there: `raw/t1/proxy.log` indexes 12 packs and 86996 entries, `raw/t2/proxy.log` 11 and 86995. Fact `napoleon.ui.templates_route`.

## Probe 5: fonts per context: partly read
`font`, 3840x2160, J67's `ui_scale_2x.pack` and `ui_scale_2x_fonts.pack` plus `zz_j96_fonts`: frontend_24 x0.6, frontend_38 x0.8, ingame_18 x1.3, ingame_24 x0.7, ingame_b_24 x1.5 of the J66 size. Crops against J67's shots: `raw/evidence/font_crops.jpg` (`font_crops.py`).

| Text | Context | Against J67 | Reading |
|---|---|---|---|
| New content box body | front end | larger, wider pitch | `ingame_18` |
| Advisor body | battle, campaign | larger, wider pitch | `ingame_18` |
| Unit-card counts | battle | about 0.67 | `ingame_24` by family; `frontend_24` not excluded |
| Date, treasury | campaign | about 0.67 | the same |
| Menu buttons, panel and advisor titles, Start Battle | all | unchanged | not read |

The bold candidate was no test: the recipe fits `ingame_b_24` to the vanilla width, em 21.67 at x1.5 against 21.63 at x1.0. Unchanged text may be that slot or a file outside the five. No slot was seen wrong, no tiny fallback. Fact `napoleon.ui.font_slots_2x`.
This cell went through `pc_deploy install` and `install_packs.ps1`, not `play.py`: see End state.

## End state
Kit and packs out, lock released, `profile_active` null, no `zz_j96` or `ui_scale` pack in `data\`. `snap_end` against `snap_after_j32`: identical. `snap_end` against `snap_start`: one file, `napoleon_remastered.ini` added.
That ini is not this job's: `pc_deploy uninstall` ended at 1564 files, identical, before J32's sitting; afterwards it was there, dated 09:19 UTC, with no proxy installed, and the watcher had just restored J32's profile (09:37:21). It is the race J67 reported. It was left as found.

## Crashes
Two first-launch deaths, `20261106T090629Z-p23456` and `20261106T090810Z-p25364`, both `c0000374` with last status `starting DllMain`, before any pack is read; `ctl` relaunched each and the scene passed (`raw/load`, `raw/r1` `ctl_scene_land_small.json`). The known `napoleon.proxy.init_heap_corruption`, with different packs each time. No hang. `ui_cache` stayed empty after every launch.
