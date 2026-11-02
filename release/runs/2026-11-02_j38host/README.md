# J38 host run, 2026-11-02 (run id 2026-11-02_j38host)

No game was launched and the game folder was not written. Everything below ran on Liam's PC on the branch's commit; the sitting with Liam present
(install on the real game folder, forced pass-through launch, saves, Steam Verify) is still to do (`release/README.md` "PC acceptance sitting").

## Build
`python3 release/core/build_release.py --dll <the PC's build/proxy/napoleon/d3d9.dll> --dxvk-dir <build/dxvk>` from a clean tree (commit 4166e0571464):
- folder `build/release/Napoleon Remastered 0.1.0`, 8 payload files + 13 others, DLL build id 715e9dfc0727 (the id of this tree's DLL inputs, carried in the DLL), core v0.9.0;
- DXVK 3.1.1 from the pinned build/dxvk (sha256 checked against the `fetch_dxvk.py` PIN by the builder);
- `ui_scale_2x` component from `C:\napoleon_remastered_pc\uiscale\work` (J66 build outputs, sha256 checked against their `.json`);
- zip `Napoleon Remastered 0.1.0.zip` 1.7 GB, sha256 2FEEFB4DAA66C85CA528513C9B0F082A1DA619CD03CA9B924BEDCC486D8791B1; `zipfile.testzip()` returns None;
- `build_release.py --check` on the folder: ok; the builder runs the same check on what it just built.
- Warnings printed: `statement` and `own_code_licence` are pending in `licenses.json` (Liam's open question 2).

## Read-only Check against the real game folder
`rr.ps1 check -StateDir C:\napoleon_remastered_pc\_scratch\j38\state` (`check` creates nothing):
- found the game by itself through Steam: `C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War`;
- `exe: ok Napoleon.exe sha1 9aebcd2172f2878d781b079f7feb45b0e12e0250 is the vanilla build this release knows`;
- `not installed by this tool`; `napoleon_remastered.ini is present but not from this installer`: an old settings file is already in the real game folder, so Install will back it up and Uninstall put it back.

## Host tests
`python -m unittest tests.test_release tests.test_release_installer` (22 + 13 tests): installer vs `pc_deploy.py` on a synthetic game folder
(same installed tree, same record, uninstall identical to the pre-install snapshot, a foreign `d3d9.dll` backed up and restored, the UI cache moved aside),
refusals (non-vanilla exe, damaged release, game running), Check/Repair (missing, changed, foreign, edited settings kept), game update (exit 3, nothing changed),
support bundle redaction (user, machine, profile path, Steam id, SID: none left; no dump without `-IncludeDumps`; no save).

## Scratch pin DLL (PC test step c, second half)
Not built: `build.sh --docker dll --adapter <scratch>` validates the adapter's identity against the `engine_sites` rows, which are pinned to the real exe sha1, and refuses
a scratch adapter with another pin (the log names every site). A scratch pin therefore needs the registry changed too. Only the forced mismatch path
(`proxy.exe_guard_force_mismatch=1`) can be run on the real exe; the core's proxy host tests cover the rest.
