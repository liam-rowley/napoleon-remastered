# Harness: PC watcher, game lock, profiles, hang watchdog (job J2)

Agents (Claude Code on the PC, D30) never start, kill or profile the game themselves. They drop job files into a folder the watcher reads. The watcher is
`harness/core/watcher.ps1` (game-agnostic); everything Napoleon-specific is in `harness/napoleon/adapter.json` and
`harness/napoleon/profiles/`. Everything is Windows PowerShell 5.1 and ASCII-only; all data files are UTF-8 without BOM (`tests/test_repo_rules.py`);
all times are UTC (`...Z`).

## Install (Liam, once)
1. In Git Bash in the repo: `python3 proxy/tools/pc_deploy.py kit --what harness` builds a kit in `build/kits/`, then
   `python3 proxy/tools/pc_deploy.py send --kit build/kits/<id> --state 'C:\napoleon_remastered_pc'` copies it sha-checked to `<state>\kits\<id>`.
2. Double-click `Install watcher.cmd` in that kit folder (`Uninstall watcher.cmd` removes it). It copies the files
   sha-checked into `C:\napoleon_remastered_pc\watcher\src`, registers the logon task `napoleon_remastered watcher` (never
   Empire's `rml_mod watcher`), starts it and writes `install_result.json`. It refuses when a game is running.
3. Later updates need no click: `send` a new kit, then job `update kit=<id>` (see below).

## Watcher root (`C:\napoleon_remastered_pc\watcher`, `/c/napoleon_remastered_pc/watcher` in Git Bash)
`src\` code, `adapter.json` and `exe_identity.json` (pc_deploy's sha-checked copy of `proxy/napoleon/identity.json`) | `jobs\` `<id>.request` `.out` `.done` `_ids.txt` | `profiles\<name>\`, `profiles\_saved\<ts>_<owner>\`,
`profiles\_active.json` | `runs\<utc>_hang\`, `runs\<utc>_winprobe\` | `vdisplay_restore.json` (only while a launch has changed the virtual display's mode) | `_to_delete\` (nothing is ever deleted) | `update\`, `backup\` | `game.lock`, `watcher.status`,
`watcher.alive`, `watcher.pid`, `watcher.log`, `watcher.ini`, `watcher.zombie.json`, `watcher.stop`, `watchdog.off`, `install.log`, `install_result.json`.
Kits live beside it: `<state>\kits\<id>`. PC experiments live in `<state>\_scratch\<owner>\` only: `job.sh scratch <owner>` creates it
and prints its Git Bash path (owner `^[a-z0-9][a-z0-9_-]{0,31}$`, the job id: `j18`). The Claude Code hook (`tools/claude_hook.py`) denies a shell
write anywhere else in the state folder or in a game folder, and any git there (J18).

## Job requests
Write `jobs\<id>.request` (write a temp name, then rename). Ids are never reused (a reused id is refused). FIFO.
- One line: `launch` | `kill` | `profile <name>` | `profile restore` | `status` | `noop` | `restart [full]` | `update kit=<id> [noop_s= healthy_s= stable_s=]`.
  `launch` takes `route=exe|steam wait_log=<text> wait_s=<n>` and the headless arguments below. **A launch is headless unless `visible=1`.**
- A script: `cmd` by default, or `ps1` with `#ps1` as the first line. Optional header `#job owner=<you> timeout=<s> type=cmd|ps1`.
- Result `<id>.done` (JSON, written last): `status` ok|failed|refused|timeout|lost, `exit` (refused = -2, timeout = -1), `reason`, `start_utc`, `end_utc`; output in `<id>.out`.
- `launch`, `kill`, `profile` need `owner=` equal to the owner in `game.lock`. A script that starts or kills the game or writes a config file needs `#job owner=` too.
  Read-only scripts never need a lock. **A script that runs `git` is refused**, lock or not, whatever `job_script_guard` says (J18: watcher
  jobs never need git; agents run it in the repo checkout).
- Every `launch` first hashes the game exe (sha1, cached by size and mtime) against `src\exe_identity.json`: a mismatch, or no identity, is
  refused (-2) before any display or config change (`exe_check=refuse`); `exe_check=warn` launches with a WARNING line. `watcher.status` has
  `exe` {sha1, ok, checked_utc, expected, detail} (refreshed by every launch and `status` job), and an `update` job's output names the verdict.

## Game lock
`game.lock` is one line: `owner= session= purpose= started=<UTC> [hang_s=<n>]`. Its mtime is the refresh time; 20 minutes without a refresh and it
expires (moved to `_to_delete`). Release = move it away. A fresh lock from the Empire watcher, or the other title running, blocks a launch. The
watchdog is armed only while a valid lock exists and the watcher launched the game.
`harness/core/job.sh` does all of it from Git Bash: `job.sh lock <owner> <session> <purpose> [hang_s]`, `job.sh <owner> <file|-> [timeout_s]`
(blocks inside one call until the result; exit code = the job's, refused 2, no answer 124), `touch`, `unlock <owner>`, `status`, `root`, `scratch <owner>`.
The root comes from the adapter: `state_dir` as a Git Bash path plus `watcher_subdir` (no environment variable; `$WATCHER_ROOT` overrides it for tests).

## Hang watchdog and zombies
Hung: an unarmed game never counts; not in `hang_startup_s`; not while minimised/hidden or while a game-touching job runs; else `IsHungAppWindow` sustained
`hung_window_s`, or no CPU progress AND no heartbeat-file write for `hang_s`. Then: out-of-process minidump (`dump.ps1`, SysWOW64 for the 32-bit game),
logs/config/lock archived to `runs\<utc>_hang\` with `hang.txt` (ends `kill: pending`), then kill, then `hang.txt` rewritten ending `kill: killed`
or `kill: ZOMBIE ...`, then the log line `HANG handled: ...` (the completion signal). A process that survives is a zombie: persisted in `watcher.zombie.json`,
every launch refused with "PC NEEDS REBOOT" until the pid is gone. No DLL change is involved.

## Config profiles
Targets are the adapter's `config_files` (prefs, keys, mod ini, dxvk.conf). `profile <name>` snapshots all targets first (absent is a state), applies
the profile's full copy / `.set` overlay / `.absent` marker, and writes `_active.json` before changing anything. Overlays are computed on the snapshot,
so profiles never stack. `profile restore` (or lock release, expiry, owner change; deferred while the game runs) restores byte for byte, checked by sha256.
Overlay styles: `ini`, `conf`, `prefs` (the game's UTF-16LE `key value; # comment #` file: a key's value is replaced in place, a missing key appended as `key value;`,
every other byte kept; `!key` refused); `style: none` allows full copies only (keys, battle_prefs).

## Update and rollback
`update kit=<id>` runs `update.ps1` detached: back up, replace sha-checked, restart, require a new pid, the expected version and a fresh heartbeat, then a
`noop` job answered by the new watcher, then a stable window. Any failure restores the backup byte for byte (dead-man switch). `watch.cmd` is never replaced.

## Settings (`watcher.ini`, key=value; not in the `config_keys` registry, whose rows feed the generated tables)
`hang_s`=120, `hang_startup_s`=180, `hung_window_s`=60, `cpu_epsilon_s`, `dump_wait_s`=90, `dump_type`, `watchdog`=1, `zombie_wait_s`=15, `job_timeout_s`=1800,
`prune_hours`=24, `lock_stale_min`=20, `job_script_guard`=refuse|warn, `exe_check`=refuse|warn, `launch_confirm_s`=20, `loop_ms`=1000, `winprobe`=1; tests only: `test_hooks`, `test_fake_zombie`, `test_vdisplay_script` (stands in for the display tool; the CI runner has no virtual display).

## Headless launch (J13)
Every `launch` puts the window on the virtual display and fails closed; the proxy side is `proxy/README.md`. The request is one line (the owner holds `game.lock`):
`launch owner=<you>` (4K) | `launch owner=<you> size=1920x1080` | `launch owner=<you> visible=1` (only with Liam present; touches nothing). Also `headless_wait_s=<n>` (default 180).
Flow, in this order; any failure refuses or fails the job and nothing stays on screen: (1) `d3d9.dll` must contain `headless_status.json` (an older proxy would put the window on a
real monitor); (2) `vdisplay_probe.ps1 -Check -Size`; at another size `-Set` (only a mode the driver offers), the mode before the lock is saved to `vdisplay_restore.json` and put back by `Pump`
once the game has exited AND the lock is released or expired (also after a crash or kill): every mode change makes Windows move Liam's cursor to the centre
of the primary, so it changes at most twice per sitting, and the tool puts a recentred cursor back; (3) the adapter's `headless` block (prefs `x_res`, `y_res`, `gfx_fullscreen false`, and muted: `sound_master_enabled false`, `sound_master_volume 0`, Liam 2026-10-29, returned by the byte-identical restore; mod ini `headless.enabled`, `headless.size`) is
overlaid on the files as they are, under a snapshot recorded like a profile (`_active.json`, `headless` in its history), so lock release or expiry restores byte for byte; a warning
when the base prefs carry `x_pos`/`y_pos` inside the virtual display's rect; (4) `win_probe.ps1` starts (every launch); (5) the game starts and the job waits for
`napoleon_remastered\headless_status.json` naming the game's pid: `on_virtual` = ok, `refused` = failed with the detail and exit code 2160, silence = the game is killed. `wait_log` still works after.
Job results: refused (-2) before the start, failed (1) for `HEADLESS FAILED: ...`.

## Display tool (`vdisplay_probe.ps1`)
Acts only on the one attached, non-primary display whose adapter or monitor string matches `-Name` ("Virtual Display Driver"); never by size, index or `DISPLAYn`; refuses a primary,
no match, two matches. `-Test <sizes>` (default: a CDS_TEST probe that prints the `vdd_settings.xml` edit for Liam when a mode is missing) | `-Check -Size WxH` | `-Set WxH [-Hz n] -SaveTo <json>` |
`-Origin X,Y -SaveTo <json>` (refuses a rect overlapping another display) | `-Restore <json>`. Changes are dynamic (no registry), CDS_TEST first, every display is printed before and after,
a changed neighbour is a warning. Exit 0 ok, 2 bad arguments, 3 `VIRTUAL MISSING`, 4 `VIRTUAL WRONG SIZE`, 5 apply failed, 6 mode not offered, 7 refused. `-Origin` is the only display change an
agent may make by hand, in a topology test. Selection is the pure function `Select-VirtualDisplay` (tested in `Test-Unit.ps1` with fake lists of Liam's topologies).

## Window probe (`win_probe.ps1`)
Started detached by every launch before the game, into `<root>\runs\<utc>_winprobe\` (named in the job output): `ready.txt`, `winprobe.txt` (live log + summary) and, when the game exits,
`winprobe.json`: `samples`, `duration_ms`, `longest_visible_on_real_ms`, `visible_on_real_ms_total`, `visible_on_real_samples`, `visible_off_target_count` (samples with a shown window not wholly inside
the virtual display), `cloaked_ms`, `monitor_changes` (each with the monitor list), `first_visible` (time, rect, monitor), `windows` (per window: class, visible / cloaked / on-real ms, helper_1x1), `topology_start`,
`topology_end`, `exit_code`. About 10 ms samples, the monitor list re-read every sample, physical pixels (per-monitor DPI V2), no admin. Windows of at most 1x1 pixel are listed, not counted.

## Tests
`harness/tests/Run-HostTests.ps1 -Suite unit|integration|all`; CI job `harness-windows` runs all under Windows PowerShell 5.1 with compiled fake games.
A flaky integration case: `-Only <case regex> -Repeat <n>` (fails on the first failed run, prints the pass count), or on the runner
`gh workflow run gates.yml --ref <branch> -f only='hang watchdog' -f repeat=10` (only `harness-windows` runs). Integration cases
assert on watcher output only after the watcher's own completion line (`Wait-LogMatch ... -Since (Log-Mark)`), never just after a
process exits or a file appears, and read a file the watcher may delete once (`Hash-OrAbsent`), never `Test-Path` then read (J42).
A failed case or watcher start prints the watcher log tail and heartbeat age (`Show-WatcherState`), so the CI log alone explains it.
A watcher start is slow on a cold machine: on fresh CI runners a new watcher process reached its main loop 17 to 35 s after it
started (39.9 s in J42 run 40970029940), while a warm load of the script takes under 3 s and the `Add-Type` compile under 2 s, so
the time is powershell.exe start-up before the first statement. The watcher logs its first-statement and compile times (in
`watcher.log`; the CI log shows them only when a start fails), and the tests give the start its own budget (150 s) before the 40 s
heartbeat wait. `Start-TestWatcher` prints `watcher up after N ms` on every run.
Locally, `python3 core/wsc.py gates` runs the unit suite under Windows PowerShell 5.1 when a harness input changed
(`tests/test_harness_host.py`, about 20 s; `WSP_HARNESS_TESTS=skip` skips it with a warning). The integration suite is CI-only and
the gate says so: it sets the machine's time zone and kills `Fake*.exe`. The CI failure classes and their guards: `docs/CI_FAILURES.md`.

## Control API and acceptance (J4, J43, J44)
`harness/core/ctl.py <verb>` (result contract in its header): `scene <id>` launches through the watcher with the adapter's `ctl.launch.keys`
when needed, moving UAC VirtualStore copies of the mod folder aside first (fact `napoleon.harness.uac_virtualstore`). `harness/core/acceptance.py
measure --run <id>` writes `harness/acceptance/baseline.json` from two passes; `run --passes 20 --run <id>` takes the lock per pass, compares with
the baseline and appends one ledger line per pass with its committed evidence `harness/runs/<id>/pass_NN.json` (rule 79, `tools/pr_policy.py`).

## Open questions
See `jobs/J2/report.md` and `jobs/J13/report.md` (open questions). Prefs file format: fact `napoleon.config.preferences_format`.
