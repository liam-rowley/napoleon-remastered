# J46: Scenario library: the rows J44 left out

Phase 1, scenario library. J44 built the library and passed the 20-pass gate on six scenarios, and recorded what it left out
(`jobs/J44/report.md` "Not built", `jobs/J44/review.md` finding 5). This job builds those rows to the same standard: the army setup
route for the large battles, a city siege or the recorded reason there is none, the storm's numbers, grand campaign mid and late, and
the cause of the empty single-player historical list. J8 and J23 are told not to assume these rows exist; J28's 20-against-20 battle
needs the army route.

Model: Sonnet. Medium effort. The army route is the front end's own Lua (`autostart.lua`), as J44's was; a route that would need
engine memory stops at a kill criterion and is proposed as an Opus job (D15). PC: yes, unattended and headless through the watcher,
no sitting with Liam. Budget about 250 tool calls; at the cap, stop, commit, report what is left. Subagents are not needed, or one
read-only one for reading the UI scripts. Waiting belongs to the harness: `job.sh`, ctl requests and the acceptance runner block or run
in the background inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J46`). Read `docs/DECISIONS.md` (D2, D15, D30, D32), `docs/plans/PLAN.md` section 5 phase 1
  (scenario library, gate), and `jobs/J44/{brief,report,review}.md` (its Decisions, the scenario table, "Deviations", review finding 2
  on history edits). `jobs/J44/report.md` open questions "J28" and "the city siege maps" are this job's.
- Search before writing: `python3 core/wsc.py find scenario autostart army siege historical campaign load_save stage_save acceptance`.
  Extend what exists: `proxy/napoleon/lua/{autostart.lua,battles/*.txt}`, `registries/scenarios.jsonl`, `harness/napoleon/adapter.json`
  (`ctl.routes`, `acceptance.order`), `tests/test_scenarios.py`, `saves/napoleon/{stage_save.py,load_save.sh,recipes/}`,
  `proxy/tools/pc_deploy.py` (`sync-lua`). The scene verbs (`harness/ctl.py`, `harness/campose.py`, `harness/acceptance.py`) are in
  the core: use them, never edit `core/`.
- The facts to start from: `napoleon.custom_battle.armies` (open: `sp_battle3` `army_box` `AddUnit` / `SetSetup(setup, true)`, or
  `FrontEnd.LoadArmySetup(path)` -> `ValidateArmySetup` -> `SetSetup`, from J44's pack reading of the UI Lua bytecode; read it with
  `proxy/tools/luac_list.py`), `napoleon.autostart.historical`, `napoleon.campaign.determinism`, `napoleon.battle.fixed_sky`,
  `napoleon.battle.naval_siege_load`, `napoleon.battle.camera_route`.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there): how its custom-battle army setup was driven, if it was
  (`rml_mod/dev/`, `docs/learnings/LEARNINGS_HARNESS.md`, search "army"). Port the method and check every fact again on Napoleon.
- Other jobs touching the same files: J8 (queued, builds on the DLL and pin; it may merge first), J16 (queued, DLL). Their merges change
  the DLL build id; see "Rule 79" below.

## Decisions already made for this job
- **J44's standard for a row stands**: pinned `time_of_day` and `weather` by option index, sky pinned by the fixed-sky pack, measured
  `load_time_s` (date and run), two stored poses (`deploy`, `turned`: the deployment view read back with `cam read`, then turned 60
  degrees) checked against the kind's clamps, determinism proved by shots on two launches with a recorded mean difference and
  threshold max(4, 2 x measured), and a row that is not deterministic says so in the row and the baseline (as `campaign_start` does).
  Presets stay hand-written next to the rows and checked by `tests/test_scenarios.py`; `launch` is `ctl.py scene <id>`.
- **Sizes, set by measurement**: `land_40` is 20 units against 20 (J44's "40-unit battle"). `land_large` and `naval_large` are both sides
  at the custom-battle screen's own army cap (read it from the screen; record the numbers). Read `land_small` and `naval_small`'s army
  counts first (they come from `.sp_default`) and name them in the rows. Maps: the same ones as the small rows unless the cap or the clamps
  argue otherwise (say why).
- **Armies through the front end's own calls** (`autostart.lua` preset keys, e.g. `army.*`), the same way J44 drove the map list: no
  coordinate clicks, no memory writes, the result read back and checked (the proxy checks the battle map and unit counts against the
  engine's own battle details if it can; else a `state` check). A fixed army per side must not depend on the remembered preferences.
  Liam's preferences file and saves are not written: the preset sets the army for the launch only.
- **Siege city**: the custom siege list has 7 forts and no city. Try, in this order and within the time-box below: the siege type with
  `all_maps` true (as the historical list needed), other `EnumerateBattleMaps` types or maps with a city, then a settlement battle
  from a campaign. If none is reachable, record the fact (`napoleon.siege.city`) with the maps listed and stop; no row.
- **Historical list**: find why `EnumerateBattleMaps("historic", false)` is empty on this PC (compare with `true`'s 15; candidates: unlock
  state, profile or pack data, an argument's meaning; read the screen's Lua). Update `napoleon.autostart.historical` (cause, or
  "cause not found" with what was ruled out). If the cause gives a single-player Austerlitz or Trafalgar cheaply, add it as a row to the
  same standard; otherwise do not.
- **`naval_storm`** gets its measured load time, two poses and a determinism result. If rain makes its shots not deterministic, it is
  marked so and kept out of the shot comparison (load and readback still count).
- **Campaign mid and late**: `campaign_mid` and `campaign_late`, Britain as in `campaign_britain_1805`. The base save is Liam's
  `j14_taxes-changed_a.save` (never modified; staged copies only, `stage_save.py`). Generate each state by ending turns from it with
  `load_save.sh --end-turn --quicksave` (the copy is kept under `<state>/saves`); "mid" is about a third of the way to the campaign's
  end date and "late" about four fifths (read the end turn from the save or db; state the turns you chose). The kept saves are not
  regenerable by a recipe: record them in `saves/napoleon/saves.json` (name, sha256, turn, run, "generated by J46") and keep them on
  the PC only. Rows: `save` starts `campaign:zz_<name>` so `ctl.py scene` can load them once staged; the staging step is named in `launch`.
  The campaign camera has no setter (`napoleon.campaign.camera_route`), so the poses are the default view and the shot is not compared.
- **Core limit**: `ctl.py scene` does not stage saves, and that is a core change. Do not make one. Campaign rows therefore stay out of
  the acceptance order; propose "scene stages the row's save" in the report as a warscape-core backlog item with the rows as its test.
- **The acceptance order grows only with a re-measured baseline.** `land_40` joins the order (it is J23's 40-unit scene; also add its
  `perf` to the baseline, extending `acceptance.py` usage only through the adapter, not the core). `land_large`, `naval_large`,
  `siege_city` and `naval_storm` join only if deterministic, and only while one measured pass stays under about 7 minutes (20 passes
  about 2.5 hours of watcher time); say which you left out and why. The order must still cover every kind and end on a plain battle
  (`test_scenarios`). The baseline is written only by `acceptance.py measure`, never by hand.
- **Rule 79 applies**: the branch changes `proxy/` (presets, `autostart.lua`) and `harness/`, so it needs 20 consecutive acceptance
  passes on its final DLL build id, run for this branch (`CLAUDE.md` Rule 79 paragraph; the id hashes the DLL inputs' content, so a
  reword or a merge of `main` that leaves them unchanged keeps the passes). Finish every `proxy/` and `harness/` change before the
  measure run, then merge `main` in (never rebase); run `git log origin/main -- proxy core` first, and if J8 or J16 changed the DLL
  inputs since your base, merge now so the passes are on the id that will merge. A later change to the DLL inputs needs a new run.
- Lua rules: never `string.find`, `string.sub` or `gmatch` in engine Lua (`napoleon.lua.string_find_stalls_pump`, lint in
  `tests/test_repo_rules.py`).

## Deliverables
1. **Army route**: `autostart.lua` (and its header) drive the army setup for a preset; `land_40`, `land_large` and `naval_large` rows
   and presets; `napoleon.custom_battle.armies` updated with its result (or the remaining gap) and a run id.
2. **Siege city** row, or the fact recording why there is none and the maps tried.
3. **Historical**: the cause of the empty single-player list as a fact; a row only if it came cheap.
4. **`naval_storm`** measured; **`campaign_mid`** and **`campaign_late`** rows with `load_time_s` (date, run) from `ctl.py scene` on
   staged saves, and their saves in `saves.json`.
5. **Determinism** per new battle row (two launches, mean difference, threshold) as facts or in the rows, with run ids.
6. **Baseline and gate**: the order extended as above, `acceptance.py measure` on the final build, then 20 passes in a row at 1920x1080
   (`acceptance.py run`, background), ledger lines with run ids and evidence committed; `acceptance.py streak` printed in the report.
7. **Registries and tests**: `scenarios` rows; `engine_facts` with run ids; `tools` rows for anything new; `tests/test_scenarios.py` green
   for every new row and preset; `python3 core/wsc.py gates` green.

## PC test
Unattended and headless through the watcher; kits go over by `pc_deploy.py` (Lua by `sync-lua`), sha-checked; every launch uses
`dev.skip_intro=1`; the game lock is held by the job's owner id. Steps: (a) the game folder against
`C:\napoleon_remastered_pc\snapshots\pre_install_20261030T090208Z.json` before the first install; (b) the army route on `land_40`,
then `land_large` and `naval_large`; (c) siege and historical probes; (d) `naval_storm`; (e) campaign mid and late generation, then
`scene` on each; (f) determinism shots on two launches per new battle row; (g) `acceptance.py measure`, then the 20 passes; (h) uninstall
is byte-identical to the snapshot, checked after the lock is released and the profile restored; `save_games` holds no `zz_` file,
Liam's saves and every settings file are as found. Results go in a dated run report under `harness/runs/`.

## Kill criteria
- **The army route** gives no checked result after about 40 tool calls: stop that line, record the calls tried as open facts, and propose
  an Opus job (memory or bytecode level) for the army setup; `land_40`, `land_large` and `naval_large` are then not built. Do not write
  game memory.
- **Siege city and the historical cause**: about 20 tool calls each; then record the fact and move on.
- **Campaign mid and late**: if one end-turn takes more than about 3 minutes, or generating the two saves exceeds about 90 minutes of
  watcher time, stop and ask Liam for two saves from a real playthrough (one mid, one late) in the report's open questions; the rows
  then wait for them.
- **The 20-pass run** fails for three different causes you cannot fix in the harness or the tools: stop, report each cause with its
  evidence, and say plainly that the gate is not passed on this branch. A failure resets the count; fix the cause, then restart.
- **Any crash or hang** in a scenario: read WER and the watcher's hang folder first; two for the same cause, drop that scenario and go on.
- **Any write into the game folder outside a deploy, into `core/`, into Liam's saves or preferences would be needed**: stop and ask Liam.

## Finish
Write `jobs/J46/report.md`: the rows built and the ones not (each with its cause), the army route, the new scenario table (kind, load time,
poses, determinism, run ids), the baseline and the 20-pass evidence, the history-edit note (merged, not rebased), deviations from this brief
and why, and open questions (the core staging item, J28's use of the army route, J23's use of `land_40` and `perf`). Then
`wsc reg set jobs J46 status=review report=jobs/J46/report.md`.
