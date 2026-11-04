# J97: Viewer housekeeping: docker volumes and the S2 capture

Phase 5, housekeeping on the review viewer (J31: `jobs/J31/report.md`, `jobs/J31/review.md` Later 1 and 2; origin
`docs/audits/LATER_TRIAGE_2026-11-04.md`, rows J31-L1 and J31-L2). Two small items: (1) Docker volumes named `napoleon-viewer-cmake-<hash>` (one
per checkout, made by `viewer/core/build.sh --docker`) pile up on the PC with every worktree and nothing removes them; (2) the S2 spike's
artifact has no console or network capture from inside the artifact, only a headless local capture and Liam's phone check. No change to what the
viewer builds or renders: the viewer wasm and its sha256 stay byte-identical.

Model: Sonnet, reason: small script and test work, no DLL or engine (D52). Budget about 60 tool calls; at the cap, stop, commit, report what
is left. No subagents. Waiting belongs to the harness: one background call for a Docker build, never repeated polling.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J97`). Read `docs/DECISIONS.md` (D30, D31, D37) and `viewer/README.md`.
- Read `viewer/core/build.sh` (the `VOL=` line and its comment), `tests/test_viewer.py`, `viewer/runs/20261031_j31/README.md` and
  `browser_capture_local.txt` in that folder, and J31 review Later 1 and 2 (`jobs/J31/review.md`).
- Search first: `python3 core/wsc.py find build.sh viewer docker volume prune` (tools row `viewer.core.build`).
- **Collision notes.** J32 (queued, PC, S3 and S4 spikes) reads `viewer/core/render.py` and the hosttest and extends `tools/ui_hosttest.py`; it
  does not edit `build.sh`, `fetch_sources.py` or the J31 run folder. This job touches only `viewer/core/build.sh`, `tests/test_viewer.py` (or a
  new `tests/test_viewer_prune.py`), `viewer/README.md`, the tools row for `viewer.core.build` (header and row text stay in step) and a new run
  folder `viewer/runs/<YYYYMMDD>_j97/`. J63 (needs_brief) promotes `viewer/core` to warscape-core later: keep the prune logic inside `build.sh`
  (no new Python tool), game-agnostic, no Napoleon names beyond the volume prefix, so it moves with the script.

## Decisions already made for this job
- **The viewer wasm is untouched.** `viewer/core/build.sh --docker build` before and after gives the same `viewer.wasm` sha256. Rule 79 does
  not apply (no DLL input), but `viewer/` is a CI input, so the `viewer` CI job runs on the branch.
- **Label the volume, then prune by label.** `build.sh --docker` creates the volume itself with `docker volume create --label
  napoleon.viewer.checkout=<ROOT> --label napoleon.viewer.hash=<hash> "$VOL" >/dev/null` when it does not exist (`docker run -v` would otherwise
  create it unlabelled; `volume create` on an existing volume is a no-op, so old unlabelled volumes keep working). `ROOT` is the same string the
  hash is computed from, so label and name agree.
- **`build.sh --prune [--dry-run]`** (a mode of the one script, like `--docker`; needs only the `docker` CLI, no image): list `docker volume ls -q`
  entries starting `napoleon-viewer-cmake`; for each, read the label `napoleon.viewer.checkout`:
  - label present and that directory still exists (`[[ -d ]]`): keep;
  - label present and the directory is gone: remove;
  - no label (made before this job): keep only if its name equals the hash name of a live checkout, where live checkouts are this `ROOT` and every
    path in `git worktree list --porcelain` that exists on disk (normalised with `cd "$p" && pwd`, so the hash matches the one `build.sh` made);
    otherwise remove;
  - the old shared `napoleon-viewer-cmake` (no suffix, J31 review item 1) is removed.
  `--dry-run` prints the same decisions as `would remove` and removes nothing. A volume in use makes `docker volume rm` fail: print
  `in use, skipped` and carry on. Exit 0 unless Docker itself is not answering (then 2, with the same "start Docker Desktop" message as the build
  path). Print each removal with the volume name and why, and a final count (kept, removed, skipped). Never touch a volume that does not start
  `napoleon-viewer-cmake`; never `docker volume prune`, `docker system prune` or any bulk command.
- **Docker volumes are build caches**, rebuilt on demand; the script deletes no files on the PC and writes nothing under the game, state or
  AppData folders.
- **Testable without Docker.** Put the decision in a shell function that reads plain inputs. The test puts a stub `docker` script first on `PATH`
  (a temp dir) that answers `info`, `volume ls -q`, `volume inspect` (the label) and `volume rm` from a fixture and logs every call. Cases: label
  with a live directory kept; label with a gone directory removed; unlabelled volume matching a live worktree kept; unlabelled with no live match
  removed; the unsuffixed legacy volume removed; a volume with another prefix never named in any `docker` call except `ls`; `volume rm` failing
  gives `in use, skipped` and exit 0; `--dry-run` makes no `volume rm` call; Docker not answering gives exit 2. Skip where `bash` is unavailable
  (Git Bash has it, CI is Linux). Use a temp git repo with `git worktree add` for the unlabelled-live case.
- **S2 capture is best effort, once.** A signed-in browser is a session property (the J31 session had none), so there are two outcomes and both
  finish the job. (a) The session has a signed-in browser (the Claude desktop browser pane, or Playwright with a profile Liam is signed in to):
  open the S2 artifact (`https://claude.ai/artifact/EoCR1JcPZH7Rnix9JoKZea`, private; if it is gone, publish a fresh stage of
  `viewer/napoleon/hello` from `render.py --stage-only` as a new private artifact and say so), capture the console messages, the network list (URL,
  status, content-type, size per request, the wasm included) and the RmlUi log lines, and save them as
  `viewer/runs/<YYYYMMDD>_j97/artifact_capture.txt` with a header giving date, browser and artifact URL; add one row for it to the table in
  `viewer/runs/20261031_j31/README.md` (the only edit allowed there). (b) No signed-in browser: do not hunt for credentials, do not sign in for
  Liam, do not change the artifact's privacy; write `viewer/runs/<YYYYMMDD>_j97/README.md` saying so with the three-line steps Liam or a later
  session runs, and list the item under the report's open questions. Never publish anything public or share the artifact.
