# J53 report: UI art play-test install

Branch `job/J53`, session `77269dc7-d1c0-49ec-8f37-c570ba58f48e`, model Opus 5.5 (the brief asks for Sonnet: see Deviations), 2026-11-02, about 110 tool calls.
Liam can now put the 2.5x UI art into the game with one command and take it out with one. The smoke run (`upscale/runs/2026-11-02_j53/README.md`) loaded 11 roles
(2.28 GB, 9170 entries) and then the default four. Each set went through a land battle, the main menu and the campaign map, with no crash and no art drawn blank or at the wrong size.
The game folder ended identical to the start.

## What was built
- **`wsc upscale pack --play`**:
  - `upscale/core/pack.py` gains `play_plan`, `held_back_reason` and `PLAY_MAX_SIDE = 4096`, and `build(..., extra=)` writes `prefix`, `role` and `held_back` into the `.pack.json`.
  - `upscale/napoleon/cli.py` gains `--play`, `play_packs` and `vanilla_paths`.
  - The usage line is in `tools/verbs/upscale.py`.
  - Config keys `play_pack_name: "ui_art_play_{role}"` and `play_packs_dir: "packs_play"` in `upscale/napoleon/config.json`.
  - The `ui_art_2x5` packs, their names and their plan signatures are unchanged; a test pins the old signature, so the PC's built packs are not rebuilt.
  - The builder refuses an entry whose path is not in the assets registry, and builds nothing for that role.
