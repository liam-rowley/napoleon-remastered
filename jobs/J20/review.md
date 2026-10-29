# Review of J20 (Local Claude Code on the PC replaces the cloud route)

## Round 1 (2026-10-29, branch `job/J20` at 2b465eb)

Reviewer: a fresh Opus 5.5 Claude Code session on the PC (session `d9c62ba5-e02b-4c06-a796-68a94f4c0ab9`) that built none of the
branch. Checked against `jobs/J20/brief.md`, `jobs/J20/report.md` and `docs/DECISIONS.md`. About 30 tool calls.

**Verdict: merge after fixes.**

### Machines
- Local `wsc gates` in Git Bash on the PC at 2b465eb: 12 ok, 0 warn, 0 failed (89 host tests). That backs deliverable 8.
- CI run 40899932444 (head 2b55738, the run the DLL proof uses): `proxy` succeeded and its artifact `proxy-d3d9-napoleon` exists. The
  run reads "cancelled" overall only because `harness-windows` was cancelled. The report should say so; it is not a finding.

### Claims against evidence
- Setup 10/10 (`setup.txt`), Docker DLL = CI artifact (`dll_sha.txt`, same sha256 `2d0e60a4...`, the build id `3218c33bf59b` matches the
  `proxy.log` header), hook proof (commit a032b09 carries `Claude-Session: 849442f7-...`), and watcher lock/launch/kill/unlock (job ids in
  `game.txt`, the frontend line at 63 s in `proxy.log`): all present and consistent.
- Deliverable 6 had no proof. I ran one: a headless Haiku session in a J20 worktree tried `Write core/_deny_probe.txt` and was refused
  ("File is in a directory that is denied by your permission settings"), and no file was created. I did not probe the game-folder and
  empire rules, because a failed deny there would write into the folders they protect. Their path forms (`//c/...`, `~/...`) follow the
  Claude Code docs.
- `send` evidence: `C:\napoleon_remastered_pc\kits\kit_20261029T152159Z_edbf71c650b7` holds 17 files and there is no `.partial`
  leftover, which matches the claim. The output lines of `kit`, `send`, the refused second send, `install` and `set` are not in the run
  folder (see should-fix 2).

### Brief
All eight deliverables are present. The deviations (Store `python3` 3.15, a WSL distro exists, Docker was started once, `hooksPath`
reset, Playwright installed, one commit without a trailer) are named in the report with reasons. The proof waits on the proxy log
line instead of `"scene": "frontend"` in `state.json`. The report covers this (open question 5) but lists it under Proof rather than
Deviations. No kill criterion fired. Scope: nothing outside the brief.

### Risk-first reading
I read in depth `tools/pr_policy.py` and `tools/claude_hook.py` (they decide whether any job can merge), `.claude/settings.json`, and
`pc_deploy.py send` / `running_check` (they write into the PC state folder and gate installs into the game folder). I skimmed
`build.sh --docker`, `job.sh` root discovery, `setup.py` and the docs.
- The policy's fail-closed logic is right: one trailer set per commit, a commit with an empty set counts against that file, and the
  report/review intersection is unchanged. The failing-fixture tests cover no trailer, distinct trailers and a shared trailer.
- `send_kit` verifies the source, copies to `<id>.<utc>.partial`, re-hashes every file and renames into place only once all match,
  and refuses a reused id. The `tasklist /FO CSV` parse matches exact image names. Both are sound.

### Findings

**Should-fix**

1. `.claude/settings.json:18`: the hook command can block every shell call. `python3 "$(git rev-parse --show-toplevel)/tools/claude_hook.py"`
   resolves to `/tools/claude_hook.py` when the hook's working directory is outside a git repository. Python then exits 2, and Claude
   Code treats exit 2 from a PreToolUse hook as "block this call". The game folder is one of this setup's working directories, so a
   session that `cd`s there may find every Bash and PowerShell call refused until it gets out, and getting out also needs a shell call.
   How to see the exit code (measured on this PC): `echo '{"session_id":"s","tool_name":"Bash","tool_input":{"command":"ls"}}' | python3 /tools/claude_hook.py; echo $?`
   prints `can't open file ... [Errno 2]` and exits 2. I could not prove the stuck session itself: this review session's sandbox refused
   a nested `claude -p` probe.
   Fix: use the documented `$CLAUDE_PROJECT_DIR` and fail open (CI's `policy` check is the backstop), e.g.
   `f="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}/tools/claude_hook.py"; [ -f "$f" ] && python3 "$f"; exit 0`.
   Add a test that runs the settings command from a temporary non-repo folder with `CLAUDE_PROJECT_DIR` unset and expects exit 0.
   I tried to make this fix on the branch, but the reviewer session's auto mode refuses edits to Claude Code's own hook configuration,
   so it is left for the job chat (or Liam).
2. `proxy/runs/20261029_j20setup/game.txt`: the run README says this file holds "kit, send, install, watcher lock/launch/kill/unlock,
   uninstall", but it starts at `game.lock taken`. The report's "17 files sha-checked", "a second send of the same id refused",
   "install from the sent copy" and "set dev.state_json=1" have no saved output. The PC state folder backs the send. The rest needs
   the console output added, or the README and report should say these steps were not captured.

**Later**

3. Merge order. `job/J19`'s report commit `0507c06` has no `Claude-Session:` trailer, so once J20 is on `main` the J19 pull request
   is refused by its own rule. Either merge J19 first, or re-commit `jobs/J19/report.md` with a trailer on `job/J19`. Report open
   question 1 (J6) no longer applies: J6 is already on `main` (#28).
4. `proxy/tools/build.sh:21`: the image is pinned by digest, but `apt-get install` takes whatever mingw version the Ubuntu archive
   serves on the day, so Docker and CI identity can drift silently. The build prints the compiler version. A later job could pin the
   package versions or compare the printed version with CI's.
5. The report's open questions 2, 3, 5 and 6 are Liam's calls or other jobs' work (the verb question, which `python3` to pin, `state_json`
   needing the Lua bridge, fast test launches). Open question 6 is already in Liam's memory as a standing rule (`dev.skip_intro=1`) and
   still needs its `needs_brief` row.

### What must change before `merge`
Should-fix 1 (the hook command plus its test) and should-fix 2 (the evidence, or a corrected claim). The row stays at `review`.
