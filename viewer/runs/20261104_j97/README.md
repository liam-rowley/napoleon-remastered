# J97 run evidence (2026-11-04)

PC: Docker Desktop 29.6.2 (server), Git Bash; emsdk image pinned in viewer/pins.json. Branch job/J97 (build.sh --prune and labelled volumes).

| File | What |
|---|---|
| prune_before.txt | `docker volume ls` of the napoleon-viewer-cmake volumes before, and the first `--prune --dry-run` (before this checkout had a volume) |
| build_local.log | `build.sh --docker build` in this checkout (tail): the sha256 of both outputs, and `docker volume inspect` of the new volume showing both labels |
| prune_after.txt | `--prune --dry-run`, `--prune` for real, then `docker volume ls` after |

- Volumes before: `napoleon-viewer-cmake` (the old shared one), `napoleon-viewer-cmake-b42762329245` (unlabelled; the hash of the live worktree
  `.claude/worktrees/agent-a3453f1c4147a7ea5`). After: `napoleon-viewer-cmake-b42762329245` and `napoleon-viewer-cmake-bcf51fa481f3` (this checkout,
  labelled). Removed: the shared one only, which the dry-run named; nothing skipped.
- viewer.wasm sha256: before (CI run 41879911815, main at 0271d10, artifact `viewer-wasm`) `2bdc8a112021772a4e4ad08004bb3e096707f9fcbff95625073f217f478b0f78`;
  after (this branch, local Docker build) the same, and viewer.js `21876236ee8b...` in both. `viewer/runs/20261031_j31/SHA256SUMS.local` is older
  (J30 changed the viewer sources since), so the CI artifact is the reference.
- Nothing was written under the game, state or AppData folders; no git ran in a game folder.

## S2 in-artifact capture: not taken (outcome b)

The J97 session had no signed-in browser: no built-in browser pane tools and no Claude in Chrome were connected, and the brief forbids hunting
for credentials or signing in for Liam. The artifact still exists and is private (Artifact read, 2026-11-04: version 1793463367-c136, 11 files):
https://claude.ai/artifact/EoCR1JcPZH7Rnix9JoKZea. Its privacy was not changed and nothing was shared or published.

Steps for Liam or a later session with a signed-in browser (the desktop browser pane, or Playwright on a profile Liam is signed in to):
1. Open the artifact URL above signed in; open DevTools (or the pane's console and network tools) before the page loads, then reload.
2. Save the console messages (the `[host]`, `[viewer]` and `[rml ...]` lines) and the network list (URL, status, content-type, size per request,
   `viewer.wasm` included) as `viewer/runs/<YYYYMMDD>_<job>/artifact_capture.txt`, headed with the date, the browser and the artifact URL.
3. Add one row for it to the table in `viewer/runs/20261031_j31/README.md` (the headless reference to compare with is `browser_capture_local.txt` there).
