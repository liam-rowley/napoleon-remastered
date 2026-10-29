# J15 report: campaign dev console

Branch `job/J15`, 2026-10-29, one PC sitting (headless, J13): `proxy/runs/20261029_j15pc` (README has every step and run folder). Static RE:
`proxy/runs/20261029_j15re`. Built by Opus 5.5 as briefed. The PC ends uninstalled (identical to the pre-install snapshot, 1564 files).

## What exists

| deliverable | state | where |
|---|---|---|
| 1 no-DLL probe | done: `CliExecute` runs system commands; campaign commands fall through to the file stage. The slot is needed | run `raw/d1_nodll`, fact `napoleon.console.no_dll_reach` |
| 2 static RE | done: executor and lookup order, both dictionaries, the slot (4 reads, 0 writes), CLI ctor, `Execute` (slot 7), who builds the CLI (a manager, never the slot), the campaign context chain | `proxy/runs/20261029_j15re/README.md`, facts `napoleon.console.*` |
| 3 command table | done: 199 campaign commands (168 acts, 10 no_op, 21 parse_only) and 68 system; vs Empire: 27 new, 0 gone, 10 status changes | `discovery/core/console_cmds.py`, `20261029_j15re/*.tsv` |
| 4 forwarder + `dev.console` | done: installed at the first `Direct3DCreate9`; the install line names every site and the slot; 73 host checks | `proxy/core/console.{h,cpp}`, `proxy/tests/test_console.cpp`, `napoleon/adapter.cpp` |
| 5 `console <line>\|status\|on\|off` | done; ctl table row and section in `proxy/README.md`; `job.sh ctl` unchanged | `proxy/core/dev.cpp` |
| 6 proof in game | a b c e done; d hit but no move (open); f hits, effect not read back | below |
| 7 registries | 8 `engine_sites` verified, `dev.console` key, 6 tools, 11 facts | `registries/` |

Also: the RE kit (`discovery/core/re_env.py`: capstone and pefile from wheels pinned by sha256 into a venv outside the repo; `x86re.py`),
`harness/core/shot.sh` (virtual-display screenshot through a read-only watcher job), the `dev-console` watcher profile, Lua probes
`console_nodll`, `campaign_select` (select and read `PosX/PosY`), `campaign_camera`. `gen_tables.py` also generates `console_table.h`.

## Deliverable 6

- **a) P1:** the pointer chain `*(*0x15c4938 + 0x9fc)` finds the live campaign context, checked by `campaign+0x28 == owner+0xf4`. Our own
  CampaignCLI is built with the exe's ctor on it: preference 2, no detour, no D26 amendment needed (`raw/c_console/status0.json`, `proxy.log`).
- **b) Verbs:** `status`; `here_kitty_kitty` path `system`; `j15_no_such_cmd` path `unknown`; `give_trait` refused as a no-op; `off` releases
  the slot and a line is refused; `on` claims it again (`raw/c_console`, shots `b0_before`, `b1_after`).
- **c) `teleport_to`: units mapped.** The target equals the agent list's `PosX/PosY` exactly, 3 of 3. The handler packs each float as 12.20
  fixed point with no scaling. `CameraTarget` is a different unit and does not follow the agent (and `SelectAndZoomToCharacter` flies the
  camera to the paper edge, as on Empire), so the shots show the selection, not the spot. Agents read their position from
  `RetrieveFactionAgentsList`, so the verb needs no conversion.
- **d) `transport_to_region`:** region keys are db keys (`eur_scotland`, 159 in `regions`). The command is a campaign hit but the spy did
  not move (5 tries: sea, land, prefixed and bare key). Open, with the trace in fact `napoleon.console.transport_to_region_no_move`.
- **e) Save and reload:** teleported to `-290 23`, quick save, relaunch, `autostart campaign:zz_j15_spy`. This was the first PC run of J3's
  `campaign:<save>` target, and it worked unchanged. The spy was at `-290 23` after the reload. The EndTurn reached the AI turn with no
  crash, then stopped at an AI diplomacy modal (known: `napoleon.campaign.modal_stops_pump`), so "one EndTurn passes" is not shown.
- **f) `declare_war spain`, `add_trait C_Agent_Spy_Network 1`:** campaign hits, no crash, shots `f1`, `f2`. Their effect was not read back.

## Saves

`j15_spy_teleported.save` (the quick save after the teleport), sha1 `bb2b8dd67654d0497ddaed92652b990397f5a44d`, kept in
`C:\napoleon_remastered_pc\_scratch\J15\saves\`. The staged `zz_j15_spy.save` was moved to `C:\napoleon_remastered_pc\_to_delete\j15_saves\`.
**`quick_save.save` in `save_games` was overwritten by this job's quick save** (it was there before, from J14 or play), and there is no copy of the old one.

## Deviations from the brief, and why

- **Liam asked mid-job to set the gate byte** (`campaign+0x54`, "Set the byte as part of this work"). The forwarder sets it to 1 for one
  `Execute` call only if it is 0, and restores it. In every live campaign it was already set, so it was never written (`gate_sets 0`). It was not the
  cause of d). The new site is `campaign.handler_gate_test`.
- The verb runs lines through the engine's own Lua `CliExecute`, not by calling `console_exec_string` from the DLL. It is the same path game
  Lua takes, on the engine thread. So there are no sites for the executor or the ca_string helpers; there are sites for the slot, chain, ctor
  and `Execute`. Path `file` never appears in results: such names are refused before the run.
- **Headless existed** (J13 merged), so Liam's monitor was not used.
- Engine sites are `hook` rows used as checked addresses (call targets and read anchors), never detoured. The schema has no `call`/`read`
  kind; the fixed anchor layout was enough (no `value_offset` change needed). Their code bytes are checked at start-up even with the key off,
  like every other site (they are part of the exe's identity). With the key off, nothing in engine data is read or written and there is
  one extra log line, `console: dev.console=0`.
- The first live try refused because of a base-vtable check (fixed with the back-pointer check), and names are UTF-16 (fixed). Both are in
  `raw/c_console_try1`.
- A stopped `load_save.sh` loop outlived its shell, sent one ctl poll and killed the game at the end. It was harmless, but `TaskStop` does not
  stop a child loop; a guard for that belongs in the harness.
- The call budget was used up: d) and f) are not closed.

## What moves to the core in J12

`proxy/core/console.{h,cpp}`, `tests/test_console.cpp` (minus the adapter-byte block), `patch_driver.cpp` `SiteAddress`,
`discovery/core/{re_env,x86re,console_cmds}.py`, `harness/core/shot.sh`. Stays: `napoleon/adapter.cpp` console block, `console_sources.json`,
the TSVs.

## Open questions

**For Liam:** is overwriting `quick_save.save` a problem? Should `console` refuse while a save of the player's own exists?

**For J4 (scenarios):**
- `teleport_to` with `PosX/PosY` from the agent list is the placement route that works.
- `transport_to_region` needs the trace of 0xaa11e0 (region lookup) and 0xa83f90 (move) to see which returns early.
- Unattended EndTurn still stops at AI diplomacy modals.
- 113 handlers check `campaign+0x54`.

**For J9 (engine API):** `x86re.py` and `console_cmds.py` take an exe and an output path. The 12.20 fixed-point position (0x8809f0) is
probably the engine's common map coordinate.

**For J14 (saves):** the save after console use loads, with the moved agent kept. Read its position record in `j15_spy_teleported.save` to
tie save coordinates to `PosX/PosY`.
