# J23 report: Performance baseline: system d3d9 against DXVK

**The baseline exists for DXVK at 1080p, 1440p and 4K across the seven library scenes (`perf/baseline.json`, 39 cell keys, run
`harness/runs/20261101_j23pc`). The system d3d9 side does not: on `proxy.backend=system` no Present reaches the proxy's hooks, so the
headless launch fails closed and the perf recorder would read nothing (fact `napoleon.render.system_backend`, open, owner J16).** Frames
are cheap and do not scale with resolution (worst p50 4.47 ms, worst p99 6.70 ms, both hist_dresden at 1080p; 4K is no slower than 1080p);
address space is the scarce resource (peak 2096 MB of 4096, flat across sizes, while VRAM grows with size). No `dxvk.conf` option beats the
stock defaults (run `harness/runs/20261101_j23sweep2`): ship none. Budgets are proposed in `perf/budgets.md` (PROPOSED). The display-mode
fact stays open: Liam could not sit today (2026-11-01); the pinned DXVK source gives the expected answer.

Build: DLL `46f52d356ce8` (main at 1bad1e0), kit `kit_20261101T205936Z_f08b12c3806a`, watcher 1.2.0, DXVK 3.1.1 stock (sha256
`265888c3...97fa`, the pin), no `dxvk.conf`, RTX 4090, NVIDIA 617.14, headless (windowed borderless on the virtual display at the cell size,
the guard thread in the Present path). Runs: `20261101_j23smoke` (step a), `20261101_j23pc` (the matrix, two sittings), `20261101_j23sweep`
(invalid, kept: see Deviations), `20261101_j23sweep2` (the `dxvk.conf` sweep). Time windows 2026-11-01 21:00 to 2026-11-02 00:45 UTC;
Liam was in the chat and may have been using the PC.

## What exists
- **`tools/perf_baseline.py`** (header, `tools` row, `tests/test_perf_baseline.py`: 13 host tests): `measure` drives `core/harness/ctl.py`
  (`scene`, `cam`, `perf`, `speed`) over size x backend x DXVK variant x pass x scenario x pose, one JSON per cell with its pins (build, kit,
  watcher, backend, size, DXVK version and sha256, GPU and driver, `dxvk.conf` sha256 and what DXVK's log says it read, every `gfx_*` pref,
  the frame-cap state, date, run); `summarize` writes the baseline shape (medians and spreads, cold and warm loads, DXVK/system ratios,
  `not_covered` worked out from refused cells and the registry, the measuring conditions); `check` validates a baseline; `compare --run <dir>
  --feature <name>` flags budget breaches; `table` prints the Markdown table. A cell without its pins is refused; a DXVK variant cell is
  refused unless DXVK logged `Found config file`. The size comes from a temporary copy of the adapter (`ctl.launch.size`, under
  `_scratch/`); the backend from `pc_deploy set` with the game closed; nothing under `core/`, `harness/` or `proxy/` changed (no rule 79 run).
  Peak address space is read host side (Get-Process `PeakVirtualMemorySize64`; its current value equals the proxy's `va_used_mb`: 1833.1
  against 1833, run `20261101_j23smoke`).
- **`perf/baseline.json`**: the file later phase 3 jobs report against (`perf_baseline.py check`: ok).
- **`perf/budgets.md`** and **`perf/budgets.json`** (PROPOSED), **`perf/dxvk_sweep.json`** (the variants).
- Run READMEs `harness/runs/20261101_j23pc/README.md` and `harness/runs/20261101_j23sweep2/README.md` with the generated tables; raw cells
  committed (`cells/`, about 0.6 MB for the matrix).

