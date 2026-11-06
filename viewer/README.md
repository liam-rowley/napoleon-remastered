# Review viewer

RmlUi, FreeType and Lua 5.1.1 with the engine's float32 numbers, compiled to WebAssembly: the one renderer for the review page and
for the gates' PNGs (`docs/plans/UI_PIPELINE.md` section 2.4). Built in J31 (S1, S2 spikes: `jobs/J31/report.md`).

- `pins.json`: the versions (RmlUi, FreeType, Lua, stb_image, the emsdk image), each by commit or sha256. J30's in-game host reads it.
- `core/` (game-agnostic, core candidate): `fetch_sources.py`, `CMakeLists.txt`, `build.sh`, `core/src/viewer.cpp` (wasm entry points),
  `web/` (host page and glue), `render.py` (headless PNGs), `core/tests/lua_numbers.mjs` (float32 proof under Node).
- `napoleon/`: fonts (each with its licence) and screens (`hello/` is the J31 test screen; `screen.json` lists a screen's files).

## Build

```sh
viewer/core/build.sh --docker all     # on the PC (Docker Desktop): build/viewer/out/viewer.js + viewer.wasm, SHA256SUMS, Node number test
python3 viewer/core/render.py viewer/napoleon/hello --size 1920x1080 --dp-ratio 1.0 --out x.png
python3 viewer/core/render.py viewer/napoleon/hello --stage-only <dir>   # the folder a review artifact is published from
python3 -m unittest tests.test_viewer
```

CI: `.github/workflows/gates.yml` job `viewer` runs the same `build.sh --docker all`, the tests and two renders on every push that
touches `viewer/` (`wsc.toml` `[ci] inputs`), and keeps everything as the `viewer-wasm` artifact. Fallback when Docker is down:
`gh run download <run id> -n viewer-wasm -D build/viewer/out`. When CI skipped `viewer` because the same input tree already passed (J54), the
run's summary names the run that built it: download from that one.

## Housekeeping

`build.sh --docker` keeps each checkout's CMake tree in its own Docker volume `napoleon-viewer-cmake-<12 hex of the checkout path's sha256>`,
labelled `napoleon.viewer.checkout=<path>` (J97). Worktrees come and go; their volumes stay until pruned:

```sh
viewer/core/build.sh --prune --dry-run   # prints keep / would remove for every napoleon-viewer-cmake volume, removes nothing
viewer/core/build.sh --prune             # removes the ones it named; a volume in use is skipped
```

It keeps a labelled volume whose checkout folder still exists, and an unlabelled one (made before J97) whose name is the hash of this checkout
or of a worktree in `git worktree list` that exists on disk; it removes the rest and the old shared `napoleon-viewer-cmake`. Volumes are build
caches: a removed one is rebuilt by the next `--docker build`. It names no other volume and runs no bulk prune. If it cannot remove the old
shared volume: `docker volume rm napoleon-viewer-cmake`. Pruning is explicit only, never part of a build.

## Publishing a screen as an artifact

Art must be a web image type (PNG or JPEG: the artifact refuses `.tga`); RML, RCSS and Lua go with `contentType: text/plain`;
`viewer.wasm` is served as `application/wasm`.
