# Release packaging, install and support (J38)

Builds the folder a player downloads (`Napoleon Remastered <version>\` and its zip), installs it with no repo, Python or Git, and gives support a
redacted bundle. It builds files only: publishing (GitHub, Nexus, ModDB) is Liam's call.

| Where | What |
|---|---|
| `release/core/` | game-agnostic (a core candidate, rule 76): `build_release.py` (builder and `--check`), `gen_licenses.py`, `installer/rr.ps1` (install, uninstall, repair, check, support) |
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
tree, an unpinned DXVK (`fetch_dxvk.py` pins), a version that is not higher than `releases.json`, a shipped component with no licence entry, and a
release value that is not off. `--allow-dirty` makes a throwaway build; `--dxvk-dir` / `--external uiscale=DIR` / `--dll` point at other inputs. The notes
(`RELEASE_NOTES.txt`) and `LICENSES.txt` are generated; `README.txt` is generated from `release.json`.

A new feature job adds **one `components.json` row** (files, source, `licences`, optional `ini_set`), the matching `licenses.json` entry (`shipped: true`),
and a clause in the release smoke test. The builder fails on a target two rows own; the installer's Check reports a file at an owned path no component owns.

## Install, uninstall, repair, check, support (the player's side)
Double-click `Install.cmd` (finds the game from its own location, Steam's registry key and `libraryfolders.vdf`, or `-GamePath`). It refuses while the game
runs and on a non-vanilla exe, verifies every staged sha256 before any copy, snapshots the game folder, backs up foreign files at owned paths, copies with
temp name and rename, and writes `%LOCALAPPDATA%\napoleon_remastered\install.json`. `Uninstall.cmd` moves everything owned away (nothing is deleted) and
exits 0 only when the folder equals the snapshot. `Repair.cmd` re-copies missing or changed files (it keeps a settings file the player edited) and, after a game
update, says "game updated, remaster is inactive until a build for this exe exists" and changes nothing (exit 3). `Check.cmd` hashes every owned file and
lists missing, changed and foreign files. `Support.cmd` writes a zip (logs, ini, install record, Check output, versions, GPU names; user name, machine name,
profile path and Steam ids redacted; saves never; dumps only with `-IncludeDumps`, listed either way). `tools\Enable crash dumps.cmd` is an optional step that
asks for administrator rights.

Parity with `core/proxy/tools/pc_deploy.py` is the contract: `tests/test_release_installer.py` installs and uninstalls a synthetic game folder with both and compares
the snapshots. Details of the proxy side: `proxy/README.md` "PC install and uninstall", "DXVK", "Crash".

## Steam Verify, game updates
Our files are additions, so Verify should leave them (not yet proved on the PC: see the report). A game update changes the exe sha1: the proxy's guard falls back to
pass-through and writes `napoleon_remastered\EXE_MISMATCH.txt`; Check says so and Uninstall returns the game to vanilla.

## PC acceptance sitting (Liam present; every launch through the watcher)
1. `build_release.py`, then `--check`. 2. `pc_deploy.py snapshot` of the real game folder to `<state>\_scratch\J38\`, then `Install.cmd`, then `Check.cmd`.
3. Forced pass-through: `pc_deploy.py set proxy.exe_guard_force_mismatch=1`, launch to the main menu through `job.sh` (lock, run, unlock): notice file, first-difference line, patch count 0 in `proxy.log`;
set it back. 4. Saves: `saves/napoleon/load_save.sh` with a vanilla save and a save made with the mod, installed and after the uninstall; vanilla save sha unchanged.
5. `Support.cmd`, open the zip. 6. Delete one owned file, `Repair.cmd`, then `Uninstall.cmd`: `identical`, `Check` clean. Evidence: `release/runs/<date>_j38pc/`.
