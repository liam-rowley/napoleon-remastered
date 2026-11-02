# J11: Discovery gate

Phase 2, the gate (`docs/plans/PLAN.md` phase 2: "every registry populated and current; briefs cite registry ids, never paths found by searching").
J6 to J10 are done and their results are committed; this job turns the gate sentence into code, so that a stale or half-empty registry and a brief
that quotes a path somebody searched for both fail CI instead of relying on a reader. It also covers J5 rules ledger row 80 ("Briefs cite registry
ids, never searched paths"), which `wsc jobs next --id J11` names as owed to this job. Nothing about the game, the PC or the registries' contents
changes here; only checks, their tests and the wiring are added. After this job `discovery/core` can be promoted (J64).

Model: Sonnet, medium effort (D15). Python in this repo only: no DLL work, no change to `core/`, `proxy/` or `harness/` (so rule 79 does not apply),
no PC and no game launch (the row says `needs_pc: false`). Budget about 150 tool calls; at the cap, stop, commit, report what is left. Subagents are
not needed. Waiting belongs to the harness: nothing here launches anything, and nothing polls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J11`; "Never change files inside `core/`"; "Reuse before you write"). Read `docs/DECISIONS.md` (D4, D14, D21, D29, D38,
  D39, D40), `docs/plans/PLAN.md` section 3 (what each registry carries) and phase 2, and the reports of the five jobs this gate checks: `jobs/J6/report.md`,
  `jobs/J7/report.md`, `jobs/J8/report.md`, `jobs/J9/report.md`, `jobs/J10/report.md` (their "Open questions" and "What moves to the core later").
- Cite registry ids when you read, in your own notes and in the report, the way the new rule demands (this brief does so itself). Look things up with
  `python3 core/wsc.py find <words>`; do not search the pack extract on the PC to find a name. The ids you need:
  - tools: `wsc.discovery` (the verb you extend), `wsc.jobs` (the verb whose `check` holds the brief shape), `wsc.hotkeys`, `tools.pr_policy`,
    `discovery.core.assets`, `discovery.core.ui_atlas`, `discovery.core.engine_api`, `discovery.core.exe_strings`, `discovery.core.tsvgz`,
    `proxy.tools.gen_tables` (the engine-sites table generator and its `--check`), `proxy.tools.build_id`.
  - engine_facts that bear on "current": `napoleon.assets.index`, `napoleon.assets.pack_order`, `napoleon.assets.ui_first`, `napoleon.ui.layout_base`,
    `napoleon.diff.layouts.versions`, `napoleon.diff.packs.format`, `napoleon.files.loose_override` (open: a pack entry versus a loose file),
    `napoleon.proxy.init_heap_corruption`.
  - jobs: J5 (the rules ledger; row 80 is yours, `jobs/J5/rules.md`), J6 to J10 (the inputs), J12 (`discovery/core` is listed in its promotion table as waiting
    for this job), J64 (promotes `discovery/core` after this job and takes the code you write with it).
- Existing machinery to extend, not duplicate: `wsc discovery check` (`tools/verbs/discovery.py`: `_load`, `readmes`, `j7_problems`, `ui_problems`),
  `wsc jobs check` (`tools/verbs/jobs.py`: `brief_problems`, `LEGACY_REVIEWS` as the precedent for a frozen exemption set), `wsc hotkeys check`,
  `wsc reg check`, `wsc gates` (`tests` gate runs the host tests, which is how a game-side check reaches CI until core backlog B1 lands:
  see how `tests/test_jobs.py` runs `jobs check` on the real queue), `tools/pr_policy.py` (the `brief/` kind may only touch the brief and its row).
- Evidence base `empire-remastered` has no equivalent gate (its phase gates were prose); there is nothing to port. It stays untouched.

## Target facts
Check them again yourself with the commands named; record any change as `engine_facts` rows (date and run id; a CI run id or a commit sha for a result
that needs no game).
- Registries and their row counts on main when this brief was written (2026-11-02): `assets` 12,295, `ui_elements` 262 (248 screens, widgets and templates
  plus 14 `engine.*`, all at `atlas`), `engine_sites` 57, `hotkeys` 128, `config_keys` 38, `scenarios` 10, `tools` 94, `engine_facts` 186 (161 verified, 23 open,
  2 refuted), `jobs` 67. `python3 core/wsc.py reg check` and `python3 core/wsc.py discovery check` are green on that main.
- A `assets` row's `id` is its pack path in forward-slash form (the row's `path` keeps the backslash form the engine and the index use). So for an asset the id and
  the searched path look alike; the rule below has to tell a registry id from the same string found some other way (see Decisions, "What counts as a found path").
- A `ui_elements` row is a pipeline unit (J10): its id is `<context>.<name>`; the layout and script paths live only in `vanilla_source`. A brief that names a
  layout or compiled-script path instead of the unit id is the main case the rule exists for.
- Gaps the gate must say out loud, not hide: 23 `open` engine facts (19 name a job in their text, 4 do not: `napoleon.campaign.camera_route`,
  `napoleon.campaign.quit_to_menu`, `napoleon.harness.kill_slow_once`, `napoleon.steam.installscript_vdf_mtime`); `ui_elements` has 3,711 unresolved data fields
  (counted in `discovery/ui/summary.json`, not in the rows) and 106 scripts named but not shipped; `assets` has 10,500 rows with no string reference;
  `napoleon.files.loose_override` is open. None of these makes a registry "not populated": they are the report's table of what the next jobs inherit.
- Which briefs exist: 48 briefs are on main (jobs with `queued`, `review` or `done`); 19 rows are `needs_brief`. Their text has legitimate mentions of pack
  names (`data.pack`), fx file names and the like (Empire notes, evidence), and a few quote game paths directly (J7 and J10 name the extract store). The rule must
  not turn all of that red on day one: see "Legacy set".

## Decisions already made for this job
Settled by the conservative reading of the row and D14; Liam can overrule in the review.
- **Two checks, one verb.** `wsc discovery gate` (new action in `tools/verbs/discovery.py`; the logic in a new `discovery/core/gate.py`, a core candidate that
  travels with `discovery/core` in J64) checks that every registry is populated and current. The brief rule is a pure function `found_path_problems(text, known)` in a
  new `discovery/core/briefpaths.py`, called from `brief_problems` in `tools/verbs/jobs.py`, so it runs wherever `wsc jobs check` runs (the `tests` gate in CI,
  and the writer's own run before pushing a brief). `wsc discovery check` calls the gate too, so there is one command to run after a discovery pass.
  The gate prints one line per registry (rows, floor, which currency checks ran) and one line per failure, and exits 1 on any failure.
- **"Populated" is a floor, written down.** `discovery/napoleon/gate.json` (new, hand-edited, reviewed like code) holds a minimum row count per registry, set
  at the counts in Target facts (a little below, so a normal clean-up does not trip it; state the numbers) and, for `ui_elements`, a minimum per context
  (`battle`, `campaign`, `common`, `frontend`, `template`, `engine`). A floor only moves in a commit that says why. A registry below its floor, or an empty
  context, fails. Also required: `ui_elements` rows all at `atlas` or later; every non-`engine` row has a layout or a script in `vanilla_source` and at least one
  interaction entry (`none: display only` counts); every `engine.*` row starts its description with `route:` (D39); every `engine_sites` row carries a
  `verified` date and run, and the `exe` it names is the pinned identity (a row for another exe is stale by definition); every `config_keys` row's `owner`
  resolves to a jobs row id or `liam`; every `scenarios` row has a launch recipe; every `open` engine fact names a jobs row or `liam` in its text (the four above
  fail until they do: add the job or `liam` to their notes with `wsc reg set`, which is a small data fix in this job, not a change to what they claim).
- **"Current" is a recomputation, not a date.** The gate re-runs, offline and from committed inputs only, the checks that already exist and refuses to trust a
  green someone else saw: `wsc reg check`; the `assets` registry equals what `discovery/assets/index.tsv.gz`, `refs.json` and the roles file give
  (`j7_problems` today); the `ui_elements` rows and the atlas files equal their recorded sha256 (`ui_problems` today); `engine_sites` equals the generated table
  (`proxy.tools.gen_tables --check`); `hotkeys check`; the committed READMEs are current (`readmes`); every `tools` row's path exists and every file under
  `discovery/core` has a row (the `tools` gate already does both: call it, do not copy it). Add two new currency facts that no check has today and that the
  phase-2 sentence needs: (1) the pack fingerprints the index was built from (each pack's size and the `pack_order`) are recorded in
  `discovery/assets/summary.json`, and `wsc discovery gate --install` compares them with the installed game's packs and the exe sha1 with the pinned identity
  (read-only; needs the game folder, so it is the PC mode: CI and agents without the install run the offline mode, which says "install not compared" as a
  warning and never as ok); (2) a registry or atlas result built from an older index than the one committed (a row cites an index sha that is not the committed
  one) fails offline. If (2) needs a field the registries do not have, record it in `discovery/napoleon/gate.json` (index sha256 and build date) instead of
  adding a schema field: `core/` cannot change here.
- **Findings go in as warnings with owners, not as red.** The "Gaps" in Target facts are printed by the gate as a table (registry, gap, count, owner job) and
  written to `discovery/gate/summary.json` (deterministic, sorted, no timestamps, committed, checked by `discovery check` like the other results). They never fail
  the gate; a gap that grows past the number recorded in `gate.json` does (ratchet: it may only shrink, and the file moves down in the commit that fixes some).
- **What counts as a found path (the row 80 rule).** A brief may name a game-side path only as a registry id. In a brief the checker looks at every backticked
  token and every bare token that contains a path separator, and flags it when:
  1. it starts with the extract store (`/extract/napoleon/` or the `extract/napoleon/` form; the store is derived, uncommitted and PC-only: never a citation), or
  2. it contains a backslash and its first segment is a top-level game folder in the committed asset index (the pack form of a path), or
  3. its first segment is a top-level game folder in the asset index and it is not exactly an `assets` row id, a `ui_elements` id or a file tracked in this
     repo (`git ls-files`; the repo has folders that share a name with a game folder, so the repo wins), or
  4. it names a layout path or a script path that a `ui_elements` row holds in `vanilla_source` (spaces and backslashes included: `<context> ui\<name>` and
     `<context> ui/<name>.luac` forms), whichever separator is used; the error names the unit id to cite instead.
  Not flagged: pack file names (`data.pack`), db table names, loc keys, fx names, `engine_sites` and `engine_facts` ids, tool ids, job ids, repo paths that
  exist, Empire's paths (`rml_mod/...`, `docs/...` in the `empire-remastered` evidence list: a token under a folder named in the brief's own "Evidence base"
  paragraph, or one that matches no game folder, is not a game path), paths inside a fenced code block that is explicitly a quote (the brief marks it with
  a line `Quoted, not a citation:` directly above), and anything in a `Quoted, not a citation:` bullet. The error text says what to cite instead and how to find
  the id (`python3 core/wsc.py find <words>`).
- **Escape hatch, visible: `## Registry gaps`.** When the thing a brief must name has no row (a layout nobody put in `ui_elements`, an asset the index
  lacks) the right fix is a registry row, so the gate makes the gap a section, not a free pass: a brief may carry `## Registry gaps` with one bullet per path,
  each `path: <path>; owner: <job id or liam>; reason: <why no row>`. The checker lets exactly those paths through, fails a bullet with no owner or reason, and
  `jobs check` prints the gap count so the review sees it. The gap list of all briefs is part of `discovery/gate/summary.json` (warning, ratcheted as above).
