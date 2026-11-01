# J23: Performance baseline: system d3d9 against DXVK

Phase 3, job 1 (PLAN section 5). Measure what Napoleon costs today, so every later phase 3 change (J24 shadows, J26 cascades, J27 distances)
is reported against a committed number: frame time p50 and p99, load time, address space, commit and VRAM, for the proxy on the system
d3d9 (`proxy.backend=system`) against the pinned stock DXVK, at 1080p, 1440p and 4K, across the scenario library J44 built. Settle DXVK's
display mode and its `dxvk.conf` defaults. Propose per-feature budgets for Liam to agree. No feature work, no proxy change.

Model: Sonnet, medium effort (D15 default: a Python driver in `tools/`, PC runs through the harness, and writing up numbers; no DLL, shader or reverse
engineering). Budget about 150 tool calls; at the cap, stop, commit, report what is left. No subagents needed. Waiting belongs to the harness:
the matrix runs in the background inside one call and you read its summary; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J23`). Read `docs/DECISIONS.md` (D2, D15, D30), `docs/plans/PLAN.md` phase 3 item 1 and section 5 phase 1
  ("Frame-time and memory capture"), `harness/README.md` ("Config profiles", "Headless launch") and `harness/napoleon/adapter.json` (`ctl`, `headless`).
- Reports to read first: `jobs/J44/report.md` ("The scenario table", "The baseline and the 20 passes", Open questions: J23), `jobs/J13/report.md`
  (Open questions 4 and 5) and `jobs/J13/review.md` (Later 4), `jobs/J4/report.md` (the `perf` verb). Do not reread their briefs.
- Search before writing: `python3 core/wsc.py find perf ctl acceptance headless dxvk vram`. What exists and what you extend:
  - `core/harness/ctl.py` `scene`, `cam`, `reset`, `perf <seconds>`: one checked JSON result per verb; `perf` returns `frame_ms` (p50, p99, max, mean),
    `frames`, `mem` (address space used/total/free, commit, working set, peak) from the proxy's Present-path recorder (`dev.perf`), VRAM (Windows
    `GPU Process Memory` per pid plus `nvidia-smi` for the device) and the build, backend and size. It is the measuring instrument; do not write another.
  - `harness/acceptance/baseline.json` `perf` (1080p, DXVK, `land_small` deploy pose: p50 1.84 ms, p99 3.31, VA 1899 of 4096 MB, commit 1213, VRAM
    595 MB, build `dc95ededfbe8`, 2026-10-30): your first sanity check. `harness/acceptance/*` is the 20-pass gate's file: **do not edit it**.
  - Scenarios: `registries/scenarios.jsonl`; poses by id (`deploy`, `turned`); the acceptance order (`hist_dresden hist_nile campaign_start naval_small
    siege_small land_small`) plus `naval_storm` (in the library, no poses, load never measured).
  - Facts: `napoleon.dxvk.menu_display_mode` (open), `napoleon.dxvk.pipeline_cache`, `napoleon.env.dxvk_state_cache_path`, `napoleon.proxy.fpu_precision`,
    `napoleon.ctl.settle_signal`. Config keys: `proxy.backend`, `proxy.dxvk_path`, `dev.perf`, `headless.*`.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there): `docs/learnings/` on DXVK, frame pacing and memory. Port the
  method, then check every number again on Napoleon.

## Decisions already made for this job
- **Measure through the existing verbs, in the background.** A new `tools/perf_baseline.py` (header and `tools` row; `measure`, `check`, `compare`)
  drives `ctl.py` over the matrix backend x size x scenario x pose x repeat, and writes one JSON per cell plus a summary. It lives in `tools/`, **not**
  `harness/`: a new file under `harness/` or `proxy/` would make rule 79 demand 20 acceptance passes on this branch. Likewise no new profile folder
  under `harness/napoleon/profiles/`: set the backend with `pc_deploy.py set proxy.backend=<dxvk|system>` while the game is closed.
- **The size comes from a temporary copy of the adapter** (`ctl.launch.size` set to `1920x1080`, `2560x1440`, `3840x2160`, passed with `--adapter`);
  the committed adapter is not edited, and there is no core change (`core/` is read-only; a core change would be a warscape-core PR plus a pin bump,
  which rule 79 counts again). If that cannot work, stop and ask (kill criteria).
- **Headless on, and said so.** All cells run headless on the virtual display (the harness's only mode; J13 proved 1080p, 1440p, 4K with 0 ms on a real
  monitor). The report states the size per cell, that headless runs windowed borderless, that the guard thread takes the Present lock
  (J13 review Later 4), and that Liam may have been using the PC (note the time windows). One visible comparison is part of the Liam-present
  sitting below.
- **Pin what a number belongs to**, in the baseline file: DLL build id, kit, watcher version, DXVK version and sha256 (`fetch_dxvk.py --print-pin`),
  GPU and driver, `dxvk.conf` sha256, `prefs` graphics keys and the vsync / frame-limit state (a p50 of 1.8 ms means the frame is not capped; state
  what caps or does not), date, and the run id of every cell. A cell without these is not a baseline.
- **Cells.** Each scenario of the library that exists today (the six acceptance rows plus `naval_storm`) at each of its poses; scenes without poses
  (`naval_storm`, `campaign_start`) at the settled default view. Per cell: `scene` (load time as the verb reports it), `perf 20`, three repeats, report
  median and spread; first launch per backend and size is a warm-up that does not count (DXVK's cache: fact `napoleon.dxvk.pipeline_cache`). Also one
  `--deploy end` run of `land_small` for 60 s at 1x with `perf`, because a deployment view is not a battle in progress. Address space is the number that
  matters most (32-bit, 4 GB): report the peak seen, not only the value at the end of `perf`.
- **Rows that do not exist yet are not built here.** Land large, the 40-unit battle, naval large and the city siege belong to J46 (needs_brief); the
  tool takes its scenario list from the registry and `--scenarios`, so J46's rows are measured by re-running it, and the baseline file says which
  rows it covers. `docs/plans/PLAN.md` and rows J24 and J27 name "the 40-unit battle": see Open questions.
- **Budgets are proposals.** `perf/budgets.md` (marked PROPOSED, dated) gives for each later feature (shadow resolution and fit, cascades,
  imposter and LOD distances, the upscaler, UI) a frame-time budget (p50 and p99, at 1080p, 1440p, 4K) and a memory budget (address space, commit,
  VRAM) with the reasoning from the baseline's headroom, a target frame rate, and a proposed address-space stop line for J27's memory gate. Liam
  agrees or changes them in chat; nothing in this job treats them as agreed.
- **Out of scope:** any change to the proxy, shaders, shadows, distances, DXVK itself (stock, pinned), the acceptance baseline, the scenario library.

## Deliverables
1. `tools/perf_baseline.py` with a header and `tools` row, and host tests (`tests/test_perf_baseline.py`: matrix expansion, median and spread,
   baseline-shape validation, compare thresholds, refusal of a cell without its pins). `check` validates a baseline file; `compare --run <dir>`
   prints a table of a later job's `perf` runs against the baseline and flags a breach of the budget.
2. **The baseline:** `perf/baseline.json` (committed; the file every later phase 3 job reports against) and a run folder
   `harness/runs/<date>_j23pc/` with a README (run ids, build, kit, profile, sizes, time windows, incidents) and the raw cell JSONs
   (summaries and anything over a few MB stay out; sha256 in the README). A short table in the README: backend x size x scenario with p50, p99, load
   time, VA peak, commit, VRAM, and the DXVK against system ratio.
3. **DXVK display mode:** settle `napoleon.dxvk.menu_display_mode`. Needs Liam (visible window on his primary): see PC test. Read the window style and
   what DXVK does for a fullscreen D3D9 request (the pinned release's own source and docs), compare vanilla and DXVK on the same prefs, record the result
   as a verified fact with date and run id. If Liam is not there, leave it open with the exact step he needs, and finish the rest.
4. **`dxvk.conf` defaults:** from the pinned release's documented options, choose and measure the ones that can matter for this game
   (frame latency and back-buffer count, `d3d9.maxFrameRate`/present interval, `d3d9.maxAvailableMemory`, texture upload and shader-compile
   options as the pinned release has them; confirm the names against the release, not memory). Each default you settle becomes a `config_keys` row
   (owner `dxvk`, default and release value, what it does, the measurement behind it) and, if it is not already so, the shipped `dxvk.conf`
   (adapter `dxvk_conf`). Change at most one option at a time and re-measure `land_small` and `siege_small` at 1080p and 4K; keep a default that is
   not slower. An option that needs a proxy change goes to Open questions, not into this job.
5. `perf/budgets.md` as above, with the headroom each budget leaves.
6. `engine_facts` rows (date, run id): the DXVK against system ratios worth keeping, address-space peak per scene and size, VRAM per size, whether the
   system backend changes load time, and the display-mode answer. Every claim in the report appears in a cell or a fact.
7. `python3 core/wsc.py gates` green.

## PC test
All game launches through the watcher and `ctl.py`; the agent never starts `Napoleon.exe`. Take the lock with an owner name, release it at the end.
Install the current `main` build as a kit (`pc_deploy.py kit`, `send`, `install`; unique staged names), check `status`, and put the game back
byte for byte at the end (`uninstall`, a fresh snapshot against the one taken first, as J44 step f).
a) smoke: `land_small` at 1080p on DXVK reproduces `baseline.json` `perf` within the noise you measure; if not, find out why before the matrix.
b) the matrix, in the background: 2 backends x 3 sizes, in the order that avoids switching the virtual display more than needed (size outermost
   per lock, backend innermost). Each mode change moves Liam's real cursor; run size changes together and tell Liam when the run starts and ends.
c) the `dxvk.conf` sweep of deliverable 4 (DXVK only).
d) **One short sitting with Liam present, ask before starting:** visible window (`visible=1`) with `gfx_fullscreen true` through the profile mechanism
   (prefs restored byte for byte) on DXVK, then on the system backend: record the window style, whether a mode change happened and what Liam sees;
   plus `land_small` `perf` visible against headless at 4K. Liam launches nothing; the watcher does.
Typical cost: 2 to 3 hours of watcher time in the background. Check `wsc jobs view` / `pc_deploy.py status` once at the start for a foreign lock.

## Kill criteria
- The smoke cell (a) differs from `baseline.json` `perf` by more than 3 times the spread of three repeats and you cannot explain it in about 15
  calls: stop, report; a baseline measured on an unexplained setup is worthless.
- A size or backend cannot be launched headless twice in a row (refused topology, the virtual display's mode missing, a crash with dumps): record
  the cell as failed with its run and dumps, finish the other cells, do not keep relaunching it. If every 1440p or 4K launch fails, stop and report
  (J48 and J16 are the known display risks).
- Changing the size needs a core change or the committed adapter edited: stop and ask Liam; do not edit `core/` or `harness/`.
- A measurement run is still not producing cells after about 40 calls on it, or a single cell's spread stays above 15 % of its median after 5
  repeats: write down what is known, mark those cells noisy in the file, and finish the rest.
- Over about 150 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J23/report.md`: what exists (tool, baseline file, run folder), the headline table with run ids, the `dxvk.conf` and display-mode
answers, the proposed budgets and the reasoning, which scenarios are not covered and why, deviations from this brief and why, and Open questions
for Liam, J24, J27 and J46. Then `wsc reg set jobs J23 status=review report=jobs/J23/report.md`.

## Open questions (conservative reading taken; Liam may overrule before or during the build)
- **The 40-unit battle does not exist** (J44: land large, land 20 against 20 and naval large need the army setup route, J46). J24 and J27 measure
  against it. This brief baselines what exists now and ships the tool that adds rows; it does not wait for J46 and does not build rows. Should
  J23's baseline be extended after J46 lands (a small follow-up run), and should budgets then be re-agreed against the 40-unit numbers?
- **Real-monitor versus headless numbers** are compared only in the Liam-present sitting; is a visible-window baseline wanted for every cell?
- The row says "load time" per backend: DXVK's shader cache makes the first launch slower (fact `napoleon.dxvk.pipeline_cache`: n=1, no gap seen);
  this brief reports cold and warm separately rather than only a warm number.
