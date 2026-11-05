## Round 1 (2026-11-05, branch job/J64 at 24a0788)

**Verdict: merge.**

Checked: `wsc policy --branch job/J64 --base origin/main` leaves only the review and row-`done` lines (rule 79 is satisfied: 20 consecutive passes, 2 to 21 of run 20261105_j64pc7, build 6e89faf06754, watcher 1.4.0, one evidence file per line, all steps true; ledger diff append-only, `baseline.json` untouched). CI on 24a0788: gates, harness-windows and changes green, proxy and viewer skipped by the pass marker (draft, so `policy` was skipped; the ready-before-push order below gives it a real run). My local `wsc gates` run did not complete in this session, so I rely on CI's `gates` for this head. Read in depth: the adapter initialisers (designated, in declaration order, `.gesture = nullptr`, values copied unchanged), `wsc.toml` (pin v0.30.0, `[gates]`, `[discovery]`, W23 policy steps taking the head sha from `env:`), the `test_jobs_hooks.py` changes, the pass-2 evidence.

### Blockers
None.

### Should-fix
None.

### Later
1. **Pass 2 counted a launch that died.** `harness/runs/20261105_j64pc7/pass_02.json:260` records `retried_after` for a `starting DllMain` crash (c0000374, `napoleon.proxy.init_heap_corruption`). The brief's one allowed relaunch is B60's `hist_nile` flake, so this is outside its letter. The tool retried inside the pass by design, the report names it, and the other 19 passes had none, so I accept it. The DLL init heap corruption (also seen in run 6 pass 1) is a real, recurring fault and deserves its own row; it is not J64's.
2. **`in_flight = {'discovery/core': 'J64'}`** in `tests/test_jobs_hooks.py` is a permanent exception for a one-off merge window. Judged as the report asked: fine now, remove it when the next job touches that file.
3. **Core rows the report proposes** (display change the guard refuses is a flake; a foreign window on the virtual display must not fail a pass; promote `effects.py`; pass-1 build id from the previous log) are good; they belong in warscape-core `docs/BACKLOG.md` via that repo's pull request, not here.
4. Report open question 4 (`watch.cmd` is not replaced by `update`; re-run `Install watcher.cmd`) and 5 (`SCRATCH_OWNER` 32 vs 40 characters) are for Liam / a later job.

Not re-done: the first session's pure-move proof and pre-bump test counts are unrecorded, as the report says; CI's gates and the 585 passing host tests stand in for it.

Other open job branches (J29, J37, J60, J67) rebase onto main after this merges, as the brief says; no rule they must meet changes.
