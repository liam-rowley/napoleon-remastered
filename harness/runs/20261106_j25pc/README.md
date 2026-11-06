# J25 PC run 20261106_j25pc: cascaded shadows spike

PC: RTX 4090, driver 617.14, Windows 11, DXVK 3.1.1, watcher 1.4.0, headless at 1920x1080 (shots are 1280x720 JPEGs) and 1080p / 4K (cost). Prefs: `gfx_shadow_quality` 3,
`gfx_hardware_shadows` false, the watcher's headless overlay. Lock owner `j25`. One sitting, 2026-11-06, 01:39 to 03:37 UTC, about 2 h of watcher time.
The virtual display stayed up throughout: no launch was refused (no exit 2160).

## Builds and kits
The build id does not change between spike builds (`a005f6cccc17-dirty`), and a kit's name ends in the game repo's commit, not the DLL: identify a build by the DLL's sha256 (a kit stores
each file under its hash prefix, checked before each install).

| spike commit | DLL sha256 | kit | used for |
|---|---|---|---|
| none: `main` at core v0.30.0 | build 54413755d6d2 | kit_20261106T013925Z_54413755d6d2 | `a_main` |
| 0d350a4 | ab70b8d131c9 | kit_20261106T020245Z_54413755d6d2 | `b_idle`, `c_on`, `c_tint` |
| 5843f2a | fca7bd5f6950 | not deployed | the gate fix, built and tested only |
| 3b9134a | 1fe1d99c7afb | kit_20261106T022314Z_54413755d6d2 | `d_*`, `y_*`, `e_*`, every cost arm |

Spike: local warscape-core branch `spike/J25-cascades`, cut from 4d69d112 (v0.30.0, this repo's pin), head 3b9134a330bc702c780c2ebb9caa171d70c19439, never pushed. `patches/` holds the series
and the scratch `config_keys` rows. Its clone lived in the job's temporary folder: the patches are the durable copy.

## Launches
Every launch below went through the watcher; each scene and kill returned 0, no hang folder and no dump appeared. Keys were set with the game closed.

| tag | keys | what it showed |
|---|---|---|
| `a_main` | `main`, release values on | the pass, casters, receivers (`passes_a_main.json`). 8192 map: the installed ini ships J24's release values, so this is not stock 2048 |
| `b_idle` | prototype off | idle: no cascade activity in the log, 64 of 64 sites ok |
| `c_on` | on | casters duplicated, but the receivers read nothing (below). DXVK log lost |
| `c_tint` | on, tint | the failure: stock shadows outside the cascade, so the cascade was not being read |
| `d_tint` | on, tint, stock CTAB splice | the pick works |
| `d_on` | on | real shadows, 8192 |
| `y_ctl`, `y_s25`, `y_s40`, `y_s60` | off; on at split 25, 40, 60; map 2048 | the yaw sweep |
| `d_skip` | on, `dev.cascade_skip_ps=5c9bd7a4bb31b068` | question 6: the outline goes, nothing else |
| `e_ctl2k`, `e_on2k`, `e_tint2k` | off, on, tint; map 2048 | the 2048 shot sets |

Poses are J24's p1..p6 and s1 and `land_40`'s two rows (`cas.sh`). Coverage, last line of each log: seen equals duplicated, 0 unknown, 0 without a fit, in all 10 prototype launches, for
example `e_on2k` 8,532,501 and `d_on` 5,540,732.

## Cost
Eight `20261106_j25cost_*` runs, in this order: at 1080p control, prototype, control, prototype (`land_40`, `hist_dresden`), then the same at 4K (`land_40`), 2 repeats each. The sizes are grouped so
the virtual display changes once. Same kit, only `dev.cascade_proto` differs, release values on, no capture, no counters. `cost.py` writes `cost.md`; `ladder_tables.md` is `perf_baseline.py ladder`.
The cascade is the engine map's size in these arms: 8192. `compare_1080.txt` is `compare --feature cascades`: 0 comparisons, as the brief expected (`land_40` is not in the baseline).

## Helpers (run evidence, as J24's, not registered tools)
`cap.sh`, `cas.sh`, `sitting_d.sh`, `sitting_e.sh` (drivers; never edit one while it runs), `receivers.py` and `cascade.fx_fragment` (the offline compile and gate; `receivers/` holds the result),
`passes.py`, `blended.py`, `sprites.py` (questions 1, 2, 6), `q3_stacks.py` (question 3), `cost.py`, `shotdiff.py`, `pick_check.py`. Sheets in `sheets/`.

## Incidents
- **`c_on`'s DXVK log is lost.** The driver looked in the wrong folder, a refused compound command did not copy it, and the next launch overwrote it. `c_tint`'s was read in place. From `d_tint` on, `cas.sh`
  records each launch's `err:` and `warn:` lines in `dxvk_errors.txt`. A direct copy of the log out of the game folder was denied, so no raw DXVK log is committed. All of them: 0 `err:`; the only
  warnings are `QueryInterface` for the texture interfaces, from the capture's own `GetContainer`.
- **`shadow_density.py`'s import reads the whole capture folder.** With prototype captures in it, it added 26 shaders to `discovery/napoleon/shaders/`. Nothing was committed: the 52 generated files were
  removed. Cascade density needs only the control's import, so use `--no-import` after a prototype sitting.
- **`test_capture` failed once in six builds** (`stress seed 3: 1 errors`), with `capture.h`, `capture.cpp` and the test unchanged: timing, most likely, in core's threaded stress test.
- **Raw `frame.txt` stayed in `<state>\captures`** (`dev.capture_dir`), not `_scratch\j25`.
- **`pick_check.py` gave wrong numbers twice** before it read the main pass's camera: the first terrain draw is the reflection pass, which has a mirrored camera.
- **Uninstall:** game folder identical to the pre-install snapshot (1564 files), exe sha1 9aebcd2172f2878d781b079f7feb45b0e12e0250, `preferences.script.txt` sha256 83b9b32b2b73..., J24's end state.
  The replacements stay in `<state>\_scratch\j25\swap`.

## Results
`jobs/J25/report.md`.