- **Legacy set.** Every brief on main when this job's branch was cut is exempt from the found-path rule only (its shape rules still apply), in a frozen
  `LEGACY_BRIEFS` set in `tools/verbs/jobs.py`, exactly as `LEGACY_REVIEWS` exempts old reviews; a test asserts the set equals `git ls-tree` of the base commit's
  briefs (as `test_the_legacy_set_is_every_review_on_main_at_j52s_base` does) and that a brief not in the set is checked. The nine `queued` and the nineteen
  `needs_brief` rows are not edited here: other jobs' briefs are not in this job's scope. But report, as a table, which `queued` briefs would have failed the rule
  and the one-line fix for each, so the owner of that job can apply it before building (Open questions).
  Briefs that reach main between the base and this job's merge are added to the set by the builder when it rebases (the test lists them).
- **Failing fixtures first.** Every rule gets a test that fails on a bad fixture and passes on the matching good one (stdlib only, in the style of `tests/test_jobs.py`):
  a registry below its floor, an empty context, a stale README, an `assets` registry out of step with a changed index fixture, an `engine_sites` row with another
  exe, an `open` fact with no owner, a context missing from `ui_elements`; and for the brief rule: each of the four shapes above, an id that looks like a path
  (an `assets` id, accepted), a layout cited by unit id (accepted) and by its path (refused with the unit id in the message), a repo path (accepted), the `Quoted, not
  a citation:` line, a `## Registry gaps` bullet with and without an owner, and a legacy brief (exempt) versus a new one with the same text (refused). Build the
  fixtures from small synthetic indexes and rows; do not read the 88,415-row index in a unit test except in the one test that runs the gate on the real repo.
