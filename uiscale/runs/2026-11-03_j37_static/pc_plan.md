# J37 PC plan (for the later PC slot)

Written at the end of the desk phase (run 2026-11-03_j37_static, branch `job/J37`). It follows `jobs/J37/brief.md` "PC test" and the watcher rules in `CLAUDE.md`:
- headless;
- lock owner `J37`;
- the watcher is the only launcher;
- no exe patch;
- no git in a game folder.

The call estimates count tool calls. The PC part totals about **46 calls**, under the brief's cap of about 50. The desk wrap-up after it is about 8 more.

## What the PC slot must answer (from the static RE)
1. **The clamp:** is `font\frontend_32.cuf` opened for `Frontend 38`, and is `font\frontend_38.cuf` never opened? This is fact `napoleon.fonts.getfont_rule`, open. If it holds, J66's 2x pack drew every `Frontend 38` text with the vanilla `frontend_32` face, and this job's `frontend_32.cuf` alias fixes that.
2. **Frontend 22:** in which contexts is `font\frontend_22.cuf` opened, and what on screen is drawn with it? The candidates are the front-end version string and the ribbon text on the campaign map.
3. **The loading quote:** which of `frontend_20` .. `frontend_10` does the fit loop open last at 1080p and at 4K? Last means the one it keeps. The answer settles whether the box follows the screen (fact `napoleon.fonts.loading_quote`, open).
4. **Subtitles and other text:** does any `font\*.cuf` outside the list and the fixed sites get opened in any scene?
5. **Crispness and size:** take the crop pair (vanilla 4K against 2x at 4K) for each engine-text item, with the measured cap height in pixels.

## Steps

| # | step | how | calls |
|---|---|---|---|
| 0 | Preflight | `git pull` on `job/J37`. `python3 core/wsc.py setup` (watcher, lock free, exe vanilla). Check that the profile and display give 1920x1080 and 3840x2160 (J66 ran 4K, J53 ran 1080p) | 2 |
| 1 | Build | `python3 core/wsc.py uiscale build`: the full build, with the art cached, so `ui_scale_2x.pack` is kept. Never use `--no-art` here: it rewrites `ui_scale_2x.pack` without the art. The fonts pack gains `frontend_10`..`frontend_22` at 2x and `frontend_32` (the alias). Then `python3 core/wsc.py uiscale check-fonts` must say `ok`; the expected note is `frontend_38.cuf ... never opens`. Record the fonts pack sha256 | 2 |
| 2 | Start state | snapshot the game folder against `post_uninstall_*` (J66's last), build the kit, send the proxy (J66 steps a) | 3 |
| 3 | Vanilla 1080p | One watcher scene script per launch, J10's `sit*.sh` shape. It turns on the file survey (J9) for `font\` opens, then visits the scenes below and takes a shot of each. WER and the dumps folder are checked after each launch inside the same script | 4 |
| 4 | Vanilla 4K | the same script at 3840x2160 | 4 |
| 5 | Install | `python3 upscale/pc/play.py install --scale 2`, then `status` (templates sha, packs in) | 2 |
| 6 | 2x at 4K | the same script at 3840x2160 | 4 |
| 7 | Out | `play.py uninstall` (must end `identical`), `pc_deploy uninstall`, an end snapshot identical to step 2, the lock released | 3 |
| 8 | Fetch | fetch the shots and survey logs into `uiscale/runs/<date>_j37pc/raw/` (JPG, about 3 MB in all, 1280 px per `shot.sh` plus full-size crops) | 2 |
| 9 | Measure | host script (Pillow): a crop pair per item and the cap height in pixels, saved into the run folder; load time against J66's 3.0 s / 3.8 s | 3 |
| 10 | Buffer | one honest repair or a retry of one launch (the known `napoleon.proxy.init_heap_corruption`), per the brief's kill criteria | 17 |

**Scenes for each launch** (steps 3, 4 and 6):
- Front-end main menu, once. It shows the version string (candidate `frontend_22`) and the `Frontend 38` titles on a page that has them, such as the single-player page.
- `land_small`, poses `deploy` and `turned`: banners and flags. They are art only (`napoleon.fonts.banner_text`); the shot shows that nothing is text.
- `naval_small` pose `deploy`, and `siege_small` pose `deploy`.
- `campaign_start` default view, after the harness's own settle: settlement labels (`city_info_bar`, `covered_by_j66`) and any ribbon text.

That makes four launches per resolution if each scenario needs its own launch. The scene scripts reuse J10's `harness/runs/20261102_j10pc` sequence, so the estimate assumes one call per launch.

## The survey readout (desk, step 9)
- Per context (front end, campaign, battle), list every `font\*.cuf` opened, with and without the packs.
- Expected from the static model (`uiscale/napoleon/font_slots.json`):
  - the 19 list files at UI start, with `frontend_32` for `Frontend 38`;
  - `frontend_22` from the two fixed callers;
  - the quote files only while a loading screen is up;
  - `console_12`, `frontend_12` and `frontend_16` only if the console is built.
- Anything else is a new fact, for example a subtitle font. A file that is expected but not opened refutes the model: fix `font_slots.json` and rerun `engine-text`.

## Facts to write with the run id
These are the brief's ids:
- `napoleon.fonts.engine_text_slots`: item to file, per context.
- `napoleon.fonts.banner_text`: confirm it, with the shots.
- `napoleon.fonts.loading_quote`: the file kept at 1080p and at 4K.
- `napoleon.fonts.subtitles`: the font, or `static_only` with the reason (no movie with subtitles in the library).
- `napoleon.fonts.factor_follows_install`.
- `napoleon.fonts.licence`: Lora OFL-1.1, checked 2026-11-03 (`font_licences.json`).

Set `napoleon.fonts.getfont_rule` to verified or refuted.

## Not shot (static_only)
- **Loading-screen quote:** no scenario in the library holds a loading screen for the shot verbs. It is proved by the survey (which file the loop keeps).
- **Subtitles:** no movie with subtitles in the library. They wait for the Liam-present sitting before release (brief open question 5).
- **Credits:** they stop the front-end pump.
