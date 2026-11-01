# J40 report: Campaign console: close the open checks

Branch `job/J40`, 2026-10-31 to 11-01. PC sitting `proxy/runs/20261031_j40pc` (on core v0.4.0, build `31094f6055c2`), final build
check `proxy/runs/20261101_j40final` and acceptance run `harness/runs/20261101_j40acc` (core v0.5.0, build `f3e33f228416`). Static trace:
`proxy/runs/20261029_j15re/README.md` section "J40". The core fixes are warscape-core PR #9, merged and tagged v0.5.0 by Liam, pinned in `d465747`.
The PC ends with the final kit installed (as after J12's acceptance run) and `save_games` equal to its snapshot.

## What each deliverable found

| # | state | evidence |
|---|---|---|
| 1 `transport_to_region` | **open, narrowed** (kill criterion's outcome three, with the next step named) | fact `napoleon.console.transport_to_region_no_move`; RE README "J40"; run raw `tr_*`, `army1-2`, `hl_*`, `et3`, `et4` |
| 2 read-back | **verified** 2026-10-31, run 20261031_j40pc | fact `napoleon.console.acting_commands`; raw `rb0-rb3`, `rb8` |
| 3 EndTurn after console use and a reload | **passes unattended** | fact `napoleon.campaign.modal_stops_pump`; raw `et2_loop.txt`, `ls_endturn*.jsonl` |
| 4 three console fixes | **done** in warscape-core (one commit each, host tests), v0.5.0, pinned | warscape-core `7c96f82`, `824eff0`, `7b39c48`; `proxy/runs/20261101_j40final` |
| 5 saves left as found | **equal** to the snapshot (8 files, sha1) | `raw/saves_before.sha1`, `raw/saves_end.sha1` |
| 6 registries | 3 facts updated, 2 new probes and `campaign_turn` re-registered, gates pass | `registries/` |

1. **`transport_to_region`.** It is a campaign hit, but it never moves anyone: not the spy, not a general, not to a neighbouring land
   region, not after a full EndTurn (10 tries over 3 launches). Static trace:
   - The handler (0xaafa30) looks the key up among the region objects. The keys are the region records' strings, and the save's 72
     region keys are `eur_*`, `eur_scotland` among them.
   - On a match it calls 0xa83f90. That function does not move anything: it builds a 0x148-byte **transport order** and queues it in the
     command sink (0xa61af0).
   - The order's execute (vtable 0x1383ef8 slot 12) is a route-and-cost move that ends silently on failure.
   - The sister command `transport_to_hlci` queues the same kind of order, and those orders **do** run at end of turn: cell indices 0, 1, 100
     and 1000 crashed the next EndTurn in the path code (Napoleon.exe+0x9611c9).

   So the queue works, and the region path fails at the lookup (0xaa11e0 returns null) or at the order's route check. Telling them apart
   needs a runtime read of 0xaa11e0's return. The proxy has no memory-read verb and no watch site kind, so that is a core change; proposed
   below, not made. **`teleport_to` with `PosX/PosY` stays J4's placement route** (fact `napoleon.console.teleport_units`). The command
   status in `console_cmds.py` stays `acts` (it does create an order), so the generated table is unchanged.
2. **Read-back.** `campaign_readback.lua` returns the player's relationship with every faction (`CampaignUI.RetrieveFactionListForDiplomacy`,
   field `Relationship`) and the first agent's name, location, position and traits (the agent list entry's `Traits[].Name`).
   - `declare_war spain` changes nothing, because Britain starts the 1805 grand campaign at war with Spain (J15's target could never show it).
   - `declare_war denmark`: Denmark went from no relationship to `at war`, nothing else changed.
   - `add_trait C_Agent_Spy_Network 1` on the selected spy: traits went from `Assassin` to `A Good Listener, Assassin` (the trait's level-1 name).
   - Both survive a quick save and reload.
3. **EndTurn.** Two popups wait on the player after an EndTurn: the AI's diplomacy proposal (`diplomacy_panel`) and the turn-start event
   (`event_message`). In a **headless** launch the campaign Lua keeps pumping behind them; J14's freeze was a visible, unfocused window. The
   new `campaign_modal_close.lua` clears them from Lua:
   - The proposal: `DeclineOffer`, then `ClosePopup` on a later poll. `ClosePopup` in the same frame leaves the panel up, and so does
     `DeclineOffer` alone.
   - The event message: `OnOk`.

   `load_save.sh --end-turn` now calls it on every poll and compares the HUD date, which `campaign_turn.lua` returns as a sixth field. A turn
   is two weeks, so year and season stay the same across one (Early -> Late January 1805 are both Winter). It passed twice, 118 s and
   103 s, from the saved console-used game.
4. **Fixes** (warscape-core, all in `proxy/src`, game-agnostic):
   - `console off` leaves the forwarder in the slot and refuses lines, so it never writes 0 (`DecideSlotWrite`).
   - The verb counts a forwarder record only when it names the line's command (`RecordIsForLine`).
   - Each `_console` chunk is deleted right after `RunLua`, on every path.

   Pure host tests for both rules, and lints for one slot write and none of 0, the deletion and the match; the no-game-in-core lint passes.
   On the final build: `off` kept the slot value and refused a line, `on` let lines through again, a line acted and read back, and the
   chunk folder was empty.
5. **Saves.** The game rewrote `auto_save.save` (EndTurn) and `quick_save.save` (our quick save). Both are kept as `j40_*` in
   `C:\napoleon_remastered_pc\_scratch\j40\saves\`, then restored from the snapshot. The staged `zz_j40_console.save` went to `_to_delete`.
   Manual steps J18's guard would replace: snapshot copies before the first launch, the copy and restore at the end, and `stage_save.py clear`.

## Deviations from the brief, and why
- **Call budget:** Liam lifted it mid-job ("Bypass the call budget and continue"). Deliverable 1 went past the kill criterion's ~60 calls,
  with two more PC tests (`transport_to_hlci`, a transport left over an EndTurn).
- **No fresh install for the sitting:** J12's acceptance kit (the same DLL build as `main`) was installed. The sitting used it with
  `sync-lua` for the new probes, and ended with `uninstall` (identical to J12's pre-install snapshot, 1564 files).
- **Launch size:** most launches ran at 1920x1080 after the first 4K launch died at start-up (below). Later 4K launches (`load_save.sh`) worked.
- **Two crashes in the sitting**, neither from new code: one at start-up in `ntdll` (launch 1, before any window), and one at an EndTurn
  after the bogus `transport_to_hlci` cells (launch 7). Dumps: proxy `dumps\` copies (moved to `_to_delete` with the uninstall) and WER
  `%LOCALAPPDATA%\CrashDumps\napoleon_remastered\Napoleon.exe.33012.dmp`, `.33276.dmp`. The final-build launch and every acceptance launch
  are judged separately (run READMEs).
- **A Lua call that stops the pump:** during discovery, one of `RetrieveDiplomacyDetails`, `RetrieveExistingTreaties`,
  `RetrieveDiplomaticOpinions`, `RetrieveDiplomaticStanceString` and `FactionDetails` (called with guessed arguments) stopped the campaign Lua
  update; the scene tracker said `loading`, as in fact `napoleon.lua.string_find_stalls_pump`. Not bisected; the probes use none of them.
- **Core tests run in CI, not locally:** this PC has no g++, and `build.sh --docker` cannot run the core's null-game build (backlog B16).
  The game repo's `build.sh --docker all` on the pinned v0.5.0 ran every host test, `test_console` included.

## Open questions
- **For the core (proposal, not filed as a change):** a read-only `peek <site>+<off>` ctl verb, or a `watch` site kind that logs a
  function's return. Either would decide deliverable 1 (0xaa11e0's return) and other "hits but does nothing" commands without new detours.
- **`transport_to_hlci` crashes the game** at the next EndTurn when its cell index is wrong. Should the adapter refuse it like the no-ops,
  or should the verb refuse any command whose argument it cannot check? Today only the briefed caution stands between a typo and a crash.
- **J4:** `load_save.sh --end-turn` and `campaign_modal_close.lua` make unattended turns possible, so J4's J14 carry-over
  (`napoleon.save.endturn_survival`) can run now.
- **J18:** the save snapshot and restore here were manual (above); the watcher could do it per launch.
- **Watcher:** right after a `kill` job, its process list still names the game for a few seconds, and `pc_deploy` refuses `sync-lua`.
  Waiting for `status` to say `not_running` works; the kill job could wait for that itself.

## Finish
`wsc reg set jobs J40 status=review report=jobs/J40/report.md`
