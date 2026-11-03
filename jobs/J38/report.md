# J38 report: Release packaging, install and support

Built: a release builder, a PowerShell player installer, a support bundle and the licence data, so a later feature job adds one
`components.json` row instead of new packaging work (details in `release/README.md`). Host-proven on 2026-11-02, including a
full-size install and byte-exact uninstall rehearsal; the brief's Liam-present PC sitting (steps b to f) is not done, and Liam chose
to send the job to review with it open. Branch `job/J38`.

## What was built
- **Builder (`release/core/build_release.py`):** builds `Napoleon Remastered 0.1.0\` and its zip from a clean commit: payload per
  component, `manifest.json` (every file's target, size and sha256, plus core tag and DLL build id), installer scripts, five `.cmd`
  entry points, and generated `README.txt`, `LICENSES.txt`, `RELEASE_NOTES.txt`. `--check` verifies a built folder. It refuses a
  dirty tree (tracked changes or uncommitted `release/` files), a DLL not carrying this tree's `build_id.py` id, an unpinned DXVK, a
  version not higher than `releases.json`, a target two components own, a shipped licence with no entry, or a release value that is
  not off. "CI-built DLL" is read as "carries this tree's DLL-input content id" (D31: a local Docker build is byte-identical to
  CI's); there is no byte comparison with a CI artifact.
- **Installer (`release/core/installer/rr.ps1`):** Windows PowerShell 5.1, ASCII only, no Python, Git or repo. It finds the game from
  its own location, the Steam registry key plus `libraryfolders.vdf`, or `-GamePath`.
  - Install, uninstall, repair, check and support all refuse while the game runs; install, uninstall and repair also refuse on a
    non-vanilla exe.
  - Install checks every staged sha256 before any copy, snapshots first, backs up foreign files at owned paths, and copies with temp
    name and rename. Uninstall moves things (nothing is deleted) and exits 0 only when the folder equals the snapshot.
  - Repair re-copies missing or changed files and keeps a settings file the player edited; after a game update it says "game
    updated, remaster is inactive until a build for this exe exists", changes nothing and exits 3. Check lists missing, changed and
    foreign files.
  - State lives in `%LOCALAPPDATA%\napoleon_remastered\`, outside the game folder (D25). Install and uninstall also move the game's
    UI cache files aside. `Enable crash dumps.cmd` is an optional step offered after install.
- **Support bundle:** logs, the ini, `EXE_MISMATCH.txt`, the install record, the Check output, versions, GPU names and a dump
  listing; user name, machine name, profile path, Steam ids and SID redacted; dumps only with `-IncludeDumps`, saves never.
- **Licences:** `LICENSES.txt` is generated from `release/napoleon/licenses.json`, says it is not legal advice, and a gate checks
  shipped components against entries.
  - Shipped: DXVK 3.1.1 (text sha256 equals the `fetch_dxvk.py` pin), Lora (OFL, from `uiscale/fonts/OFL.txt`), the two upscaling
    models (CC BY 4.0 credit lines).
  - Not yet shipped: RmlUi, FreeType (with its required credit line), Lua, the UI fonts (pending J37).
  - Read 2026-11-02, not re-checked by J36's review: both Phhofm release pages say "License: CC BY 4.0", author Philip Hofmann;
    RmlUi 6.3 is MIT with the same copyright lines as Empire's draft; the FreeType licence is dated 2006-Jan-27; lua.org says MIT for
    Lua 5.0 and later.
- **Components today:** `proxy` and `ui_scale_2x`. `ui_scale_2x` is included because D42(4) says J38 packages the stop-gap for
  0.1.0, although the brief lists UI packs as deferred. It ships `ui_scale_2x.pack` (1.8 GB), the fonts pack, the scaled templates
  file and a rules file from the J66 build in `C:\napoleon_remastered_pc\uiscale\work`, sha256-checked against their `.json` files,
  and sets the file rule through `dev.file_rules` in the player ini. J53's `install_packs.ps1` and `play.py` are not duplicated.
- **Release values:** the gate in `tests/test_release.py`: dev, proof and test keys off, `proxy.exe_guard` 1,
  `proxy.exe_guard_force_mismatch` 0, `proxy.minidump` 2, and the shipped dev-side ini equals the generated one. J1 open question 1
  is closed: the compiled default in `tables.h` and the ini both say 2. The player ini omits the dev, headless, proof and exe-guard
  keys, and the gate proves every omitted key's DLL default equals its release value (D46).
- **Other changes:** `'release/core': None` in `PROMOTIONS` in `tools/jobs_hooks.py` (no promotion job yet); three tools rows; D45
  and D46 in `docs/DECISIONS.md`; a `README.md` row and `release/README.md`; two `engine_facts` rows
  (`napoleon.release.steam_detect`, `napoleon.release.stray_ini`).

## How to build, install, uninstall, get support
```
core/proxy/tools/build.sh --docker dll     # or the CI artifact of the commit
python3 core/wsc.py uiscale build          # only if the J66 work folder is gone
python3 release/core/build_release.py      # -> build/release/Napoleon Remastered 0.1.0 and .zip
python3 release/core/build_release.py --check "build/release/Napoleon Remastered 0.1.0"
```
The player runs `Install.cmd`, `Uninstall.cmd`, `Repair.cmd`, `Check.cmd` and `Support.cmd` from the release folder.

## Evidence
Run id `2026-11-02_j38host`, all dated 2026-11-02; report in `release/runs/2026-11-02_j38host/README.md`.
- **Build from a clean tree (commit 4166e0571464):** 8 payload files plus 13 others, DLL build id 715e9dfc0727, core v0.9.0; zip
  1.7 GB, sha256 2FEEFB4DAA66C85CA528513C9B0F082A1DA619CD03CA9B924BEDCC486D8791B1, `testzip()` clean; `--check` ok.
- **Host tests:** `tests/test_release.py` (22) and `tests/test_release_installer.py` (13) pass. The installer against `pc_deploy.py`
  on a synthetic game folder gives the same installed tree and install record and a byte-identical uninstall for both; a foreign
  `d3d9.dll` is backed up and restored. Refusals tested: non-vanilla exe, damaged release folder, game running (a fake process).
  Also covered: check and repair, game update, the UI cache move. The redaction test plants a user name, machine name, profile path,
  Steam id and SID and finds none in the bundle, nor the real user or machine name.
- **Full-size rehearsal:** the real 1.8 GB release into a synthetic game folder with a fake exe and a stray ini: install 6 s, Check
  clean, Uninstall "identical to the pre-install snapshot" with an empty `pc_deploy.diff_snapshots`.
- **Real game folder, read-only:** `Check.cmd` found the game through Steam with no argument and reported the exe vanilla (sha1
  9aebcd21...); it wrote nothing. The folder already holds a `napoleon_remastered.ini` no install owns: Install backs it up and
  Uninstall restores it, but the pre-install snapshot already contains it. The game lock was never taken.
- **Gates (2026-11-02, final branch):** `jobs check` 68 rows, ok; `gates --fast` 12 ok, 1 warn (worktree hook path), 0 failed; the
  full `gates` earlier on the branch 12 ok, 2 warn, 0 failed (later commits only added run-evidence text).
  With the report and the row set (2026-11-02): full `python3 core/wsc.py gates` 12 ok, 2 warn (worktree hook path; skipped tests), 0 failed; `python3 core/wsc.py policy --branch job/J38 --base origin/main` refuses only on the reviewer's part (no `review.md`, row not `done`).

## Deviations
1. **The PC sitting (steps b to f) is not done.** The brief wants one sitting with Liam present, asked before starting. Step (a)
   (read-only Check) is done. Asked on 2026-11-02, Liam chose "Review it as is": the job goes to review with the sitting open. The
   steps are written in `release/README.md` "PC acceptance sitting": `Install.cmd` on the real folder then Check; the forced
   pass-through launch through the watcher (`proxy.exe_guard_force_mismatch=1`: notice file, first-difference line, patch count 0);
   a vanilla save and a mod-era save load; the real support bundle; `Repair.cmd` after deleting a file, then `Uninstall.cmd` and a
   clean Check.
2. **No scratch DLL with another pinned identity:** `build.sh --docker dll --adapter <scratch>` validates the adapter against
   `engine_sites` rows pinned to the real sha1 (27 rows), so a scratch pin needs the registry changed too; only the forced mismatch
   path can run on the real exe.
3. **Steam Verify is not proved:** tests simulate a deleted file only. Our files are additions, so Verify should leave them; needs a
   real Verify on the PC.
4. **The PowerShell tests skip on Linux CI;** they run in `gates` on the PC. Hooking them into `harness-windows` is a core change
   (generated workflow). `tests/test_release.py` runs everywhere.
5. **`ui_scale_2x` ships the dev key `dev.file_rules`** (D46); a player key needs a DLL job under rule 79.
6. **`dev.file_rules` with the release DLL is unproven:** J66 ran it from a dev-style kit with the dev Lua pack, which the release
   does not carry. The sitting must show the `proxy.log` redirect line for `data\ui\templates\uied.templates`.
7. **Release notes list 45 done jobs** because there is no previous release; later releases list only jobs since the last
   `releases.json` entry.
8. **Report written by the orchestrating chat:** the build ran as a subagent whose harness refuses writing report files; the
   orchestrating chat (same Claude-Session) wrote this from the subagent's text, with Liam's approval (2026-11-02).

## Open questions
1. **Unofficial-mod statement and licence of our own code:** Liam's call; asked 2026-11-02, he chose "Decide later". Both read
   "pending" in `LICENSES.txt`, and the builder warns on every build until they are set.
2. **The PC sitting** (deviation 1): when Liam has time; an agent then runs steps b to f with him present, building from a committed tree.
3. **Name and version:** "Napoleon Remastered" 0.1.0 and the PowerShell installer with parity tests stand (D38).
4. **A player key for the stop-gap's `dev.file_rules`:** a DLL job under rule 79, to queue if wanted.
5. **A Python-free frozen-exe installer route,** and a core promotion job for `release/core` (not queued).
6. **Antivirus:** the `.cmd` files launch `powershell -ExecutionPolicy Bypass`, which some antivirus products flag. Untested.

## Left behind
`C:\napoleon_remastered_pc\_scratch\j38\rehearsal` (about 1.8 GB); in the build worktree `_scratch\j38_pin`, `build\release` (the
built folder and zip) and `build\release_dev_old` (an earlier dev build).
