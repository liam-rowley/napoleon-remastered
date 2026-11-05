# J69: Component library from vanilla, with Liam

Phase 5, foundation (`docs/plans/UI_PIPELINE.md` section 2.2, D55). Liam deferred this on 2026-11-02 ("We will need to come back to the
component board and spend a lot of time refining the style but we can defer it for now") and asked for it on 2026-11-04 in the vanilla-first
form: "To build the component library I need to see vanilla screens and iterate over them. I can't come up with components from scratch."
A series of Liam-present sittings walks J99's vanilla components in use order. For each kind, Liam decides what the Engraved Plate version
keeps from vanilla (size, proportion, states, ornament, density). The library changes to match, gains the vanilla kinds it lacks, and is
republished every round, until Liam locks the board. This job changes tokens and library components only: no screens, no panel host, no
in-game work, no change to the language itself (D43).

Model: Opus, reason: D52 (Opus for builds; Sonnet for its reviews). Budget about 120 tool calls per sitting
and about 600 in all; at a cap, stop, commit, report what is left. Waiting belongs to the harness: one background call per wasm build or render
batch, never repeated polling.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J69`; one branch for the whole series, pushed after every sitting). Read `docs/DECISIONS.md` (D8, D9,
  D14, D19, D43, D55) and `docs/plans/UI_PIPELINE.md` sections 2.2, 2.5 and 3 ("Library and token changes").
- `design/napoleon/LANGUAGE.md` is binding for anything this job does not ask Liam about. `uikit/napoleon/README.md` (the screen author's
  contract, lint rules, gate, change detector), `jobs/J34/report.md` (its open questions are yours, below), `viewer/README.md`.
- J99's page and `uikit/napoleon/vanilla/components.json`: the vanilla kinds, their states and screens, and the proposed `library` mapping
  you confirm or correct with Liam. `jobs/J99/report.md` for its URL and counts.
- The board: `viewer/napoleon/board/` and its private artifact (URL in `jobs/J34/report.md`). Republish to the same URL each round.
- Read-only anti-reference, `../empire-remastered` `rml_mod/docs/UI_PERF.md` and `rml_mod/docs/PANEL_GUIDE.md` "RmlUi gotchas" (the J34
  brief's two binding findings still bind). Do not copy Empire's tokens, names or chrome (D8).

## Decisions already made for this job
- **A sitting is Liam-present.** Liam answers in chat or by comments on the board or J99's page (read them with `ArtifactComments`, answer
  every one). Style choices are his: when he is not present, prepare the next group (twins rendered, the short questions written) and stop;
  never choose a look on his behalf.
- **Sitting order (default; Liam may reorder):**
  1. Frames and plates: the 9-slice frame groups, the panel plate and header band, dialogue box, tooltip.
  2. Lists: list, listview, list header, sortable list, list rows, the scrollbar (vslider and handle).
  3. Controls: text and round icon buttons, close button, tab and tab group, button group, checkbox, dropdown menu, slider, text and
     numerical input.
  4. Content: campaign character card and unit cards (frame and art slot only), heading, textview, flag slot (size from vanilla
     `template.faction_flag_small`), ranking and progress bars, number badge.
  5. Whole board: faction tint across factions, density, the J34 open questions below, then the lock.
- **Per kind, the same loop.** Show vanilla (J99 Components view) beside the current library twin. Ask at most three short questions, each
  with a default (for example: keep vanilla's size? keep its state set? which ornament?). Change `uikit/napoleon/tokens.json` and
  `src/*.rcss`, add the kind if it is a `gap`, update its `components.json` mapping, rebuild (`build.py`), keep `lint.py`, `gate.py` at the
  four D19 corners and the tests green, re-render the board and J99's library twins, republish both, and ask Liam to look. Repeat until he
  moves on.
- **The library may grow to vanilla's reusable set.** J34's "nothing beyond this" limit is lifted for kinds in `components.json`; a kind not
  there still waits for the screen that needs it. Every new class has its state twins (`.is-hover`, `.is-pressed`, `.is-focus`,
  `.is-selected`, `.is-disabled`) and a place on the board.
- **Vanilla art as content** (LANGUAGE.md: vanilla colour art kept as content) may be used in art slots through the J36/J51 masters. New art
  (sprites, J34's 24) needs Liam's acceptance in the sitting under D14; record his answer.
- **What a sitting leaves.** Code first: tokens, library, board, mapping. Then one `uikit/napoleon/runs/<YYYYMMDD>_j69_s<n>/README.md` with
  the kinds covered, Liam's choices in a line each (quote him where he gave a rule), the board artifact version, and what is next.
  `changes.py` reports which screens moved after each change (none are locked yet).
- **The lock.** When Liam says the board is locked, write `uikit/napoleon/LOCK.json` (`{"locked": ["board"]}` plus the date and the
  sitting), accept the baseline with `changes.py --accept --allow-locked`, and finish.

## Order of work
1. Before sitting 1: confirm J99's page and the board render from `main`; prepare group 1 (twins, questions). Tell Liam it is ready.
2. Sittings 1 to 5 as above, one commit and push per kind, one run README per sitting.
3. After the lock: full `wsc gates`, report.

## Deliverables
1. The library, tokens and board as Liam left them, lint and gate clean, tests green.
2. `uikit/napoleon/LOCK.json` if Liam locked the board; otherwise a report that says which groups remain.
3. `uikit/napoleon/vanilla/components.json` with every mapping confirmed or corrected (no `uncertain` left for a covered kind).
4. Run READMEs per sitting; the board and J99 artifacts republished at their URLs.

## Kill criteria
- Liam asks for a change to the language itself (D43: palette roles, the faction tint rule, the type families, the ornament vocabulary), not a
  token value: stop that change, write a proposed decision row in the report for a `plan/` branch, and carry on with other kinds.
- A recipe Liam wants cannot be drawn by RmlUi 6.3 after 2 attempts: record the engine fact, offer the nearest recipe, move on.
- The wasm build or a render fails 3 times for a cause you did not introduce: stop, report the exact failure; do not retry.
- At about 600 tool calls, or when Liam ends the series without a lock: stop, commit, report which groups remain.

## Open questions
Written here so the builder does not stall; each has a default, is asked in sitting 5 unless Liam raises it earlier, and goes in the report
if it still stands. All are carried from `jobs/J34/report.md`.
- **Blurred plate shadow** (LANGUAGE.md asks for one; the viewer paints it black, `viewer.rcss.shadow_needs_background`). Default: keep the
  hard shadow until J32 shows what the game's host draws.
- **The 24 new sprites and 4 missing order-button states.** Default: vanilla art in the slots where a vanilla twin exists; new sprites only if
  Liam accepts them.
- **Flag slot size.** Default: vanilla `template.faction_flag_small`'s size from the atlas.
- **Rebel factions tint** by the same rule. Default: yes.
- **Does the board get a `ui_elements` row?** Default: no; `LOCK.json` is the record.

## Finish
Write `jobs/J69/report.md`: what changed (tokens, classes added, mappings), Liam's choices per sitting with the run READMEs, the lock (or the
groups left), artifact URLs and versions, deviations from this brief and why, and the open questions that still stand. Run
`python3 core/wsc.py jobs check` and `python3 core/wsc.py gates` before pushing. Then
`wsc reg set jobs J69 status=review report=jobs/J69/report.md`.
