# J81 report: Installer robustness: owned set union, backups, Steam updates, cleanup

Written by the orchestrating session (same session id) from the builder's hand-back; the harness refused the builder's write of this file.

The four audit rows G5 (installer half), G6, G7 and G14 (sidecar, `--record`, `key_text`, discovery text) are fixed in `release/core/installer/rr.ps1` and
`release/core/build_release.py`, and each has a test that failed first. Upgrades keep every owned path. Every install backs up foreign files, including a re-run
after a failed install. An uninstall after a Steam update exits 0 and lists what the update changed. `Clean.cmd` frees `_to_delete` after the player confirms.
The builder refuses an external output without its sidecar and a rebuild of a recorded version with other content. Nothing under `core/` changed, and
`pc_deploy.py` was not touched. The builder's own independent read found five issues it did not fix (Open questions 5); two of them can lose a player's original
file and are reviewer fixes for this branch.

## What was built
Branch `job/J81`, commits: 657252b (installer and its tests), 2a7339f (tools row of `rr.ps1`), af4630d (builder, README, `releases.json` note, builder tests and
tools row), the merge of main, then this report and the row.

- **G5a, owned is the union** (`Union-Owned`, end of `Do-Install`). `rec.owned` becomes the ordinal-sorted union of the old record's `owned` and the manifest's.
  Repair keeps the record as it is. Besides the brief: on an upgrade, a file the old release shipped and the new one does not is moved to `_to_delete` if it still
  has its recorded sha256.
- **G5b, back up on every install.** The backup loop no longer sits inside `if ($null -eq $rec)`. It runs on every install over the union set and skips paths
  already in `backups` (matched on `path`).
  - A path is ours when the installer has already copied files in (`Install-Touched`: `installed_utc` is set or the history holds `install started`) and the file
    is listed in the record or in this release with the sha256 it still has.
  - A settings file (`config`) counts as ours even after the player edited it.
  - A folder is ours when every file in it is ours or matches `runtime_globs`.
  - Before anything was copied, everything at an owned path is foreign, which is the old first-install rule, so parity with `pc_deploy` is unchanged.
  - `install.json` keeps its shape; only the history entry gains optional keys.
- **G7, Steam update then uninstall** (`Diff-Path`, `Ours-Path`).
  - With the exe verdict MISMATCH, each difference outside the owned union and outside the backed-up paths is listed under
    `rr uninstall: changed by the game update, not by this tool (<n>)`. The uninstall exits 0 when only such differences remain.
  - A difference at an owned or backed-up path stays a DIFFERS and exits 1. With a vanilla exe the strict DIFFERS and exit 1 are unchanged.
  - The history entry records `identical=false`, `steam_update_diffs` (the count) and the first 50 `steam_update` lines.
  - On uninstall, the "NOT VANILLA" alarm is replaced by a line saying a game update changed the exe.
- **G6, `_to_delete`.**
  - New `clean` verb (`Do-Clean`) and a generated `Clean.cmd` (a `CMDS` row, so it gets the same ASCII and CRLF rules and the same `--check` rule as `Support.cmd`).
  - `Do-Clean` refuses while the game runs and lists each stamp folder with its size. It asks `Delete these? [y/N]`; `-Yes` skips the prompt, and `-NoPause`
    without `-Yes` deletes nothing.
  - It deletes only children of `<state>\_to_delete` after a prefix check, and needs no game folder.
  - Install, repair and uninstall end with `rr: _to_delete holds <size> in <n> folders: run Clean.cmd to free it`.
- **G14a, the sidecar** (`external_problem`). An external output is refused when its sidecar is missing, does not parse, names no sha256 or names another sha256.
  When the file row pins a `build_id`, the sidecar must name that build id.
- **G14b, `--record`** (`content_sha256`, `record_problems`, `record_release`, `is_published`).
  - After a clean build, `--record` writes version, `recorded_utc`, `manifest_sha256` (the manifest without `created_utc`), `build_id`, `commit`, `jobs_done` and
    `published: false`.
  - Every build checks the record, with or without `--record`. A recorded version with other content is refused: "bump `VERSION` or pass `--rebuild-unreleased`".
  - `--rebuild-unreleased` overwrites only an entry not yet published. A published entry, or a hand entry without a sha, is final.
  - `--record` is refused together with `--allow-dirty`.
