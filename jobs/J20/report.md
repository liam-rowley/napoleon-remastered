# J20 report: Local Claude Code on the PC replaces the cloud route

Built on `job/J20` from Claude Code on officepc (Git Bash), session `9c22f827-331a-4564-89b0-d0635315c622`, 2026-10-29. Evidence:
`proxy/runs/20261029_j20setup/`.

## What changed and why
1. **`wsc setup`** (`tools/verbs/setup.py`, tests `tests/test_setup.py`): ten checks, each with a one-line fix: Git Bash (and that `bash`
   on PATH is Git's, not the WSL launcher: the J6 Windows test failures), `python3` >= 3.12 (`--fix` copies `python.exe` to `python3.exe`),
   core at the pinned tag, `core.hooksPath` exactly `core/.githooks` (as the core `hooks` gate wants; `--fix` sets it), no CR in tracked
   `.sh`/`.py`, `gh auth status`, `docker info`, the `empire-remastered` sibling clean (found from a worktree too), Python Playwright
   with Chromium, `job.sh status`. CLAUDE.md now says "run `wsc setup`".
2. **job.sh root from `state_dir`**: `C:\napoleon_remastered_pc` -> `/c/napoleon_remastered_pc` (+ `watcher_subdir`); `DEVICE_MOUNTS` and
   the adapter's `device_mount` are gone (adapter, job.sh, `tests/test_job_sh.py`, `harness/tests/Test-Lib.ps1`, README). `$WATCHER_ROOT`
   stays as a test override. All job.sh tests pass in Git Bash on the PC (MSYS converts `/c/...` arguments for Windows `python3`).
3. **`pc_deploy.py send --kit <dir> --state <state>`**: verifies the source kit, copies to `<state>\kits\<id>.<utc>.partial`, re-hashes
   every file, renames into place; an existing id is refused. `running_check` without a watcher parses `tasklist /FO CSV` (exact image
   names, not a substring of the whole output); the log heuristic is left for non-Windows hosts (tests). Watcher refusal text names
   `pc_deploy.py send`. Headers of `pc_deploy`, `exe_info`, `pack_list`, `job.sh`, `watcher.ps1` say where they run now.
4. **`build.sh --docker <target>`** (D31): runs the same target in `ubuntu:24.04` pinned by digest
   (`sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852`) with `g++-mingw-w64-i686 g++ python3 ca-certificates`
   (CI installs the first; the runner image has the rest). The build id is computed on the host and passed as `WSP_BUILD_ID`, because a
   worktree's `.git` file points at a Windows path the container cannot see. `smoke` (wine) is refused under `--docker`. ~55 s per build.
5. **Review independence fails closed**: `pr_policy.py` gets one trailer set per commit and refuses a job branch when any commit touching
   `report.md` or `review.md` has no `Claude-Session:` trailer. Route for the trailer: a PreToolUse hook (`tools/claude_hook.py`, wired
   in the committed `.claude/settings.json`, matcher `Bash|PowerShell`) **denies** a `git commit` that lacks
   `--trailer "Claude-Session: <this session id>"` and names that exact flag; the agent re-runs with it. Chosen over rewriting the command
   (`updatedInput`): the docs only define `updatedInput` together with an `allow`/`ask` decision, and `allow` would auto-approve whole
   compound commands (`git add && git commit && git push`). No warscape-core change was needed.
6. **`.claude/settings.json` deny rules**: `Edit(//c/Program Files (x86)/Steam/steamapps/common/Napoleon Total War/**)`,
   `Edit(~/repos/empire-remastered/**)`, `Edit(/core/**)` (Edit rules cover Write). `.gitignore`: `.claude/worktrees/`, `.claude/settings.local.json`.
7. **Docs and registries**: `harness/README.md`, `proxy/README.md` ("Build", "PC install and uninstall", dev channel), the CI comment and
   the tools rows describe only the local route. The brief's grep now hits only CLAUDE.md's "no cloud sessions" rule, the game's cloud
   shaders and dated DECISIONS rows.
8. **Gates on the PC**: `python3 core/wsc.py gates` 12 ok in Git Bash (was 1 failed: the two Windows-only test failures, both fixed here).

## Proof
- `wsc setup`: 10 of 10 ok (`setup.txt`; python3 is the Microsoft Store Python 3.15.2 alias, see open questions).
- **D31 proven**: Docker DLL build `3218c33bf59b` sha256 `2d0e60a44db106981a59b9e9527c2005c0a48f784fe91c19495542af2fbf452c` =
  CI `proxy` artifact of run 40899932444 (head 2b557389fc30), `cmp` identical (`dll_sha.txt`). `build.sh --docker repro`: identical.
- Hook, live: a fresh headless Claude Code session in the worktree tried `git commit --allow-empty` -> denied with the flag -> retried ->
  commit `a032b09` with `Claude-Session: 849442f7-a0c0-4324-b2e7-990cd2c74c6e` (`hook_proof.txt`; the empty commit stays as evidence).
- Policy on git: `tests/test_pr_policy.py::PolicyOnGit` builds a fixture repo: report and review without trailers -> refused (exit 1, both
  files named); distinct trailers -> ok; the same trailer on both -> refused.
- Game (`game.txt` for the watcher steps, `deploy_steps.txt` for the deploy steps (transcribed, backed by `install_history.json`,
  `sent_kit_listing.txt`, `resend_refused.txt`), `proxy.log`, `uninstall.txt`): `pc_deploy.py kit` -> `kit_20261029T152159Z_edbf71c650b7`; `send` to
  `C:\napoleon_remastered_pc\kits\` (17 files sha-checked; a second send of the same id refused); `install` from the sent copy; `set
  dev.state_json=1`. Watcher only: `job.sh lock j20`, `launch wait_log=scene:.intro.->.frontend` -> job
  `j20-20261029T152646Z-2214931641` ok, frontend after 63 s (pid 21372); `kill` -> job `j20-20261029T152753Z-1241922141` ok; `unlock`.
  `proxy.log`: `build 3218c33bf59b` = the Docker/CI DLL. `pc_deploy.py uninstall` exit 0, game folder identical to the pre-install
  snapshot (1564 files). That uninstall removed J3's earlier install too (same `install.json` record); nothing proxy-side is installed now.
  A first launch (job `j20-20261029T152223Z-223499665`) failed only because my `wait_log` pattern targeted `state.json`, which was
  not written (open question 5); the game had reached the frontend at 15:24:14Z and was killed through the watcher.

## Deviations
- The brief's facts said no `python3` and no WSL distro. On this PC `python3` already resolves (WindowsApps alias, Python 3.15.2) and a
  stopped WSL `Ubuntu` distro exists (as well as `docker-desktop`). Nothing needed `py -3`; `wsc setup` checks that `bash` is Git's.
- Docker Desktop is a per-user install (`%LOCALAPPDATA%\Programs\DockerDesktop`) and was not running; I started it once.
- `wsc setup --fix` set `core.hooksPath core/.githooks` in the shared clone config (it was the absolute path to the main clone's hooks,
  which the core `hooks` gate warns about and which would run the main checkout's pin from a worktree).
- I installed Python Playwright and Chromium into the user's python3 (`pip install --user playwright`, `playwright install chromium`)
  for the setup check.
- One commit (`7c4dd5e`) has no trailer: this session's hooks come from the main checkout's settings, which had no hook yet. It touches
  no report or review, so the policy does not care.

## Open questions
1. **Merge order with J6**: J6's report commits (`d407c03`, `512a8db`) have no `Claude-Session:` trailer, so once J20 is on main the J6
   pull request is refused. Merge J6 first, or re-commit `jobs/J6/report.md` with a trailer on `job/J6`.
2. **Verbs** (deliverable 3): `pc_deploy` must stay a standalone stdlib script while the kit carries a copy for `Install watcher.cmd`;
   its repo-side subcommands (`kit`, `send`, `status`) could become a `wsc deploy` verb that calls it. `exe_info` and `pack_list` read one
   file each and fit `wsc` verbs now that the repo is on the PC (natural home: J7's asset index). Not done here.
3. `python3` is the Store alias (3.15.2), not the Python 3.12 install the brief named. It works; whether to pin one interpreter (and
   CI's 3.12) is Liam's call.
4. Hooks load from the folder a session started in, and the hook command runs `$CLAUDE_PROJECT_DIR/tools/claude_hook.py` (the
   session's start folder, not the current one). Until this is on main, sessions started in the main checkout find no script and the
   hook does nothing; CI's policy check still refuses a job without trailers.

## Review fixes (J20 review, f6bb8de)
1. The hook command no longer calls `git rev-parse`: outside a repo it resolved to `/tools/claude_hook.py`, and python's exit 2
   would block every shell call. It now runs `${CLAUDE_PROJECT_DIR:-.}/tools/claude_hook.py` only when it exists and exits 0 on any
   failure; `claude_hook.py` itself never exits non-zero. Test: `test_the_settings_command_never_blocks` runs the committed command
   string from a non-repo folder with no, an empty and a missing project dir (exit 0, no output), and with the real one (deny).
   The `.claude/settings.json` edit was made with Liam's explicit permission (auto mode refuses hook-setting edits otherwise).
2. The deploy-step output is now in `deploy_steps.txt`, marked as transcribed, with the on-disk records that back it.
5. `dev.state_json=1` alone wrote no `state.json` in this run (the scene tracker logged `scene: intro -> frontend` in `proxy.log`).
   Whether it also needs `dev.lua_bridge` is for J3's owner; `harness/README.md`'s `"scene": "frontend"` wait depends on it.
6. **Fast test launches by default** (Liam, 2026-10-29, during this run): the kit installs release defaults (`dev.skip_intro=0`), so a
   test launch plays every splash and the intro (63-110 s to the frontend). Liam wants fast launches in all test cases: a test profile
   or kit default with `dev.skip_intro=1` (and whatever else shortens the start). Out of this brief's scope; needs a `needs_brief` row.
