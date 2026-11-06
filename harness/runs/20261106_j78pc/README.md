# Run 20261106_j78pc: J78's 20 acceptance passes

Rule 79's run for J78, 2026-11-06 18:14 to 20:57 UTC. Build `96722f4b8d52`, watcher 1.5.0, kit `kit_20261106T180846Z_6e96ce56fed1`, branch `job/J78`, core v0.47.0.
Run as `acceptance.py run --passes 20`, headless, same baseline and limits. Result: 20 of 20 `pass`, no `flake` line, no false step. Pass 1's ledger line already names the build.

Layout, read before and after the run: DISPLAY1 3840x2160@240Hz primary at 0,0 (the MSI), DISPLAY10 3840x2160@60Hz virtual at 3839,2160 (1920x1080 while a launch runs), DISPLAY2 2560x1440@144Hz at -2560,327 (the Dell; layout M in J101's terms). Sizes from the display tool, `attempts/pass_14/attempt_1/job_output.txt`.

## Files
- `pass_01.json` to `pass_20.json`: each pass's evidence. Shots stay on the PC under `C:\napoleon_remastered_pc\acceptance\20261106_j78pc`.
- `foreign_windows.log`: the observer (`harness/runs/20261104_j64pc5/foreign_windows.ps1 -X 3839 -Y 2160`), started 17:55:44, stopped 21:00:25 UTC. Only `explorer` on the virtual display.
  Its one `Empire.exe` line, 18:07:29, is `tests/test_release_installer.py` `test_refuses_while_the_game_runs` (a renamed `PING.EXE`) in the gates run before the install, not during a pass.
- `attempts/pass_14/attempt_1`, `attempts/pass_18/attempt_1`: `proxy.log`, `headless_status.json` and the job output of the two launches that died, copied from the PC.

## Start-up deaths: 2 of 122 launches
Counted from `watcher.log`, because the pass files undercount (below). Both c0000374 at ntdll+0xfd71f, last status `starting DllMain`, retried by `ctl.py`, the retry ran.

| Pass | Launch | pid | Dump |
|---|---|---|---|
| 14 | first of the pass | 5296 | `20261106T195943Z-p5296_c0000374.dmp` (5,530,099 bytes) |
| 18 | `naval_small` relaunch | 19876 | `20261106T203606Z-p19876_c0000374.dmp` (5,534,614 bytes) |

- **`pass_14.json` holds no trace of its death:** `acceptance.py` drops the return value of a pass's first launch, so its `retried_after` is lost. Only `attempts/pass_14` and `watcher.log` show it. `evidence.launches` lists survivors only: 120 across the pass files.
- Both logs have one thread and stop 6 ms to 7 ms after `init done`, before the first `Direct3DCreate9`. One healthy launch of this build, the run's last, logs `Direct3DCreate9(` 1.06 s after `init done` (its wndproc guard line is at 0.94 s).
- The dumps were not opened (J101 measures first). In-process dumps: `C:\napoleon_remastered_pc\_to_delete\uninstall_20261106T210043Z\napoleon_remastered\dumps`. WER full dumps, copied before WER evicts them: `C:\napoleon_remastered_pc\_scratch\j78`.
