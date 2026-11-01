# Run 20261101_j40acc (+ 20261101_j40acc2): J40 acceptance gate, 20 passes

2026-11-01, 07:03 to 08:34 UTC, on the PC. `python3 core/harness/acceptance.py run --passes 20 --run 20261101_j40acc --owner j40 --branch job/J40`,
then `--passes 1 --run 20261101_j40acc2`.

- DLL build `f3e33f228416` (core v0.5.0: the J40 console fixes), kit `kit_20261101T070023Z_d465747d7269`, watcher 1.2.0.
- Result: **21 of 21 passed**; `acceptance.py streak --build f3e33f228416 --watcher 1.2.0` says 20 (the ledger lines of passes 2-20 and acc2 pass 1).
- Pass 1's ledger line names build `d465747d7269`, the kit's id: the kit had just been installed, so no `proxy.log` existed when
  `ctl.py` `build_info()` read the identity before the pass's launch, and it fell back to `install.json`. Passes 2-20 read the log the
  previous pass left. The one extra pass (`20261101_j40acc2`) completes the streak. The fix is core's (read the identity after the launch, or
  never fall back to the kit id): jobs/J40/report.md, Open questions.
- Loads, min to max over the 21 passes: hist_dresden 7.0-9.4 s, hist_nile 4.1-4.6 s, campaign_start 2.5-4.0 s, naval_small 3.2-4.5 s,
  siege_small 5.1-7.2 s, land_small 3.8-5.3 s (inside the baseline's tolerance). Every pose and shot within its threshold, settings
  byte-identical after every exit.
