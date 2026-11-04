# J45 PC run 20261031_j45pc: the fixed-sky launch guard, the 20 passes on the content-hash id, a reword, a clean uninstall

PC (Windows 11), headless 1920x1080 through the watcher 1.1.0, 2026-10-31 11:50 to 13:25 UTC, game lock `j45`. Every game change went
through `pc_deploy.py`, sha-checked. DLL build `41cde4716ac7` (sha256 `b1ff76a0b7f677b47e5332bf09b5c03d050af26b600d381f9a7b099d869dcfa7`,
`build.sh --docker all`; `build.sh --docker repro`: identical from another path).

## Start state
J18's kit `kit_20261031T080721Z_03354d8bfb63` was still installed. `pc_deploy uninstall` first: the game folder was then identical to the
pre-install snapshot (1564 files), the exe vanilla (sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`).

## a) A kit without the fixed-sky pack is refused at launch
`kit_without_sky.py` (this folder) builds a kit with the pack's builder made to fail, as on a machine whose game packs are unreadable.
Kit `kit_20261031T115322Z_40377bbdba78`: manifest `fixed_sky` = `{"present": false, "reason": "J45 step a: ..."}`. Installed, then
`ctl.py --owner j45 scene land_small` answered `refused` (exit 2) in 0.3 s: `step_a_scene.json`. The watcher afterwards: game
`not_running`, no lock. Nothing launched.

## b) 20 acceptance passes
Real kit `kit_20261031T115513Z_40377bbdba78` (manifest `fixed_sky` present, sha256 `e23ad1a7b064...`); the installed `d3d9.dll` has the
build's sha256.
- First attempt, run `20261031_j45acc`: pass 1 failed before any launch, `ModuleNotFoundError: No module named 'PIL'` (`python` on PATH is
  Python 3.14 without Pillow; `python3` is 3.15 with it), and its ledger line has no branch and the kit's id (ledger line 46). Kept as a
  record; `acceptance.py run` now refuses both before pass 1 (`run_problems`).
- Gate run `20261031_j45acc2` (`python3 harness/core/acceptance.py run --passes 20 --run 20261031_j45acc2 --owner j45`): 20 of 20 passed,
  11:57:38 to 13:18:15 UTC, ledger lines 47 to 66, each with `build_id` `41cde4716ac7`, watcher 1.1.0, branch `job/J45`. Every pass:
  six scenarios (hist_dresden, hist_nile, campaign_start, naval_small, siege_small, land_small) loaded, posed, shot and matched,
  perf, warm reset, settings files identical.
  `acceptance.py streak --build 41cde4716ac7 --watcher 1.1.0`: 20.

## c) A reword after the passes keeps them
Commit `bb1adb9` (the build id change, touches `proxy/`) reworded with `git filter-branch --msg-filter` (subject only, trailers kept) over
`6e94e28..HEAD`; the tree is unchanged. Pushed with `--force-with-lease=job/J45:2037059`; the branch head became `6de786c`.
- The old id formula (`git log -1 --format=%h --abbrev=12 -- <inputs>`) moved `bb1adb9ef790` to `775dfe9b6201`: J44's incident.
- `proxy/tools/build_id.py` still says `41cde4716ac7`; `acceptance.py streak` still 20.
- `tools/pr_policy.py --branch job/J45 --base origin/main`: no rule 79 error (rule 79 is active on main:
  `acceptance_active(...)` True); it refuses only for the report, the review and the row status, which come later.

## d) Uninstall
`pc_deploy uninstall`: game folder identical to the pre-install snapshot (1564 files), exe vanilla. `save_games`: newest file
2026-10-29T20:32:30, untouched. Settings files: identical after every pass (each `pass_NN.json` `settings_identical`). The PC is left
with no kit installed (J18's kit was not reinstalled).
