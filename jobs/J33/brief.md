# J33: Napoleon design language

Phase 5, the first step of UI foundation (D8, `docs/plans/UI_PIPELINE.md` section 2, step 2). Napoleon gets its own design language, not
Empire's re-themed. This job explores two or three directions in Claude Design on the same three test screens, with real data from the
atlas and real art from the contact sheets, and gets Liam to pick one. The exploration is free and cheap and is **never translated into the
build**: only the chosen direction's rules survive, written down so J34 can turn them into RCSS tokens and a component library.
L-heavy: the pick is Liam's, asked in this chat.

Model: Sonnet. No reverse engineering, no DLL, no game launch: it is design work on data the repo already holds (D15 default).
Budget about 250 tool calls; at the cap, stop, commit, report what is left. Subagents only for independent read-only work (for example
cropping art from the sheets while you build a page). Waiting belongs to the harness, not to polling calls: when you have asked Liam to
pick, end your turn with the question.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J33`). Read `docs/DECISIONS.md` (D5, D6, D7, D8, D9, D14, D19, D35, D39),
  `docs/plans/UI_PIPELINE.md` sections 1 to 3 and `docs/plans/PLAN.md` section 1.
- Read `jobs/J10/report.md` (proposal (c): the three test screens; the layout base and docking facts; the engine-drawn list) and
  `jobs/J7/report.md` (roles, art rules, what is committed and what stays under `/extract`).
- Data and art, all in the repo or the git-ignored extract (`discovery/README.md` says how to rebuild `/extract/napoleon/` if it is missing):
  - `registries/ui_elements.jsonl` rows `campaign.region_details`, `common.unit_information`, `battle.land_battle_orders`;
    `discovery/ui/{campaign,common,battle,template}.json.gz` (component trees, states, text and tooltip keys, art as `assets` ids, interactions),
    `discovery/ui/units.json.gz` (data fields and their sources), `discovery/ui/art_keys.json` (which db key names which art).
  - Strings and numbers: loc text and decoded db rows under `/extract/napoleon/` (`discovery/loc`, `discovery/db` explain the layout).
  - Art: the committed contact sheets `upscale/sheets/*.jpg` (the "after" sides, J36; D35 approved the look) and, for full size, the J36
    outputs and the extract on the PC converted to PNG or JPEG (the artifact host refuses `.tga` and `.dds`). Vanilla "before" references:
    `harness/runs/20261102_j10pc/shots/j10_land_running.jpg` (the orders bar, in a battle) and `j10_camp_settlement.jpg` (the campaign HUD);
    there is no live shot of `region_details` or `unit_information` (J10 could not reach them), so their layout comes from the atlas trees.
- Read-only anti-reference, `../empire-remastered` (never edit; D8 says do not re-theme it): `docs/ui/GOV_PANEL_STYLE.md`, `docs/ui/FONTS.md`
  and the tokens it points to. Read them to know what Empire chose and which of its mistakes to avoid (HTML-only effects that RmlUi cannot
  draw, tokens drifting from the build). Do not copy its palette, type scale, chrome or component names.

## Decisions already made for this job
- **The three test screens** (J10 proposal (c), one panel, one popup, one HUD piece): `campaign.region_details` (tabbed info panel, 94
  components), `common.unit_information` (popup, 138 components, includes an engine 3D preview shown as a render target), and
  `battle.land_battle_orders` (HUD piece: the round order buttons, the formations panel, five ability slots; 202 states). Every direction
  draws all three, from the same data, so the directions are comparable.
- **Directions:** three; two only if the kill criterion on time applies. They must differ on the five axes Liam is choosing between (below),
  not only in colour. Do not name a direction after a faction or an Empire board. Give each a plain working name and a one-line stance.
- **What each direction must make a choice on** (these become the written rules): palette (named roles, not just hues), type (families,
  sizes, weights, numerals), ornament (frames, dividers, corners, texture, light), density (row heights, padding, how much a panel shows at
  once), iconography (source and style of icons, the size grid, state colouring).
- **Buildable in RmlUi and RCSS (D6, D9) or it does not count.** A direction may not use what RmlUi cannot draw: backdrop blur, CSS
  blend modes, arbitrary SVG filters, text shadows beyond RmlUi's `text-shadow`, variable-font tricks. Chrome is made of RCSS borders,
  gradients, box shadows and 9-slice decorators; content art is the vanilla art (flags, unit cards, portraits, building and technology
  icons, event pictures, the round order buttons) at the J36 2.5x masters. Bespoke illustrated chrome art or a new icon set is allowed,
  but the direction must say so and the rules file must price it ("needs about N new sprites"), because new art is outside D14 unless Liam
  accepts it. Icons are PNG sprites or an icon font (the pinned viewer has no SVG).
- **Scale and size rules apply to the mock-ups** (D19): lengths in `dp`, 1 dp = 1 px at 1080p; the panels are drawn on a 1920x1080 frame at
  100 %; minimum text 14 dp; body text and its background meet contrast 4.5:1 and large text and icons 3:1 (compute the ratios, do not
  judge by eye). Show each direction once at 1080p x 100 % and once at the 4K x 125 % corner (2.5x the pixels, so the crispness claim is visible).
- **Fonts (D7):** open-licence families only, named with licence and source URL in each direction's rules (they go into `LICENSES.txt`
  in J38), and from Google Fonts so the artifact can load them. At most one direction may use Empire's Lora. Say which face you would give
  engine-drawn text (unit banners, map labels: `engine.*` rows, J37), because those follow the `.cuf` route and cannot use a variable font.
- **Real data, not lorem ipsum:** each screen is shown with at least three data cases that the contract stage will also need: a normal case,
  the longest names and largest numbers the db has, and an empty or negative case (empty building slot, zero upkeep, a debuff). Pick the
  cases from the db and loc; record the keys and ids you used in the rules file, never the text (see the data rule below).
- **States, not poses:** each direction shows, on the three screens, hover, pressed, disabled and selected on at least the buttons, a tab
  row and a list row, and focus-visible on one control.
- **A kit strip per direction** (one image): button (all states), tab, list row, tooltip, progress bar, card frame, divider, number badge.
  It is what Liam will judge and what J34 grows from; keep it to those eight.
- **Where it is shown:** Claude Design if this session has it. First call `Artifact` with `action: "quickstart"`, `intent: "design"` and
  `design_systems: false` (Napoleon has no design system yet and Empire's must not be attached; if the Design type insists on one, choose the
  most neutral and say so in the report). If the account lists no Design type, write plain HTML artifacts following the `artifact-design`
  skill and say so in the report. One private artifact with a page per direction is enough. Artifacts stay private: do not share the link
  outside Liam, do not delete anything, report the URL.
- **Scope (D14):** UI chrome and typography only. Not the 3D world, not the campaign map, not unit banners' behaviour, not a scale
  slider, not any screen but the three. No RCSS, no Lua, no viewer work: that is J34.

## Data rule (J7, unchanged)
Loc text and decoded db row values are never committed. Committed files carry loc keys, table and field names, ids and the numeric size of
cases (for example "longest unit name in `land_units`: key X, 31 characters"). The private artifacts and the preview images may show the
real strings, because a design needs real lengths; the HTML sources are not committed (the artifact is the source until the pick; the
rules file and previews are what stays).

## Deliverables
1. The review artifact: three directions (A, B, C), each with the three screens at 1080p x 100 %, the three at the 4K x 125 % corner (or one
   screen at that corner if the artifact limit forces it; say which), the data cases switchable or laid out side by side, and its kit strip.
   The page for each direction starts with its one-line stance. Also on the page: the vanilla "before" shots, so Liam sees what changes.
2. `design/napoleon/directions/a.md`, `b.md`, `c.md`, each at most 8 KB: stance; the five rules sections (palette as a token table with hex,
   role and the contrast ratio against its text pair; type scale in dp with family, weight, line height and the licence line; ornament with the
   RCSS decorator that builds each piece; density with the dp values; iconography); what each screen drops or changes from the vanilla
   element inventory, with a reason; cost in new art; the data cases by key and id; the faction question (below).
3. `design/napoleon/previews/`: for each direction the three screens, the corner view and the kit strip as JPEG or PNG, at most 3 MB in
   total, named `a_region_details_1080.jpg` style. They stay as the record of what Liam chose between.
4. **The pick.** When the artifact is up, ask Liam in this chat to play it and choose: one direction, or one direction with named swaps
   (for example "A's palette, C's type"). Allow one revision round if he asks for changes; a second request for changes is a different
   job. Do not set the job to `review` before he has answered. If you have asked and he has not answered, end your turn with the question.
5. On the pick: `design/napoleon/LANGUAGE.md` (at most 12 KB): the chosen rules, merged if he asked for a mix, complete enough for J34 to
   write tokens from it without reading the artifact (token table with hex and roles, type scale, ornament recipes, density table, icon
   grid), plus a "J34 handoff" section listing, per component the kit strip shows, its states and the RCSS technique. Also a
   `design/napoleon/tokens.draft.json` (names and values only, in dp and hex; J34 owns the final shape).
6. One decision row appended to `docs/DECISIONS.md`, `D<next number>`, who `Liam`, dated, with his pick in his own words and the path to
   `LANGUAGE.md`, reversible yes. Write it only from what he said in chat; do not infer a choice.
7. A short contrast check: a tested helper only if no existing tool does it (search the tools registry first: `python3 core/wsc.py find contrast`);
   otherwise a few lines in a throwaway script under `_scratch/`, with the ratios pasted into each directions file.

## The faction question
Napoleon has 53 factions with their own flags and colours. Each direction answers, in one line, whether the chrome tints by faction (flag
colour as an accent token) or stays neutral and only the flag and crest carry identity. This is a rule J34 needs; show it on the unit
information popup with two factions.

## PC test
None. No game launch, no watcher job, nothing written in a game folder (`needs_pc` is false). Reading the extract and the committed
shots is enough. The only person-in-the-loop step is the pick in deliverable 4.

## Kill criteria
- Claude Design and plain HTML artifacts both fail to publish after 3 attempts: stop, report the error, and propose another review
  surface (committed preview images and a local HTML file). Do not keep retrying.
- After about 150 tool calls there are not yet three directions with all three screens: cut to two directions (A and B), say so, and
  carry on with the pick.
- A direction needs something RmlUi cannot draw to look right: redesign it once; if it still does, drop that effect and say in its file
  what it cost. Do not ship a mock-up that cannot be built.
- Strings or numbers for a test case cannot be read from `/extract` or rebuilt after 2 attempts: use the atlas keys and mark that case
  "placeholder text" on the page, and list it in the report as an open question.
- Liam asks for a second revision round, or a fourth direction: stop and report; that is a new brief.

## Finish
Write `jobs/J33/report.md`: what exists (artifact URL, route used, files), the pick and the decision row, how each direction differed,
the contrast numbers, what you left out and why, deviations from this brief and why, what moves to the core later (nothing expected),
open questions (the faction rule if Liam left it open, any case marked placeholder, and anything J34 must settle). Run
`python3 core/wsc.py jobs check` and `python3 core/wsc.py gates` before pushing. Then
`wsc reg set jobs J33 status=review report=jobs/J33/report.md`.
