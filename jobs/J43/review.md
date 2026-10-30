# Review of J43 (Battle camera and speed route)

## Round 1 (2026-10-30, branch `job/J43` at 02c6a2e)

Reviewer: session `28e9ec68-dcb4-4540-b3e2-31830bb7ee83` (did not build the branch; builder `d9f7e898-ee56-4f30-afc0-86e559cf1403`).

**Verdict: merge.**

The job does what the brief asked in land, siege and naval: `cam`, `pause` and `speed` return checked results through per-kind
`ctl.routes`, the stall has a cause with a lint, and J44 has measured tolerances, clamps and speeds. The one real problem (finding 1)
is in the watcher's profile restore, not in this branch's code: it left a stray mod ini in the game folder after the job's uninstall.
It is not a reason to hold the camera route; it goes to J18, and the run README is corrected on the branch.

### Machines
- `wsc gates`: 11 ok, 1 warn (hooks path written absolute in this clone), 0 failed; 270 host tests passed (includes `test_camera`,
  the new `test_ctl` cases and the engine-Lua string lint).
- `tools/pr_policy.py --branch job/J43 --base origin/main` before this commit: refused only for the missing review and the row status.
- `git merge-tree --write-tree origin/main HEAD`: merges clean.

### Claims against evidence
- Stall cause (string.find): `harness/runs/20261030_j43pc/README.md` section 1 (launch-by-launch table), fact
  `napoleon.lua.string_find_stalls_pump`. Coded as a lint in `tests/test_repo_rules.py`. Accepted.
- Whole-battle pump: `raw/pump_10min.txt`, 23 samples 10:20:08 to 10:31:34, scene `battle`, `pump_age` 0.0 throughout, battle clock
  702 s at the last sample. Accepted (11.4 minutes, brief asked 10).
- `cam` in three kinds: `raw/{land,siege,naval}_cam{1,2,3}.json`; pause and speed: the matching `raw/*_pause_*`, `*_speed_*`.
  Repeatability: `raw/repeat_{a,b}_cam.json` and the two shots. Key off: `raw/keyoff_*.json`. Accepted.
- Uninstall byte-identical (step e): **contradicted by the PC now** (finding 1).

### Risk-first reading
Picked `proxy/core/camera.cpp` and its adapter/site rows: it calls an engine virtual on a heap object from the Lua pump, the costliest
place for a mistake (a crash mid-battle, or a call into the wrong class). Read in full: every hop of the chain is `VirtualQuery`-checked,
the mode's vtable must lie inside the exe image, and the slot must equal the anchor-checked `battle.camera_set_target_pos` before every
call; `dev.camera=0` reads nothing (`CameraInstall` returns before any site read; `keyoff` log agrees); the three operands come from
stock bytes the patch engine verified, and `test_camera.cpp` checks each adapter offset against its row. Sound. Skimmed `ctl.py`
(`rate`, `v_cam`, `pose_check` with yaw wrap), `campose.py` and the three Lua chunks.

### Findings

**should-fix**
1. **The watcher's auto-restore puts the mod ini back after an uninstall.** `C:\napoleon_remastered_pc\watcher\watcher.log` 10:32:32:
   "AUTO-RESTORE under owner=j43 of 'headless'" restored `profiles\_saved\20261030T090232Z_j43\files\mod_ini` (main's ini, 5331 bytes,
   sha256 8d8a4af0..., saved 09:02:33) into the game folder 2 s after `pc_deploy uninstall` (10:32:30) and its post-uninstall snapshot.
   See it: `python3 proxy/tools/pc_deploy.py diff` of `snapshots\pre_install_20261030T090208Z.json` against the folder, or list the game
   folder: `napoleon_remastered.ini` is there (created 09:02:14 UTC, mtime kept by the restore), 1565 files against 1564. Harmless alone
   (no `d3d9.dll` loads it) but the next install's "as found" baseline is wrong and an ini from another build can mask config defaults.
   Fixed here: the run README section 6 says so. Not fixed here (harness/watcher code, J18's files): the guard. Proposed for **J18**:
   `pc_deploy uninstall` refuses while a watcher overlay holding a game-folder file is applied (or the restore skips files whose owner
   install is gone), and the post-uninstall check runs after the lock release. The stray file needs removing on the PC (moved to
   `_to_delete`): left for Liam or the next PC job, since the game folder is deploy-only.

**later**
2. `cam` with `dev.camera=0` answers `failed` at step set (`tests/test_ctl.py:310`), and the need for `dev.camera=1` lives only in the
   route's `why` text. J44's `scene` must launch with `dev.camera=1`, or ctl reads `dev_config` and refuses up front. Into the J44 brief.
3. Siege falls back to the land route when no scenario row is loaded (`harness/core/ctl.py` `current_kind`). J44's `scene` sets the row;
   the siege clamps are the land ones measured under land detection (report Deviations). Into the J44 brief.
4. The engine-Lua string lint covers tracked `proxy/*.lua` only, not Lua sent inline by Python or held in `wrappers.txt` (none today).
   Core candidate with the lint itself (J12).
5. The out-of-process `memdump.ps1` / `memwrite.ps1` that proved the camera fields are scratch only (`_scratch\j43\`). J28 will want
   the same reads: port the read half as a watcher job type rather than rewriting it.
6. Route 2 (`.battle_script` on a custom preset) and the campaign camera setters remain untried or open (facts
   `napoleon.battle.script_api_reachable`, `napoleon.campaign.camera_route`). Recorded, nothing to do now.

### Rule changes for other branches
The string lint fails any open branch that adds `find`/`sub`/`gmatch` in `proxy/*.lua`. No open job branch touches those files.
