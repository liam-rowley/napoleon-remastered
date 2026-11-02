## Round 1 (2026-11-02, branch job/J23 at 4f92a13)
**Verdict: merge.**

Checked: `wsc gates` 11 ok, 1 warn (skips only); 13 host tests of `tests/test_perf_baseline.py` pass; `perf_baseline.py check`: ok (39 cell keys); all 11 branch commits carry the session trailer; nothing changed under `core/`, `proxy/`, `harness/napoleon` or `harness/acceptance` (no rule 79 run owed). Recomputed hist_dresden 1080p p50 from the three raw cells (4.573, 4.464, 4.47): median 4.47 ms, as reported. Budget sums in `perf/budgets.md` add up (p50 5.0, p99 7.5 ms, 950 MB VA at 4K). Risk-first reading: the variant-cell guard (refused unless DXVK logged the conf file) and the pin check, since an unpinned or unapplied cell would poison every later comparison; both are tested.

Deviations accepted because the report names them with a reason and a brief rule covers them: no system-d3d9 cells (the brief's kill criterion for a backend that cannot launch headless; fact `napoleon.render.system_backend` open for J16); no `config_keys` rows for DXVK defaults (a `dxvk`-owned row would enter the proxy ini and change a DLL input; the defaults are in fact `napoleon.dxvk.conf_defaults`); display-mode sitting not done (Liam unavailable; the step is written out); the invalid first sweep kept as evidence and refused by `summarize`.

### Blocker
None.

### Should-fix
None.

### Later
- Core: `gen_tables.py` should skip non-proxy `config_keys` owners, and the `proxy.dxvk_path` description plus the adapter's `dxvk_conf` path are wrong (report, Open questions). Not a J23 defect.
- After J16 fixes the system backend, re-run `measure --backends system` to get the ratios; J59 extends to J46's rows and re-agrees the budgets (D38).
- The budgets stay PROPOSED until Liam agrees them.
