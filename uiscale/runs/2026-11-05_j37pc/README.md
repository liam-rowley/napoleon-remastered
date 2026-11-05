# J37 PC run 2026-11-05_j37pc

Session `68bb79d1-9e8b-4ff4-89ea-c70d5a0eb183`, branch `job/J37` (resumed after the desk steps 1-3 of 2026-11-03), lock `j37`, watcher 1.4.0.
Driver `sit.sh <label> <adapter>`: land_small deploy + turned, naval_small deploy, siege_small deploy, front end, campaign_start; scratch adapters (size, `dev.log_files=1`, `frontend` added to the settle scenes).
Kit `kit_20261105T182703Z_ea213e2e71b7` built with the DLL copied from the main checkout (built at id 6e89faf06754; this branch's inputs are a005f6cccc17, because the DLL could not be rebuilt: lua.org unreachable, no mingw). No DLL input is changed by J37.

| cell | launch | packs | result |
|---|---|---|---|
| `raw/v1080` | 1920x1080 | vanilla | all scenes shot; the front-end shot failed to settle (frontend was not a settle scene yet) |
| `raw/v4k` | 3840x2160 | vanilla | all 7 shots; load_s 3.9 (land) |
| `raw/x2_4k` | 3840x2160 | `play.py install --scale 2` (layouts+art pack, fonts pack with frontend_10..22 and the frontend_32 alias, templates redirect) | all 7 shots; load_s 3.7-3.9 (J66: 3.8) |

End state: `play.py uninstall` identical, `pc_deploy uninstall` identical, start and end snapshots byte-identical (1564 files), lock released. No dump folder created.

## Findings
1. **The file survey cannot show `.cuf` opens.** 0 rows with `font` or `cuf` in any of the 9 launch surveys. The planned readout of "which font each context opens" (pc_plan.md steps 3-4, facts `engine_text_slots`, `loading_quote`, `getfont_rule`) is therefore not answerable this way; those stay static (`font_slots.json`). A real answer needs a proxy pack-read log (DLL change: out of this job).
2. **Fonts pack effect, by eye:** at 4K the campaign settlement labels (Paris, Toulouse, Marseille...) are about twice the vanilla size with the 2x set (`raw/x2_4k/campaign.jpg` vs `raw/v4k/campaign.jpg`). J66's report said map labels stayed 1x; this job's added slots change that.
3. Shots are the harness's 1280-wide copies (`shot.sh` downsizes), so no pixel-height measurement at 4K was made.