- **README.** `viewer/README.md` gains a short "Housekeeping" section: `build.sh --prune --dry-run`, `build.sh --prune`, what it keeps and why, and
  the hand command for the old shared volume if `--prune` cannot remove it (`docker volume rm napoleon-viewer-cmake`). Update the `build.sh` header
  `usage:` line and the tools row (`python3 core/wsc.py find build.sh` shows the fields; the `tools` gate checks header and row agree).

## Order of work
1. Prune function and `--prune` mode in `build.sh`, volume labelling on the build path, header usage, tools row, the test with the fake `docker`.
2. `python3 -m unittest tests.test_viewer tests.test_viewer_prune` (or the file you chose); `python3 core/wsc.py gates --fast`.
3. The PC check (below), then the S2 capture, outcome (a) or (b).
4. README section, run folder, report.

## Deliverables
1. `build.sh --prune [--dry-run]` and labelled volumes, with the unit test, header and tools row in step.
2. `viewer/README.md` Housekeeping section.
3. `viewer/runs/<YYYYMMDD>_j97/` with `README.md` (what ran, the before and after `docker volume ls` of the napoleon-viewer-cmake volumes, the wasm
   sha256 before and after) and either `artifact_capture.txt` or the no-browser note.

## PC test
Docker Desktop running. (1) Record `docker volume ls` filtered to `napoleon-viewer-cmake`. (2) `viewer/core/build.sh --prune --dry-run`: it names
only volumes of checkouts that no longer exist (plus the legacy shared one if present), and this checkout's volume says keep. (3) Run
`viewer/core/build.sh --docker build` in your checkout (a labelled volume is made if it had none: `docker volume inspect` shows both labels); the
`viewer.wasm` sha256 equals the one in `viewer/runs/20261031_j31/SHA256SUMS.local` or the latest `viewer-wasm` CI artifact's. (4) `--prune` for
real, then `docker volume ls` again: the removed volumes are the dry-run ones, and every kept one still builds (re-run `--docker build` in one
other live worktree if one exists). Nothing under the game, state or AppData folders is touched; no git in a game folder.

## Kill criteria
- Docker Desktop not answering after one start attempt: do the script, test and README work, mark the PC test as not run in the report, and stop;
  do not loop on Docker.
- `docker volume inspect` cannot return labels in the installed Docker (the format string fails twice): fall back to the hash-only rule (keep a
  volume only when its name is the hash of a live checkout) and say so in the report.
- The S2 capture is attempted once; spend no more than about 10 tool calls on it.

## Open questions
Each has a default; it goes in the report if it still stands.
- **Should `wsc` own a clean verb instead of `build.sh --prune`?** Default: no, the script owns it (J31 review offered either); J63 moves it to
  the core with `build.sh`.
- **Auto-prune at the end of every `--docker` build?** Default: no, explicit only: a surprise removal on a shared PC is worse than an extra volume.

## Finish
Write `jobs/J97/report.md`: what changed, the PC test numbers (volumes before and after, wasm sha256 before and after), the S2 outcome (a) or
(b) with the artifact URL if captured, deviations from this brief and why, and open questions. Run `python3 core/wsc.py jobs check` and
`python3 core/wsc.py gates` before pushing. Then `wsc reg set jobs J97 status=review report=jobs/J97/report.md`.
