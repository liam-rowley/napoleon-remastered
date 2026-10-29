# J20 proof run, 2026-10-29 (PC officepc, Git Bash, Claude Code session 9c22f827-331a-4564-89b0-d0635315c622)

- `setup.txt`: `python3 core/wsc.py setup`, 10 of 10 ok.
- `dll_sha.txt`: `proxy/tools/build.sh --docker all` at 3218c33bf59b vs the CI `proxy` artifact of run 40899932444 (head 2b557389fc30, the
  same DLL inputs): byte-identical. `build.sh --docker repro`: identical from another path.
- `hook_proof.txt`: a fresh headless Claude Code session in the J20 worktree ran `git commit --allow-empty`; the PreToolUse hook denied it
  and named the flag; the retry made commit a032b09 with `Claude-Session: 849442f7-a0c0-4324-b2e7-990cd2c74c6e`.
- `game.txt`: kit, send, install, watcher lock/launch/kill/unlock, uninstall; `proxy.log` from the launch.
