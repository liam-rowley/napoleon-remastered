# J59: Performance baseline on the J46 rows; budgets re-agreed

**Scope note (the row was written before J46 finished; this brief covers what J46 delivered).** The rows that exist and are measured here: `land_40`
(20 against 20, the unit cap), `naval_large` (10 ships a side) and `hist_lodi` (new), plus a re-measure of the library on the current build so the
baseline is one build. There is **no `land_large` row** (the cap is 20 units, the same as `land_40`), **no siege-city row** (`siege_small` is the siege
row; fact `napoleon.siege.city`), and **`campaign_mid` and `campaign_late` are not built** (they wait for two real saves; fact
`napoleon.campaign.end_turn_time`). The acceptance order is now 10 scenarios (J46 report, run `20261102_j46acc`; verified 2026-11-03 by the orchestrator
on 5ea3c81). Do not build rows; the tool measures what the registry has.

Phase 3. J23 baselined the seven scenes that existed on 2026-11-01 on DXVK (`perf/baseline.json`, run `20261101_j23pc`, DLL `46f52d356ce8`). J46
added the larger battles and changed naval_small and naval_storm from 10 ships to 3 (army pinned), so their old numbers are no longer those scenes.
This job re-runs `tools/perf_baseline.py` on the current build over the J46 library, extends `perf/baseline.json`, and re-proposes the per-feature
budgets against the 40-unit numbers for Liam to agree (D38). No feature work, no proxy change, nothing shipped as agreed.

