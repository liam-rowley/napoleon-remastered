# Harness: PC watcher, game lock, profiles, hang watchdog (job J2)

Cloud agents never touch the PC directly. They drop job files into a folder the PC's watcher reads. The watcher is
`harness/core/watcher.ps1` (game-agnostic); everything Napoleon-specific is in `harness/napoleon/adapter.json` and
`harness/napoleon/profiles/`. Everything is Windows PowerShell 5.1 and ASCII-only; all data files are UTF-8 without BOM (`tests/test_repo_rules.py`);
all times are UTC (`...Z`).

## Install (Liam, once)
1. In the cloud: `python3 proxy/tools/pc_deploy.py kit --what harness` stages a kit; sync it to the PC (`pc_deploy`).
2. On the PC double-click `Install watcher.cmd` in the kit folder (`Uninstall watcher.cmd` removes it). It copies the files
   sha-checked into `C:\napoleon_remastered_pc\watcher\src`, registers the logon task `napoleon_remastered watcher` (never
   Empire's `rml_mod watcher`), starts it and writes `install_result.json`. It refuses when a game is running.
3. Later updates need no click: job `update kit=<id>` (see below).

## Watcher root (`C:\napoleon_remastered_pc\watcher`, seen as `$HOME/mnt/napoleon_remastered_pc/watcher`)
`src\` code and `adapter.json` | `jobs\` `<id>.request` `.out` `.done` `_ids.txt` | `profiles\<name>\`, `profiles\_saved\<ts>_<owner>\`,
`profiles\_active.json` | `runs\<utc>_hang\` | `_to_delete\` (nothing is ever deleted) | `update\`, `backup\` | `game.lock`, `watcher.status`,
`watcher.alive`, `watcher.pid`, `watcher.log`, `watcher.ini`, `watcher.zombie.json`, `watcher.stop`, `watchdog.off`, `install.log`, `install_result.json`.
Kits live beside it: `<state>\kits\<id>`.

## Job requests
Write `jobs\<id>.request` (write a temp name, then rename). Ids are never reused (a reused id is refused). FIFO.
- One line: `launch` | `kill` | `profile <name>` | `profile restore` | `status` | `noop` | `restart [full]` | `update kit=<id> [noop_s= healthy_s= stable_s=]`.
  `launch` takes `route=exe|steam wait_log=<text> wait_s=<n>`.
- A script: `cmd` by default, or `ps1` with `#ps1` as the first line. Optional header `#job owner=<you> timeout=<s> type=cmd|ps1`.
- Result `<id>.done` (JSON, written last): `status` ok|failed|refused|timeout|lost, `exit` (refused = -2, timeout = -1), `reason`, `start_utc`, `end_utc`; output in `<id>.out`.
- `launch`, `kill`, `profile` need `owner=` equal to the owner in `game.lock`. A script that starts or kills the game or writes a config file needs `#job owner=` too.
  Read-only scripts never need a lock.

## Game lock
`game.lock` is one line: `owner= session= purpose= started=<UTC> [hang_s=<n>]`. Its mtime is the refresh time; 20 minutes without a refresh and it
expires (moved to `_to_delete`). Release = move it away. A fresh lock from the Empire watcher, or the other title running, blocks a launch. The
watchdog is armed only while a valid lock exists and the watcher launched the game.
`harness/core/job.sh` does all of it from the device VM: `job.sh lock <owner> <session> <purpose> [hang_s]`, `job.sh <owner> <file|-> [timeout_s]`
(blocks inside one call until the result; exit code = the job's, refused 2, no answer 124), `touch`, `unlock <owner>`, `status`, `root`.
The mount comes from the adapter (`device_mount` under `$DEVICE_MOUNTS`, default `$HOME/mnt`).

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
Overlay `style: none` allows full copies only (prefs/keys formats are unread, see open questions).

## Update and rollback
`update kit=<id>` runs `update.ps1` detached: back up, replace sha-checked, restart, require a new pid, the expected version and a fresh heartbeat, then a
`noop` job answered by the new watcher, then a stable window. Any failure restores the backup byte for byte (dead-man switch). `watch.cmd` is never replaced.

## Settings (`watcher.ini`, key=value; not in the `config_keys` registry, whose rows feed the generated tables)
`hang_s`=120, `hang_startup_s`=180, `hung_window_s`=60, `cpu_epsilon_s`, `dump_wait_s`=90, `dump_type`, `watchdog`=1, `zombie_wait_s`=15, `job_timeout_s`=1800,
`prune_hours`=24, `lock_stale_min`=20, `job_script_guard`=refuse|warn, `launch_confirm_s`=20, `loop_ms`=1000; tests only: `test_hooks`, `test_fake_zombie`.

## Display probe
`vdisplay_probe.ps1` only validates (`CDS_TEST`): it lists displays and modes and, if the wanted mode is missing, prints the exact `vdd_settings.xml` edit.
Exit 3 and "NO UNIQUE VIRTUAL DISPLAY" when there is none (the CI runner).

## Tests
`harness/tests/Run-HostTests.ps1 -Suite unit|integration|all`; CI job `harness-windows` runs all under Windows PowerShell 5.1 with compiled fake games.
A flaky integration case: `-Only <case regex> -Repeat <n>` (fails on the first failed run, prints the pass count), or on the runner
`gh workflow run gates.yml --ref <branch> -f only='hang watchdog' -f repeat=10` (only `harness-windows` runs). Integration cases
assert on watcher output only after the watcher's own completion line (`Wait-LogMatch ... -Since (Log-Mark)`), never just after a
process exits or a file appears.

## Open questions
See `jobs/J2/report.md` (open questions). Prefs file format: fact `napoleon.config.preferences_format` (UTF-16LE, `key value;` lines); no overlay style for it yet.
