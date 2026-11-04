# J40 review: Campaign console: close the open checks

## Round 1 (2026-11-01, branch job/J40 at 291fea2)

Independent review (Claude Code session 7f335c20, Opus as D15 allows for independent checks) of `job/J40` at `291fea2`, against
`jobs/J40/brief.md`, following `docs/REVIEW.md`. I did not build or fix this branch.

**Verdict: merge.**

### What I ran
- `wsc gates` on the branch: **11 ok, 1 warn, 0 failed** (235.9 s; the warn is skipped image and viewer tests: no numpy, Pillow or
  `viewer.wasm` on this PC). `tools/pr_policy.py --branch job/J40 --base origin/main` before this review: refused only for the missing
  review and the row not `done`, as expected. `wsc jobs review`: all 6 CI checks on `291fea2` passed or were skipped.
- warscape-core PR #9: merged 2026-11-01T06:51Z, every check green (gates on ubuntu and windows, proxy, harness-windows); `v0.5.0` is
  `e7893fe`, and `core` plus `wsc.toml` `[core] version` move together in `d465747`.
- **Claims against evidence**, opened rather than trusted:
  - Read-back (`proxy/runs/20261031_j40pc/raw/rb0..rb3, rb8`): Denmark `nil -> at war` after `declare_war denmark`, Spain `at war`
    throughout; the spy's traits `Assassin -> A Good Listener,Assassin` after `add_trait`; `rb8` (after the quick save and reload) keeps
    both. Matches the fact `napoleon.console.acting_commands`.
  - EndTurn: `ls_endturn.txt` and `ls_endturn2.txt` show the closer declining the proposal (`ClosePopup` on a later poll), closing the
    event message, and the date moving `Early -> Late January 1805` in 118 s and 103 s, each with a clean kill.
  - Saves: `raw/saves_before.sha1` and `raw/saves_end.sha1` are identical (8 files).
  - Rule 79: `harness/acceptance/ledger.jsonl` has 20 consecutive passes on build `f3e33f228416` (j40acc passes 2-20 plus j40acc2
    pass 1); j40acc pass 1 carries the kit id `d465747d7269` and is correctly not counted (see later 3).
  - Final build (`proxy/runs/20261101_j40final`): `off` kept the slot value and refused a line, `on` let one act and read back, the
    `_console` folder was empty, and the uninstall matched the pre-install snapshot (1564 files).

### Risk-first reading
I picked the three core fixes (`proxy/src/console.cpp` `SetSlot`, `console.h` `DecideSlotWrite`/`RecordIsForLine`, `dev.cpp`
`Console`), because they write into engine memory from the control thread while the engine's executor reads the same slot, and a
mistake there is a null call inside the game. Read in depth at `v0.5.0`:
- `SetSlot` now writes only on empty-to-ours; `off` sets `s_on = false` and the forwarder (`FwdRun`) refuses under `s_cs` and returns
  `false` ("not handled"), so the executor falls through as without a handler. `on` after `off` sees `Ours`, writes nothing and flips
  `s_on` back. The source lint pins exactly one slot write and no `= 0`.
- The chunk is deleted right after `RunLua`, before any result path. On a timeout `RunLua` calls `BridgeDrop(id)` first, so the bridge
  never loads a chunk that is already gone.
- `RecordIsForLine` resets `fr`, `hits` and the reason when the latest record names another command, so a game-Lua `CliExecute` in the
  same pump cannot be reported as this line's result.
- The no-game-in-core lint still passes (core CI), and the key-off path is unchanged.

Then `campaign_modal_close.lua` (it changes campaign state) and the `load_save.sh --end-turn` loop: one route per call, a try count
that resets when no panel is up, and the loop counts a turn only when the closer answered `none` and the HUD date moved. Skimmed
`campaign_readback.lua` (read only, no stalling string calls), `campaign_turn.lua` (6th field; existing readers use `_` for the
rest) and the fact and tools rows.

### Brief
Every deliverable is present. Deliverable 1 ends in the kill criterion's outcome three with the next step named (a read of
0xaa11e0's return), and `teleport_to` with `PosX/PosY` stays the placement route, as the brief allows. `declare_war spain` could not
show a change because Britain starts at war with Spain; the report names it and proves the read-back with Denmark instead. The
deviations (call budget lifted by Liam, J12's kit reused for the sitting, 1920x1080 launches, two crashes not from new code) are named
with reasons. One core round trip, one minor version, pin bump in one commit, 20 passes after the last DLL input change: all followed.

### Findings

#### Blocker
None.

#### Should-fix
None left on the branch.

#### Later
1. **`transport_to_hlci` crashes the next EndTurn on a bad cell index, and only prose stops it** (report "Open questions";
   `proxy/runs/20261031_j40pc` launch 7, Napoleon.exe+0x9611c9). How to see it fail: `console transport_to_hlci 0`, then EndTurn.
   This is an Empire repeat: a trap that should be a guard. The adapter can refuse it the way it refuses the no-ops (a status in
   `discovery/core/console_cmds.py`, regenerated `console_table.h`), which changes a DLL input and so needs the 20 passes again: a
   follow-up job, before J4 or any scenario uses the console unattended.
2. **`transport_to_region` stays open** (`napoleon.console.transport_to_region_no_move`): deciding lookup vs. route check needs a
   read-only memory read or a return-logging site kind in the core. Filed as warscape-core backlog B25.
3. **Acceptance identity on a fresh install** (`core/harness/acceptance.py` with `ctl.py` `build_info()`): pass 1 was recorded with the
   kit's id because no `proxy.log` existed yet; the streak needed one extra pass. A pass should read the build id after its launch, or
   refuse the fallback. Filed as warscape-core backlog B26.
4. **Watcher `kill` returns before the game is gone**: `pc_deploy sync-lua` refuses for a few seconds after it. The kill job could wait
   for `not_running`. Filed as warscape-core backlog B27.
5. **Save snapshot and restore were manual** (report deliverable 5): J18's guard should own them per launch, as the brief says.
6. **One Lua call among five diplomacy getters stops the pump** (report "Deviations"), not bisected. Worth one bisect before any probe
   uses them; until then the probes avoid all five.

No rule that other open job branches must meet changes with this merge (the `campaign_turn.lua` sixth field is additive).
