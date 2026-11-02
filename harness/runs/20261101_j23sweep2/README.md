# J23 PC run 20261101_j23sweep2: the dxvk.conf sweep (deliverable 4)

Same PC, build, kit, watcher and prefs as run `20261101_j23pc` (its README). 2026-11-01 23:49 UTC to 2026-11-02 00:45 UTC, lock owner
`claude-j23`; Liam may have been using the PC. Command:
`perf_baseline.py measure --run 20261101_j23sweep2 --backends dxvk --sizes 1920x1080,3840x2160 --scenarios land_small,siege_small --poses deploy --repeats 3 --deploy-end-s 0 --dxvk-variants perf/dxvk_sweep.json`.

**One option at a time** against a control (`none`: a conf with only a comment), each its own block (fresh launch, a warm-up pass, three
measured passes): `d3d9.maxFrameLatency = 1`, `d3d9.presentInterval = 0`, `d3d9.maxAvailableMemory = 2048`, `dxvk.latencySleep = False`.
Each conf was written to `<game>\napoleon_remastered\dxvk\dxvk.conf` (where the proxy points `DXVK_CONFIG_FILE`) by an owner-locked watcher
ps1 job with the game closed, sha256-checked, and removed at the end (00:45:01). Every cell's `pins.dxvk_conf_read` is DXVK's own log: `Found
config file` and the option under `Effective configuration` (e.g. `{'d3d9.maxFrameLatency': '1'}`); a cell without it is refused.

**Run `20261101_j23sweep` (22:51 to 23:46 UTC) is not valid and is kept as the record of why:** it served each conf beside a copy of the DLL
(`proxy.dxvk_path` pointed at `<state>\_scratch\claude-j23\dxvk_<name>\`); the proxy still pointed DXVK at `<mod>\dxvk\dxvk.conf` and DXVK
logged no config file in any block, so it measured the stock defaults ten times (now refused by `perf_baseline.py summarize`: 80 of 80 cells).
It stays useful as a noise sample: ten fresh launches of the same setup. Fact `napoleon.proxy.dxvk_config_dir`.

## Answer
No option is faster than the stock defaults beyond the noise, and none is slower: p50 differs from the control by at most 0.06 ms
(land_small 1080p: control 2.055, variants 2.025 to 2.115; spreads 0.06 to 0.17), p99 by at most 0.3 ms in either direction, address space
and commit within the launch-to-launch noise (VA used 1858 to 1860 against the control's 1859 to 1875). `d3d9.maxAvailableMemory = 2048` (the
value GetAvailableTextureMem starts from) changes no address space here. **Settled: ship no dxvk.conf (DXVK 3.1.1's own defaults).** Not
measured: a back-buffer count (no such option in 3.1.1: the DLL's option strings have no `numBackBuffers`), texture upload and shader-compile
options (`dxvk.numCompilerThreads`, `dxvk.enableGraphicsPipelineLibrary`: loads are 3.5 to 7.3 s with cold = warm, nothing to win).

## The table (`perf_baseline.py table --run harness/runs/20261101_j23sweep2`; deploy pose, medians of 3)

| backend | size | scenario | pose | p50 ms (spread) | p99 ms | load s (cold) | VA used / peak MB | commit MB | VRAM MB |
|---|---|---|---|---|---|---|---|---|---|
| dxvk+availmem2048 | 1920x1080 | land_small | deploy | 2.025 (0.079) | 3.533 | 4.1 (3.6) | 1859 / 1894.7 | 1204 | 567.5 |
| dxvk+availmem2048 | 1920x1080 | siege_small | deploy | 2.203 (0.101) | 3.836 | 5.4 (5.2) | 1881 / 1894.4 | 1265 | 823.5 |
| dxvk+availmem2048 | 3840x2160 | land_small | deploy | 1.855 (0.028) | 3.312 | 3.9 (3.6) | 1860 / 1892.3 | 1194 | 817.4 |
| dxvk+availmem2048 | 3840x2160 | siege_small | deploy | 1.948 (0.08) | 3.43 | 5.2 (5.1) | 1881 / 1891.9 | 1250 | 1073.4 |
| dxvk+interval0 | 1920x1080 | land_small | deploy | 2.112 (0.12) | 3.506 | 4.0 (3.6) | 1859 / 1890.4 | 1209 | 575.5 |
| dxvk+interval0 | 1920x1080 | siege_small | deploy | 2.215 (0.105) | 3.759 | 5.4 (5.2) | 1880 / 1889.9 | 1251 | 831.5 |
| dxvk+interval0 | 3840x2160 | land_small | deploy | 1.87 (0.022) | 3.276 | 3.9 (3.5) | 1859 / 1892.1 | 1196 | 817.4 |
| dxvk+interval0 | 3840x2160 | siege_small | deploy | 1.972 (0.072) | 3.499 | 5.3 (5.1) | 1881 / 1892.3 | 1254 | 1073.4 |
| dxvk+latency1 | 1920x1080 | land_small | deploy | 2.115 (0.167) | 3.644 | 4.1 (3.6) | 1859 / 1895.5 | 1190 | 567.5 |
| dxvk+latency1 | 1920x1080 | siege_small | deploy | 2.224 (0.087) | 3.712 | 5.4 (5.2) | 1881 / 1896.0 | 1247 | 823.5 |
| dxvk+latency1 | 3840x2160 | land_small | deploy | 1.857 (0.023) | 3.296 | 4.0 (3.6) | 1859 / 1895.7 | 1188 | 815.4 |
| dxvk+latency1 | 3840x2160 | siege_small | deploy | 1.97 (0.064) | 3.556 | 5.4 (5.1) | 1881 / 1895.8 | 1245 | 1071.4 |
| dxvk+latencysleep_off | 1920x1080 | land_small | deploy | 2.058 (0.062) | 3.467 | 4.1 (3.6) | 1858 / 1894.1 | 1195 | 567.5 |
| dxvk+latencysleep_off | 1920x1080 | siege_small | deploy | 2.201 (0.104) | 3.739 | 5.4 (5.2) | 1880 / 1894.1 | 1252 | 823.5 |
| dxvk+latencysleep_off | 3840x2160 | land_small | deploy | 1.874 (0.05) | 3.285 | 3.9 (3.5) | 1859 / 1895.8 | 1193 | 817.4 |
| dxvk+latencysleep_off | 3840x2160 | siege_small | deploy | 1.967 (0.088) | 3.415 | 5.3 (5.1) | 1881 / 1896.1 | 1252 | 1073.4 |
| dxvk+none | 1920x1080 | land_small | deploy | 2.055 (0.091) | 3.683 | 4.0 (3.6) | 1875 / 1894.8 | 1195 | 567.5 |
| dxvk+none | 1920x1080 | siege_small | deploy | 2.221 (0.079) | 3.875 | 5.4 (5.3) | 1896 / 1900.0 | 1251 | 823.5 |
| dxvk+none | 3840x2160 | land_small | deploy | 1.874 (0.029) | 3.269 | 3.9 (3.5) | 1859 / 1894.3 | 1197 | 829.4 |
| dxvk+none | 3840x2160 | siege_small | deploy | 1.975 (0.069) | 3.342 | 5.3 (5.1) | 1881 / 1894.5 | 1251 | 1085.4 |