- **No new CLI, no schema change, no change to `core/`.** `gate` is an action of `wsc discovery`; the new modules and the verb change get `tools` rows with
  headers (header format in `core/warscape/tools.py`; the `tools` gate fails otherwise); `discovery/gate/README.md` is generated by `wsc discovery render`
  under the doc cap, linking rather than copying content.
- **What stays out.** Reading the game, re-running any discovery pass, adding or changing assets/ui_elements rows beyond the four engine-fact notes above, fixing the
  3,711 unresolved fields, deciding the `loose_override` question, and promoting anything to the core (J64). If a currency check turns up a stale registry that
  needs a pass run on the PC, do not fix it here: record it as the gate's first red finding in the report and queue a `needs_brief` row on a `plan/` branch
  proposal in Open questions (all work goes through the queue, D21).

## Deliverables
Priority order; the first four are the job, 5 and 6 may be thin. Each tool has a header and a `tools` row.
1. **`discovery/core/briefpaths.py` and the `brief_problems` hook** (row 80). `found_path_problems(text, known)` with `known` built once from the committed
   index (top-level game folders), the `assets` ids, the `ui_elements` ids and `vanilla_source` paths, and `git ls-files`; the loader is cached per process
   so `jobs check` stays fast (state the time on the 67-row queue before and after; the budget is under one second added). `LEGACY_BRIEFS` and the
   `## Registry gaps` parser. Errors name the brief, the line, the token and the id to cite.
