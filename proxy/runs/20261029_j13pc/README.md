# Run 20261029_j13pc: J13 headless runs on the virtual display (PC sitting, 17:37-18:53Z)

Liam approved the sitting (all of a-e, including the visible baseline) and made the `vdd_settings.xml` edit at the start, so the virtual
display offers 1920x1080, 2560x1440 and 3840x2160 (fact `napoleon.display.vdd_modes`). Every launch went through the watcher
(`harness/core/job.sh`, lock owner `j13`, profile `dev-dxvk` = proxy on DXVK 3.1.1 + `dev.skip_intro` and the control channel), under
the whole-launch window probe (`harness/core/win_probe.ps1`). Per launch: Liam's prefs sha256 before, the prefs as the game left them,
`profile restore`, the sha256 again. Raw data per launch in `raw/<run>/` (launch, ctl, proxy.log, headless_status.json, winprobe.json
and .txt, prefs). Scratch scripts were not kept (they are the job.sh calls listed in `raw/*/launch.txt` and `ctl.txt`).

**Topology** all sitting: `\\.\DISPLAY1` 3840x2160@240 primary at 0,0 (144 DPI); Dell `\\.\DISPLAY2` 2560x1440 at -2560,327 (120 DPI);
virtual `\\.\DISPLAY11` ("Virtual Display Driver", GDI number 10 before the driver reload) at **3839,2160** (96 DPI), touching the primary
only at a corner. **Liam's prefs** sha256 `83b9b32b2b738ebcafa4910a9b3b6f0c69b9a06e3e6270fb55d6e51bdee2cea7` before the sitting and after it.

Builds: proxy `35c8241b2e63` -> `614ce5082497` (SetFocus) -> `5ddc7e107ab2` (helper device) -> `8565a96e131c` (DirectInput levels; installed
at the end); watcher 1.0.1 kits `35c8241b2e63` -> `614ce5082497` (mute) -> `388f362a2dc4` (-Origin) -> `8565a96e131c` (probe cursor) ->
`8f2625b5715e` (mode kept per lock, cursor put back).

## Results

| test | result |
|---|---|
| a) visible baseline | window `Napoleon` at 0,0 3840x2160 on the primary 1.3 s after start; **112.7 s** longest on a real monitor (173.7 s total) |
| b) 4K headless, 5 to the menu | all `on_virtual` at 1.2 s, **0 ms** on a real monitor, 0 cloaked, no activation, frames presented unfocused |
| b) 4K headless, 3 into `battle:land_small` + warm reset | all ok (autostart 4.5-4.6 s, reset 15.7 s), 0 ms on a real monitor |
| c) size the driver does not offer (1280x720) | refused by the watcher before anything started, nothing changed |
| c) forced no target (`headless.display_name` = a name no display has) | the proxy refused at `Direct3DCreate9`, exit 2160, 1.1 s under the probe, 0 ms on a real monitor, status `refused` with the reason |
| d) virtual display moved to 3840,0 and back mid-run | cloaked on the metrics change, relocated and verified in 85 ms, uncloaked after the 500 ms settle; both moves; **0 ms** on a real monitor, 1352 ms cloaked |
| e) 1080p and 1440p: 5 to the menu + 3 battles (the first with warm resets) each | all `on_virtual` at the size, 0 ms on a real monitor, 0 cursor recentres, the game never in the foreground |
| prefs | byte-identical after every launch, including the refused ones and the one killed mid-way (see "Incident") |

Per launch (generated from `raw/`; "-" = the probe did not record cursor recentres yet; activation messages are logged only under headless):

