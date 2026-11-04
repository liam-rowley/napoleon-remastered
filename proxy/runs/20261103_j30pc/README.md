# J30 PC re-run 2026-11-03: the RmlUi host on the shipping core (warscape-core v0.10.0)

The checks of `proxy/runs/20261102_j30pc/` again, on the DLL that will ship: Napoleon `job/J30` with the core pinned at the tag `v0.10.0`
(`c242f2f`, W2 after its review fixes). The 2026-11-02 run used a local, never pushed W2 commit (`f12b56e`, build `68a9bc84bb05`), so its
numbers stay as the record of that build and this folder is the evidence for the final one. Same driver (`run.py`, copied, unchanged
apart from the folder name) and summary (`summary.py`); lock owner `j30`, watcher 1.2.0, DXVK, headless at 1920x1080, 2560x1440 and
3840x2160. Raw step records: `results.jsonl`.

## Build
| | |
|---|---|
| build id | `af34b0c1f7d1` (`core/proxy/tools/build_id.py`, matches the DLL's own load line) |
| DLL | 4,224,512 B, sha256 `9b4bad0c78117dacf1a5b49aa1713c7d5b2663d91389bf633b88c1a527630d54` (before the host: 973,312 B) |
| imports | advapi32, dbghelp, kernel32, msvcrt, user32 (system only) |
| `build.sh --docker all` | 212 s with the RmlUi/FreeType objects cached; every host test passed (`test_ui_core` 212, `test_ui_rml` 25) |
| `build.sh --docker repro` | identical from another path (151 s) |
| kit | `kit_20261103T145025Z_1fcff35f261b` (56 files, the `kit_ui` fonts, `hosttest` and `hello` folders included) |

## b) dumps and checks (`tools/ui_hosttest.py check`, `checks/*.json`, crops in `crops/`)
| cell | rules solid | box edges | H height | note |
|---|---|---|---|---|
| front end, campaign, battle, after warm reset at 1080p x 100 | ok | ok | ok | |
| the same at 1440p x 100 | ok | ok | ok | dp 1.3333 |
| the same at 4K x 100 | ok | ok | ok | dp 2.0 |
| front end, campaign, battle at 1080p x 85 | **fail** | ok | ok | as on 2026-11-02: the 1 dp rule on a half pixel vanishes (fact `rmlui63.sub_pixel_rule`) |
| front end, campaign, battle at 4K x 125 | ok | ok | **fail (1 of 4)** | as on 2026-11-02: 14 dp at 35 px, H ink 26 rows against a 24.2 px cap height |
Every number matches the 2026-11-02 run cell for cell (`summary.py` prints the H ink rows). The crispness verdict is Liam's, from `crops/`.
Full PNGs (not committed) are on the PC in `C:\napoleon_remastered_pc\ui_dumps\`; sha256:
```
cf55ad3fa8b27c1a3b341e6db36d0c6e2539f4fb826a4bfb5b7f4aa4fcb7e454  after_reset_1080.png
3aee3a6be4195d83ef2874a53ec0163d5f0be1340d52800edf91cead6fa837b9  after_reset_1440.png
1694ecca6c5210435c06cd98228787fc91a415fd12a65138f531d23179b3313c  after_reset_2160.png
37948398469a348a322e1647ec3d05dba8a36950cd5da076ad610192848b6496  battle_1080_100.png
8a9209eef20624802d52a4e430b99015a4122e82a2dfa2a11425a473f0b83877  battle_1080_85.png
3d2de653b5e191047ebad12995a4bb90df36526b2f176640e2ea6dc7c147af8e  battle_1440_100.png
0e8f312bf808bcb147307415b3dcef8dfb6607577f19c195765646c6d6c341bd  battle_2160_100.png
157bf3534de69c2c80cd4561527f2aaf2990e88e95075e9fecf18b90bfd8e43d  battle_2160_125.png
ecb084d8524ece787420f3bf126bf38944ce96c3410e22b4f67b50f2e365cde9  campaign_1080_100.png
aadb9499df407cb437358f03116bf23d9785ff5dd44fca72d279bd5cae400cd5  campaign_1080_85.png
38684acbc819efc1814e3f5c678e949802b7232f637d853f242732b41b153b30  campaign_1440_100.png
82866164c569627f88a15383b95de401a5517d4873c351edf3f7bebe098af73d  campaign_2160_100.png
313c27a8a7462a5000ae75b09617a507acfd86406147556b9623eca55d170e25  campaign_2160_125.png
5bfaa2f728f556b6d0d0eaef4eb58df34f5047fed4e57d3049e9be6cf2657043  frontend_1080_100.png
60d373840189d443f4d35ca476a6b0bbb3447c40ba87250bc1164e1b90f98c52  frontend_1080_85.png
640f704791f39e1e07da4769bc6c6faea1c8fc0fd9905698b461a6bad534ff0e  frontend_1440_100.png
563ec4d3ec91e5155e5caa6965883eb7064c41333094a5de59803be33d4fa181  frontend_2160_100.png
54b50b232b907ffd684261aaee619b5f9e117de72b5cb4f07c068db82bd17c23  frontend_2160_125.png
6ee2d8f545208953f87fefbf784a77f20a484e51dffcf1aeaec8825e0bd5ac6f  smoke_fe_1080.png
```

## c) interaction and e) scene changes (`results.jsonl` step `interaction`)
All nine routing checks passed in all twelve cells (front end, campaign, battle and after a warm reset from the battle, at 1080p, 1440p
and 4K): a click on the target counts in RmlUi and not the engine; a click off the document is the engine's; a press begun on the engine
and released over the document stays the engine's; the wheel scrolls only the list; hidden, the target's spot is the engine's; shown
again and reloaded, RmlUi's. The document stayed open from the front end into the campaign, the battle and back through the warm reset:
`ui state` reports `life ready`, Lua up, RmlUi log 0 warnings and 0 errors at every step; Present and the window run on one thread.

## d) frame cost (DXVK; `perf 10` x 3 per cell, one sitting, `off` is the same-sitting control)
Frame time p50 / p99 in ms (mean of 3 runs); host = `ui state` update + render p50 in ms for the drawn frames of the same window.
| size | scene | off | idle (enabled, nothing shown) | document | host p50 (document) | whole hook p50 |
|---|---|---|---|---|---|---|
| 1080p | front end | 0.28 / 0.82 | 0.28 / 0.90 | 0.31 / 0.73 | 0.062 | 0.067 |
| 1080p | campaign | 1.97 / 4.51 | 2.03 / 3.78 | 1.96 / 3.46 | 0.087 | 0.088 |
| 1080p | battle | 2.14 / 6.30 | 2.34 / 5.74 | 2.22 / 4.84 | 0.069 | 0.079 |
| 1440p | front end | 0.27 / 0.69 | 0.28 / 1.17 | 0.33 / 0.74 | 0.066 | 0.070 |
| 1440p | campaign | 1.95 / 4.17 | 1.89 / 4.57 | 2.23 / 5.20 | 0.094 | 0.096 |
| 1440p | battle | 1.91 / 5.72 | 2.07 / 7.30 | 2.12 / 7.62 | 0.094 | 0.094 |
| 4K | front end | 0.22 / 0.72 | 0.22 / 0.70 | 0.29 / 0.69 | 0.064 | 0.068 |
| 4K | campaign | 1.92 / 3.29 | 1.89 / 3.53 | 1.99 / 3.70 | 0.079 | 0.080 |
| 4K | battle | 1.88 / 4.84 | 1.88 / 4.92 | 1.96 / 4.93 | 0.091 | 0.091 |
Against D38: the document costs at most 0.096 ms p50 of host time (1 ms budget at 4K, 2 ms hard stop); the idle host's hook is 0.000 ms
p50 in every cell (0.1 ms budget). Frame-time p50, document minus off: -0.01 to +0.28 ms; idle minus off: -0.06 to +0.20 ms, inside the
run-to-run spread of one cell (up to about 0.3 ms), so the idle host is not separable from off. Frame time is the CPU-side Present to
Present interval; GPU time of the UI draw is not measured on its own. Memory, document over off: address space +5 to +16 MB, commit +0 to
+6 MB (`summary.py` prints `va` and `commit` per cell).

System d3d9 backend: still not measured. `run.py sys` (1080p, `proxy.backend=system`, host off) failed the headless launch before the
front end: `HEADLESS FAILED: no on_virtual status ... within 180 s (last: target_ok target resolved at Direct3DCreate9)`, the watcher
killed the game (fail closed), exactly as on 2026-11-02. The failure is with the host off, so it is the headless layer on the system
backend, not the UI. `proxy.backend` was set back to `dxvk` afterwards.

## f) acceptance and restore
- `harness/runs/20261103_j30acc/` (1 pass, **setup error, not the host**): pass 1 failed `hist_dresden:shot_match` (14.47 against 7.8)
  because the test document was on screen. `run.py` sets the `ui.*` keys with `pc_deploy set` before its first launch, the watcher's
  headless snapshot of that launch (`20261103T145114Z_j30`) therefore held `ui.enabled=1`, `ui.show=hosttest/hosttest.rml`, and the
  lock release restored the mod ini to it, undoing the `pc_deploy set` back to release values made while the lock was still held
  (watcher.log 15:47:41 UTC). Keys set to release values again with no lock held, then the run below.
- The 20-pass run on this build with the J30 keys at their release values (`ui.enabled=0`, `ui.show=` empty, `ui.scale=100`):
  `harness/runs/20261103_j30acc2/` (ledger lines with `branch job/J30`): passes 1-16 passed, pass 17 failed at `campaign_start:scene`:
  the headless launch and its one retry both ended `HEADLESS FAILED: the game exited before reporting on_virtual (last status: starting
  DllMain)`, minidumps `20261103T182311Z-p20684_c0000374.dmp` and `20261103T182324Z-p41828_c0000005.dmp` (in the game folder's
  `napoleon_remastered\dumps`, moved to `_to_delete` by the uninstall). Streak on `af34b0c1f7d1`: 16, not 20. The same start-up exit
  happened and was retried 10 times in passes 1-16 (3 times in J46's 20 passes on `7631068c014b`); J24's build `75739186b92e` (no RmlUi
  host) shows the same early exits at 4-9 an hour in `watcher.log` the same morning, so it is the PC's launch flake and not the host,
  which is off at these keys (`ui.enabled=0`: `UiInit` returns after reading the key). Stopped there: two broken runs (job instruction).
- Final build `cb34c06baf42` (after the main merge; DLL 4,225,536 B, sha256 `b9c2bc2b...`), idle host per deliverable 7 (`ui.enabled=1`,
  `ui.show` empty): `20261103_j30acc3`, `acc4` and `acc5` each broke on one scene load just over its limit while the PC had about 2 GB free
  (see the J30 report). After a reboot, `harness/runs/20261103_j30acc6/` (2026-11-03 22:35 to 2026-11-04 00:42 UTC, watcher 1.2.0, kit
  `kit_20261103T195609Z_6ee33bd89704`): **21 of 21 passes**; pass 1 carries the fresh-install kit label `6ee33bd89704` (no proxy log yet),
  passes 2-21 are 20 consecutive passes on `cb34c06baf42`. Every load stayed at or under 52 % of its limit (worst: `campaign_start` 3.5 of
  6.75 s in pass 1; `hist_lodi` 5.1-6.1 s against 14.75 s). Two launches were retried and recovered: pass 5 `hist_nile` (exit at DllMain,
  minidump `20261103T225938Z-p2052_c0000374.dmp`, fact `napoleon.proxy.init_heap_corruption`) and pass 18 `naval_small` (no `on_virtual`
  within 180 s, last status `starting DllMain`, the game spinning about two cores until killed; the retry moved a stale VirtualStore
  `headless_status.json` aside). PC load over the run, 10 s samples in `acc6_pc_load.tsv`: free RAM 18.8 to 22.6 GB, commit at most 17.7
  of 46.2 GB, CPU median 23 % (the game itself), 13 to 17 `claude` processes, no busy loop. Uninstall: identical to the snapshot (1565
  files), exe sha1 `9aebcd21...` vanilla, prefs sha256 `83b9b32b...` unchanged, no lock.
