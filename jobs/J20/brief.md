# J20: Local Claude Code on the PC replaces the cloud route

Phase 1, job 20: make the repo work from Claude Code on Liam's PC (D30) and retire every cloud-only path: the device VM mount, the
`device_commit_files` kit delivery and the cloud build. Afterwards a fresh Claude Code session in the repo folder can run the gates,
build the proxy, install it and drive the game through the watcher with nothing but this repo's instructions.

Model: Sonnet, no reason needed (scripts, Python tooling, docs, D15). Budget about 100 tool calls; at the cap, stop, commit,
report what is left. No subagents.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J20`; "Where agents run"). Read `docs/DECISIONS.md` (D2, D20-D22, D25, D29-D31),
  `harness/README.md`, `proxy/README.md` ("Build", "PC install and uninstall") and the reports of J2 and J3.
- Bootstrap: this job runs before `python3` is guaranteed in Git Bash. If `python3 --version` fails, use `py -3` for this job's
  commands until deliverable 1 fixes it.
- Search before writing: `python3 core/wsc.py find job.sh`, `find pc_deploy`, `find build`.

## Facts (read 2026-10-29 from the planning chat)
- PC: Windows x64, device name `officepc`. Installed: Python 3.12 (`%LOCALAPPDATA%\Programs\Python\Python312`, no `python3`
  command), Docker Desktop, GitHub CLI, Claude Code CLI. **No WSL distro.** Repos folder: `%USERPROFILE%\repos`.
- Cloud-only assumptions still in the tree (`grep -rniE "cloud|device VM|device_mount|DEVICE_MOUNTS|device_commit"`):
  `harness/core/job.sh` (mount root `$DEVICE_MOUNTS`, default `$HOME/mnt`, + adapter `device_mount`), `harness/README.md`,
  `harness/core/watcher.ps1` (the refusal text naming `device_commit_files`), `proxy/README.md` (Build; PC install steps 1-2),
  `proxy/tools/pc_deploy.py`, `exe_info.py`, `pack_list.py` (headers: "runs on the device VM"; `pc_deploy` process detection
  "the device VM cannot see Windows processes"), `registries/tools.jsonl` rows `harness.core.job`, `harness.core.watcher`,
  `proxy.tools.pc_deploy`, `tests/test_job_sh.py`, `tests/test_pc_deploy.py`, `.github/workflows/gates.yml` (a comment).
- Review independence: `tools/pr_policy.py` refuses a job branch whose report and review share a `Claude-Session:` trailer. Local
  Claude Code adds no such trailer, so today the check **passes silently** when both files have none.

## Deliverables
1. **Setup check as a verb:** `python3 core/wsc.py setup` (a verb in `tools/verbs/`; check only, `--fix` for the safe fixes) checks,
   each with a one-line fix hint: Git Bash; `python3` resolves to Python >= 3.12 (`--fix`: a `python3.exe` copy of `python.exe`
   beside it, or the shim you prove works); the submodule at the pinned tag; `core.hooksPath`; shell scripts check out with LF
   (`.gitattributes`, `core.autocrlf`); `gh auth status`; Docker Desktop answering; the `empire-remastered` sibling clone present
   with no local changes; Python Playwright with Chromium; the watcher root reachable and the watcher alive (`job.sh status`).
   Host tests for the pure parts. Replace CLAUDE.md's "until it lands" line with "run `wsc setup`".
2. **Watcher from Git Bash:** `job.sh` finds the watcher root from the adapter's `state_dir` (`C:\napoleon_remastered_pc` ->
   `/c/napoleon_remastered_pc`) with no environment variable needed; `DEVICE_MOUNTS` and `device_mount` go (adapter, tests, README).
   Every `python3` call in shell tools still works on the PC.
3. **Kits without the bridge:** `pc_deploy.py send --kit <dir>` copies a built kit sha-checked into `<state>\kits\<id>` (a reused
   id is refused), so `install` and the watcher's `update kit=<id>` work as before; process detection uses `tasklist` on Windows.
   Fix the watcher's refusal text. Tool headers say where each tool runs now; whether `pc_deploy`, `exe_info` and `pack_list` can
   become verbs now that the repo is on the PC is an open question for the report, not this job.
4. **Proxy build in Docker (D31):** `proxy/tools/build.sh` gains a `--docker` route (or a wrapper with a tools row) that runs the
   same `all` target in `ubuntu:24.04` pinned by digest, with the same apt packages as the CI `proxy` job, the repo mounted, outputs
   in `build/`. Document it in `proxy/README.md` "Build" (the cloud container leg goes).
5. **Review independence fails closed:** every local session's commits carry a `Claude-Session:` trailer that names the Claude Code
   session id, set automatically (a Claude Code hook in a committed `.claude/settings.json`, a repo-local git hook, or both; prove the
   route you pick). `pr_policy.py` refuses a job branch when `report.md` or `review.md` was committed with **no** trailer. Failing-
   fixture tests for both cases. A git hook that must live in `core/.githooks` is a warscape-core change (PR and tag), not a local edit.
6. **Guard rails in `.claude/settings.json`:** deny Edit and Write under the game folder, `../empire-remastered/` and `core/`.
7. **Docs and registries:** `harness/README.md`, `proxy/README.md` and the tools rows describe the local route only; no living doc
   names the device VM, the cloud container or `device_commit_files` (the grep above returns only dated run reports and job history).
8. **Gates on the PC:** `python3 core/wsc.py gates` green in Git Bash on the PC as well as in CI. A Windows-only failure in this repo
   is fixed here; one inside `core/` is filed in warscape-core (`docs/BACKLOG.md` PR), never patched locally.

## Proof (on the PC, run ids in the report)
- `wsc setup` all green (output saved under `proxy/runs/<utc>_j20setup/`).
- The Docker-built `d3d9.dll` is byte-identical (sha256) to the CI `proxy` artifact for the same commit (`gh run download`).
- That DLL sent and installed with `pc_deploy.py send` + `install`; then through the watcher only: `job.sh lock`, `launch` waiting
  for `"scene": "frontend"`, `kill`, `unlock`. `proxy.log` names the build id = the commit. Then `pc_deploy.py uninstall` exits 0.
- A test branch whose report and review carry no trailer is refused by `pr_policy.py`; one with distinct trailers passes.

## Out of scope
J18's PC rule guards, J19's watchdog race, moving anything into warscape-core (J12), any change to watcher behaviour beyond root
discovery and messages, new game features. Liam updates the claude.ai Project instructions himself.

## Kill criteria
- Docker Desktop cannot run the build after about 10 calls (virtualisation off, daemon down): use the CI artifact (`gh run download`)
  for the proof, mark D31 unproven in the report, finish the rest.
- Docker and CI DLLs differ: stop that part after about 5 calls; record both sha256 and the differing PE fields; do not change
  build flags to force a match.
- Automatic trailers need more than one small hook in warscape-core: ship the fail-closed policy with a documented manual trailer,
  and report the core change as a follow-up job.
- Anything would launch the game outside the watcher or write into the game folder outside `pc_deploy.py`: stop and ask Liam.

## Finish
Write `jobs/J20/report.md`: what changed and why, the proof run ids and both DLL sha256, the setup check output, deviations from this
brief and why, open questions (including the verb question in deliverable 3). Then
`wsc reg set jobs J20 status=review report=jobs/J20/report.md`.
