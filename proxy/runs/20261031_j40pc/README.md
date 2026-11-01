# J40 PC sitting: campaign console checks (2026-10-31 to 11-01)

Headless watcher launches, owner `j40`, every launch `dev.skip_intro=1` with the `dev-console` profile (`dev.console=1`). The installed
kit was J12's acceptance kit `kit_20261031T194958Z_d5c606bb5661`, DLL build `31094f6055c2` (core v0.4.0, the build on `main`); new probes were
staged with `pc_deploy.py sync-lua`. `raw/<label>.json` is each ctl result; `raw/*_loop.txt` and `raw/ls_endturn*.jsonl` are the EndTurn polls.

## Before the first launch
- `save_games`: 8 files, sha1s in `raw/saves_before.sha1`, copies in `C:\napoleon_remastered_pc\_scratch\j40\saves_snapshot\`.
- Game folder snapshot: `_scratch\j40\game_before.json` (1607 entries: the J12 install in place).

## Launches and steps

| # | launch | steps | result |
|---|---|---|---|
| 1 | 4K (default) | launch | **failed**: the game exited during DllMain after an access violation in `ntdll.dll+0x5010e` (read 0x14) on a non-main thread, before any window; proxy dump `20261031T225453Z-p33012`, WER dump `Napoleon.exe.33012.dmp`. No J40 code involved. |
| 2 | 1920x1080 | `new:grand:britain`; discovery `d_ui`, `d_traits`, `d_diplo` | traits read from the agent entry; `RetrieveFactionListForDiplomacy()` gives each faction's `Relationship`. Right after `d_diplo` the scene went `campaign -> loading` and the Lua pump stopped (frames went on): one of `RetrieveDiplomacyDetails`, `RetrieveExistingTreaties`, `RetrieveDiplomaticOpinions`, `RetrieveDiplomaticStanceString`, `FactionDetails` (called with guessed arguments) breaks the campaign Lua update. Not bisected; the probes use none of them. |
| 3 | 1920x1080 | `rb0`; `declare_war spain` -> `rb1`; `declare_war denmark` -> `rb2`; select spy; `add_trait C_Agent_Spy_Network 1` -> `rb3`; `transport_to_region eur_scotland`, `eur_wales` (spy) -> `rb4-6`; select the London general; transport to `eur_wales`, `eur_scotland` -> `army1-2`; quick save `qs` | Spain was already `at war` (the 1805 start), no change; **Denmark nil -> at war**; **traits Assassin -> A Good Listener, Assassin**; no transport moved anyone. Save kept as `_scratch\j40\saves\j40_console_used.save` (sha1 `910311c4...`). |
| 4 | 1920x1080 | `campaign:zz_j40_console` (the saved game); `rb8`; EndTurn loop `et1` | after the reload Denmark is still at war and the trait kept. The turn passed (Late January 1805); the loop compared the season and missed it (both Winter): `campaign_turn.lua` now returns the HUD date. |
| 5 | 1920x1080 | reload; EndTurn loop `et2` with `campaign_modal_close.lua` | proposal (poll 3-4) and turn-start event (poll 6) cleared; Late January 1805 with End Turn back at poll 7 |
| 6 | 4K | `load_save.sh --end-turn` (`ls_endturn`) | **passed**, 118 s; one route per poll showed `DeclineOffer` alone leaves the panel up and `ClosePopup` on a later poll closes it |
| 7 | 1920x1080 | new campaign; spy `transport_to_hlci 0/1/100/1000` (`hl_*`), then `transport_to_region eur_scotland`, EndTurn `et3` | no move; **the next EndTurn crashed** at `Napoleon.exe+0x9611c9` (read 0x144, function 0xd61190 in the character position code): the queued hlci orders ran with bogus cells. Proxy dump `20261031T233328Z-p33276`, WER dump `Napoleon.exe.33276.dmp` (1.5 GB, local). |
| 8 | 1920x1080 | new campaign; spy `transport_to_region eur_scotland` only; EndTurn `et4`; `rb12` | no crash; the spy still in England at (-296, 23) next turn. `DeclineOffer`+`ClosePopup` in one call left the panel up (the order the probe uses now is one per call). |
| 9 | 4K | `load_save.sh --end-turn` (`ls_endturn2`), final probe | **passed**, 103 s: `DeclineOffer`, then `ClosePopup`, then `event_message` `OnOk` |

## At the end
- `save_games`: the game had rewritten `auto_save.save` (EndTurn) and `quick_save.save` (our quick save). Both kept in `_scratch\j40\saves\`
  (`j40_auto_save_after_endturn.save`, `j40_console_used.save`), then restored from the snapshot. `raw/saves_end.sha1` equals
  `raw/saves_before.sha1` (8 files). The staged `zz_j40_console.save` went to `_to_delete\saves_20261101T000451Z`.
- Profile restored (`profile restore`), then `pc_deploy.py uninstall`: game folder identical to the pre-install snapshot (1564 files, the
  vanilla folder J12 installed over), exe vanilla. Lock released. The PC ends uninstalled.
- New dumps this sitting: 2 crashes (launch 1 at start-up, launch 7 after bogus `transport_to_hlci` orders); every other launch exited clean.

Static trace: `proxy/runs/20261029_j15re/README.md` section "J40". Facts: `napoleon.console.acting_commands` (verified),
`napoleon.console.transport_to_region_no_move` (open, narrowed), `napoleon.campaign.modal_stops_pump` (headless handling).
