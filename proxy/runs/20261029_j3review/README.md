# Run 20261029_j3review: J3 review re-check (map check counts only the load's probe)

officepc, 2026-10-29 11:30-11:33 UTC, build `753dd22bcc85` (kit `kit_20261029T113002Z_753dd22bcc85`): `FilesMapReset` after
`autostart.lua` returns, so only map-folder probes made while the battle loads count (review finding 1). Dev keys as in run
`20261029_j3pc2` (intro skip on), watcher profile `proxy-dxvk`, restored afterwards with 0 mismatches. `job.sh` on the PC re-synced
to the review's version (`e1644cb6...`, withdraws an unanswered ctl request).

| preset | map (selected = preset) | `map_folder_loaded` | probe after the load request | battle load | log (`raw/<label>/proxy.log`) |
|---|---|---|---|---|---|
| land_small | NAP_MP_Grassy_Flatlands | nap_mp_grassy_flatlands | 141 ms | 3.5 s | report at 11:31:21.819, 0.15 s after `frontend -> loading` |
| naval_small | caribbean | caribbean | 125 ms | 3.1 s | 11:31:35.469, 0.12 s after |
| siege_small | rti_fort_1 | rti_fort_1 | 171 ms | 5.1 s | 11:32:02.081, 0.17 s after |

Each log now shows the folder reported twice: once by the front end's map-list walk (before loading) and once by the load itself
(after `frontend -> loading`). Before the fix the second report was swallowed by the dedup when the walk ended on the same folder.

**Load times changed with the PC state, not the build.** Battle loads were 3.1-5.1 s here against 18.1-20.9 s in run
`20261029_j3pc2` (09:42-10:36Z). One extra land launch on the previous build `066fbd0b7c62` (`raw/R_old_land`) gave 3.4 s too, so the
code is not the cause. The watcher restarted at 11:06Z (Liam's PC restarted or logged on again between the runs). Front end 3.9-4.4 s
against 5.7-7.4 s. The run-2 baselines compare arms measured in the same state; absolute numbers depend on the PC's state.
