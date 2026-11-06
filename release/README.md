# Release packaging, install and support (J38)

Builds the folder a player downloads (`Napoleon Remastered <version>\` and its zip), installs it with no repo, Python or Git, and gives support a
redacted bundle. It builds files only: publishing (GitHub, Nexus, ModDB) is Liam's call.

| Where | What |
|---|---|
| `release/core/` | game-agnostic (a core candidate, rule 76): `build_release.py` (builder and `--check`), `gen_licenses.py`, `core/installer/rr.ps1` (install, uninstall, repair, check, support) |
| `release/napoleon/` | this game's data: `VERSION`, `release.json` (names, player-ini and release-value rules, known limits), `components.json` (one row per component), `licenses.json`, `releases.json` (what was handed out) |
| `release/runs/` | dated PC run reports (`<date>_j38pc/`) |

## Build (one command, a clean checkout)
```
python3 core/proxy/tools/build.sh --docker dll        # or the CI artifact of the commit; the DLL must carry this tree's build id
python3 core/wsc.py uiscale build                     # the ui_scale_2x component's packs (J66); skip by removing the row only with Liam's say
python3 release/core/build_release.py                 # -> build/release/Napoleon Remastered <version>[.zip]
python3 release/core/build_release.py --check "build/release/Napoleon Remastered 0.1.0"
```
It refuses a dirty tree (tracked changes, uncommitted `release/` files), a DLL whose embedded build id is not `core/proxy/tools/build_id.py`'s for this
tree, an unpinned DXVK (`fetch_dxvk.py` pins), a version that is not higher than `releases.json`, a shipped component with no licence entry, a
release value that is not off, an external build output without its `.json` sidecar naming its sha256 (and the build id, when its `components.json` row pins
one in `build_id`), and a rebuild of a version `releases.json` records with another manifest sha256 (bump `VERSION`; `--rebuild-unreleased` overwrites an
entry not marked `published`). `--record` (only when Liam says this build is the one) writes the version, the manifest sha256 (without `created_utc`) and the
build id into `releases.json`; Liam sets `published` by hand; the builder never publishes. `--allow-dirty` makes a throwaway build (never with `--record`);
`--dxvk-dir` / `--external uiscale=DIR` / `--dll` point at other inputs. The notes
(`RELEASE_NOTES.txt`) and `LICENSES.txt` are generated; `README.txt` is generated from `release.json`.

A new feature job adds **one `components.json` row** (files, source, `licences`, optional `ini_set`), the matching `licenses.json` entry (`shipped: true`),
and a clause in the release smoke test. The builder fails on a target two rows own; the installer's Check reports a file at an owned path no component owns.

## Install, uninstall, repair, check, support (the player's side)
The release folder may be unzipped anywhere: `Install.cmd` finds the game upward from its own location first (so a copy inside the game folder works, but
verify-and-reinstall in Steam deletes it: keep a copy elsewhere), then Steam's registry key and `libraryfolders.vdf`, or `-GamePath`. It refuses while the game
runs and on a non-vanilla exe, verifies every staged sha256 before any copy, snapshots the game folder, backs up foreign files at owned paths on every run
(a re-run after a failed install and an upgrade too; a path already backed up is not repeated; a file is ours only when the record or the release lists it
with the sha256 it still has), moves aside a file the installed release shipped and this one does not, copies with temp name and rename, and writes
`%LOCALAPPDATA%\napoleon_remastered\install.json`, whose `owned` is the union of every release installed so far (J81). `Uninstall.cmd` moves everything owned
away and exits 0 only when the folder equals the snapshot; after a game update (exe verdict MISMATCH) a difference outside the owned set and the backups is
listed under "changed by the game update, not by this tool" and does not fail it, while one at an owned or backed-up path always does (the history entry
records `identical=false` and `steam_update_diffs`). Install, repair and uninstall end with the size of `_to_delete`; `Clean.cmd` lists its stamp folders,
asks `Delete these? [y/N]` (`-Yes` skips it) and deletes only inside `_to_delete`, never `backup\`, `snapshots\`, `history\` or `install.json`. `Repair.cmd` re-copies missing or changed files (it keeps a settings file the player edited) and, after a game
update, says "game updated, remaster is inactive until a build for this exe exists" and changes nothing (exit 3). `Check.cmd` hashes every owned file and
lists missing, changed and foreign files. `Support.cmd` writes a zip (logs, ini, install record, Check output, versions, GPU names; user name, machine name,
profile path and Steam ids redacted; saves never; dumps only with `-IncludeDumps`, listed either way). `tools\Enable crash dumps.cmd` is an optional step that
asks for administrator rights.

Parity with `core/proxy/tools/pc_deploy.py` is the contract: `tests/test_release_installer.py` installs and uninstalls a synthetic game folder with both and compares
the snapshots. Details of the proxy side: `proxy/README.md` "PC install and uninstall", "DXVK", "Crash".

## Release gates (J74)
- **Component keys are gated.** A component's `ini_set` goes through the same release-value gate as the registry (`value_problems(..., ini_set=)`) before anything is built, and the rendered player ini is checked again (`shipped_ini_problems`). A dev, proof or test
key may be on only if `release.json` `release_values.allowed_dev_keys` names it with a reason that cites a decision (`D<n>`); a stale or unknown entry fails. Today: `dev.file_rules` (D46).
- **The DLL must be the proven one.** Its build id must appear as a whole token (not `<id>-dirty`, not inside a longer hex run), no `-dirty` literal may sit beside it, and `harness/acceptance/ledger.jsonl` (`release.json` `acceptance`)
must end in 20 consecutive passes on that id, each with an evidence file in the tree. `--allow-dirty` skips only the pass count.
- **Crash-dump tools work outside the repo.** `tools\Enable crash dumps.cmd` and `Disable crash dumps.cmd` are generated from `identity.json` (`crash_dump_cmd`) with `-ExeName` and `-DumpFolder` (unexpanded `%LOCALAPPDATA%`); `--check` fails a `tools\*.cmd` that names `wer_localdumps.ps1` without them.
- **CI runs the installer.** `harness-windows` runs `tests.test_release_installer`, `tests.test_play` and `tests.test_install_packs` (`-v`), and `release/` changes start that job.

## Steam Verify, game updates
Our files are additions, so Verify should leave them (not yet proved on the PC: see the report). A game update changes the exe sha1: the proxy's guard falls back to
pass-through and writes `napoleon_remastered\EXE_MISMATCH.txt`; Check says so and Uninstall removes the mod, restores the backups and lists the files the
update changed apart (exit 0).

## PC acceptance sitting (Liam present; every launch through the watcher)
1. `build_release.py`, then `--check`. 2. `pc_deploy.py snapshot` of the real game folder to `<state>\_scratch\J38\`, then `Install.cmd`, then `Check.cmd`.
3. Forced pass-through: `pc_deploy.py set proxy.exe_guard_force_mismatch=1`, launch to the main menu through `job.sh` (lock, run, unlock): notice file, first-difference line, patch count 0 in `proxy.log`;
set it back. 4. Saves: `saves/napoleon/load_save.sh` with a vanilla save and a save made with the mod, installed and after the uninstall; vanilla save sha unchanged.
5. `Support.cmd`, open the zip. 6. Delete one owned file, `Repair.cmd`, then `Uninstall.cmd`: `identical`, `Check` clean. Evidence: `release/runs/<date>_j38pc/`.
