## Round 1 (2026-11-04, branch job/J97 at 5dbd8d5)

**Verdict: merge.**

Checked: CI green (8 checks passed or skipped); `wsc policy` refused only for the missing review and row, which this commit supplies; `tests.test_viewer_prune` 6/6 OK locally.

### Blocker
None.

### Should-fix
None.

### Later
- `build.sh --prune` compares the label to `[[ -d ]]` using the Git Bash path form (`/c/...`). Run from WSL or another shell with a different path form, it would see a Git Bash label as gone and remove a live volume. Single-shell PC use today (D30), so not a blocker; worth a README line if another shell is ever used.
- S2 in-artifact capture is still open (outcome b, as the brief allows); steps are in viewer/runs/20261104_j97/README.md.

### Reading notes
- Risk-first: the removal path (`prune`, `prune_decide`). Only exact `napoleon-viewer-cmake` or `napoleon-viewer-cmake-*` names reach `docker volume rm`, one volume per call, no bulk prune; `--dry-run` never reaches `rm`; Docker down exits 2. Matches the brief; the test asserts each case, including that other-prefix volumes are never named.
- Claims vs evidence: wasm sha256 `2bdc8a11...` before and after, both labels on the new volume, and prune before/after are in the run folder (build_local.log, prune_after.txt). Deviations (exact-or-dash prefix, CI artifact as wasm reference, no rebuild in another agent's worktree) are named in the report with reasons and are sound.
- Header usage line and tools row agree.
