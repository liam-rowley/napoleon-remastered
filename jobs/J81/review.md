## Round 2 (2026-11-04, branch job/J81 at 5db543c)
**Verdict: merge.**

All three round-1 findings are answered in `## Fix round 1` and commit 0409780. I fixed one regression that fix introduced (commit 6ae19d0, below).

Checked: `wsc gates` 12 ok, 2 warn, 0 failed; `tests.test_release_installer` + `tests.test_release` 74 OK with the fix below; CI on 5db543c green
(`gates`, `harness-windows` pass; `proxy`, `viewer`, `policy` skipped as the inputs rule says). No `core/` change; rule 79 does not apply (no `proxy/` or `harness/` change).
Round-1 tests checked against the pre-fix `rr.ps1` (77a9ce5): the 5.1 test fails and the 5.2 test errors on it, and both pass now. The 5.3 junction test passes on
the old code too on this PC (Windows 11, PowerShell 5.1), which the report says openly. The `Remove-Links` change is right as defence for older builds: it never
descends into a reparse point and deletes a junction stamp folder as a link.

Risk-first reading: the `Do-Install` backup loop, `Is-Ours`/`Listed-File` and `Do-Clean` in `release/core/installer/rr.ps1`, because they move and delete players' files.

## Fixed in this review (should-fix)
1. **The 5.2 "finish the move" could back up our own file as the original** (`release/core/installer/rr.ps1:335`, commit 6ae19d0). The setup: a completed install,
   then the player deletes `backup\`, then a re-run. The recorded backup is missing and the source is present, so the loop moved our installed `d3d9.dll` into the
   backup path. The uninstall then "restored" the mod's DLL and exited 1 (`game folder DIFFERS`), which I reproduced with a probe. Now, when the installer has already
   touched the game and the file is ours, the re-run warns and skips. Test `test_missing_backup_after_a_completed_install_never_takes_our_file` fails on 5db543c and
   passes now. The unfinished-backup case in 5.2 still moves the file, because no install has touched the game yet.

## Later
- With 5.1, a file the player drops into our own mod folder counts as ours, so the uninstall moves it to `_to_delete` with the folder. That is acceptable
  because the folder is ours, but say so in the player-facing readme if it ever comes up.
- 5.4 and 5.5 stay decisions for Liam, as round 1 left them.

## Round 1 (2026-11-04, branch job/J81 at 77a9ce5)
**Verdict: merge after fixes.**

Three defects in the installer can lose a player's file or delete outside `_to_delete`; the rest of the branch checks out.

Checked: `tests.test_release_installer` + `tests.test_release` 70 OK locally; CI on 77a9ce5 green (2 checks passed or skipped); no `core/` change; the
report's claims match the diff (`Union-Owned`, backup loop outside `if ($null -eq $rec)`, `Do-Clean`, `Clean.cmd`, sidecar, `--record`, `key_text` gone).
`wsc policy` refuses only because this review and `status=done` are missing, as expected for a fix verdict. Rule 79 does not apply (no `proxy/` or `harness/` change).

## Must fix (Open questions 5.1 to 5.3 are real; confirmed in `release/core/installer/rr.ps1`)
1. **Re-run backs up our own mod folder as foreign (5.1).** `Is-Ours` on a folder rejects it if any file is neither listed nor matches `runtime_globs`
   (a leftover `.tmp`); for a single owned file it ignores `runtime_globs` altogether. Treat runtime-glob matches as ours in both paths, and treat an
   unlisted file inside our own mod folder as ours-or-ignored rather than making the whole folder foreign. Add a test with a stray `.tmp` in the mod folder.
2. **Unfinished backup lets Clean delete the original (5.2).** The record entry is written (`Write-Json`) before `Move-Out`; the `$done` skip then trusts any
   recorded path. If the move never finished, the original is still at the game path, is skipped, gets overwritten or moved to `_to_delete`, and Clean deletes
   it. Skip only when the recorded backup exists and the source is gone; otherwise redo the move (or record after the move). Test: record a backup entry
   without the backup file, source still present, re-run, assert the original is in `backup\` and not lost.
3. **Clean may follow junctions out of `_to_delete` (5.3).** `Remove-Item -Recurse -Force` on PowerShell 5.1 descends into junctions and symlinks.
   Before deleting, walk the tree and remove reparse points (`Attributes -band ReparsePoint`) as links (`[IO.Directory]::Delete($p)` / `cmd /c rmdir`) without
   recursing, or refuse the folder. Also check the stamp folder itself. Test with a junction to a temp folder holding a sentinel file (temp folders only).

## Decisions for Liam (not blocking this round)
- 5.4 `content_sha256` includes `commit`, so the first rebuild after the `--record` commit needs `--rebuild-unreleased`. Recommend excluding `commit` from the hash.
- 5.5 player-added files counted as the update's in the Steam-update list: harmless for exit code, but the wording says "changed by the game update". Accept or word it "not by this tool".
- Open questions 1 to 4 in the report: defaults built are fine.

Round 2 checks: the three tests above fail on the old code and pass on the fix; the 70 tests stay green; `wsc policy` after the row is set.
