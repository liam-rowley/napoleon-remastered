# J24 review

## Round 2 (2026-11-03, branch job/J24 at 17fdabe)

**Verdict: merge.**

Both round 1 should-fix items are answered in `## Fix round 1`, and I checked each against its evidence. CI's `gates` check was red on 17fdabe
because of the new test file. I fixed that on the branch (below). No DLL input changed: `build_id.py` still gives 75739186b92e, so the 20 passes
still count (rule 79), and the policy hook does not complain about them.

### What I checked
- **Machines.**
  - CI run 41662162027 (`gates`) failed on 17fdabe: `test_run_helpers.ShotSheet.test_build_marks_missing_cells` raised `ModuleNotFoundError: No module named 'PIL'`.
    The CI runner has no Pillow, and the PC does, so the fixer's local gates passed.
  - After my fix (192170c), local `wsc gates`: 12 ok, 2 warn, 0 failed (425 s). The warnings are the hook path in a fresh worktree and 40 skipped host tests (573 passed).
  - `wsc policy --branch job/J24 --base origin/main` before the verdict refused only for the verdict and the row.
  - `proxy` and `harness-windows` were skipped, which counts as passed: no input of theirs changed.
- **Should-fix 1 (deliverable 7).** warscape-core pull request #30 (`plan/backlog-numeric-keys-nile-flake`, open) touches only `docs/BACKLOG.md`.
  It adds B59 (numeric patch values from config keys) and B60 (the hist_nile headless relaunch flake). The report links it. The brief allows a
  backlog row or a draft PR, and a `plan/` branch waits for Liam, so this is done.
- **Should-fix 2 (tool rows).** `tools/shot_sheet.py`, `tools/shadow_density.py`, `tools/acceptance_summary.py` and the `ladder` verb on
  `tools/perf_baseline.py` have headers, registry rows and host tests. I re-checked the fix round's two equivalence claims:
  - `shadow_density.py --run 20261103_j24pc --no-import` over the 20 settings in `density.tsv` rewrites it byte for byte (`git status` clean).
  - `perf_baseline.py ladder --control ..._j24ladder_ctl --run ..._j24ladder_4k --run ..._j24ladder_8k` gives the same medians as
    `harness/runs/20261103_j24pc/ladder_table.md`. Only the row labels differ: the full run names and the backend prefix.
  - The run-folder copies are deleted, and the README points at the tools.

### Findings

**Fixed by the reviewer**
- **Blocker: red `gates` on CI** (`tests/test_run_helpers.py:36`). The sheet test imported Pillow without a guard. To see it fail, run the
  file without Pillow installed: CI run 41662162027. Commit 192170c skips that one test where Pillow is missing, the way `test_x86re` skips
  without capstone. I checked the skip with Pillow hidden: 9 tests, 1 skipped. The other 8 tests do not need Pillow.

**Later**
- A test that imports a package CI does not install fails only on CI. This is the second CI-only class in `docs/CI_FAILURES.md` (after the
  J7 zlib bytes). A host check in the `tests` gate could list the non-stdlib imports in `tests/` that are neither guarded nor installed by
  `gates.yml`. That belongs to the core's test runner, so it goes to warscape-core `docs/BACKLOG.md` when its owner next files rows.
- The `tools.shot_sheet` row's `purpose` ends `marked "missing` without the closing quote, but the header line has it (`tools/shot_sheet.py:4`).
  The header-to-row extraction seems to strip a trailing quote. It is cosmetic.
- The fix round says "10 tests", but `tests/test_run_helpers.py` has 9.
- Round 1's later items still stand: the cut-off line question is Liam's, and J59 should re-measure the 4K p50 drift.

### Merge note
No rule that other open job branches must meet changes with this branch.

## Round 1 (2026-11-03, branch job/J24 at 77a40e7)

**Verdict: merge after fixes.**

The engineering is sound and the evidence holds up. One brief deliverable (7, the core backlog filing) is missing, and the report does not
name it as a deviation. The fix needs no new DLL build: nothing below touches a DLL input, so the 20 passes on build 75739186b92e still count.

### What I checked
- **Machines.** `wsc gates`: 13 ok, 1 warn, 0 failed (381 s, on 77a40e7). `wsc policy --branch job/J24 --base origin/main` refuses only for the
  missing review and the row, as expected before a verdict. CI: `harness-windows` was still running on 77a40e7 when the review started.
  `acceptance.py streak --build 75739186b92e --watcher 1.2.0` gives "20 consecutive passes (need 20)", and `build_id.py` on the branch gives 75739186b92e.
