# J32 run 20261106_j32pc: viewer parity (S3) and panel-host routes (S4)

PC, 2026-11-06 07:17 to 08:21 UTC, game lock `j32`, session `1f457253-79f1-49ab-b7e2-9bf63066eaa1`, DXVK, headless. The PC display layout had changed on 2026-11-05; no foreign-window observer was used and the headless guard never refused.

## Builds
| what | id | sha256 |
|---|---|---|
| acceptance kit `kit_20261106T071945Z_b5a7ccec7f29` | DLL build `a005f6cccc17` (main at bca3b99, no DLL input changed) | d3d9.dll `dada8d8237167718ae80e6a9472a473f0e6ac33d8e4c75265258576c73584676` |
| scratch kit `kit_20261106T080617Z_af482d0562e0` | the same sources, the RmlUi objects and `ui_lua.cpp` with `-msse2 -mfpmath=sse`; the rest of the host, `ui_host.cpp` with `UiDpRatio` among it, stayed x87 (J32 review: `ApplyScale` in this DLL is still `fild`/`fdiv`), which is why its dp ratio did not change | d3d9.dll `e4cc67808689258ce68f2cc24dbd63176b741c4915b7f2d3f199bb7c5cab8079` |
| viewer (pinned) | CI run 42058592470 `viewer-wasm`, the baseline's | viewer.wasm `2bdc8a112021772a4e4ad08004bb3e096707f9fcbff95625073f217f478b0f78` |
| viewer (scratch, Clear before BeginFrame) | Docker build, source put back | viewer.wasm `41675bac46743ce4a46e2d63cf6be21cf4907b3ae0d9aa6ce589229d27edf32c` |

The scratch DLL was installed 08:07 to 08:17 UTC for one sitting and `boxes.py`, then uninstalled. Neither scratch build is on this branch; their files are in `build/j32/` of the job worktree and the scratch kit stays in `C:\napoleon_remastered_pc\kits`. `ui.dir` pointed at `C:\napoleon_remastered_pc\_scratch\j32\ui` (a `..` path from the game folder), so the test documents never went in the game folder.

## Sittings
| when (UTC) | driver | what | result |
|---|---|---|---|
| 07:20 | `s3.py sit --sizes 1920x1080 --scenes frontend` | smoke | `<script src>` failed: fact `napoleon.ui.script_src_absolute_path` |
| 07:23 | `s3.py sit` | three documents, three sizes, front end and battle | host test and recipes good; the board's Lua still off (a CDATA wrapper) |
| 07:33 | `s4.py camp` attempt 1 | | stopped: the driver read the wrong result field; `s4_attempt1_no_results.jsonl` |
| 07:36 | `s4.py camp` | panel, costs, means | first launch retried once by `ctl.py` (HEADLESS FAILED, game exited before reporting). The popup half is void: the popup was not up yet |
| 07:44 | `s3.py sit --docs board` | the board with its Lua, 0 RmlUi warnings | the board dumps used below |
| 07:48 | `s4.py camp2` | popup, hit tests, unit popup | |
| 07:53 | `s4.py battle` | HUD (`hist_dresden`) | |
| 07:58 to 08:03 | `s4.py fe` | page, handler, means | first try stopped: `ctl.py shot` never settles in the front end |
| 08:08 | `s3.py sit --scenes frontend` | scratch SSE DLL | dumps byte-identical to the x87 ones, so float width is not the cause |
| 08:11 to 08:15 | `boxes.py` | 507 div boxes at 1440p and 1080p x 85 (scratch SSE DLL) | the dp ratio |
| 08:18 | `s4.py fe2`, `camp3` | acceptance kit again: main menu pump, unit popup route A, click control | |
| 09:19 | `s4.py battle2` | fix round 1, acceptance kit: hit test on the order bar, each means | 20 points answer visible; of 6 kept, `SetVisible`, `PropagateVisibility`, move all nil, opacity all answer, restored all answer |
| 09:31 | `s4.py fe3` | fix round 1: hit test on the main menu, visible and hidden | first launch died in `DllMain`, dump below, `ctl.py` retried; hidden, 4 points answer `movie_bg` |

