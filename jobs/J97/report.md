# J97 report: Viewer housekeeping: docker volumes and the S2 capture

`viewer/core/build.sh --prune [--dry-run]` removes the per-checkout `napoleon-viewer-cmake-*` Docker volumes whose checkout is gone (and the old
shared `napoleon-viewer-cmake`), and `--docker` now creates its volume labelled with the checkout path, so pruning can tell. A stub-`docker` unit
test covers every case in the brief without Docker. On the PC the prune removed only the shared legacy volume and kept both live ones; the
viewer.wasm sha256 is unchanged (`2bdc8a11...`). The S2 in-artifact capture was not taken: no signed-in browser in this session (outcome b).

## What was built
- `viewer/core/build.sh`: `vol_name` (the existing hash rule), `prune_decide NAME LABEL LIVE...` (plain inputs, no docker calls) and `prune`:
  lists `docker volume ls -q`, considers only `napoleon-viewer-cmake` and `napoleon-viewer-cmake-*`, reads the `napoleon.viewer.checkout` label with
  `docker volume inspect -f`, keeps a label whose directory exists, removes a label whose directory is gone, keeps an unlabelled volume only when it
  is the hash of this `ROOT` or of an existing path in `git worktree list --porcelain` (normalised with `cd && pwd`), removes the legacy shared one.
  One `docker volume rm` per volume; a failure prints `in use, skipped` with Docker's message; final count line; exit 2 with the same "start Docker
  Desktop" message when Docker is down. The build path runs `docker volume create --label napoleon.viewer.checkout=<ROOT> --label
  napoleon.viewer.hash=<hash>` when the volume does not exist (`MSYS_NO_PATHCONV=1` so Git Bash does not rewrite the label path).
  Header `usage:` and `when:` lines and the `viewer.core.build` tools row updated together (`wsc reg add tools`).
- `tests/test_viewer_prune.py`: six tests on a temp git repo with one `git worktree add` and a stub `docker` first on `PATH` that logs every call:
  labelled live kept, labelled gone removed, unlabelled live worktree kept, unlabelled dead removed, legacy removed, another prefix never named in a
  call, no bulk prune; `volume rm` failing gives `in use, skipped` and exit 0; `--dry-run` makes no `rm`; this checkout's own hash kept; Docker down
  gives exit 2 after only `info`. Skips without bash (and ignores WSL's `System32\bash.exe`).
- `viewer/README.md`: "Housekeeping" section (the two commands, what is kept and why, the hand command for the shared volume).
- `viewer/runs/20261104_j97/`: README, `prune_before.txt`, `build_local.log`, `prune_after.txt`.

## Proof
- `python3 -m unittest tests.test_viewer tests.test_viewer_prune`: 16 tests OK (4 render tests skip locally: no build output at test time).
- PC (Docker Desktop 29.6.2), 2026-11-04: volumes before `napoleon-viewer-cmake`, `napoleon-viewer-cmake-b42762329245` (unlabelled, the hash of live
  worktree `agent-a3453f1c4147a7ea5`). Dry-run: would remove the shared one, keep the other. `--docker build` in job-J97 made
  `napoleon-viewer-cmake-bcf51fa481f3` with both labels. `--prune`: removed 1 (the dry-run's one), kept 2, skipped 0. After: `b42762329245`, `bcf51fa481f3`.
- viewer.wasm sha256 before (CI run 41879911815, main 0271d10, `viewer-wasm` artifact) and after (this branch, local Docker build):
  `2bdc8a112021772a4e4ad08004bb3e096707f9fcbff95625073f217f478b0f78` both; viewer.js `21876236ee8b...` both.
- `python3 core/wsc.py gates --fast` green on every commit (pre-push hook); CI on the PR.

## Deviations
- **Prefix match is exact-or-dash**: only `napoleon-viewer-cmake` and `napoleon-viewer-cmake-*` are considered, not every name starting with the
  string (a stray `napoleon-viewer-cmakeX` is left alone). Stricter than the brief, same intent.
- **The wasm reference is the latest main CI artifact, not `SHA256SUMS.local` of J31**: J30 changed the viewer sources after that file was
  written, so its hash (`fee33899...`) is stale; the brief allows either.
- **No re-build in another live worktree** (PC test step 4): the only other kept volume belongs to another agent's worktree, and building there
  would write into a checkout this job does not own. This checkout's kept, labelled volume built green; the other volume was not touched.
- **S2 note as a section of the run README** rather than a separate file; the run README is a deliverable anyway.
- After this job's worktree is removed, its volume `napoleon-viewer-cmake-bcf51fa481f3` is labelled with a gone checkout: the next `--prune`
  removes it (not run here, to leave the evidence as recorded).

## Open questions
- **S2 in-artifact capture still open** (outcome b): no signed-in browser in this session. The artifact exists and is private
  (https://claude.ai/artifact/EoCR1JcPZH7Rnix9JoKZea); the three steps for a signed-in session are in `viewer/runs/20261104_j97/README.md`.
- **Should `wsc` own a clean verb instead of `build.sh --prune`?** Default kept: no, the script owns it; J63 moves it to the core with `build.sh`.
- **Auto-prune at the end of every `--docker` build?** Default kept: no, explicit only.
