# J29 PC plan (the later slot)

Written 2026-11-03 by the desk phase (no PC used). The desk phase left `job/J29` with the core at v0.13.0, Napoleon's `GestureAdapter`
(`proxy/napoleon/gesture_rules.h`, wired in `adapter.cpp`), the `controls.gestures` key, the two hotkey rows and their host tests. This file
is the order of work for the PC slot; its results go to `harness/runs/<date>_j29pc/` and then `jobs/J29/report.md`.

## Before the PC: what has to land first
1. **J30 merges, then `git merge origin/main` into `job/J29`** (merge, never rebase). The gesture stage rides the RmlUi host: with
   `ui.enabled` unknown to this repo (J30 owns the `ui.*` rows) the host is off and the layer is inert (`gesture info`: "the RmlUi host is
   off"). After the merge:
   - add `"ui.enabled": "1"` to `harness/napoleon/adapter.json` `ctl.launch.keys` (W6 report, "What napoleon J29 must do");
   - expected conflicts: `core` (take v0.13.0), `wsc.toml` (`version = "v0.13.0"`), `proxy/napoleon/generated/tables.h` and
     `napoleon_remastered.ini` (rerun `python3 core/proxy/tools/gen_tables.py`), `harness/napoleon/adapter.json` (keep both: J30's `kit_ui`,
     J29's `controls.gestures` and the new `ui.enabled`). `viewer/pins.json` and `registries/config_keys.jsonl` merge cleanly (identical
     `stb_image_write` entry; `merge=union`).
   - `python3 core/wsc.py gates`, commit, push. About 8 calls.
   - **Until then the wine smoke fails on this branch** (the `tests` gate locally and CI's `proxy` job): core v0.13.0's `build.sh smoke`
     launch 6 writes `[controls] gestures=1` and `[ui] enabled=1` and expects "gesture: on: drag 6 px", but this repo has no `ui.enabled` row
     ("config: unknown key ui.enabled ... ignored", desk run 2026-11-03), so the host stays off and the layer is inert. Every other gate and
     every host suite is green. A core backlog row: the smoke should skip launches 6 and 7 for a game without the `ui.*` or `controls.gestures` rows.
2. **Run `git log origin/main -- proxy core viewer/pins.json`** for J8, J16, J27, J47, J60 changes to the DLL inputs; merge them in too.
3. **The DLL**: `core/proxy/tools/build.sh --docker all` then `--docker smoke` (the RmlUi compile is cached in `build/ui/obj`; the first build
   on a clean tree takes about 5 minutes). Note the build id (`build.sh id`). 2 calls.

## Steps on the PC (all through the watcher; owner id `J29`; every launch `dev.skip_intro=1`)
Each step is one script under `harness/runs/<date>_j29pc/` that makes all its `job.sh ctl` and `ctl.py` calls inside one tool call (waiting
belongs to the harness), writes `raw/*.json` and a table. Estimated tool calls per step include writing the script, one run, one fix and rerun,
and the commit.

| step | what | calls |
|---|---|---|
| a | game folder against `C:\napoleon_remastered_pc\snapshots\pre_install_20261030T090208Z.json`, take the lock, `pc_deploy.py kit` + `install`, sha check | 4 |
| b | frontage clamps on `land_40` | 12 |
| c | the pick proof | 14 |
| d1 | window messages against DirectInput | 4 |
| d2 | the move and rotate walk on `land_40`, then `siege_small` | 30 |
| d3 | the hotkey rows and the passed-message counts | 6 |
| e | the 20 acceptance passes (background, one call) and the streak | 6 |
| g | uninstall byte-identical, lock released, profile restored, no `zz_` in `save_games` | 4 |
| | report, registry rows (`wsc reg add engine_facts`), push | 12 |
| | **total** | **about 92**, under the brief's 200 with room for one crash triage (kill criteria) |

### b. Frontage clamps (fact `napoleon.battle.frontage_clamps`, new)
- `ctl.py scene land_40 --deploy end`, then for one unit of each class present (line infantry, light infantry, cavalry, artillery, the
  general's bodyguard): `ctl.py order <n> move x z 0 <w>` for w in 1, 2, 4, 8, 60, 120, 250 m, reading `order list` after each (`width` is the
  destination frontage UNIT+0x324, J28). The accepted min and max are where the read-back width stops following the order.
- The C++ side reads no unit class, only men alive: fit the clamps as a function of men (e.g. min = men / max ranks x file spacing). If no
  men-based rule fits the classes, record the fact as open and keep one clamp row per men band; a class read is new reverse engineering (kill
  criterion 2: propose an Opus job).
- Put the numbers in `gesture_rules.h` `kClamps` (replacing the PROVISIONAL row), update `tests/cpp/test_gesture_napoleon.cpp`, rebuild.

### c. The pick proof against `BackProjectPosition` (land_40 and siege_small; deploy pose and a pose turned 90 degrees)
- Select one unit (`BattleUI.SelectAllInfantry`, then one card, or the probe J28 used), then for 5 pairs (A, B) across the screen (corners,
  edges, centre, both above and below the screen middle, never the sky): `gesture press Ax Ay alt`, `gesture move Bx By alt`, `gesture plan`,
  `gesture cancel right` (not `esc`: W6 review asks whether Esc opens the game menu; check it once at the end and record it).
- With one unit and no clamp in the way (keep |AB| over 1 m), the plan's front-left and front-right corners are the picked ground points of A
  and B (the front edge lies on the line, draped at the ground height). One Lua probe chunk then calls `BattleUI.BackProjectPosition(x, y, z, 0)`
  for each and the table gives the pixel error: pass at 1 px or less, kill at 2 px (brief: about 30 calls, then the error table and the cause:
  aspect, fov, near plane, or the half-pixel convention of `BackProjectPosition` against D3D9 pixel centres).
- 2 scenarios x 2 poses x 5 gestures = 20 gestures, 40 points (the brief asks 10 points per pose).
- The same run checks an off-map point: press inside, move to a point past the map edge; the plan must mark the far units refused ("no ground
  under the target"). If `OrdersGroundAt` places off-map points (fact `napoleon.battle.order_off_map`: the engine walks units off the map and
  they withdraw), `placeable` needs a map-bounds test before any commit: stop the walk until it has one.

### d1. Window messages against DirectInput
- J30's fact `napoleon.ui.input_path` (on `job/J30`, verified 2026-11-02, run 20261102_j30pc) says the game makes no DirectInput mouse device:
  the mouse arrives by window messages only, so a swallowed press never reaches the engine and a replayed Alt+click is seen.
- Check it on this build: `ctl ui state` (`input_paths`: `di_mouse false`), then one `gesture press` and `release` without a drag on a unit
  card's unit in the world: the selection changes (Alt+click still selects) and `gesture info` counts one replay.

### d2. The move and rotate walk (deliverable 4; land_40, then siege_small)
Select all infantry (`BattleUI.SelectAllInfantry`), settle, then through `job.sh ctl J29 'gesture ...'`:
- **(a) move**: press and drag a 60 m line ahead of the army, release; after the settle every unit's front centre is on the planned target
  (J28's tolerances: 0.6 m, facing 1 degree, width exact) and on the drawn line.
- **(b) rotate**: Alt+Ctrl press, move right by the pixels for 90 degrees (400 px at 3840 wide; 200 px at 1920), release; every bearing
  changes by 90 +- 1. **Expect a gap**: the core's `FootDepth` floors depths at 4 m and places a front-referenced unit's centre 2 m behind its
  front, so with Napoleon's real depths under 4 m the pivot is up to 1.125 m behind the true centre and the block centre moves up to 1.59 m
  (pinned in `test_gesture_napoleon.cpp`, "KNOWN GAP"). After walk (a) the 3 m-wide blocks are deep, so (b) there should be exact; run it
  also on the start formation (31.9 m wide, 1.75 m deep) and record both. A fix is a core change (backlog row), not an adapter one.
- **(c)** Ctrl pressed and released mid-gesture (`gesture move ... alt+ctrl` then `... alt`): one switch, the pose rebased; a cancel by right press
  and by Esc sends no order; a release without a drag sends no order and replays one click.
- **(d)** deployment phase (`ctl.py scene land_40` without `--deploy end`), an empty selection, `naval_small` and `campaign_start`: no swallowed
  message, no order, `gesture info` says why. After an inert press always send `gesture release` at the same point before any move (W6 review
  finding 5: the verb remembers the button as held and the next move would box-select).
- **(e)** plain left-drag, right-drag and key messages pass (the counters' `passed` delta), Alt+F4 and Alt+Tab key messages are never swallowed
  (send them with `job.sh ctl J29 'key ...'` while a gesture is Active; never with the real keyboard).
- Fixtures for `tests/test_ctl.py` from the raw results, and a `gesture` route block in `harness/napoleon/adapter.json` with the run id.

### d3. The hotkey rows
- The rows are in (`mod.gesture.move` Alt+LeftDrag, `mod.gesture.rotate` Ctrl+Alt+LeftDrag, context `battle_land`; `hotkeys check` green).
  On the PC: with the layer on and a gesture Active, the vanilla Alt rows (Alt+S, Alt+M, Alt+1 to Alt+9) still pass as key messages (counts).

### e. The 20 acceptance passes (Rule 79)
- Only after every `proxy/` change (the clamps from step b) and the merges above. `acceptance.py run --passes 20 --run <date>_j29acc --owner J29`
  in the background inside one call; the layer is on and idle in every pass (`controls.gestures=1`, `ui.enabled=1` in the launch keys).
- Then `acceptance.py streak --build <id> --watcher <version>` printed in the report. A failure resets the count; three causes not fixed = stop.

## Open questions for Liam (carried to the report)
1. Line semantics (the press is one end of the drawn line) against Empire's grab (the press point is a handle on the block).
2. The rotate pivot: 0 m (in place) now; Empire used 2 m ahead.
3. What J38 needs to ship gestures: `dev.orders`, `dev.camera` and the scene tracker's Lua bridge are dev keys the player ini omits (D46), and
   `ui.enabled=1` (core B57). `controls.gestures` is omitted from the player ini until then (`release/napoleon/release.json`).
4. The order sound (20 orders in one millisecond), the bodyguard that does not hold its facing, grouped selections (`OrdersSelection` reads loose
   units only; a grouped-only selection is inert with that reason).