No crash and no hang in any sitting once the game was up. Two launches died before it was: 07:36 (no dump looked at) and 09:30, whose dump `20261106T093045Z-p14632_c0000374.dmp` (now in `<state>\_to_delete\uninstall_20261106T093718Z\napoleon_remastered\dumps`) has the code of the known `napoleon.proxy.init_heap_corruption`. Every game dump's sha256 is in `results.jsonl`. Full PNGs are in `C:\napoleon_remastered_pc\ui_dumps`, not committed; `crops/` has the worst tiles (viewer, game, difference x 8).

## S3 numbers (share of pixels more than 8 levels off, max delta)
Front end; every board and recipes battle dump is byte-identical to its front-end dump. The host test covers only part of the screen, so its dumps differ outside its body, where the scene shows; inside the compared rect they are identical (J32 review, all four cells).

| cell | board pinned | board fixed viewer | host test | recipes pinned | recipes fixed viewer |
|---|---|---|---|---|---|
| 1080p x 100 | 0 / 2 | 0 / 2 | 0.5533 % / 134 | 0.9502 % / 216 | 0.0995 % / 100 |
| 1080p x 85 | 1.8086 % / 245 | 1.8083 % / 173 | 0.5777 % / 149 | 0.7092 % / 216 | 0.0291 % / 100 |
| 1440p x 100 | 1.0940 % / 228, 2 tiles moved | 1.0384 % / 99, none moved at the game's ratio | 0.4087 % / 105 | 0.9537 % / 216 | 0.0354 % / 100 |
| 4K x 125 | 0.3953 % / 238 | 0.3953 % / 173 | 0 / 1 | 1.4555 % / 216 | 0.1868 % / 100 |

`parity.jsonl` is the pinned viewer, `parity_fixed.jsonl` the fixed one, `parity_sse.jsonl` the SSE DLL (board and host test), `recipes_table.json` per recipe cell, `parity_gate.jsonl` the 12 cells again through the moved-tile check as fix round 1 changed it (fixed viewer, the 1440p board at the game's ratio): same shares, no moved tile; the 1440p board at the correct ratio still reports its button row. The board's two moved tiles at 1440p are one button row. `boxes/`: with the viewer at the correct ratio 301 of 507 boxes differed in the last digits; at 1.3333334922790527, 0 differed; one step below, 470. At 1080p x 85, 0 differed.

## S4 evidence
Fix round 1 rows are at the end of `s4.jsonl`, from 09:19 UTC (tags `hud_*` and `main_*`). The scan's points are logged as `hud_points` and `main_points`; a point counts for the bar when its id is one of the bar's own in `j32snap.txt`.

`s4.jsonl` (every call and result), `j32snap.txt` (the row-level snapshots from the sittings' proxy logs, one line per chunk, prefixed by the sitting: reassemble a snapshot's chunks in order and split on `;`), `route_b.json`, `shots/camp_means.png` (HUD, panel open, hidden with SetVisible, opacity, moved), `shots/fe_means.png`. Frame p50 at 1080p: campaign closed 0.85 to 0.90 ms, panel open 1.08, panel hidden 0.98 to 1.00, event popup 0.94 open and 0.87 hidden, unit popup 1.04 open and 0.86 hidden; battle 4.18 open and 4.32 to 4.50 hidden.

## PC end state after fix round 1 (2026-11-06 09:37 UTC)
`job.sh status`: no lock, no job. `pc_deploy.py uninstall`: identical to the snapshot (1564 files). `pc_deploy.py status`: not installed, exe vanilla (sha1 `9aebcd21...`), no `.git`. Prefs sha256 `83b9b32b...`, restored byte-identical by the watcher at lock release.

## PC end state (2026-11-06 08:21 UTC)
`job.sh status`: no lock, no active profile, game not running. `pc_deploy.py uninstall`: identical to the snapshot (1564 files). `pc_deploy.py status`: not installed, exe vanilla (sha1 `9aebcd21...`), no `.git`. Prefs sha256 `83b9b32b...` unchanged. Scratch left on the PC: `_scratch\j32\ui` and the two kits.
