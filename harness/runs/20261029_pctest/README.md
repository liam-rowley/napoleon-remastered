# J2 PC test, 2026-10-28/29 (UTC), officepc

The watcher was installed by Liam (sitting 1, 2026-10-28T23:07Z, kit `harness_20261028T230555Z_8421be73be1c`; `install_result.json`).
Everything else ran through the watcher with Liam away, on the **live root** `C:\napoleon_remastered_pc\watcher` (deviation: no
side-by-side root, see `jobs/J2/report.md`). Agent helper: `job.sh` from the kit, owner `j2agent`. The watcher under test: kit
`harness_20261029T001255Z_917e22ec7ece` (commit 917e22e, CI run 40791989477 green), then `harness_20261029T002304Z_f57f8e955799`
(f57f8e9, the probe fix). Files here: `watcher.log` (the live log after the run), `watcher.status.json`, the hang note, both update logs.

| test | result | job ids / evidence |
|---|---|---|
| a) `noop`, `status` | pass | `j2agent-20261028T230807Z-480526327`, `j2agent-20261028T230809Z-3274810486` (status JSON, UTC times, no lock) |
| b) refusals | pass: no lock (exit 2), wrong owner (exit 2), a script that starts `Napoleon.exe` without an owner (refused with the line quoted), second launch while running (exit 2) | `j2agent-20261028T230810Z-1631331592`, `someoneelse-20261029T001424Z-1401815609`, `j2agent-ownerless-1793232865`, `j2agent-20261029T001506Z-257279667` |
| b) zombie | pass with a **faked** flag on the live root (`watcher.zombie.json` pointing at the launcher's pid 26440 as a live stand-in): survives `restart`, status `zombie`/`needs_reboot`, launch `failed` exit 1 "PC NEEDS REBOOT"; flag moved to `_to_delete\`, `restart`, cleared. The real survive-the-kill path is covered by CI only | `j2agent-20261029T002158Z-1566623985` |
| c) launch, kill, relaunch | pass, route `exe` (`Napoleon.exe` started directly, Steam client running): pid 16728 confirmed, still running 20 s later with a visible window and CPU progress; kill clean (taskkill /F /T); relaunch pid 28236; kill clean; no zombie | `j2agent-20261029T001435Z-847429292`, `...001508Z-631314717`, `...001509Z-1691928289`, `...001525Z-18087262` |
| d) profile `proxy-dxvk`, launch, restore | pass: J1 proxy kit `kit_20261028T212023Z_30a7b815163a` installed for the test (sha-checked); profile snapshot `profiles\_saved\20261029T002016Z_j2agent` (3 of 4 files, `dxvk.conf` absent recorded); game ran on DXVK through the proxy (`Direct3DCreate9(sdk=32) -> [dxvk]` in `proxy.log`); restore: all four files byte-identical to the baseline, `dxvk.conf` absent again | `j2agent-20261029T002015Z-95139222`, `...002104Z-1827923761`, `...002106Z-37378128` |
| e) lock expiry with a profile active | pass: lock backdated 25 min; at 00:21:19Z `LOCK EXPIRED` (moved to `_to_delete\game.lock.expired_j2agent_20261029T002119Z`) and `AUTO-RESTORE under owner=j2agent` in the log; files at baseline | `j2agent-20261029T002116Z-874528156` |
| f) forced hang | pass: lock `hang_s=30`, launch pid 24052, start-up grace (180 s) waited out, `procfreeze.ps1 -Mode suspend` (NTSTATUS 0); caught at 00:19:22Z "no CPU-time progress for 31 s ... window=not_responding"; out-of-process minidump 25,561,966 bytes, configs, lock and status archived in `runs\20261029T001922Z_hang\` (on the PC; the dump stays there), killed | freeze `j2agent-20261029T001850Z-231239251`; `hang_20261029T001922Z.txt` |
| g) display probe | pass after a fix: first run (`j2agent-20261029T002222Z-2389130896`) tested nothing yet passed (the `-Test` array bug, fixed in 7c2509b); after the update: 1920x1080 and 2560x1440 `DISP_CHANGE_BADMODE` (exit 6, `vdd_settings.xml` edit printed), 3840x2160 accepted, empty `-Test` exit 2; DISPLAY10 unchanged at 3840x2160@60 every time; primary DISPLAY2 never targeted | `j2agent-20261029T002415Z-2169717563`, `...002417Z-475428279`, `...002419Z-651529014` |
| h) update and rollback | pass: two good updates CONFIRMED (noop answered within 60 s, heartbeat stable 30 s); a kit with a deliberate syntax error in `watcher.ps1` (`harness_20261029T002600Z_j2badwatcher2`, built on the PC from the good kit with a correct manifest) was installed, not healthy within 90 s, REVERTED byte-exact (sha256 verified), old watcher healthy (pid 18388) | `update_20261029T001331Z_confirmed.log`, `update_20261029T002527Z_reverted.log` |

After the run: proxy uninstalled with `pc_deploy.py uninstall` (game folder identical to the pre-install and vanilla snapshots, 1564
files), no lock, no profile active, no zombie, watcher 1.0.0 on f57f8e9's files running (status 2026-10-29T06:46Z).

Baselines (sha256, 2026-10-29, vanilla game folder): `preferences.script.txt` c2202172bdcb8051156add790bb61b424f1df429e3a2706e7861621c27181cca
(20,736 bytes, UTF-16LE with BOM), `custom_keys.keys.xml` adc99cc410b653e4a58179deed6baee522a5d67a8a3723c86d55d84c24ea019c,
`Napoleon.exe` 44880ec1770f600163a336eec83b4366901484c5cceec83dc326e2932f02a054; with the J1 proxy kit installed,
`napoleon_remastered.ini` 94b59cb3bab449a205490f6fe0eaa2ae391d3ee07fc47dcb0f8ab285095f22d0; `dxvk.conf` absent.