2. **`discovery/core/gate.py` and `wsc discovery gate`**: the floors, the shape checks, the currency recomputations and the findings table described in
   Decisions; `--install` for the PC comparison (read-only; the fingerprint recording lands in `discovery/assets/summary.json` through the existing assets
   pass code path, with the summary's sha in `discovery/gate/summary.json`, without re-running the pass: add the fingerprint from the committed index and
   the recorded pack sizes if those are there, otherwise record the gap as a finding and let the next assets pass fill it); `--json OUT` for CI.
3. **Wiring into the gates**: `wsc discovery check` includes the gate; `tests/test_discovery_gate.py` has the failing-fixture tests and one test that runs the gate and
   the brief rule on this repo's real registries and briefs (that is what puts them in the `tests` gate, as for `jobs check`). `python3 core/wsc.py gates`
   green, including `tools`, `doc_size` and `verified_dates`.
4. **Data fixes owed by the gate** on this repo's rows: the four `open` facts get an owner in their notes (`wsc reg set engine_facts <id> notes=...`), nothing else
   in the registries moves. If a floor or check cannot pass without more than that, stop and report instead of loosening the check.
   **--- cut line: items 1 to 4 are the deliverable. ---**
5. `discovery/gate/summary.json` and the generated `discovery/gate/README.md` (counts, how to run it, how to read a finding, where the floors live), and the
   `jobs check` line that prints the gap count.
6. A short "How a brief cites" paragraph in the doc that owns brief writing, not a new doc: find it with `wsc find brief` and add three lines there (cite
   `wsc find` ids; the four flagged shapes; `## Registry gaps` is for a missing row and names an owner). Do not edit `jobs/J1/brief.md` or `docs/DECISIONS.md`
   (append only; no decision row is needed: D14 and the J5 ledger own the rule). In `jobs/J5/rules.md` row 80 is a merged baseline ledger; do not edit it. The J11
   report says "row 80: enforced, by `found_path_problems`" and the ledger's owner (J5 follow-up) updates it.

