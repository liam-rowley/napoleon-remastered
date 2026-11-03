# J24 review

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