- **G14c**: `key_text()` is deleted.
- **G14d, one discovery story.** The upward search in `Find-Game` stays. Its comment, README.txt ("Unzip this folder anywhere. If it sits inside the game folder,
  the installer still finds the game, but verify-and-reinstall in Steam deletes it, so keep a copy elsewhere.") and `release/README.md` now say the same thing.
- Docs: the README.txt UNINSTALL paragraph, the `Uninstall.cmd` blurb, `release/README.md` and the `releases.json` `_note` now match the code. The tools rows
  `release.core.installer.rr` and `release.core.build_release` were updated.

## Evidence
- **Red first, installer.** The new tests were run against `origin/main`'s `rr.ps1` on Windows PowerShell 5.1, on temp folders:
  - `test_upgrade_keeps_the_old_release_owned_set` FAIL: `'data/a_only.pack' not found in ['d3d9.dll', 'data/ui_scale_x.pack', 'napoleon_remastered.ini', 'napoleon_remastered/']`
  - `test_rerun_after_a_failed_install_backs_up_foreign_files` FAIL: `'backed up the existing data/ui_scale_x.pack' not found`
  - `test_uninstall_after_a_steam_update_exits_0` FAIL: `1 != 0 ... DIFFERS: changed Napoleon.exe, changed data/vanilla.pack`
  - `test_clean_removes_only_to_delete_after_confirmation` FAIL: `Cannot validate argument on parameter 'Verb'`
  - `test_uninstall_prints_the_to_delete_size` FAIL: the size line was not found
  - `test_uninstall_reports_a_difference` ok on both: it asserts exit 1 on a changed pack with a vanilla exe.
- **Red first, builder:** 6 failures and 4 errors of 50 tests. No `record_*` functions; `SystemExit not raised` for a missing sidecar, another sha256 and a pin;
  `KeyError 'Clean.cmd'`; `key_text` present; README.txt contains `EXCEPT`.
- **Green:** `tests.test_release_installer`: 20 OK, including parity, 8.3 paths and `test_finds_the_game_from_the_scripts_own_location`. `tests.test_release`:
  50 OK. `wsc gates`: 13 ok, 1 warn (30 skipped tests), 0 failed. `gates --fast`: 13 ok.
- **CI:** `gates` run 41889244924 (commit af4630d) includes the `harness-windows` job. It was still running at hand-back, so the reviewer reads its result.
- **`key_text` was unused:** before the deletion, `grep -rn key_text --include=*.py .` outside `core/` found only `release/core/build_release.py:94:def key_text(v):`,
  the definition and no caller.
- **`pc_deploy.py` lines still carrying G5, for W25** (pin v0.10.0): 583-600, the backup loop sits inside `if rec is None:` (593-600); 617,
  `rec.update({... 'owned': man['owned'] ...})` overwrites `owned` on an upgrade.
- **Clean transcript** (synthetic game and state in a temp folder):

```
$ rr.ps1 install -> exit 0
rr install: backed up the existing d3d9.dll to <tmp>\state\backup\20261104T183926Z\d3d9.dll
rr: _to_delete holds 5 bytes in 1 folders: run Clean.cmd to free it
$ rr.ps1 repair -> exit 0
rr repair: restored napoleon_remastered/dxvk/d3d9_dxvk.dll
rr: _to_delete holds 12 bytes in 2 folders: run Clean.cmd to free it
$ rr.ps1 clean (typed: n) -> exit 0
rr clean:    5 bytes  20261104T183926Z
rr clean:    7 bytes  repair_20261104T183927Z
rr clean: 12 bytes in 2 folders under <tmp>\state\_to_delete (...; your backups, snapshots, history and install record are elsewhere and are kept)
Delete these? [y/N] n
rr clean: nothing deleted
$ rr.ps1 clean (typed: y) -> exit 0
rr clean: deleted 20261104T183926Z
rr clean: deleted repair_20261104T183927Z
rr clean: freed 12 bytes
$ rr.ps1 uninstall -> exit 0
rr uninstall: restored the original d3d9.dll
rr uninstall: game folder identical to the pre-install snapshot (5 files)
rr: _to_delete holds 5.8 KB in 1 folders: run Clean.cmd to free it
```

## Deviations
- **Stale files of the previous release are moved aside on an upgrade.** Not asked for. Without it, a renamed pack stays loaded next to the new one. The upgrade
  test asserts the move.
- **No `release/core/installer/Clean.cmd` source file.** It is generated from a `CMDS` row like `Support.cmd`, which is what the brief's "generated like the other
  .cmd files" asks for.
- **The sidecar build-id check applies only where a row pins `build_id`.** No producer writes one today, and `components.json` is outside the brief's files.
- **The ownership rule uses `Install-Touched`.** Before any copy, everything at an owned path is foreign, which keeps parity with `pc_deploy`.
- **The report was written by the orchestrating session** from the builder's hand-back text, unchanged in substance.

## Open questions
1. (Liam decides; default built: no) Should `Clean.cmd` offer to remove `_to_delete` by itself at the end of a successful uninstall?
2. (Liam decides; default built: any path outside owned and backups) Should a steam-update difference also require the path to exist in the pre-install snapshot?
3. Should a separate command set `published` instead of the hand edit and the `--rebuild-unreleased` flag? A follow-up row if wanted.
4. Should the uiscale build write a `build_id` into its sidecars, and the `components.json` rows pin it?
5. The builder's independent read found these, all unfixed:
   1. A leftover `.tmp` or other unlisted file in the mod folder makes a re-run back up our own folder as foreign, so uninstall reports DIFFERS; single owned files
      ignore `runtime_globs`.
   2. A recorded backup whose move never finished is skipped, so the original can end up in `_to_delete` and Clean deletes it. The fix is to skip only when the
      source is gone.
   3. Clean may follow junctions inside `_to_delete` on PowerShell 5.1 and delete outside it.
   4. `content_sha256` includes `commit`, so once the `--record` commit lands, any rebuild needs `--rebuild-unreleased`.
   5. Files the player added are counted as the update's.

   5.1 and 5.2 are reviewer fixes for this branch; 5.3 can delete outside `_to_delete` and should be fixed here too; 5.4 and 5.5 may need a decision.

## Fix round 1
Commit 0409780 (one commit for the three installer fixes, each with its own test in `tests/test_release_installer.py`).

- **5.1 Re-run backs up our own mod folder as foreign (fixed).** `Is-Ours` now treats a `runtime_globs` match as ours for a single file as well as inside a folder,
  and a file inside our own mod folder that no manifest lists (a leftover `.tmp`) no longer makes the whole folder foreign (a listed file with a different sha still does).
  Test: `test_rerun_keeps_our_mod_folder_with_a_stray_tmp_and_runtime_files`; fails on the old code, passes now.
- **5.2 Unfinished backup lets Clean delete the original (fixed).** A recorded backup is skipped only when the backup file exists; when it is missing and the source is
  still at the game path, the install finishes the move to the recorded backup path. Test: `test_unfinished_backup_is_finished_not_deleted` (clean afterwards, uninstall
  restores the original); fails on the old code, passes now.
- **5.3 Clean may follow junctions (fixed, defensively).** `Do-Clean` now removes any reparse point as a link without descending (`Remove-Links`), and deletes a stamp
  folder that is itself a junction as a link. Test: `test_clean_does_not_follow_a_junction_out_of_to_delete` (temp folders only, sentinel file outside). It passes on the
  old code too on this machine (Windows 11, PowerShell 5.1), so it guards the behaviour but does not reproduce the reviewer's failure here; the fix is kept for older builds.
- **5.4, 5.5, open questions 1-4:** left as the reviewer set them (decisions for Liam, defaults built); nothing changed.

Checks: `tests.test_release_installer` + `tests.test_release` 73 OK locally.
