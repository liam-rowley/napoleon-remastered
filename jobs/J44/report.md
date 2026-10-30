# J44 report: Scenario library and the 20-pass acceptance gate

RESULT_LINE

Runs: `harness/runs/20261030_j44pc` (verbs, sky, historical route, baseline), `harness/runs/20261030_j44acc` (first 20-pass attempt: failed pass 1),
`harness/runs/20261030_j44acc2` (the gate run). Build: DLL `dc95ededfbe8` (kit `kit_*_dc95ededfbe8`), watcher 1.0.1, 1920x1080 headless.

## The verbs on the PC
All but `order` ran through `ctl.py` on the PC (results in `harness/runs/20261030_j44pc/raw/`; table in that README):
- `scene` now launches by itself: the adapter's `ctl.launch.keys` (incl. `dev.camera=1`, `dev.perf=1` and the fixed-sky file rule) are set with
  `pc_deploy set` before a watcher launch, never by callers. From the front end it autostarts; from a battle it warm-resets; from a campaign or a
  historical battle it relaunches. `--deploy end` (the row's `launch` names it) ends deployment and checks the battle clock runs. The loaded
  row is kept per game pid in `<state>/ctl/_ctl_session.json`, so a siege is a siege in a later CLI call (J43 review 3).
- `shot` (shot.sh into `--out`), `perf` (VRAM: Windows `GPU Process Memory` counter per pid plus nvidia-smi for the device; build id from the
  DLL's own load line), `state`, `reset`, and `cam read` (the pose as it is, used to find the stored poses).
- Settle (`ctl.settle`: scene ready + 30 frames + 2000 ms stable, one value for every kind): it ends about 2.7 s after the load answer; a
  shot then is within the 2.56/255 noise floor of one 10 s later. Fact `napoleon.ctl.settle_signal` (verified), run id in the adapter.
- A real bug found and fixed: `perf` frame times were quantized to 0/8/16 ms because the engine thread's FPU runs at 24 bits after device
  creation (fact `napoleon.proxy.fpu_precision`); the delta is now taken in integer ticks (`devcore.h PerfDeltaMs`, `test_dev`). After:
  p50 1.84 ms, p99 3.31 ms on land_small.

## The scenario table
| id | kind | load s (baseline) | poses | determinism (two launches, mean abs /255) |
|---|---|---|---|---|
| land_small | land | LOAD_land_small | deploy, turned | DIFF_land_small |
| siege_small | siege | LOAD_siege_small | deploy, turned | DIFF_siege_small |
| naval_small | naval | LOAD_naval_small | deploy, turned | DIFF_naval_small |
| naval_storm | naval | not measured | none yet | not measured (in the library, not in the acceptance order) |
| hist_dresden | historical (land) | LOAD_hist_dresden | deploy, turned | DIFF_hist_dresden |
| hist_nile | historical (naval) | LOAD_hist_nile | deploy, turned | DIFF_hist_nile |
| campaign_start | campaign | LOAD_campaign_start | default view (no setter) | DIFF_campaign_start: **not deterministic** |
| campaign_britain_1805 (+2 J14 recipes) | campaign | J14's | default view | not measured (load_save.sh route, not ctl scene) |

Not built: land large, land 40 (20 against 20), naval large (fact `napoleon.custom_battle.armies`, open: armies come from the remembered prefs,
the army setup route was not driven), siege city (the custom siege list has 7 forts and no city), grand campaign mid and late (recipes not
wired into `scene`). Poses are the engine's deployment view read back (`cam read`) and that view turned 60 degrees: inside the clamps by
construction (same position and height). `tests/test_scenarios.py` checks rows and presets agree (type, map, weather and time-of-day option
indexes, launch command, no orphan preset, pitch clamp, the acceptance order).

## Sky and weather, per kind
- Weather and time of day: no random option exists (`napoleon.battle.weather_options`); presets pin them by 0-based index through
  `SetPerBattlePrefs`, read back in the autostart result.
- Sky: picked per launch among the skies that fit (`napoleon.battle.fixed_sky`). A junction cut alone did nothing; cutting `battle_sky_types`
  too pinned it on 5 launches of 6, and pass 1 of the first run showed why not 6: 11 groups still had two skies. The pack now keeps exactly
  one per group ("clear" first) and points the junction at it (`proxy/tools/build_fixed_sky_pack.py`, `tests/test_fixed_sky.py`), served by a
  `dev.file_rules` add rule: zero bytes written into `data\`.
- Land, siege, naval, historical: deterministic (thresholds max(4, 2 x measured diff)). Campaign: not deterministic (the camera pans by
  itself, no setter: `napoleon.campaign.determinism`); its shot is taken and kept but not compared; load still counts.

## The baseline and the 20 passes
GATE_SECTION

## Rules as they now stand
| rule | where | test |
|---|---|---|
| 28 | `exe_pin_ok` (identity.json sha1) is the first step of every pass; J18 has not landed (queued), so its guard is not called | `test_acceptance.OnePass.test_a_wrong_exe_*` |
| 74 | `baseline_problems`; `run` refuses without a valid baseline; the baseline is written only by `measure` | `test_acceptance.Baseline` |
| 75 | `wsc jobs view` shows the PC block when run on the PC: lock holder, watcher version and heartbeat, installed kit, last acceptance pass; usage source: **none** (no tool on the PC can read Claude usage numbers): handed to a meta row | `test_jobs.PcState` |
| 77 | `make_result` turns an ok without a check into failed (unchanged) | `test_ctl.Contract` |
| 78 | scan of rows, presets and acceptance.py for key/click (unchanged; covers the new presets) | `test_ctl.Rule78` |
| 79 | active once the base holds the ledger and a baseline that the **base's** `acceptance.py` accepts (`show(a.base, ...)`, J4 review round 2); a pass counts only with a `run` and an `evidence` file committed on the branch (J4 review 7); exemptions by path segment, not substring (J4 review 6) | `test_pr_policy.Rule79` (failing fixtures: uncommitted evidence, a weakened checker, `README.md.bak`) |

Merging this branch turns rule 79 on for every later `job/` branch that changes `proxy/` or `harness/`.

## Deviations
- **Historical battles are the NHMPB_ setups** (Dresden 3v3, the Nile 1v1), not Austerlitz and Trafalgar: `EnumerateBattleMaps("historic",
  false)` lists no single-player NHB_ battle on this PC (the vanilla button makes the same call; cause open). The target is `battle:<preset>`
  with `type=historic` rather than a new `historical:<key>` DLL target: no DLL change was needed.
- **`deploy: end` lives in the row's `launch`** (`ctl.py scene <id> --deploy end`): the core scenarios schema has no such field
  (`additionalProperties: false`). Determinism is stated in the row's `weather` text and the baseline, not a field. Proposed core fields:
  `deploy`, `deterministic`.
- **Presets are hand-written next to the rows and checked by a test**, not generated by a tool: the generator would have to parse the same
  free text the test reads.
- **Merged `main` instead of rebasing**: a rebase rewrites the commits and so the DLL build id (`git log -1 -- <DLL inputs>`) the 20 passes
  are tied to; `main` had only brief commits.
- **Two harness guards added from incidents**: `Pc.launch` moves UAC VirtualStore copies of the mod folder aside before every launch (fact
  `napoleon.harness.uac_virtualstore`: it hid every headless status from the watcher for 11 minutes) and retries a lost headless start once,
  recorded in the pass file (`retried_after`). The proxy-side cause is J16's (it owns the headless code).
- `perf` on "the 40-unit battle": does not exist; land_small only (baseline `perf`).
- J14 carry-over: not run, J40 is queued (no answer for the diplomacy modal). Spent nothing.
- Calls: CALLS.

## Open questions
- **J8**: the scenes to catalogue are the acceptance order; lighting is pinned by the fixed-sky pack only with `dev.file_rules` set (the
  `ctl.launch.keys`), so frame captures should go through `ctl.py scene`.
- **J12**: core candidates: `ctl.py` (with `campose.py`), `acceptance.py`, `build_fixed_sky_pack.py` (the method; the tables are per game),
  `sync-lua`; the VirtualStore guard belongs in the core watcher or launcher, not only in `ctl.py`.
- **J16**: the proxy's status writes under Program Files can fall into UAC virtualization after one failed rename (evidence in the run
  README, Incidents): a manifest without virtualization, or a retried rename, would remove the cause. One heap corruption 10 ms after init
  (dump in the run README) was not seen again.
- **J23**: build on `perf` (frame times now correct) and `baseline.json` `perf`; DXVK is the only backend measured.
- **J28**: `order` stays refused; the 20-against-20 battle needs the army setup route (`napoleon.custom_battle.armies`).
- Why the single-player historical list is empty here (unlock state? profile?), and the city siege maps.
- Usage source for rule 75: a meta row.
