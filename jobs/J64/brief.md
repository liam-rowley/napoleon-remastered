# J64: Phase 2 promotion: discovery/core to warscape-core

Phase 2, the promotion job (`docs/plans/PLAN.md` section 4, rules ledger row 76). The game-agnostic discovery code built in phase 2 under
`discovery/core/` moves to `liam-rowley/warscape-core` and comes back as the next core tag (v0.9.0 unless J62's core release is cut first).
Napoleon keeps its adapter (`discovery/napoleon/`), every committed result (`discovery/<area>/`, the registries) and the wiring. The move changes
no result: every committed discovery output must come out byte for byte the same from the moved tools. Merging this job closes the `discovery/core`
row of the rule 76 table; `uiscale/core`, `upscale/core` and `viewer/core` keep their own rows (J63 and later) and now import the core's discovery
modules.

Model: Sonnet, medium effort (D15). Python, Markdown and JSON only: no DLL work (rule 79 does not apply: no DLL input changes), no game launch, no
watcher, no game lock. Budget about 320 tool calls; at the cap, stop, commit, push both repos, report what is left. No subagents. Waiting belongs to
the harness: nothing here polls CI or a merge.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J64`; "Never change files inside `core/`"; "Reuse before you write"). Read `docs/DECISIONS.md` (D2, D10, D14, D29,
  D30, D32, D38 to D42) and `docs/plans/PLAN.md` section 4 (promotion) and phase 2.
- The precedent is `jobs/J12/brief.md` and `jobs/J12/report.md` (read "Path wiring and the game-name lint", "Part 2", "Deviations"): same shape, same
  proof of a pure move. J12 was Opus because of DLL fixes; this move has none, so it is Sonnet.
- Read the core side: `core/CLAUDE.md`, `core/docs/CONSUMING.md` (upgrade steps, "The proxy, the harness and the save tools"), `core/docs/DECISIONS.md`
  (C2, C8, C13, C14), `core/docs/BACKLOG.md` (B1, B17, B35), `core/proxy/tools/layout.py` (how a core tool finds the game) and
  `core/tests/test_moved_tools.py` (the game-name lint). Core changes are made in a `warscape-core` clone beside this one
  (`/c/Users/liamr/repos/warscape-core`, `git pull` first), on the branch `napoleon-j64`. Never edit inside `core/` here.
- Read the reports that say what moves and what stays: `jobs/J11/report.md` (open question 5: `briefpaths.py` and `gate.py` go with the folder, the
  `LEGACY_BRIEFS` pattern and the `jobs check` hook go with the pipeline in J62), `jobs/J12/report.md` ("Deviations": `build_fixed_sky_pack.py` and
  `exe_info.py` waited for this job), `jobs/J6/report.md`, `jobs/J7/report.md`, `jobs/J10/report.md` ("What moves to the core later").
- Look things up with `python3 core/wsc.py find <words>`. Tools rows you will move (ids): `wsc.discovery`, `proxy.tools.exe_info`, and every
  `discovery.core.*` row (31: `discovery.core.assets`, `.sheets`, `.layouts`, `.fonts`, `.packs`, `.packfs`, `.lua_api`, `.shaders`, `.exe`, `.uic`,
  `.tpl`, `.cuf`, `.ui_atlas`, `.x86re`, `.re_env`, `.gate`, `.briefpaths` and the rest). Stay-behind tool: `proxy.tools.build_fixed_sky_pack`.
  Facts that bear on the move: `napoleon.assets.index`, `napoleon.files.loose_override` (open; the packfs `loose_wins` parameter stays a parameter).
- **Other work on the same files (check `git branch -r` at the start and again just before the move):**
  - **J65** (queued; edits `discovery/core/ui_atlas.py` and `tests/test_discovery_ui.py`) is a dependency of this job: it must be `done` first, so the move
    carries its fix. If it is not, stop and report; do not carry its change.
  - **J62** (job pipeline promotion, being briefed in parallel) owns `tools/verbs/jobs.py`, `tools/pr_policy.py`, `tools/claude_hook.py`, the CI
    notifier, `docs/REVIEW.md`, `tests/test_jobs.py`, `tests/test_pr_policy.py` and the workflows. This job touches only: the `discovery/core` line of
    `PROMOTIONS` in `tools/verbs/jobs.py` (set to `J64`), the two lines in `jobs.py` that load `briefpaths` (they point at `core/discovery`), and
    `tests/test_jobs.py` not at all. If J62 merged first, those lines are in the core's copy and the core PR adjusts them there; if this job merges
    first, J62 inherits `briefpaths` in `core/discovery`. Also expect both core PRs to want the same next version, `VERSION` line and `C<n>` and `D<n>`
    number: the second to merge takes the next free number and rebases; the pin bump then names the tag that holds both.
  - Queued jobs whose briefs cite `discovery/core/...` paths (J24, J27, J37; and the done J66's code): they are not edited (merged history). The
    tools rows keep their ids in the core (`wsc find` shows the new path), and the "Where things moved" table in `discovery/README.md` (deliverable 7)
    maps old paths to new. A job branch still open on `discovery/core` at the move is not carried: it merges `main` and repoints.

## Target facts
Check them yourself with the commands named; record any change in the report.
- Core pinned in `wsc.toml` `[core] version`: `v0.8.0` (`git -C core describe --tags`). Core tags on the remote: `gh api repos/liam-rowley/warscape-core/tags`.
- `discovery/core/` holds 31 modules, about 7,250 lines (`wc -l discovery/core/*.py`). All carry a header and a row (`discovery.core.*`), none is a verb.
  The verb `discovery` lives in `tools/verbs/discovery.py` (`wsc.discovery`), 226 lines.
- Game names in the code: 28 of the 31 modules say `napoleon` or `empire` (`grep -ic napoleon discovery/core/*.py`): `GAME = 'napoleon'`, the diff row
  fields `empire` and `napoleon` in `diffout.py`, the pass defaults `discovery/napoleon/...`, `REPO` found as two folders above the file, and prose
  in the generated rows (`ui_atlas.py` `STATIC_ONLY`, art rules). The core's lint (`core/tests/test_moved_tools.py` `NoGameNames`) covers `proxy/`,
  `harness/` and `saves/` today and would fail on all of it.
- Importers of the folder outside it (each must be repointed): `tools/verbs/hotkeys.py` (packfs, loc), `tools/verbs/jobs.py` (briefpaths),
  `proxy/tools/build_fixed_sky_pack.py` (packfs, db), `uiscale/core/cuf_encode.py` and `uiscale/core/scale.py` (cuf, tpl, uic, packfs),
  `uiscale/napoleon/cli.py`, `upscale/napoleon/cli.py`, and the tests `tests/test_mod_packs.py`, `tests/test_play_pack.py`, `tests/test_uiscale.py`,
  `tests/test_uiscale_fonts.py`, `tests/test_upscale.py`. Frozen run scripts under `harness/runs/**/re/` also import it: history, not repointed.
- `discovery/core/exe.py` imports `parse_pe`, `imports` and `rva_to_off` from `proxy/tools/exe_info.py` (a Napoleon file: the dependency points the
  wrong way once `exe.py` is in the core).
- The tests for the folder: `tests/test_discovery.py` (13), `test_discovery_assets.py` (22), `test_discovery_gate.py` (45), `test_discovery_lua.py` (6),
  `test_discovery_ui.py` (16), `test_engine_api.py` (8), `test_exe_strings.py` (3), `test_x86re.py` (4, skipped without capstone). Run
  `python3 core/wsc.py gates` first and keep the green baseline (counts, skips, the 11 ok / 1 warn from J11's report) to compare with at the end.
- Dependencies today: Pillow 13.0.0 (`discovery/requirements.txt`, sheets only), capstone 5.0.6 and pefile 2024.8.26 in the RE venv made by
  `discovery/core/re_env.py` (wheel sha256 pins in the file). Everything else is the standard library (C2).
- Outputs that must not change a byte: everything under `discovery/` except `discovery/core/`; `registries/assets.jsonl`, `registries/ui_elements.jsonl`;
  the generated READMEs. Record their sha256 list **before** you touch anything (`_scratch/j64/before.sha256`, git-ignored) so the proof is a diff.

## Decisions already made for this job
Settled by the conservative reading of the row and of J12; Liam can overrule in the review.
- **The whole folder moves** (rule 76 fails while any `discovery/core/*` file remains once this job is `done`). The row names the passes and tools
  explicitly; the rest follows because the same reasons hold: `db`, `loc`, `ron2json`, `console_cmds`, `packfs`, `imagehdr`, `tsvgz`, `ui_atlas`, `ui_walk`,
  `re_env`, and J11's `gate` and `briefpaths`. Per-game parts stay: `discovery/napoleon/*` (games.json, carry_over.json, gate.json, asset_roles.json,
  db_schema.json, console.json, engine_api.json, probe_safe.json, exe_strings.tsv.gz, shader_catalog.json, shaders/, the two notes) and every
  `napoleon.*` output.
- **Where it lands:** `discovery/` in warscape-core, the modules flat as in `proxy/src` (`core/discovery/x86re.py`), with `discovery/tests/` for
  the host tests and a short `discovery/README.md`. `exe_info.py` goes to `proxy/tools/exe_info.py` in the core (it already sits with the other
  generic PE and pack tools); its two Napoleon defaults (`--identity`, `--def`) come from `layout.py` instead. Tools rows: `wsc reg add tools <new path>
  --id <the old id>` in the core (ids are cited by briefs; they keep `discovery.core.` although the path does not), then the Napoleon rows removed, not
  superseded (J12's finding: the tools gate only takes a superseded target in the same registry).
- **How a core tool finds the game (C14 again):** `layout.py` gains `discovery_adapter()`; `wsc.toml` gets `[discovery] adapter = "discovery/napoleon"`
  (repo-relative folder holding `games.json` and the other inputs); the committed results stay where they are (`discovery/<area>/` in the game repo, next to
  the adapter folder). Core 0.4.0 added `[proxy]` and `[harness]` the same way, so `warscape/repo.py` `DEFAULTS` takes one more table; Napoleon's
  `wsc.toml` sets it at the same commit as the pin bump (the pinned core refuses unknown keys, which is why the bump and the key are one commit). No module
  finds the game by its own location (`REPO = ..`, `HERE/../napoleon`); they take the game root and the adapter from `layout.py`, with `--games`
  and `--out` flags still overriding.
- **Game names leave the code.** `games.json` gains `"target": "napoleon"` and `"reference": "empire"` (names are data); `diffout.py` builds its row
  fields from them, so the committed diff files keep the same field names and bytes. Tool behaviour that is really Napoleon's data (the `STATIC_ONLY` reasons,
  art rules and similar prose in `ui_atlas.py`, the probe-safe naming rule, `console_cmds` profile) moves to adapter JSON in `discovery/napoleon/` that the
  tool reads. The core's `NoGameNames` lint is extended to `discovery/`. Fallback (kill criterion 2): a module that cannot be made name-free within the
  budget gets a named, reasoned allowlist entry in that test plus a core backlog row; the lint never gets a blanket exemption.
- **The verb moves too.** `wsc discovery` (check, render, gate, the passes) becomes a core verb (`warscape/verbs/discovery.py`) driven by `[discovery]
  adapter`; Napoleon's `tools/verbs/discovery.py` is deleted in the pin-bump commit (a game verb of the same name is a load error). What is Napoleon's
  stays in the adapter: floors, ratchet and `config_key_owners` (gate.json), `carry_over.json`, the context names. B1 (game gates) is not needed: the
  gate is still reached by `wsc discovery gate` and by the `tests` gate through the thin real-repo test below.
- **Optional dependencies (C2 and C13 stand).** The core PR proposes a `C<n>` line (Liam's merge accepts it): discovery passes that need Pillow (`sheets`)
  or the RE environment (capstone, pefile: `x86re`, `console_cmds`, `exe_strings build`) are PC-side tools; the dependency is checked before first use
  with a message naming the fix, and no gate or host test imports it without a skip. The pins move with the code: `discovery/requirements.txt` (Pillow)
  and `re_env.py` (wheel sha256 pins) in the core, documented in a `CONSUMING.md` section "Discovery (optional extras)"; Napoleon's copy of the
  requirements file is deleted and the places that name it are fixed.
- **Tests split.** The unit tests that need no game data move to `discovery/tests/` in the core and run in its `tests` gate (add the folder to the core's
  `wsc.toml` `[tests] dirs`; the capstone tests keep their skip). The tests that run against Napoleon's real registries and committed results stay here as
  one thin file `tests/test_discovery_repo.py`: `discovery check` and `discovery gate` pass on this repo, every committed brief passes or is legacy, the engine
  API / probe-safe / exe-strings / shader-catalog tables are current. `tests/test_mod_packs.py` and the uiscale and upscale tests stay and are repointed.
- **`build_fixed_sky_pack.py` stays whole in Napoleon** (its junction and pack names are Napoleon's); it is repointed to `core/discovery`. Whether its
  generic table codec moves later is a question for the report, not this job.
- **Rule 76 as code:** `PROMOTIONS['discovery/core']` is `J64` (it said `None`, no row yet). Once this job is `done` the folder must be gone, and is.

## Deliverables
1. **Baseline first (Napoleon, `job/J64`).** `git pull`; `python3 core/wsc.py gates` green; write `_scratch/j64/before.sha256` for the outputs listed in
   Target facts and note the test counts. Confirm J65 is `done`.
2. **Parameterise before the move**, each change a host test and no output byte moved (compare to the baseline after each step): the game root and adapter from
   a `layout.py`-style resolver (a local stand-in in `discovery/core/` until the move, so the diff of the move stays pure), `target` and `reference`
   names from `games.json`, adapter JSON for the Napoleon rules, the PE helpers' import. Run the extended lint against the files in place
   (`NoGameNames` regex over `discovery/core/`) so the move commit changes only where files live.
3. **The core PR** (`warscape-core`, branch `napoleon-j64`): the moved modules and tests, `exe_info.py` in `proxy/tools`, `layout.py` `discovery_adapter()`, the
   `[discovery]` table in `warscape/repo.py` `DEFAULTS` (with a test that an unknown key is still refused and the new one is accepted), the `discovery` verb,
   the core CI covering `discovery/tests/` on Linux and Windows, the extended lint, tools rows with the old ids, the `C<n>` line, a `CONSUMING.md` section
   (adapter files a game provides; the optional extras; the re-run steps), backlog rows for anything left (B-items), `VERSION`. Gates and every moved host
   test green in the core's CI. **Liam merges and tags the core** (core `CLAUDE.md`): open the PR, ask Liam to merge it and tag the version, then stop and end
   the turn. Do not wait or poll. Resume when Liam says it is tagged.
4. **The Napoleon switch** (after the tag), one commit for the pin: `core` gitlink, `wsc.toml` `[core] version` and `[discovery] adapter`, the deletion of
   `discovery/core/`, `discovery/requirements.txt` and `tools/verbs/discovery.py`, `PROMOTIONS`, the repointed importers (Target facts) and tests, the
   removed tools rows (31 `discovery.core.*`, `wsc.discovery`, `proxy.tools.exe_info`; check the tools gate afterwards), and `tests/test_discovery_repo.py`.
5. **Proof of a pure move** (state each result in the report):
   - every file in `before.sha256` equal after the switch (`sha256sum -c`), and `python3 core/wsc.py discovery render` followed by `git status` shows no change;
   - `discovery check` and `discovery gate` ok (same lines and findings as before; the ratchet figures in `discovery/napoleon/gate.json` unchanged);
   - the `--check` modes that need only committed files: `engine_api.py build --check`, `engine_api.py probe-safe --check`, `shader_catalog.py build --check`;
   - the passes that read the game (`assets`, `db`, `loc`, `sheets`, `packs`, `layouts`, `fonts`, `lua_api`, `shaders`, `exe`, `ui`, and `exe_strings.py build --check`): when
     the install and the extract store are on this machine, re-run them read-only (no launch, no watcher; nothing is written in a game folder, and never run git
     there) and show `git status` clean for `discovery/` and the registries; when they are not, say so and prove them by their host tests through the moved code;
     the first PC sitting then runs `python3 core/wsc.py discovery all` and `git diff --stat` must be empty (written into the report as the follow-up);
   - `python3 core/wsc.py gates` green in this repo and `python3 wsc.py gates` in the core, test counts compared with the baseline (the moved tests plus the
     thin file add up to the old total, nothing silently dropped);
   - `python3 core/wsc.py jobs check` ok (0 registry gaps) and `python3 tools/pr_policy.py --branch job/J64 --base origin/main` shows only the reviewer's part.
6. **Living copies fixed:** `grep -rn "discovery/core"` over `CLAUDE.md`, `README.md`, `docs/`, `discovery/README.md`, `uiscale/`, `upscale/`, `viewer/`, `perf/`,
   `proxy/README.md`, `harness/README.md` and the tool headers; the `CLAUDE.md` bullet "Since J12 the core carries ..." gets the discovery sentence; PLAN
   section 4's promotion note says phase 2 was J64. Merged history (briefs, reports, reviews, run folders) is left alone.
7. **"Where things moved"** table (old path, new path) at the top of `discovery/README.md`, and a one-line `D<n>` in `docs/DECISIONS.md` (append only):
   discovery lives in the core, found through `[discovery] adapter`; the optional extras; the lint extension.

## Out of scope
- New discovery passes, new registry rows or changes to any committed result. If the move would change one, that is a kill criterion, not a fix.
- Moving the job pipeline, `upscale/core`, `viewer/core`, `uiscale/core` (J62, J63 and later rows), editing `empire-remastered`, or any DLL, harness or game change.
- A game-gates mechanism in the core (B1) and moving `LEGACY_BRIEFS` or the `jobs check` hook (J62).

## Kill criteria
- Any committed output differs from the baseline after the move and two attempts to find the cause: stop, report the diff and the first diverging step; do
  not regenerate and commit a "new" output to make the proof pass.
- Making a module name-free costs more than about 40 calls or changes an output byte after two attempts: stop on that module, use the named allowlist entry
  (Decisions), report it; do not widen the lint exemption.
- The core CI is red after three fix attempts, or the core needs a design change beyond a `[discovery]` config table and `layout.py` function (for example
  B1): stop before the tag and report the proposal.
- J65 is not `done` when you start, or another job branch changes `discovery/core` between your baseline and the move in a way a merge of `main` cannot
  carry: stop and report which.
- The sha256 baseline cannot be taken (no outputs on this machine): stop; the proof has nothing to compare with.

## Finish
Write `jobs/J64/report.md`. Cover:
- what moved, as a table of old path and core path, and what stayed (adapter files, outputs, wiring);
- the core PR and the tag, the `C<n>` and `D<n>` numbers, and the extended lint (and any allowlist entry with its reason);
- the proof of a pure move: the `sha256sum -c` result, the test counts before and after, which passes were re-run read-only and which were proved by
  host tests only (the PC follow-up), the `discovery check` and `discovery gate` output;
- deviations from this brief and why, open job branches left on old paths and what each needs, and the interplay with J62 (what it inherits);
- open questions, with a recommendation each. Already settled here as recommended, unless Liam overrules: the whole folder moves, `exe_info.py` moves,
  the verb moves, tests split core/thin file, `build_fixed_sky_pack.py` stays, tools rows keep their ids, `needs_pc` stays false (the read-only re-runs
  are a bonus where the install is present, not a requirement).

Then `wsc reg set jobs J64 status=review report=jobs/J64/report.md`.