- **Risk-first: the eleven `shadow.*` engine sites (they write engine memory).** I checked each against the vanilla `Napoleon.exe`
  (sha1 9aebcd21...) with my own PE reader (session scratch, not committed). At every RVA the anchor bytes are present and the stock bytes follow.
  No base-relocation entry overlaps any anchor or stock span. Every `patch_bytes` decodes to the value the row claims: 8192, 1000.0, -150.0,
  200.0, 0.3, 0.5 and 0. Crop keep clears only byte +0x66 (`01 01 00 01`). The two hardware-force rows turn a `je` into a zero-displacement no-op.
  The bool keys default off and the release values match `release.json` `keep_ids`. The generated ini carries the release values.
  The `keep_ids` change in `build_release.py` has a test for each direction.
- **Claims against evidence.**
  - Every density figure in the report's fit table matches `harness/runs/20261103_j24pc/density.tsv` (stock, cutoff + extrusion, 8192).
  - The ladder and release tables match `ladder_table.md` and `release_table.md`.
  - I re-ran `perf_baseline.py compare --feature shadows` on two pairs:
    - `j24ladder_8k` against `j24ladder_ctl`: 70 comparisons, 0 breaches.
    - `j24rel` against `j24rel_ctl`: 90 comparisons, 2 breaches, the two 1080p "turned" p99 cells the report names.
  - Every J24 launch's `proxy.log` shows "64 sites: 64 ok, 0 bad".
  - The contact sheet `sheets/land_before_after.jpg` has the poses and labels the report describes.
- **The brief.** Deliverables 1 to 6 and 8 are present. The no-core route was taken and the reason is recorded (shared-RVA rows refused).
  The kill criteria were respected: 8192 is within 2x of the budget in hist_dresden and the siege, and `core/` is untouched.
  Release values are left to Liam as proposals.

### Findings

**Should-fix**
1. **Deliverable 7 is not done** (`jobs/J24/report.md:149`, brief `jobs/J24/brief.md:99`). The brief says "the numeric-key change ... written as a
   warscape-core backlog row or draft PR". The report instead writes the spec under "Core (for the orchestrator to file)". You can see it fail:
   warscape-core `docs/BACKLOG.md` on main has no numeric or `value_key` row, and no warscape-core pull request mentions one.
   The hist_nile headless relaunch flake (report: "about one 20-pass run in ten") is not filed either. B26, B30, B31 and B41 already exist.
   - Fix: a warscape-core `plan/` pull request that adds both backlog rows, linked from the report's Fix round.
   - J27 depends on the numeric key, so it should not wait on someone remembering this.
2. **Reusable helpers have no tool rows** (`jobs/J24/report.md:32`, brief deliverable 6: "`tools` rows with headers for anything new ... under `tools/`").
   - `sheet.py` (labelled contact sheets), `dens.py`, `ladder_table.py` and `accsum.py` in `harness/runs/20261103_j24pc/` are general tools.
     J25, J26 and J59 will need the same sheets and the same same-sitting ladder tables, and `wsc find contact sheet` finds nothing.
   - The deviation is named, but "as J9's `proof.sh`" fits the one-off drivers (`fit.sh`, `final*.sh`), not these.
   - Fix: move the four to `tools/` with headers and `wsc reg add tools`. The drivers can stay as run evidence. None is a DLL or harness input,
     so rule 79 is unaffected.

**Fixed by the reviewer**
- `discovery/napoleon/engine_sites_routes.md:40` said "All 45 rows pass the proxy's start-up check on the final build". The registry has 64 rows,
  and the J24 logs say "64 sites: 64 ok". Corrected in commit ea2020f.

**Later**
- **Learnings left as prose** (`jobs/J24/report.md:163-164`, "Worth remembering"):
  - `shader_catalog.py import` fails entirely when one named capture is missing.
  - `density` breaks past about 40 paths on a Windows command line.

  Both are tool fixes: skip and list the missing capture; read paths from a file or a glob. "Never edit a running `.sh`" could be a watcher guard
  (refuse a script whose mtime changed since it was queued). These go to the owner of `discovery/core` (W4 is moving it into the core).
- **For Liam, not a defect:** the proposed release turns on the height cutoff, which wins its density by shortening the fitted farz from 250 m to
  150 m at deploy height (`jobs/J24/report.md:60`). The brief's own recommendation was to ship a fit control only if the worst case beats stock at
  every pose; a nearer shadow cut-off line is such a cost. The report asks Liam this (open questions); it should stay his call before a release.
- At 4K the release p50 is +0.24 to +0.40 ms in every cell (`release_table.md`). That is small but systematic, not noise, so J59 should re-measure it on J46's rows.

### Merge note
No rule that other open job branches must meet changes with this branch.
