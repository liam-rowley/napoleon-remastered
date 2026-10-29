# J15 review: campaign dev console

2026-10-29. Independent review of `job/J15` at `27b8e22`, by a fresh session that did not build it (`docs/REVIEW.md`).

**Verdict: merge.**

The console works and is safe with the key off. The route is re-found on Napoleon: the slot is read 4 times and written 0 times, it held 0
on the PC, and the live campaign context is reached through a pointer chain (preference 2: no detour, no D26 change). Every address is a
checked `engine_sites` row, and the key-off path does no engine reads or writes (lint in `test_console.cpp`). `teleport_to` units are
mapped (3/3), and the save/reload keeps the moved agent. Three checks are not closed: 6d (`transport_to_region` does not move the agent),
the EndTurn in 6e (it stopped at a diplomacy modal), and the read-back in 6f. The report names all three, and the brief's call budget allows
stopping there. They need a follow-up job (below).

## Machines

- `wsc gates`: 11 ok, 1 warn (`hooks`: this clone's `core.hooksPath` is absolute, a local setup issue), 145 host tests pass, including
  `test_console.cpp`.
- Report claims checked against the evidence: the slot reads and writes against the RE README and fact
  `napoleon.console.slot_never_written`; key off against `raw/a_keyoff`; P1 against `raw/c_console/status0.json`; units against `tp1-3`/`sel1-3`
  and the fact; save/reload against `raw/e_save` and the fact; `gate_sets 0` against fact `napoleon.console.handler_gate`. No claim was missing
  its evidence.
- Spot check of the command table: 4 commands (`damage_unit`, `destroy_army`, `remove_ap`, `replenish_ap`) share handler 0x523060 and are
  `parse_only`. Disassembled: the handler only tail-calls the selection's getter (`jmp [vtbl+4]`). `split_general` (0x56bf50) calls the same
  getter twice and discards the result. Both are rightly `parse_only`: their bodies were stripped from retail.

## Risk-first reading

`proxy/core/console.cpp` (writes into engine memory: the slot and the gate byte; calls the exe's ctor and `Execute`), its wiring in
`dev.cpp`, `patch_driver.cpp` `SiteAddress`, and the 8 `engine_sites` rows. The slot claim rule, the chain and vtable checks before every call,
the set-and-restore of the gate byte (only if 0) and the lock order (scene before `s_cs`) are all correct. The rest was skimmed.

## Findings

**blocker:** none.

**should-fix (fixed on the branch by this review, one commit each):**
1. `proxy/core/console.cpp:107`, `proxy/napoleon/adapter.cpp:28`: comments said retail never sets the gate byte and leaves it 0. The PC fact
   `napoleon.console.handler_gate` says it was already set in every live campaign (`gate_sets 0`). Fixed in `6316cb9`. That comment named the fact id, which broke `test_console`'s no-game-in-core lint (CI `proxy`); `c01ff2d` rewords it.
2. `harness/core/shot.sh`: it saved full-resolution JPEGs at about 1.2 MB each. The branch added 19 of them (18.9 MB), twice the size of every
   earlier run folder together, for evidence that reads fine at 1280 px. Fixed in `0819b78`: at most 1280 px wide, quality 70, about 165 KB
   (the PowerShell code was tested on the PC against `b0_before.jpg`). `8c93f57` shrinks this run's 19 shots the same way (18.9 MB to 2.6 MB).

**should-fix (for Liam / a follow-up job):**
3. **Saves on the PC.** `raw/e_save/saves_before.txt` shows that `save_games` held `quick_save.save`, `auto_save.save` and six J14 saves (the
   brief assumed there were none). `CampaignUI.QuickSave` overwrote `quick_save.save`, and no copy of the old file was kept. The J15 quick
   save is still in `save_games` under that name, against the brief ("Remove them from save_games at the end"). This should be enforced in
   code, not prose: the watcher should snapshot `save_games` before any launch and restore it after, the same way it restores the profiles.
   J18 (PC-side rule guards) is the natural home. The report asks Liam whether the lost quick save mattered.
4. **Unclosed checks (6d, 6e EndTurn, 6f read-back).** These need a `needs_brief` row on a `plan/` branch: trace `transport_to_region`
   through 0xaa11e0 and 0xa83f90; read back `declare_war` and `add_trait` (diplomacy state and character traits); one EndTurn that passes,
   once the modal pump (`napoleon.campaign.modal_stops_pump`) is handled.

**later:**
5. `proxy/core/console.cpp:134`: `console off` writes 0 to the slot from the control thread. The executor tests the slot at 0xc5612b and
   reads it again for the call at 0xc5613e. If game Lua runs `CliExecute` on the engine thread inside that window, the call dereferences a
   null pointer. The window is a few instructions and needs a concurrent `CliExecute`, so it is unlikely. Fix: `off` leaves the forwarder in
   the slot and sets `s_on=false`, so the forwarder returns "not handled". Only empty-to-ours writes are race-free.
6. `proxy/core/dev.cpp:310`: the verb attributes the latest forwarder record to its own line without comparing names, so a game-Lua
   `CliExecute` in the same pump could be reported as this line's result. Fix: require `fname == l.name`.
7. `proxy/core/dev.cpp:302`: every `console <line>` writes `napoleon_remastered\lua\_console\<id>.lua` in the game folder and never
   deletes it. Uninstall removes the owned folder, so the restore is still byte-exact, but the files pile up during a sitting. Fix: delete the
   chunk once `RunLua` returns a result.
8. `discovery/core/x86re.py:146`: `walk` drops an indirect `jmp` (a register or memory tail call): it is recorded as neither an icall nor a
   tail. A handler whose only action is a non-selection indirect tail jump would be classed `parse_only`, and the verb would refuse it. The
   handlers checked above are correct; record indirect jumps as icalls before J9 reuses the kit.
9. `harness/core/shot.sh:10`: the Napoleon game path is hard-coded in `harness/core`. It has to come from the adapter before J12 moves the
   script to the core.

## Rule changes for other branches

None: no gate, policy or trailer rule changes with this merge.
