# J4 report: Scenario library, control API, acceptance gate

**The phase 1 gate is NOT passed.** The route probe hit the brief's kill criterion (the battle script objects are unreachable from `ctl lua`),
so `cam`, `order`, `pause` and `speed` answer `refused` with that reason, no 20-pass run exists, and the scenario library was not extended.
What is built is the host-side layer, the proxy frame-time recorder, the rules as code, and the facts that decide the next job.

## What was built
- **`harness/core/ctl.py`** (control API; result contract in its header, tests `tests/test_ctl.py`): verbs `scene`, `cam`, `shot`, `order`,
  `pause`, `speed`, `reset`, `perf`, `state`; `key`/`click`/`wait` are refused as probe-only. `scene` (autostart a battle preset of the same id, then
  settle), `shot`, `reset`, `perf` and `state` are tested against a fake game only; **none has been run through the CLI on the PC** (only the
  proxy's own `autostart` and `lua` verbs were run there, by hand). `cam`, `order`, `pause`, `speed` are refused by the adapter's `ctl.routes`.
  Settle = scene ready + N frames + scene stable for T ms (adapter `ctl.settle`: 30 frames, 2000 ms, **provisional, not measured**).
- **Proxy**: `dev.perf` (default 0, release 0, `config_keys` row, shipped ini, `test_dev` lint) and ctl `perf <seconds>`: p50, p99, max, mean, frame count,
  address space (used, total, free), commit and working set, from a recorder in the Present path (`proxy/core/dev.cpp`, `ComputeFrameStats` in
  `devcore.h`; host tests pass in docker, 151 checks in `test_dev`). **Not run on the PC.** VRAM is not read; the plan is `nvidia-smi` from a watcher
  job (`ctl.perf.vram_source`). Also `lua <file> [t] -- <args>` (args via `wsp.dev_config("lua_args")`), confirmed on the PC (run 20261029_j4pc, 2026-10-29).
- **`pc_deploy.py sync-lua`** (J3 review item 6): changed dev Lua files are copied with unique staged names and a sha check and recorded in
  `install.json`; test in `tests/test_pc_deploy.py` (uninstall stays byte-exact). Used on the PC.
- **`harness/core/acceptance.py`** (tests `tests/test_acceptance.py`): baseline schema and checker, comparisons (load time tolerance, shot threshold,
  settings files, exe sha1 pin), ledger and streak, `run_pass` against injected fakes. `run` loads and validates the baseline (it refuses without
  one) and then stops: the PC binding (launch, exit, shot, settings snapshot) is **not wired**. No `baseline.json` is committed (no measured one
  exists); `harness/acceptance/ledger.jsonl` is committed empty and marks rule 79 active for later branches.
- Probes `battle_api.lua`, `battle_route.lua`, `battleui_names.lua`, `echo_args.lua`. Registries: `tools` rows, `config_keys` `dev.perf`, three `engine_facts`.

## Route probe answers (run `harness/runs/20261029_j4pc`, land_small only)
- `empire_battle`, `battle_manager`, `camera` and controllers are **unreachable** from `ctl lua` (fact `napoleon.battle.script_api_reachable`, refuted).
  Not probed: siege, naval, the campaign camera calls.
- The UI Lua has a `BattleUI` table with camera, order and speed calls (`CameraZoomTo`, `RequestSpeed`, `Current_Selection_*`); none was called.
- The battle UI pump stops by itself 20 to 175 s after the load; the cause is unknown. This limits every `ctl lua` verb in a battle.
- About 17 of the 20 calls the kill criterion allows were spent on the route.

## Rules into code
| row | where | test |
|---|---|---|
| 77 | `make_result` turns an ok without a `check` into failed | `test_ctl.Contract.test_row77_*` |
| 78 | scan of scenario rows, battle presets and `acceptance.py` for key or click | `test_ctl.Rule78` (with a test that the scan catches one) |
| 79 | `tools/pr_policy.py acceptance_problems`: a `job/` branch that changes proxy/ or harness/ needs 20 consecutive ledger passes on its DLL build id and watcher version; active once `harness/acceptance/ledger.jsonl` is on the base, so J4's own branch is exempt | `test_pr_policy.Rule79` (failing fixture: 19 passes) |
| 74 | baseline schema and checker; `run` refuses without a valid baseline | `test_acceptance.Baseline` |
| 28 | `exe_pin_ok` is the first step of a pass; J18's guard was not called (not checked whether it landed) | `test_acceptance.OnePass.test_a_wrong_exe_*` |
| 75 | **not done**: `wsc jobs view` PC state and a usage source | hand to a meta job |

## Not done
- Deliverable 2 (scenario library): no new rows, presets or load times; historical, campaign mid and late, naval and siege variants are open. `scene`
  refuses historical and campaign rows with their open state.
- Deliverable 4 (fixed sky and weather, determinism proofs): not started; no row is marked deterministic.
- Deliverables 6 run and 7 (the 20-pass run, committed baseline, ledger lines): impossible without the camera route.
- Deliverable 9 (J14 carry-over): not run; J40's answer was not checked.

## Deviations
- Stopped at the kill criterion instead of building the library on poses that cannot be set.
- One scratch Lua file was written into `napoleon_remastered\lua` (an args test) and removed at once; it was outside a deploy and I should have used `sync-lua`.

## Proposed follow-ups
- **Opus job: the camera and speed route.** First test the `BattleUI.*` calls and find why the pump stops; if that fails, port Empire's `camctl`
  (`rml_mod/src/camctl.h`) into the proxy. Everything else in J4 waits on it.
- Then a Sonnet job for the rest of J4: scenario library, sky pin, determinism, baseline, the 20-pass run, rows 75 and 28's J18 call.
- Core: no schema change proposed. `ctl.py`, `acceptance.py` and `sync-lua` are J12 candidates once they have run on the PC.

## Open questions
- J8, J9, J23, J28: all blocked on the gate. J23 builds on `perf` (written, untested on the PC). J28 owns `order` and its route.
- J12: promote `ctl.py`, `acceptance.py` and `sync-lua` after a PC run.
- Does `require "Scripting_Library"` stop the pump? One launch, not isolated.
