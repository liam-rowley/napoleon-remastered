# Run 20261031_j12acc3: J12 acceptance gate, 20 passes

2026-10-31, 20:07 to 21:33 UTC, on the PC. `python3 harness/core/acceptance.py run --passes 20 --run 20261031_j12acc3 --owner j12 --branch job/J12`.

- DLL build `31094f6055c2` (J12 fixes 1a and 1b, the test hooks off), kit `kit_20261031T194958Z_d5c606bb5661`, watcher 1.2.0.
- Result: **20 of 20 passed** (`pass_01.json` to `pass_20.json`); `acceptance.py streak --build 31094f6055c2 --watcher 1.2.0` says 20.
- Loads, min to max over the 20 passes: hist_dresden 7.0-9.1 s, hist_nile 4.1-5.1 s, campaign_start 2.5-3.2 s, naval_small 3.2-3.5 s,
  siege_small 5.1-5.8 s, land_small 3.8-5.2 s (all inside the baseline's 150 % tolerance). Every pose read back within 0.05, every
  shot within its threshold, settings byte-identical after every exit.
- Before it: run `20261031_j12acc` (pass 1 failed `settings_identical`: started under the sitting's own lock and headless overlay) and
  `20261031_j12acc2` (pass 1 failed `settings_identical`: the launch keys were written into a fresh ini outside the snapshot). Both
  causes are guarded in `acceptance.py` since (jobs/J12/report.md, Deviations); their pass files are kept beside this one.