- **Held back:** a DXT output with a side that is not a multiple of 4, and any output over 4096 px on a side. `rules.py` is untouched.
- **`upscale/pc/play.py install [--roles a,b | --all] [--kit ID] [--intro] | uninstall | status`** (new tools row `upscale.pc.play`) composes `pc_deploy.py` (imported) and
  `install_packs.ps1`; it writes the game folder through nothing else.
  - **Refusals, all before the first change:** a running game, an agent's game lock, a non-vanilla exe, a `.git`, a play install or proxy kit already in,
    a missing pack, a pack already in `data\`, a pack whose sha256 is not its `.pack.json`'s, or a kit that does not verify.
  - **Install:** the record `<state>\play\play.json` and a snapshot first, then `pc_deploy install` of the newest sent kit, then `dev.skip_intro=1`
    (Liam's standing preference for test launches; `--intro` keeps the intro), then the packs.
  - **Uninstall:** the packs to `<state>\_to_delete\play_<stamp>\`, then `pc_deploy uninstall`, then a diff against the pre-install snapshot; non-zero unless `identical`.
  - **Status:** re-hashes each pack, the kit files and the exe, and lists foreign files (the play packs excluded) and dumps.
- **`discovery/napoleon/games.json` `mod_packs`:** gains the 14 `ui_art_play_<role>.pack` names. `tests/test_mod_packs.py` now covers both name keys for every role,
  and checks that a play name sorts after `media.pack`.
- **Tests:**
  - `tests/test_play_pack.py` (7, standard library): vanilla paths and empty prefix, both held-back rules, the vanilla-path refusal, the `cli.play_packs` path,
    a J7 `PackFS` re-read with the play pack winning over `data.pack` and after `media.pack`, a byte-identical rebuild, and the unchanged 2x5 signature.
  - `tests/test_play.py` (7, under PowerShell with a fake game, state and kit): install then uninstall `identical`, roles by name and a missing pack,
    refuse overwrite, a bad sha refused, a foreign file reported with the uninstall exiting 1, a non-vanilla exe, and an agent lock.
- **Docs and records:** `upscale/README.md` gains "Play test" (commands and what to expect), and `install_packs.ps1`'s `when:` names `play.py`.
  New fact `napoleon.ui_art.play_packs_load` (verified, run `2026-11-02_j53`).
- `python3 core/wsc.py gates`: 11 ok, 1 warn, 0 failed. The warn is the `tests` gate: 521 passed, and the 20 skips are tooling this machine lacks
  (numpy and Pillow, capstone, the viewer wasm, the unchanged proxy). The new tests are not among them.

## Evidence
Run `upscale/runs/2026-11-02_j53/README.md`. It has the job ids, six shots (676 KB), the per-role table and the snapshots.
- **Play packs:** 13 roles, 9410 entries, 2823 MB, in `C:\napoleon_remastered_pc\upscale\work\packs_play\` (not committed). `cursor` has no outputs, so it has no pack.
- **Held back:** 28, all in `loading_screen`: 6 DXT not a multiple of 4 and 23 over 4096 px, with `2.dds` in both. `loading_screen` keeps 11 of 39, so it is not empty.
  No other role holds anything back.
- **Smoke run a (11 roles):**
  - `land_small` loaded in **3.9 s** (J50: 4.2 s) and `campaign_start` in 3.3 s; the main menu was ok.
  - The proxy indexed 86995 vanilla + 9170 play entries.
- **Smoke run b (default four):** `land_small` in **3.8 s**, 3484 play entries indexed, the front end and campaign ok.
- **Crashes:** no dump, WER report or hang in either stage. The known init heap corruption did not appear.
- **Shots (by eye):** unit cards, portraits, unit and campaign flags, settlement icons, HUD frames and buttons sit at the vanilla size. No sizing-by-texture finding.
- **Back out:** start snapshot identical to J28's post-uninstall snapshot (1564 files). `pc_deploy uninstall` identical to its own snapshot, then end against start **identical**.
  Lock released, profile restored byte for byte, exe vanilla, nothing installed.

## For Liam: the commands
In Git Bash on the PC, from the repo checkout, with the game closed and no agent job running (`bash core/harness/job.sh status` shows the lock):
```
git pull                                      # once this job is merged
python3 upscale/pc/play.py install            # default: ui_art, icon, panel_frame, button_state (709 MB)
python3 upscale/pc/play.py install --all      # or every role (2.8 GB); or --roles flag,portrait,unit_card,building_icon
python3 upscale/pc/play.py status             # what is in, sha re-check, dumps, the uninstall command
python3 upscale/pc/play.py uninstall          # everything out; prints "identical" or the diff, exit 0 only when identical
```
The packs are already built. After a new upscale run, rebuild them with `python3 core/wsc.py upscale pack --play --roles <roles>`. The install takes the newest sent kit
(`kit_20261102T154016Z_23dbc9e2d143`, DLL build `715e9dfc0727`) and sets `dev.skip_intro=1`.

**What you will and will not see:**
- At UI scale 1 the art is minified into the vanilla rect, so it will not look sharper.
- The test is whether anything breaks:
  - blank or wrong art;
  - an element too big or too small (flags, portraits, unit cards and building icons first; event pictures and loading screens only with `--all` or by name);
  - a crash;
  - slower loading or stutter.
- The proxy log is `<game>\napoleon_remastered\logs\proxy.log` and dumps go to `<game>\napoleon_remastered\dumps\`. `status` lists dumps, and `uninstall` keeps both under
  `C:\napoleon_remastered_pc\_to_delete\uninstall_<stamp>\`.
- `uninstall` is the answer to anything odd. Run it before agents use the PC again.

## Deviations from the brief and why
- **`play.py`, not `play.sh`** (the brief allows a rename). The wrapper keeps a JSON record, hashes packs and diffs snapshots, and that is plain Python against `pc_deploy`'s own
  functions. It runs in Git Bash as `python3 upscale/pc/play.py`.
- **The smoke run did not run `play.py`.** As the brief says, the agent's run used `pc_deploy` for the kit and watcher ps1 jobs that run
  `install_packs.ps1` for the packs. The hook (`tools/claude_hook.py` `EXEMPT`) exempts only `pc_deploy.py` and `job.sh`, and `play.py` refuses while the game lock is held,
  which an agent's launches need. So the wrapper cannot run under an agent as built. On real files it is exercised only through the parts it composes; the whole sequence is
  host-tested against a fake game folder.
- **Two checks moved earlier than the brief's sketch:** a pack already in `data\` and a bad pack sha256 are refused by `play.py` before any change.
  `install_packs.ps1` still checks while copying. Otherwise the refusal came after the kit install, and an uninstall would have moved a pack that was not ours.
- **`dev.skip_intro=1` in the play install** is not in the brief. It is Liam's standing preference for test launches; `--intro` turns it off.
- **No DLL build.** The kit uses `build/proxy/napoleon/d3d9.dll` of the main checkout, build `715e9dfc0727`. That is the build id of this branch's DLL inputs (`build_id.py`),
  so it is J28's accepted build; the kit's own id `23dbc9e2d143` is this branch's commit. Rule 79 does not apply: no proxy or harness input changed.
- **Harness path:** J50's `harness/core/ctl.py` is now `core/harness/ctl.py` (J12). The first launch call failed on the old path before anything ran.
- **Memory** was not measured: the scene JSONs carry no memory figure, and the brief's "memory" stays with Liam's play test.
- **Model:** the session ran on Opus 5.5, not Sonnet; nothing here needed it.

## Open questions
1. **Agents and a play install:** the watcher and `pc_deploy install` do not know about `<state>\play\play.json`. If Liam leaves a play install in, the next agent job
   launches with the play packs in `data\`, and its `pc_deploy install` sees a kit already installed. Should the watcher (or `job.sh lock`) refuse while `play.json` exists?
   That is a harness change in `core/`, so it needs a `needs_brief` row.
2. **Held-back loading screens:** 28 `loading_screen` files stay out until a probe shows the engine draws a DXT whose side is not a multiple of 4, or a texture over 4096 px.
   J50 review item 3 (a 4-aligned DDS at a TGA path) could share that probe's launch. Liam decides whether it is worth a job before the UI host draws loading screens.
3. **Hook exemption for `play.py`:** should agents be able to run `play.py` (an `EXEMPT` entry in the hook, and a lock-owner allowance in `play.py`), so the next smoke run
   tests the exact command Liam runs? This job kept the brief's route.
4. **Visible play test:** this run proved headless loading at 1080p in three scenes only. Event pictures, loading screens and most panels (diplomacy, technology, building browser)
   were not on screen. Liam's play test is the check for those.
