# Run 20261030_j18pc: J18 PC-rule guards on the live PC

officepc, 2026-10-30 23:51-23:56 UTC, Napoleon.exe sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250` (the `proxy/napoleon/identity.json`
value). Build `d5ee0a5997e6` (job/J18). Unattended through the watcher; headless launch on the virtual display. Every command's full output is
in `raw/`. The proxy was not installed when the run started (last history entry: an uninstall) and is not installed after it: the game folder
ended byte-identical to the pre-install snapshot.

## Watcher update and the exe verdict
- `pc_deploy.py kit --what harness`: `harness_20261030T235125Z_d5ee0a5997e6` (22 files + 5 kit files; watcher 1.1.0), `src/exe_identity.json`
  staged; `send`: 29 files, sha256 checked.
- `update kit=harness_20261030T235125Z_d5ee0a5997e6` (answered by the old 1.0.1 watcher, so without the new `exe:` line):
  `[update] CONFIRMED: watcher 1.1.0 stays` after the noop and the 30 s heartbeat window (`raw/update.log`).
- `status` job on 1.1.0, `exe` field: `{"sha1": "9aebcd2172f2878d781b079f7feb45b0e12e0250", "ok": true, "checked_utc": "2026-10-30T23:52:21Z",
  "expected": "9aebcd2172f2878d781b079f7feb45b0e12e0250"}` (`raw/status_job.txt`).

## pc_deploy and wsc setup
- Proxy kit `kit_20261030T235230Z_d5ee0a5997e6` (DLL from the main checkout's `build/proxy/napoleon/d3d9.dll`), `install`:
  `exe: ok Napoleon.exe sha1 9aebcd21... is the vanilla build in the identity` before the change and again after it; installed.
- `status` (installed): `exe: ok ...`, `git: ok, no .git in the game folder or its parents`, `foreign: 0 file(s) added or changed outside the
  install and the config files`; exit 0. The same after the launch and kill below (`raw/status_after_launch.txt`): the game wrote nothing foreign.
- `wsc setup`: `ok pc_rules: exe: ok ...; git: ok ...; foreign: 0 file(s) ...; git (Empire Total War): ok ...`; `setup: 11 ok, 0 failed`.
- `uninstall`: `exe: ok ...`, `game folder identical to the pre-install snapshot (1564 files)`. Final `status`: not installed, `exe: ok`, `git: ok`.

## Launch and kill through job.sh (dev-dxvk: dev.skip_intro=1)
`lock j18`, `profile dev-dxvk`, `launch size=1920x1080`:
`exe check: ok, Napoleon.exe sha1 9aebcd2172f2878d781b079f7feb45b0e12e0250 is the vanilla build in exe_identity.json`, then the headless
prepare, `running: Napoleon.exe pid 15216`, `headless: on_virtual (... window 1920x1080 ...)`, job ok. `kill`: terminated, ok;
`profile restore`: every file byte-identical or absent again; `unlock`. (`raw/launch.txt`, `raw/kill.txt`)

## The hook
This session was started in `C:\Users\liamr\repos`, not in the repo folder, so Claude Code did not load this repo's `.claude/settings.json` and
the hook did not run on its calls (D30 says to start in the repo folder). Running `git status` with the game folder as cwd here would have run
git there, so instead the exact settings command was fed the PreToolUse event (`raw/hook.txt`):
- `git status` in the Napoleon folder: `deny: Never run git in a game folder or the PC state folder (CLAUDE.md, J18) ...`
- `git status` in the repo worktree: allowed; `ls` in the Napoleon folder: allowed.

## Scratch
`job.sh scratch j18` -> `/c/napoleon_remastered_pc/_scratch/j18` (empty; nothing was written there).
