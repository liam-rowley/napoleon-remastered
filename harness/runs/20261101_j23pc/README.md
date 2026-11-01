# J23 PC run 20261101_j23pc: the performance baseline matrix

PC: RTX 4090, NVIDIA 617.14, Windows 11. Headless through watcher 1.2.0 (the harness's only mode: the game runs windowed borderless on the
virtual display at the cell size; the guard thread takes the Present lock, J13 review Later 4). DLL build `46f52d356ce8` (main at
1bad1e0, built with `core/proxy/tools/build.sh --docker dll`), kit `kit_20261101T205936Z_f08b12c3806a`, DXVK 3.1.1 stock (d3d9 sha256
`265888c31ca78dffa290c39cb7e50bfb02762590e41927906e46fb32f01497fa`, the `fetch_dxvk.py --print-pin` value), no `dxvk.conf`. Game lock owner
`claude-j23`, one lock per sitting. Launch keys: the adapter's `ctl.launch.keys` (`dev.perf=1`, fixed sky). Prefs: Liam's, with the headless
overlay (`gfx_fullscreen false`, `x_res`/`y_res` = the cell size, sound muted); `gfx_vsync false`, `gfx_frame_rate 60` (not a cap here: p50
1 to 4.5 ms), every `gfx_*` key in each cell's `pins.prefs_gfx`. Driver: `tools/perf_baseline.py measure` (commands below).

**Liam may have been using the PC** during both sittings (he was in the chat): 2026-11-01 21:04 to 21:52 UTC and 21:54 to 22:51 UTC.

## Sittings
1. `measure --run 20261101_j23pc` (2 backends x 3 sizes, 21:04 to 21:52 UTC): `dxvk|1920x1080` complete (21:04:59 to 21:31:55, 44 cells +
   the battle cell); `system|1920x1080` failed (below); then the run stopped on a tool bug (the plan's `perf` flag collided with the perf
   result in a skipped cell, fixed in commit "the plan's measure flag no longer collides"). Lock released, keys put back (`proxy.backend=dxvk`).
2. `measure --run 20261101_j23pc --backends dxvk --sizes 2560x1440,3840x2160` (21:54 to 22:51 UTC): `dxvk|2560x1440` 21:54:34 to 22:21:05,
   `dxvk|3840x2160` 22:22:45 to 22:49:18, every cell ok. Its closing summary crashed on sitting 1's cells (the process predated the fix that
   reads them); `summarize` afterwards wrote `perf/baseline.json`. The system backend was not tried at 1440p and 4K (below).

`run.json` lists both sittings with their blocks; `events.log` has every cell's line; `cells/` the raw cell JSONs (pins, scene, perf,
host memory). The run's `summary.json` is not committed: `perf/baseline.json` is the same summary (`summarize --run harness/runs/20261101_j23pc`).

## The system d3d9 backend: no cell
`proxy.backend=system` at 1920x1080: three scenes, each launch tried twice by `ctl.py` (its one HEADLESS retry), all six
`HEADLESS FAILED: no on_virtual status for pid ... within 180 s (last: target_ok target resolved at Direct3DCreate9); the game was killed
(fail closed)` (cells `system_1920x1080_*_p0.json`, 21:33:41 to 21:52:25 UTC). The proxy log of the last one: system d3d9 loaded
(`C:\WINDOWS\system32\d3d9.dll`), device created at the virtual display size, both Present slots hooked, the front end reached and pumping,
then nothing for 180 s with **frame 0**: no Present reached the hook, so the headless `on_virtual` post-check (and the perf recorder, which
hooks the same Present) never ran. The same as J8 with `dev.capture=1` (run 20261101_j8pc), so not the capture key. Brief kill criterion
"cannot be launched headless twice in a row": recorded failed, the block skipped, the other cells finished. 1440p and 4K were not tried:
the failure is before any size-dependent step. Fact `napoleon.render.system_backend` (open, owner J16).

## Incidents
- The tool bug above (sitting 1 stopped at 21:52:25; nothing measured was lost, the lock was released and the keys put back).
- No hang, no dump, no VirtualStore copy, no foreign lock. Each size change moved the virtual display's mode (1080p, 1440p, 4K, restore).