## PC test
None. `needs_pc` is false and nothing here launches the game. `wsc discovery gate --install` is written and tested on a synthetic install tree (fake packs
with the sizes the fixture index says), and the report says plainly that it has not been run against the real game folder; the first sitting that has the
watcher idle runs it once (one command, read-only) and appends the result as a dated run note under the J11 report's follow-up, not in this job.

## Evidence required
- The gate's output on this repo (one line per registry, the findings table, exit 0) and the same run with one floor raised above its count (exit 1, the failure
  line), pasted in the report; `python3 core/wsc.py gates` green; `python3 core/wsc.py jobs check` green with the new rule on.
- The failing-fixture tests listed above, each named in the report next to the rule it proves, and a count of tests added.
- The legacy set: its size (48 at the time of writing, recomputed), the base commit it equals, and the table of `queued` and `needs_brief` rows whose current
  brief (or the queued ones' text) would fail the rule if it were not exempt, with the token and the id to cite.
- Time added to `wsc jobs check` and `wsc discovery check`; determinism: running `wsc discovery gate` twice gives byte-identical `summary.json`.
- Facts and dates: any `engine_facts` row you add or change carries date and run id or commit sha (`verified_dates` gate).

## Kill criteria
- The found-path rule flags more than about 10 percent of the tokens in the briefs written after the base on a trial run against ten known-good new-style briefs
  (take the five most recent briefs on main and the J10 and J65 briefs, run them with the legacy exemption off, and look at every hit by eye): the rule is too
  noisy. Stop tuning after 25 tool calls, keep the four shapes that were clean, list the others in Open questions as candidates, and report. A false positive on a repo
  path or an id counts double.
- A currency check cannot be made deterministic offline (it needs the install or a clock): make it a `--install` check, do not fake it. If more than two of the
  seven currency checks end up PC-only, stop and report; the gate would not guard CI.
- The gate fails on this repo's main for a reason that needs a discovery pass re-run, a PC sitting or a change to `core/`: do not fix it here and do not loosen the
  check. Record the finding, queue the proposal (Open questions) and finish with the rest.
- Anything that needs a change under `core/`, `proxy/` or `harness/`, an edit of another job's brief, row or report, or of a merged review: stop and ask Liam.
- Over about 150 tool calls: stop, commit what is committed, report what is left in cut-line order. Do not extend the budget.

## Open questions
Recommendations, for Liam to confirm or overrule in the review (write the answers you reach into the report; do not decide the ones marked Liam):
1. **Legacy exemption versus fixing the nine queued briefs.** Recommendation: exempt every brief on main now and let each job's builder apply the one-line fix the
   report tables for it; editing nine other jobs' briefs here would make this job's diff the place where their scope changes. The alternative (fix them in
   this job) is a `plan/` branch of its own and needs Liam.
2. **The `## Registry gaps` hatch.** Recommendation: allow it, visible and ratcheted. The strict alternative (no hatch: a missing row blocks the brief until a row is
   added) is cleaner but stalls a brief behind a discovery job on the PC; the report counts how often the hatch would have been needed on the five most recent briefs.
3. **The pack-fingerprint check is PC-only.** Recommendation: offline CI proves registries are consistent with the committed index, and the first PC sitting after a
   game update proves the index is the install. The cheaper CI-only alternative cannot see a game update at all.
4. **`gate.json` floors set by hand.** Recommendation: as written, each floor a few percent below today's count. A floor computed from the last green run would
   ratchet itself but would let a bad merge lower the bar silently.
5. **Where the check lives after J62 and J64.** The brief rule is game-agnostic (`briefpaths.py` takes the folder list and the id sets as arguments), the gate floors are
   per game. Recommendation: both go into the core with `discovery/core`; B1 (game-specific gates) would replace the test-based wiring. Note it in the report's
   "What moves to the core later".
6. **Liam's call, not decided here:** whether `open` engine facts older than a set age should turn the gate red (it would make the 23 a to-do list). Recommendation:
   warning only for now, revisit when the phase 3 baseline starts.

## Finish
Write `jobs/J11/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`, plus evidence): what exists and how to run it, the floors
and why each is where it is, the findings table, the legacy set and the would-have-failed table, the failing-fixture tests by rule, row 80's status, and what
moves to the core later. Then
`wsc reg set jobs J11 status=review report=jobs/J11/report.md`.