## The headline table (DXVK; medians of 3 passes; run 20261101_j23pc; full table in the run README)
| scene (pose) | p50 ms 1080p / 1440p / 4K | p99 ms 1080p / 4K | load s (cold) | VA used / peak MB | commit MB | VRAM MB 1080p / 1440p / 4K |
|---|---|---|---|---|---|---|
| land_small (deploy) | 1.894 / 1.817 / 1.806 | 3.341 / 3.171 | 3.5 to 3.6 (3.5) | 1818 / 1823 | 1178 to 1180 | 564 / 632 / 794 |
| land_small battle, 1x (`--deploy end`, n=1) | 2.336 / 2.008 / 1.998 | 3.843 / 3.592 | 3.5 to 3.6 | 1823 to 1838 / 1844 | 1187 to 1193 | 564 / 632 / 810 |
| siege_small (deploy) | 2.27 / 2.024 / 2.007 | 3.815 / 3.414 | 5.1 to 5.2 | 1886 to 1887 / 1887 | 1243 to 1246 | 788 / 856 / 957 |
| naval_small (deploy) | 1.689 / 1.409 / 1.358 | 3.174 / 2.843 | 3.6 to 3.7 | 1760 / 1887 (siege's) | 1087 to 1091 | 605 / 609 / 800 |
| naval_storm (default view) | 1.649 / 1.373 / 1.337 | 3.186 / 2.848 | 3.5 | 1759 / 1887 (siege's) | 1087 to 1105 | 541 / 609 / 792 |
| hist_dresden (deploy) | 4.47 / 4.193 / 3.991 | 6.701 / 6.131 | 7.1 to 7.3 | 2078 to 2079 / **2096** | 1455 to 1467 | 824 / 892 / 1076 |
| hist_nile (deploy) | 3.518 / 2.773 / 2.74 | 6.06 / 5.323 | 4.2 (4.2 to 4.3) | 1821 to 1822 / 1824 | 1152 to 1155 | 456 / 524 / 705 |
| campaign_start (default view) | 1.989 / 1.99 / 1.967 | 2.814 / 2.799 | 2.6 (2.6 to 2.8) | 1749 to 1756 / 1757 | 1155 to 1157 | 429 / 501 / 691 |

The **DXVK against system ratio** the brief asks for does not exist: no system cell. Every DXVK cell's p50 spread is under 7 % (largest
0.136 ms): none is noisy. Step a (smoke, `20261101_j23smoke`): land_small 1080p p50 1.951 ms against the acceptance baseline's 1.958, p99 3.461
against 3.64: reproduced. VA 1829 against 1899 and VRAM 780 against 811: the acceptance `perf` runs after five other scenes in one process,
the smoke cell on a fresh launch.

## `dxvk.conf`: settled, ship none
One option at a time against a control, land_small and siege_small at 1080p and 4K (run `20261101_j23sweep2`): `d3d9.maxFrameLatency = 1`,
`d3d9.presentInterval = 0`, `d3d9.maxAvailableMemory = 2048`, `dxvk.latencySleep = False` (names from the pinned release: the DLL's option
strings and v3.1.1 `dxvk.conf`/`d3d9_options.cpp`). Each was in effect (DXVK's log, per cell). None differs from the control by more than
0.06 ms p50 or 0.3 ms p99, and none moves address space or commit. Settled: DXVK 3.1.1's own defaults, no file (fact
`napoleon.dxvk.conf_defaults`). The back-buffer count has no option in 3.1.1; shader-compile options have nothing to win (cold = warm).
These are **not `config_keys` rows**: see Deviations.

## Display mode: open, the step for Liam
`napoleon.dxvk.menu_display_mode` stays open (Liam: "I cant today", 2026-11-01). The pinned source says what to expect (notes on the
fact): a D3D9 fullscreen request goes through `D3D9SwapChainEx::EnterFullscreenMode`: `ChangeDisplaySettingsExW` to the requested mode, then
the window loses `WS_OVERLAPPEDWINDOW` and goes `HWND_TOPMOST` over the monitor; Vulkan exclusive fullscreen only with `dxvk.allowFse = True`
(default False). So: borderless topmost plus a real mode change when the size differs from the desktop. **The step:** with Liam at the PC,
install a kit, take the lock, `job.sh <owner> - <<< "launch visible=1"` with Liam's prefs as they are (`gfx_fullscreen true`, 3840x2160) on
`proxy.backend=dxvk`; read the window style from the watcher's `win_probe.ps1` output (every launch runs it) and the primary monitor's mode before
and during the game (Liam: Windows display settings, or a read-only `Get-CimInstance Win32_VideoController` job), Liam says what he sees; then the same on vanilla (no proxy) for the comparison; then `land_small` `perf 20` visible at 4K
against the headless cell. The system backend's visible launch presents nothing (J8), so its comparison waits for J16.

## Budgets (PROPOSED, `perf/budgets.md`)
Target 60 Hz: p99 at or under 16.67 ms in every cell with every feature on (today's worst 6.70 ms: 9.97 ms of headroom). Address-space stop
line for J27's memory gate: a peak of 3400 MB (today 2096: 1304 MB of headroom). Per feature (p50 / p99 ms at 4K, VA MB): shadows 1.0 / 1.5,
50; cascades 1.5 / 2.0, 50; distances 1.0 / 2.0, 600; upscaler 1.2 / 1.5, 100; UI 0.3 / 0.5, 150. Sum 7.5 ms p99 at 4K and 950 MB VA,
leaving about 2.5 ms and 354 MB for J46's larger battles. Reasoning: frame time is CPU-side (draw calls) and pixels are close to free
(`napoleon.perf.resolution_scaling`); render targets cost VRAM, not address space, under DXVK (`napoleon.perf.va_peak`), so distances get
most of the address space. Launch-to-launch noise (about 50 MB VA peak, 220 MB VRAM) is as large as the smallest VA budgets: the doc says how
J24 and J26 should compare.

## Facts
New, verified 2026-11-01 (run 20261101_j23pc; the last two run 20261101_j23sweep2): `napoleon.perf.resolution_scaling`, `napoleon.perf.va_peak`, `napoleon.perf.vram_per_size`, `napoleon.perf.load_times`
(incl. naval_storm's first load: 3.5 s), `napoleon.proxy.dxvk_config_dir`, `napoleon.dxvk.conf_defaults`. Updated: `napoleon.render.system_backend`
(J23's headless evidence without `dev.capture`: not the capture key), `napoleon.dxvk.menu_display_mode` (source reading in its notes; open).
"Whether the system backend changes load time" has no answer: no system load exists.

## PC state at the end
`pc_deploy uninstall`: "game folder identical to the pre-install snapshot (1564 files)", exe vanilla; no lock, no active profile; prefs
back to Liam's (3840x2160, `gfx_fullscreen true`, sound on); VirtualStore folder empty; virtual display back at its starting mode; the
scratch DLL copies of the invalid sweep deleted from `<state>\_scratch\claude-j23\`.

## Deviations
- **No system d3d9 numbers, so no ratio.** Every system launch failed headless (six attempts at 1080p, run `20261101_j23pc`); the brief's
  kill criterion ("cannot be launched headless twice in a row") says record and finish the rest. 1440p and 4K were not tried: the failure is
  before anything size-dependent. A fix is a proxy change (out of scope), and a visible launch would not help (J8: frame 0 there too).
- **The `dxvk.conf` defaults are not `config_keys` rows.** `core/proxy/tools/gen_tables.py` renders every `config_keys` row into the proxy's
  `generated/tables.h` and its shipped ini, with no owner filter: a `dxvk`-owned row would put DXVK options in the proxy ini and change a DLL
  input (rule 79). The defaults are in a verified fact and the sweep README instead; the filter is an Open question. Nothing is shipped, so
  the adapter's `dxvk_conf` stays absent.
- **The first sweep was invalid** (run `20261101_j23sweep`): it served each conf beside a copy of the DLL through `proxy.dxvk_path`, trusting
  the `proxy.dxvk_path` description; the proxy points DXVK at `<mod>\dxvk\dxvk.conf` regardless, and DXVK read none. Found because the scratch
  folders held no DXVK log; turned into code (variants written to the real path by a watcher job, a variant cell refused unless DXVK logged
  the file) and re-run. The invalid run is committed as a ten-launch noise sample; `summarize` refuses all 80 of its cells.
- **The matrix ran in two sittings** (a tool bug stopped the first after the system block: the plan's `perf` flag collided with the perf
  result; fixed and the run resumed into the same folder). Nothing measured was lost.
- **The display-mode sitting (step d) and the visible-against-headless comparison were not done**: Liam unavailable today.
- **The `--deploy end` battle cell** ran once per size (three, not one), at 1x for 60 s.
- **VA peak is the process peak since launch**, not a per-scene peak: a warm-reset scene inherits the scenes before it in the same process
  (the table marks naval's). Per-scene peaks would need a fresh launch per scene; the per-scene value (`va_used_mb`) is in every cell.
- About 130 tool calls (budget 150). No subagents.

## Open questions
- **Liam:** agree or change the budgets (60 Hz or 120 Hz; the 3400 MB stop line). The display-mode sitting (step above), when convenient.
- **J16:** `napoleon.render.system_backend`: on the system backend no Present reaches the vtable hooks (device created, front end pumping,
  frame 0), with or without `dev.capture`. Until it is fixed there is no backend comparison; then re-run
  `perf_baseline.py measure --backends system` into a new run and `summarize` both runs together for the ratios.
- **Core / meta:** (1) `gen_tables.py` should skip `config_keys` rows whose owner is not the proxy (so `dxvk` rows can exist without
  entering the proxy ini); (2) the `proxy.dxvk_path` row says DXVK's files go "next to it" (wrong: `<mod>\dxvk\`, fact
  `napoleon.proxy.dxvk_config_dir`) and the harness adapter's `dxvk_conf` config file names `<game>\dxvk.conf`, which DXVK never reads, so a
  profile cannot set a DXVK option. Both are DLL or harness inputs (rule 79).
- **J24, J26, J27:** measure with `perf_baseline.py measure` on your build (same sizes and scenes), then `compare --run <dir> --feature
  shadows|cascades|distances`; read `va_used_mb` as well as the peak (noise, `perf/budgets.md`). The frame is CPU-bound: watch draw calls.
- **J46 / J59:** the larger battles (land_40, land_large, naval_large, a city siege) are listed in the baseline's `not_covered`; J59 runs
  `measure --scenarios <the new rows>` and re-agrees the budgets (D38). "The 40-unit battle" named by J24 and J27 does not exist yet.
- Frame time falls slightly with size (1080p ran first in every sitting): order, or the virtual display's mode? A sitting that runs 4K first
  would tell; it does not change any budget.
