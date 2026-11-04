# J30 review

## Round 1 (2026-11-04, branch job/J30 at c043eb6)

**Verdict: merge.**

Reviewer: a fresh session (Opus; D15 independent check) that did not build or fix this branch. Risk-first reading: the rule 79 evidence and
the start-up failures around it (a DLL that now runs RmlUi, FreeType and a second Lua at start), the release inertness (`release.json`, the
shipped ini, `config_keys`) and the install path (`kit_ui`), then `tools/ui_hosttest.py`, which turns the PC dumps into the step b numbers.
The host code itself is the core's (W2, `v0.10.0`, reviewed there) and was skimmed only where the adapter uses it.

### Machines
- `python3 core/wsc.py gates` on c043eb6: 13 ok, 1 warn (tests skipped for optional dependencies), 0 failed (156.7 s).
- CI on c043eb6: `gates` green, `proxy` skipped (input tree already passed), `harness-windows` still running when read; the merge is queued
  with `--auto`, so it lands only if that check is green.
- `core/proxy/tools/build_id.py` gives `cb34c06baf42` at c043eb6 and after the review commits below.

### Claims checked against evidence
- **Rule 79:** `harness/acceptance/ledger.jsonl` has 21 `20261103_j30acc6` lines; passes 2-21 are `result: pass`, `build_id cb34c06baf42`,
  watcher 1.2.0, branch `job/J30`, each naming its committed `pass_NN.json`. Pass 1 carries the kit label (fresh install), as the report says.
- **Idle host (step a):** `proxy/runs/20261103_j30pc/results.jsonl`, setting `idle`: update and render `n 0` (nothing drawn), hook p50 0.0 ms
  over 17,057 presents. The D38 budgets (1 ms document at 4K, 0.1 ms idle) are met by the README table (host p50 at most 0.096 ms).
- **Release stays inert:** `ui.enabled` default and release value false; `release.json` omits `ui.` from the player ini and
  `tests/test_release.py` (in the gates) proves that each omitted key's default equals its release value; the release builder does not
  read `kit_ui`, so the test documents are dev-kit only.
- **Facts:** every new `napoleon.ui.*` row is verified with a date and the `20261102_j30pc` run, apart from `depth_stencil`, which is open
  with an owner (J35), as the brief allows.
- **Start-up failures:** `napoleon.proxy.init_heap_corruption` predates J30 (J44, J45, J50), so the c0000374 in acc6 pass 5 is not new.
  The kill criterion "start-up crash or hang with `ui.enabled=1` and no document, twice" was not met: acc2 ran with `ui.enabled=0`, and
  with the host on there is one new event (acc6 pass 18).

### Findings
**Blocker:** none.

**Should-fix, fixed on the branch by the reviewer (one commit each; neither changes the build id):**
1. `proxy/README.md` "RmlUi host (J30)" pointed its evidence at `proxy/runs/20261102_j30pc/`, the run on the pre-tag core. It now names
   `20261103_j30pc` (the shipped `v0.10.0` build) first (0d65936).
2. `registries/engine_facts/napoleon.proxy.init_heap_corruption.json` did not record J30's occurrences, though this flake has now hit four
   jobs. It now lists the acc2 retries, including a first c0000005 access violation at DllMain (dump `...p41828_c0000005.dmp`), the acc6
   pass 5 dump, and the pass 18 spin at `starting DllMain` (629bd0b). The crash job the fact asks for is overdue: the next start-up-heavy
   job should not have to work around it again.

**Should-fix, left as notes (not merge-blocking):**
3. The report never says why the start-up kill criterion did not apply. The pass 18 stall (`starting DllMain`, about two cores busy for
   180 s, `ui.enabled=1`) is a new symptom on a host-enabled build. The report's control for the earlier exits (J24's build exiting 4-9 times
   an hour) lives only in the uncommitted `watcher.log` (`proxy/runs/20261103_j30pc/README.md` "f)"). Next time, commit the excerpt.
4. Brief step e asks for "no stray draw over a video". Fact `napoleon.ui.loading_and_video` shows that an open document *is* drawn over
   `frontend2.bik` and the loading screen, and leaves that to J35. That is a fair call for a debug document, but the report does not list it
   as a deviation. J35's brief should carry it.

**Later:**
5. Deliverable 1 asks for the CI build time before and after. The report gives the local `build.sh --docker all` time (212 s / 198 s) and
   the W2 report says the core CI timeout went to 30 minutes, but neither gives the CI minutes before and after.
6. For warscape-core `docs/BACKLOG.md`: (a) the acceptance runner should refuse to start, or pause, below a free-RAM floor, or re-measure a
   single load outlier once (acc3-acc5 broke on loads at about 2 GB free; acc6 passed 21 of 21 at about 20 GB free); (b) `build.sh smoke`
   step 6 should accept a game without a `GestureAdapter`, so a game can move past v0.13.0 before its gesture half lands. Neither is in
   the backlog yet (B57 is close to (b) but is about the hook gate, not the smoke step).
7. The `viewer/core` promotion row (rule 76) is still only proposed; it needs a `plan/` change.

### Effect on other branches
This merge moves the core pin to `v0.10.0` and makes `core/proxy/tools/fetch_ui.py` and `viewer/pins.json` DLL inputs. Any open branch that
changes the proxy gets a new build id when it merges `main`, so its rule 79 passes must be run again.
