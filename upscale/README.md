# UI art upscaler (J36)

D19: vanilla UI art is ML-upscaled by an integer factor, resampled to 2.5x its vanilla pixel size, given a full mip chain (DDS) and packed. UI art only (D14).
Report and evidence: `jobs/J36/report.md`, `upscale/runs/`. Sheets to judge: `upscale/sheets/`.

## Run
1. Once: `upscale\pc\setup_env.cmd` (a self-contained Python with torch in `C:\napoleon_remastered_pc\upscale\art_build`; nothing system-wide). Check: `python3 core/wsc.py upscale env`.
2. `python3 core/wsc.py upscale plan --roles icon` (decisions, no work), `run --roles icon --registry` (writes `<work>\out`, `manifest.json`, the registry fields), `verify`,
   `sheets` (before/after under `/extract/napoleon/upscale_sheets/`), `compare --sample 192` (model side by side), `pack` (one `ui_art_2x5_<role>.pack` per role in `<work>\packs`).
   Default work folder `C:\napoleon_remastered_pc\upscale\work`; `--roles` defaults to `first_roles` in `upscale/napoleon/config.json`.
3. Install a pack only through a watcher job running `upscale\pc\install_packs.ps1` (sha-checked copy, uninstall moves to `_to_delete`; example jobs in
   `upscale/runs/2026-10-31_j50/`); the tools never write the game folder. Every `ui_art_2x5_<role>.pack` is in `discovery/napoleon/games.json` `mod_packs`
   (`tests/test_mod_packs.py`), so the indexer never reads one as a game pack. In game (J50): the packs load without a crash; a movie pack's entry at a
   vanilla path replaces the `data.pack` art in the front end, campaign and battle, and 2.5x art there is drawn into the vanilla rect.

## Play test (J53)
To play with the upscaled art, Liam runs these in Git Bash on the PC from the repo checkout. The game must be closed and no agent may hold the game lock.
1. Once, or after a new upscale run: `python3 core/wsc.py upscale pack --play --roles <roles>`. It writes `ui_art_play_<role>.pack` with entries at the
   **vanilla paths** into `<work>\packs_play`. The builder refuses any path that is not in the assets registry, so a play pack only replaces. It holds back
   DXT outputs with a side that is not a multiple of 4 and outputs over 4096 px; they are listed as `held_back` in the pack's `.pack.json`.
   In run `2026-11-02_j53` only `loading_screen` holds anything back (28 of 39).
2. `python3 upscale/pc/play.py install` installs the default set: `ui_art`, `icon`, `panel_frame` and `button_state` (709 MB). For more:
   `--roles flag,portrait,unit_card` or `--all` (2.8 GB). `loading_screen` and `event_picture` are never in the default.
   The install refuses a running game, an agent's game lock, a non-vanilla exe, a `.git`, a proxy already installed, a pack already in `data\`, or a pack whose
   sha256 is not its `.pack.json`'s. It then:
   - snapshots the game folder (`<state>\play\`);
   - installs the newest sent proxy kit with `dev.skip_intro=1` (`--intro` keeps the intro, `--kit <id>` picks a kit);
   - copies the packs with `install_packs.ps1`.
3. Launch the game from Steam as usual. `python3 upscale/pc/play.py status` re-checks each pack's sha256 and the exe and lists foreign files and crash dumps.
4. `python3 upscale/pc/play.py uninstall` moves the packs to `<state>\_to_delete\play_<stamp>\`, then runs `pc_deploy uninstall`, then diffs the game folder
   against the pre-install snapshot. It exits non-zero unless the result is `identical`.

**What to expect:**
- At UI scale 1 the 2.5x art is drawn into the vanilla rect, so it does **not** look sharper (`napoleon.ui_art.hires_same_rect`). The sharper art pays off
  only once the UI host draws it above scale 1.
- The play test checks that nothing breaks:
  - art that is blank, wrong, or too big or too small (flags, portraits, unit cards and building icons first);
  - a crash;
  - slower loading, stutter or memory use.
- The proxy log is `<game>\napoleon_remastered\logs\proxy.log` and dumps go to `<game>\napoleon_remastered\dumps\`. `uninstall` moves both to `<state>\_to_delete\uninstall_<stamp>\`.
- `uninstall` is the answer to anything odd. Run it before handing the PC back to agent jobs: the watcher does not know about a play install.

**The whole vanilla UI at 2x for 4K (J66, `uiscale/README.md`).** Build once, then install instead of the role packs:
```
python3 core/wsc.py uiscale build                       # -> C:\napoleon_remastered_pc\uiscale\work (layouts, art, fonts, templates, rules)
python3 upscale/pc/play.py install --scale 2            # kit + ui_scale_2x.pack + ui_scale_2x_fonts.pack, dev.file_rules -> the scaled uied.templates
python3 upscale/pc/play.py status
python3 upscale/pc/play.py uninstall                    # ends "identical"
```
Other factors (J67): `--scale 1.5` for 2560x1440 (the default there), `--scale 1.25` built. The install refuses a leftover `napoleon_remastered.ini` with no proxy in (`--keep-ini` goes on, and the uninstall then leaves it); the uninstall refuses while a watcher profile is active.
`--scale` refuses `--roles` or `--all`, because the scale pack carries its own 2x art. Set the game to 3840x2160 yourself in its options:
the install does not touch the preferences. The loose `uied.templates` in `data\ui\templates\` is never written. The proxy's
`dev.file_rules` redirects its reads to the scaled copy in the state folder. Files in the engine's UI cache
(`%APPDATA%\The Creative Assembly\Napoleon\ui_cache`) are moved to the play trash at install and at uninstall.

## Rules (code: `upscale/core/rules.py`, `resample.py`, `batch.py`)
- Target = floor(2.5 x size + 0.5) per axis; a longest side at or above `native_cap` (2048) or a non-image file is skipped with a reason.
- RGB goes through the model (x2) after dilation under A = 0, then Lanczos to the exact target; alpha never meets the model (Lanczos, cut at 128 when the vanilla alpha is a cut-out).
- DDS keeps the vanilla format and header (size and mips change) with the full chain: RGB box in linear light, alpha plain box. TGA and JPG keep their container, no mips: a DDS at a `.tga` path was not drawn (fact `napoleon.ui_art.dds_at_tga_paths`, refuted in J50 on one probe whose DXT size was not a multiple of 4: see the fact's notes).
- Resume key = input sha256 + model sha256 + settings; a second run changes nothing. Pack entries sit under `ui_art_2x5\<vanilla path>`.
- Models are pinned in `upscale/napoleon/models.json` (URL, sha256, licence) and fetched into the work folder, never committed.