| run (raw/) | launch id | status | back buffer | probe samples | longest on real ms | cloaked ms | monitor changes | cursor recentres | activation msgs | ctl | prefs after |
|---|---|---|---|---|---|---|---|---|---|---|---|
| a_visible | 20261029T173711Z-p25480 | (visible) |  | 16956 | 112745 | 0 | 0 | - | - |  | identical |
| b4k_0_before_focus_fix | 20261029T174047Z-p24260 | on_virtual | 3840x2160 | 1120 | 0 | 0 | 0 | - | 6 | ping:ok state:ok | identical |
| b4k_1 | 20261029T174536Z-p3900 | on_virtual | 3840x2160 | 1029 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| b4k_2 | 20261029T174615Z-p29140 | on_virtual | 3840x2160 | 927 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| b4k_3 | 20261029T174633Z-p25500 | on_virtual | 3840x2160 | 973 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| b4k_4 | 20261029T174653Z-p15100 | on_virtual | 3840x2160 | 873 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| b4k_5 | 20261029T174710Z-p18020 | on_virtual | 3840x2160 | 922 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| b4k_battle_0a_helper_refused | 20261029T174740Z-p30444 | refused (helper device) | 3840x2160 | 692 | 0 | 0 | 0 | - | 0 |  | identical |
| b4k_bt_1 | 20261029T181023Z-p30268 | on_virtual | 3840x2160 | 3027 | 0 | 0 | 0 | - | 0 | autostart:ok reset:ok state:ok | identical |
| b4k_bt_2 | 20261029T181104Z-p28388 | on_virtual | 3840x2160 | 1401 | 0 | 0 | 0 | - | 0 | autostart:ok state:ok | identical |
| b4k_bt_3 | 20261029T181128Z-p28584 | on_virtual | 3840x2160 | 1353 | 0 | 0 | 0 | - | 0 | autostart:ok state:ok | identical |
| c_size_not_offered | (no game started) | watcher refused |  |  |  |  |  | - | - |  | identical |
| c_no_target | 20261029T181218Z-p18212 | refused (no target) |  | 103 | 0 | 0 | 0 | - | 0 |  | identical |
| d_1_origin_bad_args | 20261029T181642Z-p29796 | on_virtual | 3840x2160 | 2654 | 0 | 0 | 0 | - | 0 | state:ok | identical |
| d_topology_move | 20261029T181927Z-p11324 | on_virtual | 3840x2160 | 4543 | 0 | 1352 | 2 | - | 0 | state:ok | identical |
| e1080_menu_1 | 20261029T182058Z-p27752 | on_virtual | 1920x1080 | 1117 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| e1080_menu_2 | 20261029T182136Z-p416 | on_virtual | 1920x1080 | 1260 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| e1080_menu_3 | 20261029T182218Z-p29728 | on_virtual | 1920x1080 | 1212 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| e1080_menu_4 | 20261029T182304Z-p10244 | on_virtual | 1920x1080 | 1308 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| e1080_menu_5 | 20261029T182347Z-p22788 | on_virtual | 1920x1080 | 1309 | 0 | 0 | 0 | - | 0 | ping:ok state:ok | identical |
| e1080_mousefix_bt | 20261029T183906Z-p10940 | on_virtual | 1920x1080 | 3292 | 0 | 0 | 0 | 0 | 0 | autostart:ok reset:ok state:ok | identical |
| e1080_bt_1 | 20261029T184806Z-p25384 | on_virtual | 1920x1080 | 3290 | 0 | 0 | 0 | 0 | 0 | autostart:ok reset:ok state:ok | identical |
| e1080_bt_2 | 20261029T184850Z-p26932 | on_virtual | 1920x1080 | 1357 | 0 | 0 | 0 | 0 | 0 | autostart:ok state:ok | identical |
| e1080_bt_3 | 20261029T184913Z-p31320 | on_virtual | 1920x1080 | 1359 | 0 | 0 | 0 | 0 | 0 | autostart:ok state:ok | identical |
| e1440_menu_1 | 20261029T184945Z-p24956 | on_virtual | 2560x1440 | 1265 | 0 | 0 | 0 | 0 | 0 | ping:ok state:ok | identical |
| e1440_menu_2 | 20261029T185007Z-p18764 | on_virtual | 2560x1440 | 879 | 0 | 0 | 0 | 0 | 0 | ping:ok state:ok | identical |
| e1440_menu_3 | 20261029T185025Z-p28288 | on_virtual | 2560x1440 | 1020 | 0 | 0 | 0 | 0 | 0 | ping:ok state:ok | identical |
| e1440_menu_4 | 20261029T185046Z-p12400 | on_virtual | 2560x1440 | 878 | 0 | 0 | 0 | 0 | 0 | ping:ok state:ok | identical |
| e1440_menu_5 | 20261029T185104Z-p8392 | on_virtual | 2560x1440 | 879 | 0 | 0 | 0 | 0 | 0 | ping:ok state:ok | identical |
| e1440_bt_1 | 20261029T185122Z-p6196 | on_virtual | 2560x1440 | 2992 | 0 | 0 | 0 | 0 | 0 | autostart:ok reset:ok state:ok | identical |
| e1440_bt_2 | 20261029T185203Z-p29248 | on_virtual | 2560x1440 | 1258 | 0 | 0 | 0 | 0 | 0 | autostart:ok state:ok | identical |
| e1440_bt_3 | 20261029T185226Z-p28876 | on_virtual | 2560x1440 | 1265 | 0 | 0 | 0 | 0 | 0 | autostart:ok state:ok | identical |

