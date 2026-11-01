# J53: UI art play-test install

Phase 5. Liam asked (2026-10-31, after the J50 review) how to get the upscaled UI art into the game to play with; there is no route today.
The J36/J51 packs put every file under `ui_art_2x5\<vanilla path>`, which the game never reads. J50 proved two things this job builds on:
a movie pack (type 4) with an entry at a vanilla path replaces the `data.pack` art in the front end, campaign and battle
(`napoleon.ui_art.movie_pack_overrides`), and 2.5x art is drawn into the vanilla rect, so at UI scale 1 it is **not visibly sharper**
(`napoleon.ui_art.hires_same_rect`). Target: Liam installs the 2.5x art with one command, plays, and removes it with one command that leaves the
game folder snapshot-identical. The launch is Liam's own, visible, never an agent's.

Model: Sonnet, medium effort (D15). Python, PowerShell and shell in this repo; no DLL or engine work, no change to `core/`, `proxy/` or `harness/`
(rule 79 must not apply). Budget about 120 tool calls; at the cap, stop, commit, report what is left. Subagents are not needed.
Waiting belongs to the harness: `job.sh` and `ctl.py` calls block inside one call; never poll with repeated calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J53`; "The game is launched ... only through the watcher"; "Exe stays vanilla on disk (D2)"; "Never run git in a game folder").
- Read `jobs/J50/report.md` and `review.md` (later items 3 and 4 are this job's), `upscale/runs/2026-10-31_j50/README.md` (the install / launch / uninstall
  sequence that worked, with job ids; `probe_run.sh` is evidence, not a tool), `jobs/J36/report.md` and `jobs/J51/report.md` (roles, counts, pack sizes, open questions),
  `upscale/README.md`, `upscale/core/pack.py`, `upscale/core/rules.py`, `upscale/napoleon/{cli.py,config.json}`, `upscale/pc/install_packs.ps1`,
  `core/proxy/tools/pc_deploy.py` (header: `kit`, `send`, `install`, `uninstall`, `snapshot`, `diff`, `status`), `tools/claude_hook.py` (what the agent shell may
  write into the game folder: `EXEMPT`), `tests/test_mod_packs.py`, `tests/test_install_packs.py`, and the facts `napoleon.assets.pack_order`,
  `napoleon.packs.dev_pack_precedence`, `napoleon.ui_art.*`, `napoleon.proxy.init_heap_corruption`.
- Search before writing: `python3 core/wsc.py find pack install snapshot uninstall upscale deploy`. Reuse `pc_deploy.py` (kit, send, install, uninstall, snapshot, diff:
  sha-checked, exe stays vanilla), `install_packs.ps1` (sha-checked, refuses overwrite, moves to `_to_delete`) and `job.sh` (watcher jobs). Do not re-implement them.

## Target facts
Check each again before relying on it:
- 14 roles in `upscale/napoleon/config.json`; packs built so far: the four first roles (709 MB, J36) and nine more (2.69 GB, J51) in
  `C:\napoleon_remastered_pc\upscale\work\packs\`; `cursor` (179 `.cur`/`.ani`) is `not_needed`. Check the packs and their `.pack.json` still exist and match their sha256.
- Pack load order is type, then name (`napoleon.assets.pack_order`); a movie pack's entry at a vanilla path wins over `data.pack` (J50 used `zz_`-prefixed names).
  Play packs must be type 4 and sort after `media.pack`.
- J50 loaded only the four first roles (under the unused prefix) and, at vanilla paths, a handful of scratch files. **Nothing has loaded the J51 roles, and no role
  has ever been loaded in bulk at vanilla paths.** Unknown: whether any UI code sizes an element from the texture's pixel size (it would then be drawn 2.5x too large), load time and
  memory with 3.4 GB of extra packs, the engine's limit on texture size. That is what the play test and the smoke run below find out.
- J50 review item 4: 6 `loading_screen` DXT outputs have a 2.5x target that is not a multiple of 4 (for example `ui\frontend ui\loadingscreen\loading_screen_heading.dds`
  460x152 -> 1150x380), and J51 open question 1: 23 outputs are over 4096 px on a side. Whether D3D9 or the engine refuses either is unproven
  (`napoleon.ui_art.dds_at_tga_paths` was refuted on one unaligned probe). Count them from the manifest rather than trusting these numbers.
- The proxy had three init heap-corruption sightings in two days, each followed by a clean launch (`napoleon.proxy.init_heap_corruption`); a launch that dies at init is not the packs' fault.

## Decisions already made for this job
- **A "play" pack is a role pack at the vanilla paths.** `wsc upscale pack --play` (flag on the existing verb and `cli.py`; no second tool) writes
  `ui_art_play_<role>.pack` with entries at the vanilla path (empty prefix) into `<work>\packs_play\`, from the same verified manifest. New config keys beside `pack_name`
  (for example `play_pack_name: "ui_art_play_{role}"`), so the name is not hard-coded. The existing `ui_art_2x5_<role>` packs and their behaviour are unchanged.
- Every play pack name is in `discovery/napoleon/games.json` `mod_packs`; extend `tests/test_mod_packs.py` so the test covers the play names for all roles in the config.
- **A play pack only replaces.** The builder refuses an entry whose path is not a vanilla path of the assets registry (a stray path would add a file nobody reads), and a host test says so.
- **Hold back, do not guess.** A play pack leaves out (and lists in its `.pack.json` as `held_back` with the reason) any DXT output whose width or height is not a multiple of 4 and
  any output over 4096 px on a side. Count both per role in the run report. If after the smoke run Liam wants them anyway, that is a follow-up job with a probe. Do not change
  `rules.py` targets in this job (the existing `ui_art_2x5` packs and manifests stay valid).
- **Roles are chosen by the installer, default = the four first roles** (`ui_art`, `icon`, `panel_frame`, `button_state`; the ones J50 loaded). The other roles install by name
  (`--roles flag,portrait,...` or `--all`). `loading_screen` and `event_picture` (42 % of the extra bytes) are never in the default.
- **One command to install, one to uninstall,** a single wrapper that composes the existing tools, in this repo (`core/` cannot change). Shape (the builder may rename):
  `upscale/pc/play.sh install [--roles a,b | --all] | uninstall | status`, run in Git Bash on the PC by Liam. It must:
  1. refuse while a game runs, with a foreign `.git`, or on a non-vanilla exe (`pc_deploy status`);
  2. take a snapshot first and keep it under the state folder with a `play.json` record (kit id, packs and their sha256, snapshot path, UTC time);
  3. install the proxy kit with `pc_deploy install` (the proxy keeps the log and crash dump a play test needs; see open question 1), then the chosen play packs sha-checked against their `.pack.json`
     through `install_packs.ps1`, refusing to overwrite any file;
  4. `uninstall` moves the packs to `_to_delete` first and **then** runs `pc_deploy uninstall`, then diffs the game folder against the pre-install snapshot and exits non-zero unless it says `identical`
     (order matters: `pc_deploy uninstall` compares against the snapshot it took at the kit install);
  5. `status` prints what is installed, re-checks each installed pack's sha256 and the exe sha, and names the uninstall command.
  Steam Verify is never the only undo. Never delete on the PC: move to `_to_delete`. Never touch `save_games` or Liam's settings and keys files.
- **The agent shell may not write the game folder** (`tools/claude_hook.py`). Check how the hook exempts `pc_deploy.py` and `job.sh`: the agent's smoke run goes through
  watcher jobs and `pc_deploy`, exactly as J50 did; the wrapper itself is for Liam's shell and is host-tested against a fake game folder and fake state folder
  (install, refuse overwrite, uninstall identical, a foreign file reported, a bad sha refused). If the wrapper cannot run under an agent, say so in the report.
- **The job ends with the game folder as it started** (snapshot `identical`, no proxy, no packs, game lock released). Liam runs the install when he sits down; leaving a kit installed
  is what surprised J50 (its open question 4). The report gives the exact commands.
- **What Liam will and will not see goes in the report and in `upscale/README.md` ("Play test").** At UI scale 1 the art is minified into the vanilla rect: expect no visible gain.
  The play test checks that nothing breaks: blank or wrong art, an element drawn too big or too small, a crash, slower loading, stutter, memory. Give him a short checklist and tell him where
  the proxy log and dumps are, and that `uninstall` is the answer to anything odd.

## Deliverables
1. `wsc upscale pack --play` in `upscale/core/pack.py`, `upscale/napoleon/cli.py` and `tools/verbs/upscale.py` (usage line), the `held_back` rules, the vanilla-path guard, config keys, host tests
   (entry paths, empty prefix, held back DXT and oversize, refusal of a non-vanilla path, re-read by the J7 reader, byte-identical rebuild).
2. The play packs for all roles with finished assets, in `C:\napoleon_remastered_pc\upscale\work\packs_play\` (not committed), a table of entries, MB, sha256 and held-back counts per role in the run report.
3. The install / uninstall / status wrapper, its host tests, tools registry rows (header format: `core/warscape/tools.py`), and the `upscale/README.md` section "Play test".
4. `mod_packs` and `tests/test_mod_packs.py` extended; `python3 core/wsc.py gates` green.
5. **Smoke run on the PC (watcher, headless, lock owner `J53`),** the J50 sequence with the play packs for all roles but `loading_screen` and `event_picture`, then the default set alone:
   `scene land_small`, `reset frontend`, `scene campaign_start`, a shot in each, load time of the land battle against J50's 4.2 s, WER and the dumps folder checked after each launch.
   Look at the shots for oversized or blank art (the flags, portraits, unit cards and building icons are the first suspects: they are the roles nothing has loaded yet). Bisect by role (installer `--roles`)
   only if something is wrong, within the budget. New or updated `engine_facts` rows with the run id: for example `napoleon.ui_art.play_packs_load` and, if found, a sizing-by-texture finding.
6. A dated run report under `upscale/runs/` (job ids, shots under about 2 MB in all as JPG, snapshots before and after, `identical`), and the final state: game folder identical to the start.

## PC test
Unattended and headless through the watcher (as J50); lock owner `J53`. If the game lock is held by another job (a J8 session may be using it), wait through the watcher's own queueing in one blocking call and do not
poll; if the PC is not free after one such wait, commit what is done and report. The visible play launch is Liam's, after this job: do not start a visible launch. If a step would need one, stop and ask.
Steps: a) snapshot the game folder, compare with the last known one, build and send the proxy kit (`pc_deploy kit --dll`, `send`), b) the smoke run above, c) everything out, proxy uninstalled, lock
released, profile restored, snapshot diff `identical`.

## Kill criteria
- Any crash in a smoke launch that is not the known init heap corruption: read WER and the hang folder first, repeat once; the same crash twice with the play packs: stop, keep the dumps, bisect by role only
  if that takes under about 15 calls, report which role, and do not hand Liam an install that crashes.
- The same init heap corruption twice in a row on the smoke launches: stop, report the dump names and `napoleon.proxy.init_heap_corruption`; it needs the crash job (J50 open question 1), not more launches.
- The uninstall does not end `identical` after one honest repair: stop, report the diff, and leave the packs in `_to_delete`; do not hand Liam the install command.
- The play pack needs engine memory, a DLL change or a pack format `pack.py` cannot write, or a write into the game folder outside `pc_deploy` / a watcher job: stop and ask Liam.
- Over about 120 tool calls, or the PC part past about 40 of them: stop, commit, report what is left.

## Open questions
Settled by the conservative reading above; Liam can overrule in the review:
1. **Proxy in the play install?** The row says proxy kit plus packs; the movie-pack override needs no proxy, but the proxy gives the log and crash dump a bug report needs, at the cost of the known rare init crash.
   This brief includes it; an `--no-proxy` switch is a small follow-up if Liam prefers vanilla plus packs.
2. **Held-back files:** non-multiple-of-4 DXT and over-4096 outputs stay out of the play packs until a probe says the engine draws them. Say in the report how many files that is per role and whether `loading_screen` ends up empty.

## Finish
Write `jobs/J53/report.md`: what was built, the smoke-run evidence (job ids, run folder, shots, load times, snapshots), what Liam will and will not see, the exact install, uninstall and status commands, the held-back counts,
deviations from this brief and why, open questions. Then `wsc reg set jobs J53 status=review report=jobs/J53/report.md`.