Model: Sonnet, medium effort (D15 default: a driver already exists, PC runs go through the harness, the rest is writing up numbers; no DLL, shader or
reverse engineering). Budget about 110 tool calls; at the cap, stop, commit, report what is left. No subagents needed. Waiting belongs to the
harness: the matrix runs in the background inside one call and you read its summary; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J59`). Read `docs/DECISIONS.md` (D2, D15, D30, D38), `jobs/J23/report.md` (all of it: the pins, the deviations,
  the open questions) and `jobs/J46/report.md` ("Evidence", "Deviations", "Open questions"). Do not reread their briefs.
- Read `tools/perf_baseline.py` (header, `ORDER`, `scenario_list`, `poses_of`, `summarize`, `not_covered`), `tests/test_perf_baseline.py`, `perf/baseline.json`
  (its top-level keys and `not_covered`), `perf/budgets.md` and `perf/budgets.json`, and the run README `harness/runs/20261101_j23pc/README.md` for the table form.
- Search before writing: `python3 core/wsc.py find perf_baseline scenarios system_backend dxvk vram`. What you extend:
  - `tools/perf_baseline.py measure|summarize|check|compare|table`: the instrument. Extend it; do not write another. Its `ORDER` tuple lists the seven J23
    scenes and puts warm-reset scenes first (a historical battle and the campaign leave by a relaunch, `ctl.py scene`): add `hist_lodi` (single-player
    historical: warm-reset like the other `hist_*`), `land_40` and `naval_large` in the right places. Check how `not_covered` is worked out so the
    new baseline lists only `campaign_mid`, `campaign_late` and the system backend (if it still fails), with the cause.
  - `harness/acceptance/*` is the 20-pass gate's file: **do not edit it**. Its `perf` (land_40 p50 2.68 ms, p99 4.40, VRAM 835 MB, build `7631068c014b`,
    run `20261102_j46m2`, 1080p) is your first sanity check for `land_40`.
  - Scenario presets pin `army=` (J46): land_small 9 units, land_40 20v20, naval_small and naval_storm 3 ships, naval_large 10v10, siege_small is not
    pinned (it follows remembered prefs: record which army size the siege cell ran with from the scene's own readback, so the cell is reproducible).

## Decisions already made for this job
- **Same method as J23.** Same sizes (1080p, 1440p, 4K), headless on the virtual display, size outermost per lock, the size from a temporary adapter copy
  (`ctl.launch.size`), the backend with `pc_deploy.py set proxy.backend=<b>` with the game closed, three repeats, pass 0 as the warm-up that records the
  cold load (D38: cold and warm loads reported apart), the `--deploy end` 60 s battle cell. Every cell carries the J23 pins (build, kit, watcher, DXVK
  version and sha256, GPU and driver, `dxvk.conf` sha256, `gfx_*` prefs, frame cap state, date, run). A cell without them is refused: keep that.
- **Backends.** DXVK is the shipped backend and the whole matrix. The system d3d9 backend gave no Present in J23 (fact `napoleon.render.system_backend`,
  open): try it **once** at 1080p on `land_small` (two launches); if it still fails headless, record the cell as failed with its run and stop trying. If
  J16 or any later change made it work, run the system backend over the same matrix and report the DXVK against system ratios. Do not fix it here.
- **Scenes.** Everything the registry can load today: `land_small`, `land_40`, `siege_small`, `naval_small`, `naval_large`, `naval_storm`, `hist_dresden`,
  `hist_nile`, `hist_lodi`, `campaign_start`, at every pose each has (`deploy`, `turned`; `campaign_start` at its default view). The old seven are
  re-measured on this build because the DLL, the watcher and the naval armies changed; the baseline keeps one build. The J23 numbers stay in git history
  and in the report's comparison table (old against new for the seven), they do not stay in the baseline file next to the new ones.
- **Address space is the number that matters most** (32-bit, 4 GB): report the process peak and `va_used_mb` per cell, as J23 did. `land_40`,
  `naval_large` and `hist_lodi` are expected to be the new maxima; if a peak exceeds 3000 MB, say so at the top of the report and in the budgets.
- **Order effects.** J23 left one open question: frame time fell slightly with size, and 1080p ran first in every sitting. Run the sizes in the order
  4K, 1440p, 1080p this time (J23 ran 1080p first), and say whether the trend reversed (order) or held (resolution). This costs nothing extra.
- **Budgets are proposals.** Re-propose `perf/budgets.md` and `perf/budgets.json` (status stays `PROPOSED`, dated 2026-11-xx, `proposed_by` J59). Re-derive
  each feature's delta and the target (60 Hz p99 at or under 16.67 ms in every cell; the address-space stop line for J27's memory gate, currently 3400 MB)
  against the worst cell on the J46 rows, and show for each budget the headroom it leaves on `land_40` and `naval_large`. State plainly what changed against
  the J23 proposal and why. Keep the two open questions for Liam (60 or 120 Hz; the 3400 MB line) and answer them with numbers, not with a decision.
  Nothing in this job treats the budgets as agreed; Liam agrees in chat, and a later change sets `AGREED`.
- **J24 owns the shadows budget row.** J24 (shadow resolution and fit) is on the PC now and reports against the shadows row (1.0 ms p50, 1.5 ms p99,
  50 MB VA, 512 MB VRAM). Do not touch J24's files or branch (`job/J24`, `proxy/`, `harness/`, its keys and sites). Before editing `perf/budgets.*`, run
  `git fetch origin` and `git diff origin/main origin/job/J24 --stat -- perf/` to see whether J24 changed them; merge `main` into your branch if so. In the
  shadows row, change only what the 40-unit numbers force, mark it "re-proposed by J59 against land_40", and add a short paragraph saying how it sits with
  J24's numbers (J24 measured on `hist_dresden` and `siege_small`, with `land_40` only if it was on `main`): J24's report is the source for its own
  results and J59 does not re-measure shadows. If J24's report is on `main` by then, quote its measured ladder; if not, say "J24 not yet reported" and
  do not guess.
- **Out of scope:** any change to the proxy, harness, shaders, shadows, distances, DXVK (stock, pinned), `dxvk.conf` (J23 settled "ship none"), the
  acceptance baseline, the scenario library, `core/`.
- **Rule 79 status: no passes needed.** This job changes `tools/`, `tests/`, `perf/`, `harness/runs/`, `registries/` (engine_facts) and `jobs/` only, as J23
  did: no DLL input and no `proxy/` or `harness/` file other than a run folder. Check with `python3 core/proxy/tools/build_id.py` before and after (same id)
  and say so in the report. If you find you need a change under `proxy/`, `harness/` (other than `harness/runs/`) or `core/`, that is a kill criterion.
- **Core changes.** None planned; the job does not edit `core/`. If the run shows a core change is needed (for example the J23 note that `gen_tables.py`
  should skip non-proxy `config_keys` owners, or `ctl.py scene` staging a save for the campaign rows), name it in Open questions as a warscape-core
  `job/W<n>` candidate with its own brief; do not build it here.

## Deliverables
1. `tools/perf_baseline.py` extended (new scenes in `ORDER`, anything `summarize` needs to cover the larger scenes, the header `when:` line updated) and
   its tests extended in `tests/test_perf_baseline.py` (matrix expansion with the new rows, `not_covered` for the new library, a `hist_lodi` warm-reset
   case). `perf_baseline.py check` ok on the new file.
2. **`perf/baseline.json` extended** to the J46 rows, one build, with the pins; `not_covered` lists only what is still not covered and why. A run folder
   `harness/runs/<date>_j59pc/` with a README (run ids, build, kit, sizes, time windows, incidents, the table backend x size x scenario with p50, p99,
   cold and warm load, VA used and peak, commit, VRAM), the raw cell JSONs (summaries and anything over a few MB stay out; sha256 in the README), and the
   old against new table for the seven J23 scenes.
3. **Re-proposed budgets**: `perf/budgets.md` and `perf/budgets.json` (PROPOSED), with the J24 paragraph above.
4. `engine_facts` rows or updates (date, run id): per-scene VA peak and VRAM for `land_40`, `naval_large` and `hist_lodi`, `napoleon.perf.va_peak`,
   `napoleon.perf.vram_per_size` and `napoleon.perf.load_times` updated (not duplicated), the order-effect answer, and `napoleon.render.system_backend`
   with this job's result. Every claim in the report appears in a cell or a fact.
5. `python3 core/wsc.py gates` green.

## PC test
All game launches through the watcher and `ctl.py`; the agent never starts `Napoleon.exe`. Take the lock with an owner name, release it at the end.
Check `pc_deploy.py status` and the lock for a foreign owner first (J24 may hold the PC: if it does, do all host work first, then wait for the harness to
report the lock free once; never take over a lock). Install the current `main` build as a kit (`pc_deploy.py kit`, `send`, `install`; unique staged
names) and put the game back byte for byte at the end (`uninstall`, a fresh snapshot against the one taken first, as J44 step f).
a) smoke: `land_40` at 1080p on DXVK against the acceptance baseline's `perf` (within 3 times the spread of three repeats); `land_small` against the
   J23 value (p50 1.89 ms at 1080p, run `20261101_j23pc`) to see what the build change cost.
b) the matrix in the background, 4K then 1440p then 1080p, DXVK. Each mode change moves Liam's real cursor: tell Liam when the run starts and ends.
c) the one system-backend attempt.
Typical cost: about 2 hours of watcher time in the background (ten scenes, two poses, three repeats, three sizes). No sitting with Liam is needed
(the visible-window comparison and the display-mode fact stay open as J23 left them; do not start them here).

## Kill criteria
- The smoke cell (a) differs from its reference by more than 3 times the spread of three repeats and you cannot explain it in about 15 calls: stop,
  report; a baseline on an unexplained setup is worthless.
- A size cannot be launched headless twice in a row (refused topology, the virtual display's mode missing, a crash with dumps): record the cell as
  failed with its run and dumps, finish the others, do not keep relaunching. If every 1440p or 4K launch fails, stop and report.
- A scene crashes or hangs twice for the same cause: read WER and the watcher's hang folder first, mark the scene not covered with the evidence, go on.
- The matrix is still not producing cells after about 40 calls on it, or a cell's p50 spread stays above 15 % of its median after 5 repeats: write down
  what is known, mark those cells noisy in the file, finish the rest.
- The measurement needs a file under `proxy/`, `harness/` (other than `harness/runs/`) or `core/` to change, or a lock held by another owner for the
  whole of the job's window: stop and ask Liam; do not edit them and do not take the lock.
- Any change that would alter `build_id.py`'s output: stop (it would put rule 79 on this branch).
- Over about 110 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J59/report.md` with the headings: What was built (tool changes, baseline file, run folder), Evidence (the table with run ids, old against
new for the seven J23 scenes, the order-effect answer, the system-backend attempt), the budgets re-proposed and what changed against J23's, how the
shadows row sits with J24, Deviations from this brief and why, and Open questions (for Liam: 60 or 120 Hz, the stop line; for J24, J26, J27: how to
compare against the new baseline; any warscape-core candidate). Verified items carry a date and a run id. Then
`wsc reg set jobs J59 status=review report=jobs/J59/report.md`.

## Open questions (conservative reading taken; Liam may overrule before or during the build)
- **Whole library or only the new rows?** Recommend the whole library on this build (one build per baseline file, naval armies changed); it costs about
  twice the new rows alone. If Liam prefers only the new rows, run `--scenarios land_40,naval_large,hist_lodi` and keep the old cells with their build.
- **Should the baseline keep the old naval cells (10 ships) as a separate row?** Recommend no: `naval_large` is the 10-ship scene now.
- **Campaign rows.** `campaign_mid` and `campaign_late` need two real saves (J46); the baseline stays without them and `not_covered` says so.