## Found and fixed during the sitting (each a commit on `job/J13`)
1. **Activation** (b4k_0): the window got `WM_ACTIVATEAPP`/`WM_ACTIVATE`/`WM_SETFOCUS` at 1.1 s despite `WS_EX_NOACTIVATE`: the engine's
   `SetFocus` activates. Now dropped while another process has the foreground (fact `napoleon.window.setfocus_activates`). After: 0
   activation messages in 32 headless launches, and the game still renders and answers ctl unfocused (`napoleon.window.background_render`),
   so no deactivation swallowing was built.
2. **Mute** (Liam's request): the headless prefs overlay sets `sound_master_enabled false`, `sound_master_volume 0`; the game left them so,
   and the restore returned Liam's values byte for byte.
3. **Battle helper device** (b4k_battle_0a): loading a battle creates a windowed 1x1 device on a non-game window; the guard refused it
   (exit 2160, nothing shown, prefs identical). Now a windowed device of at most 8x8 passes (`GateDevice`, fact `napoleon.d3d.battle_helper_device`).
4. **Display tool `-Origin`** (d_1): `& tool -Origin 3840,0` arrives as an array; it was refused as bad arguments (nothing changed). Fixed.
5. **Liam's cursor jumped to the centre of his monitor** during the 1080p runs. Measured with no game running: a dynamic mode change of the
   virtual display makes Windows move the real cursor to the primary's centre (1920,1080) about 0.5 s later; the watcher switched the mode
   twice per launch. Now the mode is kept for the whole lock (restored once at release: 18:53:12Z here) and the display tool puts a
   recentred cursor back. The probe now counts cursor recentres (0 in the 15 launches after the fix) and game-foreground time (0). The
   DirectInput cooperative level is also forced non-exclusive and foreground-only under headless; the engine asks for `0x16`
   (non-exclusive, foreground, no Windows key), so DirectInput was not the cause.

## Incident: an orphaned test loop (kill criterion "prefs not byte-identical")
Stopping the first battle loop (`TaskStop` on the agent's background shell) killed only its outer shell; the inner loop kept running on
the old build and interleaved with later tests from 18:07 to 18:14Z: its `kill` ended the game of `d_0_killed_by_orphan_loop` (no ctl
step ran), and its next launch overlaid the prefs just before that run's sha check, which read `5ec8acd4...` (MISMATCH). The watcher's
snapshot was intact: `profile restore` returned `83b9b32b...` byte-identical at once, and the orphan (two bash processes) was found and
stopped. Folders `b4k_battle_0b_helper_refused`, `b4k_battle_0c_orphan` and `d_0_killed_by_orphan_loop` hold that mixed data and are
not counted above. The cause is the agent's scratch scripting, not the harness or the proxy; prose here because a scratch script is not
repo code (the lesson: stop a background loop by its process tree, then check for survivors).
