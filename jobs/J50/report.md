# J50 report: UI art packs load in game

Branch `job/J50`, session `0afa23ee-dbcb-40f4-a69e-7a223f2f7a65`, model Opus 5.5 (the brief asked for Sonnet: see Deviations). Run report with every job id and shot:
`upscale/runs/2026-10-31_j50/README.md`. Game lock `J50`, 2026-10-31 16:47:55 to 17:05:49 UTC, about 140 tool calls.

## What was run
- **Proxy:** J22's leftover kit uninstalled (identical to its pre-install snapshot), J50 start snapshot `identical` to J36's post-uninstall snapshot, then kit
  `kit_20261031T164614Z_f6850d9fe914` (DLL build `41cde4716ac7`) built, sent and installed with `pc_deploy.py`; uninstalled at the end.
- **Stage 1:** the four J36 packs (709 MB) into `data\` by `upscale/pc/install_packs.ps1` (new; job `J50-20261031T164812Z-1327310857`, sha256 of source,
  manifest and copy equal), headless to a land battle, the main menu and the campaign with a shot in each (`raw/s1_*.jpg`), then a repeat launch.
- **Stage 2:** packs out, then five launches with scratch packs built by `upscale/core/pack.py` (`_scratch\j50\packs`, never committed): marker, marker v2,
  real J36 outputs together with a battle marker, DDS at a TGA path, and one vanilla control run (`s2r`).

## Verdicts
- **`napoleon.ui_art.pack_loads`: verified 2026-10-31, run `2026-10-31_j50`.** The game reaches all three scenes with the packs in `data\`; it proves "no crash" only, as the brief says.
- **J36 kill criterion "any crash when the packed files load": not hit; J36's output passes.** One launch of the stage-1 run died (pid 33332, `0xc0000374`
  heap corruption at `ntdll+0xfd71f`), but 156 ms after process start and before the first d3d9 call or any data pack read; the repeat launch was clean;
  J44 saw it with no UI packs, and the same WER bucket was reported at 12:17 during J45 (no UI packs). That is a crash of the launch, not of the packs: new open
  fact `napoleon.proxy.init_heap_corruption`. No crash in any stage-2 launch.
- **Read proof: yes.** A movie pack's TGA at a vanilla path replaces the `data.pack` art in all three scenes (campaign end-turn button green, front-end logo and Steam
  button magenta, the whole battle HUD cyan): new fact `napoleon.ui_art.movie_pack_overrides`. This is also the pack precedence over `data.pack` the brief asked to check.
- **Real outputs:** 2.5x art at the vanilla path is drawn in the vanilla rect, layout unchanged, not visibly sharper at 1080p (`real_vs_vanilla_crops.jpg`):
  new fact `napoleon.ui_art.hires_same_rect`. No layout finding for the UI host jobs.
- **`napoleon.ui_art.dds_at_tga_paths`: refuted.** A DXT5 DDS with mips at `logo.tga` is not drawn (blank logo), no crash, no log line (the proxy has no texture hook).
  J36's TGA-stays-TGA choice stands, so no `needs_brief` row for `upscale/` is opened.

## Other changes
- `discovery/napoleon/games.json`: `napoleon.mod_packs` lists all 14 `ui_art_2x5_<role>.pack` names the upscaler config can build (the brief named four; nine more
  are already built on the PC by J51, and the new test found a 14th, `cursor`). `tests/test_mod_packs.py`: every role pack in the config is in the list, and a
  `PackFS` from `games.json` leaves such a pack out (2 tests).
- `upscale/pc/install_packs.ps1` with a tools row; `upscale/README.md` step 3 and the TGA rule updated.
- `python3 core/wsc.py gates`: 11 ok, 1 warn (`hooks`: this worktree's `core.hooksPath` is an absolute path; environment, not code), 0 failed.

## Deviations from the brief and why
- **A proxy was already installed** (J22's kit, left after its run), not "no proxy". I uninstalled it with `pc_deploy` (identical to its pre-install snapshot), checked
  the folder against J36's last snapshot (identical), then deployed this branch's kit as the brief says. Same situation and handling as J45 (J18's kit).
- **Model:** the session ran on Opus 5.5, not the Sonnet the brief names; nothing in the job needed it.
- **Scratch folder** `_scratch\j50`, not `_scratch\J50`: `job.sh scratch` only takes lower-case owners. The lock owner is `J50` as the brief says.
- **Combined launch:** the real-output pack and a battle marker (`zz_j50_marker3`) went in together in probe s2r3. Their paths do not overlap (front end and campaign
  art against `ui\battle ui\skins`), so each verdict stands; it saved a launch.
- **Marker targets:** the first guesses (`simple_button_center_up`, `ui\battle ui\buttons`) are not on screen; marker v2 and v3 tinted whole folders instead. The
  red main-menu buttons were never identified (a UI host or template question, not needed for the facts).
- **Sharpness** was judged on 1280x720 shots (`shot.sh` scales the 1920x1080 frame down), so "not visibly sharper" is weak evidence either way.
- **`ctl.py shot` at the main menu is not fixed here.** `ctl.py shot` at `frontend` waits the full 120 s settle and fails (`raw/s1_frontend_shot.json`;
  the main-menu shots were taken with `shot.sh`). I made and tested a fix (`shot` settles with `frontend` added to the ready scenes; `scene` and `reset`
  unchanged), but `harness/core/ctl.py` is a rule 79 input and 20 acceptance passes were out of this job's scope, so I took it out again (Open question 5).
- Five redundant shots were deleted to stay under about 2 MB (their result JSONs are kept): 1.6 MB of shots in all.

## Open questions
1. **Init heap corruption** (`napoleon.proxy.init_heap_corruption`): three sightings in two days (J44, J45's WER, J50), each followed by a clean launch. Worth a
   crash job (Opus, dumps under `_to_delete` and WER) before it costs an acceptance pass? It needs a `needs_brief` row on a `plan/` branch.
2. **DDS:** since a DDS at a `.tga` path is not drawn, mips for 2.5x TGA art must come from the UI host (or the TGA files must be renamed to `.dds`, which needs
   the referring layouts changed). Which one the UI host jobs choose is theirs.
3. **Sharper art needs a UI scale:** at UI scale 1 the 2.5x art is minified into the same rect. Confirm the plan is that the UI host draws it at 2.5x; until then the
   packs only add bytes.
4. **J22's leftover kit:** jobs that end with a proxy installed leave the next job a surprise. Should `pc_deploy` or the job finish steps require an uninstall
   (or name the kit left installed in the report)?
5. **`ctl.py shot` at the main menu:** the fix is about 4 lines in `Ctl.settle`/`v_shot` plus a FakeGame test (FakeGame starts at `frontend`). Bundle it into
   the next job that runs the 20 acceptance passes anyway, or give it a small job of its own?
