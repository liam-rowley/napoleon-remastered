# J50: UI art packs load in game

Phase 5, follow-up to J36. J36 built the UI art upscaler and installed the four packs (`ui_art_2x5_{ui_art,icon,panel_frame,button_state}`, 709 MB)
sha-checked and uninstalled them byte-identically, but the game never loaded them: the game folder had no proxy, so the watcher refused a headless launch
(job `J36-20261031T000057Z-756112982`, exit -2). This job deploys the proxy through the existing kit, installs the packs, launches headless to the
campaign and to a battle, and closes the two open engine facts `napoleon.ui_art.pack_loads` and `napoleon.ui_art.dds_at_tga_paths`. It also decides
J36's kill criterion "any crash when the packed files load".

Model: Sonnet, no reverse engineering planned (a probe that needs engine memory stops at a kill criterion). Budget about 150 tool calls; at the cap, stop,
commit, report what is left. Subagents are not needed. Waiting belongs to the harness: `job.sh` blocks inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J50`). Read `docs/DECISIONS.md` (D2, D5, D14, D19, D27, D30), `jobs/J36/report.md` (Deviations; Open questions 4 and 6),
  `upscale/README.md`, `upscale/runs/2026-10-31_first_roles.md` (sections d and e: the install and uninstall jobs, `install_packs.ps1`), `harness/README.md`
  (Install, Job requests, Headless launch), `proxy/README.md` ("Headless", "Dev control channel"), and the `harness/runs/` report of J44 for the working
  deploy, launch, `scene`, `shot` and uninstall sequence.
- Search before writing: `python3 core/wsc.py find ui_art pack mod_packs dds tga shot scene install`. Extend `proxy/tools/pc_deploy.py`, `harness/core/{job.sh,ctl.py,shot.sh}`,
  `proxy/tools/build_dev_pack.py` and `upscale/core/pack.py`; add no near-duplicate.
- Evidence in `empire-remastered` (read-only: never edit, commit or push there): how `ui_scale_2x*.pack` replaced UI art and whether DDS stood in for TGA
  (`docs/learnings/`, search "dds", "tga", "ui_scale"). Napoleon is the same lineage but every fact is checked again here.

## Target facts
Check each again before relying on it:
- `Napoleon.exe` sha1 `9aebcd2172f2878d781b079f7feb45b0e12e0250`; game folder `C:\Program Files (x86)\Steam\steamapps\common\Napoleon Total War`; the watcher root
  `C:\napoleon_remastered_pc\watcher` (run `job.sh status` first).
- The game folder had no proxy after J36. Compare it with the newest snapshot under `C:\napoleon_remastered_pc\snapshots\` before the first install; a stray file not in
  that snapshot (J43 review finding 1: the headless auto-restore wrote an ini back after an uninstall) means stop and ask Liam.
- The J36 packs sit under `ui_art_2x5\<vanilla path>`, so installing one replaces no vanilla path: a launch with them proves only "no crash". They cannot prove "the
  upscaled files are the ones read" by themselves (Decisions below).
- Every test launch uses `dev.skip_intro=1`. A launch is headless unless Liam is present; `visible=1` only with Liam asking for it.
- The J7 indexer treats any `.pack` in `data\` as a game pack: the J36 packs must be in `discovery/napoleon/games.json` `mod_packs` (the skip list) before the next re-index.

## Decisions already made for this job
- **Proxy by the existing kit**: `pc_deploy.py kit` then `send`, `install` (J20 flow), sha-checked, game closed. Nothing is written to the game folder by hand; the uninstall at
  the end is byte-identical, checked after the game lock is released and the profile restored.
- **Two-stage load proof.**
  1. *No crash*: the four J36 packs as built, in `data\`, headless launch to the main menu, then the campaign, then a land battle (`scene`), with `shot` in each, WER and the
     watcher hang folder checked. This closes `napoleon.ui_art.pack_loads` (the claim: the game starts with the packs in the data folder).
  2. *Read proof*: a scratch pack under `C:\napoleon_remastered_pc\_scratch\J50\` (never committed, not a J36 pack) that carries a **visible marker** (a solid-colour or
     inverted image at the vanilla size) at the vanilla path of a few UI assets that are on screen in the frontend, campaign map and battle (pick from the `ui_art`, `icon` and
     `button_state` rows by looking at the screenshots), built with `upscale/core/pack.py` or `build_dev_pack.py` so the format is the one the engine already loads. Shots with and
     without it show the marker, or they do not; the verdict goes in the fact. Then repeat with 3 to 5 real J36 outputs at the vanilla paths (the upscaled files, 2.5x size) and
     compare the shots to the vanilla shots: the art should be sharper and the layout unchanged; a changed layout is a finding for the UI host jobs, not a failure here.
     Pack precedence over `data.pack` is checked on the way (`napoleon.packs.dev_pack_precedence` is the related fact).
- **DDS at a TGA path** (`napoleon.ui_art.dds_at_tga_paths`): in a scratch pack, put a DDS (DXT5 with a mip chain, a marker image) at the path of one vanilla `.tga` that is on
  screen. Shown = yes; blank, vanilla art or a crash = no, with the log line. If yes, record that J36's TGA outputs can become DDS with mips and add a `needs_brief` row for that
  change in `upscale/` (do not change the upscaler here). If no, J36's TGA-stays-TGA choice stands; say so.
- **Crash decision.** J36's kill criterion "any crash when the packed files load" is decided here: a crash with the four packs in the clean stage-1 run fails J36's output (fix or
  report the pack, do not mask it); a crash only with a scratch pack is a finding about the probe. Name which in the report.
- **`mod_packs` skip list** gets the four `ui_art_2x5_*` pack names in `discovery/napoleon/games.json` (exact names if that is all the list takes); add a test or gate line that such
  a pack in `data\` is never indexed as a game pack if a cheap one exists. The scratch pack must never be left in `data\`.

## Deliverables
1. The proxy deployed through the kit and uninstalled again, with snapshots (`pc_deploy.py snapshot` and `diff`) before and after.
2. Stage 1: the four packs installed through a watcher job (reuse the J36 `install_packs.ps1` flow; commit it under `upscale/pc/` if it is not in the repo), headless to the main
   menu, the campaign and a land battle; result JSONs and shots in the run folder; zero WER dumps.
3. Stage 2: the marker pack, the real-output pack and the DDS-at-TGA pack; before and after shots per probe; the verdicts.
4. `engine_facts`: `napoleon.ui_art.pack_loads` and `napoleon.ui_art.dds_at_tga_paths` set to `verified` or `refuted` with date and run id; add facts for pack precedence if measured
   and for anything the shots show about layout with 2.5x art in place.
5. `mod_packs` skip list updated and `python3 core/wsc.py gates` green.
6. A dated run report under `upscale/runs/` (stage 1, stage 2, shots, job ids). Shots go in the run folder as JPG, under about 2 MB in all.
7. Byte-identical uninstall of the proxy and the packs; `save_games` and every settings file as found.

## PC test
Unattended and headless through the watcher; kits and packs go over sha-checked; lock owner `J50`. No sitting with Liam is needed; if a step would need a visible window
(for example, the proxy refuses the headless launch), stop and ask.

Steps:
- a) Game folder against the snapshot (Target facts). Build and send the proxy kit; install it; `job.sh status`.
- b) Stage 1: packs in, launch, menu, campaign, battle, shots, kill, WER and hang folder checked.
- c) Stage 2: packs out; scratch packs in one at a time (marker, real outputs, DDS at TGA); a launch and shots each; the verdicts.
- d) Everything out, proxy uninstalled, game lock released, profile restored; snapshot diff `identical`.

## Kill criteria
- The headless launch is refused or fails twice for a proxy or watcher reason after the kit deploy: stop, report the job ids and the refusal text, and ask Liam (a visible
  launch only with Liam present).
- Any crash with the four J36 packs in the clean stage-1 run: read WER and the hang folder first and repeat once; the same crash twice: stop, keep the dumps, report J36's output
  as failing, and bisect by role pack only if that takes under about 15 calls.
- The read proof needs engine memory, a change to the proxy DLL, or a pack format `pack.py` cannot write: stop and propose an Opus job.
- Stage 2 shows no marker after about 25 calls (pack not listed, precedence lost, path wrong): record the fact as `refuted` or `open` with what was tried; do not keep guessing paths.
- Any write into the game folder outside a deploy or watcher job, into `core/`, or into Liam's saves would be needed: stop and ask Liam.

## Finish
Write `jobs/J50/report.md`: what was run (job ids, run folder), the stage 1 and stage 2 verdicts with shots, the crash decision for J36, the DDS-at-TGA answer and the follow-up row
it opens, the `mod_packs` change, deviations from this brief and why, open questions. Then `wsc reg set jobs J50 status=review report=jobs/J50/report.md`.