## The table (DXVK; medians of 3 passes; battle = `--deploy end`, 1x, 60 s, n=1)
Generated: `python3 tools/perf_baseline.py table`. VA peak is the process peak since its launch: a warm-reset scene inherits the earlier
scenes' peak (naval_small's 1887 is siege_small's); `va_used` is the scene's own value at the end of perf. Cold = the warm-up pass after the
block's fresh launch. No DXVK against system ratio: no system cell.

| backend | size | scenario | pose | p50 ms (spread) | p99 ms | load s (cold) | VA used / peak MB | commit MB | VRAM MB |
|---|---|---|---|---|---|---|---|---|---|
| dxvk | 1920x1080 | campaign_start | default | 1.989 (0.036) | 2.814 | 2.6 (2.8) | 1756 / 1757.2 | 1157 | 428.7 |
| dxvk | 1920x1080 | hist_dresden | deploy | 4.47 (0.109) | 6.701 | 7.3 (7.3) | 2078 / 2095.9 | 1467 | 823.7 |
| dxvk | 1920x1080 | hist_dresden | turned | 4.258 (0.045) | 6.47 | 7.3 (7.3) | 2078 / 2095.9 | 1452 | 823.7 |
| dxvk | 1920x1080 | hist_nile | deploy | 3.518 (0.034) | 6.06 | 4.2 (4.3) | 1821 / 1823.3 | 1152 | 456.0 |
| dxvk | 1920x1080 | hist_nile | turned | 3.261 (0.085) | 6.165 | 4.2 (4.3) | 1815 / 1823.3 | 1153 | 456.0 |
| dxvk | 1920x1080 | land_small | battle1x (battle) | 2.336 (0.0) | 3.843 | 3.6 (3.5) | 1838 / 1843.5 | 1193 | 563.6 |
| dxvk | 1920x1080 | land_small | deploy | 1.894 (0.109) | 3.341 | 3.6 (3.5) | 1818 / 1822.7 | 1180 | 563.6 |
| dxvk | 1920x1080 | land_small | turned | 1.856 (0.045) | 3.162 | 3.6 (3.5) | 1814 / 1822.5 | 1179 | 563.6 |
| dxvk | 1920x1080 | naval_small | deploy | 1.689 (0.007) | 3.174 | 3.7 (3.7) | 1760 / 1887.6 | 1087 | 604.5 |
| dxvk | 1920x1080 | naval_small | turned | 1.38 (0.008) | 2.757 | 3.7 (3.7) | 1759 / 1887.3 | 1087 | 604.5 |
| dxvk | 1920x1080 | naval_storm | default | 1.649 (0.004) | 3.186 | 3.5 (3.5) | 1759 / 1887.2 | 1087 | 540.5 |
| dxvk | 1920x1080 | siege_small | deploy | 2.27 (0.035) | 3.815 | 5.2 (5.2) | 1887 / 1887.0 | 1243 | 787.5 |
| dxvk | 1920x1080 | siege_small | turned | 2.057 (0.022) | 3.448 | 5.2 (5.2) | 1878 / 1886.9 | 1241 | 787.5 |
| dxvk | 2560x1440 | campaign_start | default | 1.99 (0.003) | 2.857 | 2.6 (2.6) | 1750 / 1751.3 | 1155 | 501.1 |
| dxvk | 2560x1440 | hist_dresden | deploy | 4.193 (0.052) | 6.459 | 7.2 (7.3) | 2079 / 2095.0 | 1457 | 892.1 |
| dxvk | 2560x1440 | hist_dresden | turned | 3.892 (0.136) | 6.137 | 7.2 (7.3) | 2079 / 2095.0 | 1454 | 892.1 |
| dxvk | 2560x1440 | hist_nile | deploy | 2.773 (0.016) | 5.337 | 4.2 (4.2) | 1822 / 1823.6 | 1155 | 524.3 |
| dxvk | 2560x1440 | hist_nile | turned | 2.578 (0.007) | 5.142 | 4.2 (4.2) | 1816 / 1823.7 | 1155 | 524.3 |
| dxvk | 2560x1440 | land_small | battle1x (battle) | 2.008 (0.0) | 3.527 | 3.5 (3.6) | 1837 / 1844.1 | 1189 | 631.9 |
| dxvk | 2560x1440 | land_small | deploy | 1.817 (0.02) | 3.223 | 3.5 (3.6) | 1818 / 1822.7 | 1178 | 631.9 |
| dxvk | 2560x1440 | land_small | turned | 1.795 (0.019) | 3.092 | 3.5 (3.6) | 1813 / 1821.4 | 1178 | 631.9 |
| dxvk | 2560x1440 | naval_small | deploy | 1.409 (0.02) | 2.862 | 3.6 (3.8) | 1760 / 1885.2 | 1090 | 608.9 |
| dxvk | 2560x1440 | naval_small | turned | 1.066 (0.019) | 2.519 | 3.6 (3.8) | 1759 / 1885.8 | 1090 | 608.9 |
| dxvk | 2560x1440 | naval_storm | default | 1.373 (0.032) | 2.887 | 3.5 (3.5) | 1759 / 1885.8 | 1105 | 608.9 |
| dxvk | 2560x1440 | siege_small | deploy | 2.024 (0.023) | 3.599 | 5.2 (5.2) | 1886 / 1886.0 | 1245 | 855.9 |
| dxvk | 2560x1440 | siege_small | turned | 1.869 (0.014) | 3.313 | 5.2 (5.2) | 1878 / 1885.7 | 1243 | 855.9 |
| dxvk | 3840x2160 | campaign_start | default | 1.967 (0.035) | 2.799 | 2.6 (2.6) | 1749 / 1750.3 | 1156 | 691.2 |
| dxvk | 3840x2160 | hist_dresden | deploy | 3.991 (0.024) | 6.131 | 7.1 (7.1) | 2079 / 2095.0 | 1455 | 1075.6 |
| dxvk | 3840x2160 | hist_dresden | turned | 3.786 (0.024) | 5.988 | 7.1 (7.1) | 2079 / 2095.0 | 1455 | 1075.6 |
| dxvk | 3840x2160 | hist_nile | deploy | 2.74 (0.044) | 5.323 | 4.2 (4.2) | 1822 / 1823.6 | 1152 | 704.7 |
| dxvk | 3840x2160 | hist_nile | turned | 2.572 (0.023) | 5.156 | 4.2 (4.2) | 1816 / 1823.7 | 1153 | 704.7 |
| dxvk | 3840x2160 | land_small | battle1x (battle) | 1.998 (0.0) | 3.592 | 3.5 (3.5) | 1823 / 1828.8 | 1187 | 810.3 |
| dxvk | 3840x2160 | land_small | deploy | 1.806 (0.008) | 3.171 | 3.5 (3.5) | 1818 / 1822.6 | 1178 | 794.3 |
| dxvk | 3840x2160 | land_small | turned | 1.773 (0.001) | 3.075 | 3.5 (3.5) | 1813 / 1821.3 | 1177 | 794.3 |
| dxvk | 3840x2160 | naval_small | deploy | 1.358 (0.032) | 2.843 | 3.6 (3.6) | 1761 / 1887.3 | 1091 | 800.4 |
| dxvk | 3840x2160 | naval_small | turned | 1.045 (0.01) | 2.485 | 3.6 (3.6) | 1759 / 1886.9 | 1090 | 800.4 |
| dxvk | 3840x2160 | naval_storm | default | 1.337 (0.01) | 2.848 | 3.5 (3.5) | 1759 / 1886.9 | 1105 | 792.4 |
| dxvk | 3840x2160 | siege_small | deploy | 2.007 (0.012) | 3.414 | 5.1 (5.1) | 1887 / 1887.0 | 1246 | 957.4 |
| dxvk | 3840x2160 | siege_small | turned | 1.847 (0.009) | 3.218 | 5.1 (5.1) | 1878 / 1886.9 | 1244 | 957.4 |
