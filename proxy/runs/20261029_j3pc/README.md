# Run 20261029_j3pc: J3 dev control channel, first PC sitting

officepc, 2026-10-29 08:15-09:17 UTC, Napoleon.exe sha1 `9aebcd21...` (pinned), DXVK 3.1.1, RTX 4090. Unattended through the watcher
(Liam said go at 08:17Z; the game window was on his monitor). Builds in order: `858aa974e87c`, `1fd979ecb12c`, `5b4839555d84`,
`d10d361aaed9`, `98895eea72f0`, `edde0cedd087` (each a sha-checked `pc_deploy.py` kit). Raw evidence: `raw/` (proxy logs,
timelines, the file survey, every control result in `raw/ctl/*.done`, the reset series in `raw/f_resets*.jsonl`).

| step | result | evidence |
|---|---|---|
| a) dev keys off | log as J1 (no dev, hook or timeline line), minidump mode 2 warns about the replaced filter | `raw/a_devoff/proxy.log` |
| survey | 6,597 distinct paths; virtual pack listed; loose-copy probes under `data\` and two `working_data` folders; battle map preset folders probed while loading; `.sp_default.battle_preferences` written | `raw/b_survey/files.log`, `raw/*/files.log` |
| Lua bridge | `wsp_sentinel` + `luaopen_wsp` in front end and battle; wrapper of `main.advert` pumps on the main menu only, battle root via OnUpdatePulse | `raw/b_survey/proxy.log` |
| intro skip | 3 movies refused, main menu pumps at 7.0 s (130.3 s with the movies, n=1) | timelines in `raw/b_survey`, `raw/g_final` |
| control verbs | ping, state, lua (probes), waitfor (timeout path), autostart, reset: ok and failure paths seen | `raw/ctl/` |
| autostart battle:land_small | 8 runs, map checked against the engine's own preset-folder probes; StartBattle to battle 17.9-18.7 s | `raw/ctl/*autostart*` |
| warm reset | 3 clean resets (front end 6.7-8.8 s, back in battle 25.8-28.0 s); a race (step run by the front-end pump) fixed in `edde0ced`; one crash quitting 1.2 s after the battle appeared (mss32.dll AV, first-chance dump `20261029T091233Z-p14812_c0000005.dmp` on the PC, watcher hang kill) | `raw/f_resets*.jsonl`, `raw/g_final/proxy.log` |

Not run in this sitting: the 5-launch baselines, naval and campaign autostart, 10 resets in a row, driver-cache cold/warm, profile
restore after battles, the final uninstall. The proxy stays installed with every dev key off (release values); lock released.
