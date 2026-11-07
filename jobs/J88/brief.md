# J88: Pin bump to the core's process train

Phase 1, tooling. Audit 2026-11-03 (`docs/audits/AUDIT_2026-11-03.md`) and J95 item 10. This job moves the core pin to a tag that holds core W141, re-runs the exe pass that W141 changed, and
switches on the core's process rules that the game still has off. **Most of the train is already here:** W26, W27, W28, W29, W31 and W35 all reached the pin through J78. What is left is config, the
two discovery steps and one re-check. Nothing here should touch the DLL.

Model: Opus, reason: Liam's "Opus across the board" (2026-11-06, the row J105 writes), and the exe re-run needs an independent check that no engine site rests on a lost signature.
Budget about 90 tool calls (J95 used 100 with a core job inside it; J64 and J78 were budgeted 170 and 260 for bumps that crossed more versions and, in J78's case, a 20-pass run). Subagents are not
needed. Waiting belongs to the harness, not to repeated calls.

**No DLL or harness input changes: this job carries no 20 passes (rule 79).** Rule 79 judges the core's own diff (`core_pin_diff` in `tools/gates/pipeline.py`, J58), and the target tag is chosen so
that diff has no `proxy/` or `harness/` path. The game is not launched, so `needs_pc` stays false; the one PC step reads both exes in place. If the bump would need passes, see Kill criteria.

## Start
- If this session's model is not the row's, stop and say so.
- Follow `CLAUDE.md` (Jobs: branch `job/J88`). Start the session with `--add-dir ../empire-remastered`: `exe.py` reads the signature sources there through the `repo` key of `discovery/napoleon/games.json`. Read only, never edited.
- Read `jobs/J78/report.md` (`## Deviations from the brief and why`, `## Open questions`), `jobs/J95/report.md` and `jobs/J95/review.md` (`### The 26 signatures`), and in the core at the target tag
  `docs/UPGRADING.md` (every section between the pins), `docs/CONSUMING.md` ("Upgrading and releasing"), `jobs/W141/review.md` (`### exe.py and committed results`) and the docstring of `warscape/policy.py` (rules A and F).
- Search first: `python3 core/wsc.py find discovery.core.exe` and `python3 core/wsc.py find core bump`. Reuse those verbs.

## Target facts
Check each again before relying on it.
- **The target tag.** Read the tags with `git -C core fetch --tags`. For each candidate, `git -C core diff --name-only <current pin> <tag>` must list nothing under `proxy/` or `harness/`.
- **W32 is the one row not in any tag.** The row asks for the first tag holding W32 too. Read its status in the core's `registries/jobs/W32.json` at the tag.
- **Opt-ins, as `repo.py` DEFAULTS leaves them.** `[jobs] usage_from` is 0, so the `Usage:` rule is off. `[policy] decisions_cite_job` is false. `[policy] reviewer_code` is `warn`. The game's `wsc.toml` sets none of them. `[gates] skip` is empty, so W28's skip warning has nothing to print.
- **`usage_problems` in `core/warscape/jobq.py`** checks a row's `Usage:` line against the row's model and 1.25 x the budget, from `usage_from` on. Many older reports have no such line, so the value must sit above them.
- **`wsc discovery check` fails on a stale README.** `discovery/diff/README.md` prints the signature counts from `discovery/diff/exe.json`, so the README goes stale the moment `exe.py` rewrites that file.
- **`exe.json` has no mark of the mask rule.** `detail.method` reads the same before and after W141, and no gate sees a file left on the old rule (W141's review; core row W142). The re-run is the only thing that moves it.
- **The rows citing `exe.json`** are the PE facts `napoleon.diff.exe.pe` and `napoleon.exe.window_imports`. W141's review found they do not change. Check that on the new file.
- **`tests` gate.** The default `timeout_s` is 600, and J78's first full `gates` run hit it with no test failed (J78 report, Evidence and deviation 4). A cold Docker build is the cause it names. W139 adds a `timing:` line and warns over 75% of the cap.

## Decisions already made for this job
1. **Target: the newest tag whose diff from the current pin has no `proxy/` or `harness/` path, and never earlier than v0.50.1.** v0.50.1 meets that, so this job never needs a run. A newer tag that fails the test is left for a later bump.
2. **Do not wait for W32.** W32 is `queued` with no build yet, the row's opt-ins do not need it, and D56 asks for the bump that follows J95's core fixes. If the target tag holds W32, say so. If not, say so, and a later bump brings it.
3. **J104 is not folded in.** Its row says to fold only if the core has tagged W47 while J88 is `needs_brief`. It has not. So `[jobs] max_sessions`, `auto_actions`, `[audit]` and `decide/` in the hook stay J104's.
4. **`usage_from` is set here; the reader is J87's.** J88's row and J87's row both name the switch. Set `usage_from` here, and leave `usage_cmd`, `tools/usage_reader.py` and the view chip to J87. Until J87 lands, a report's line is written by hand or with `wsc jobs usage <id> --write --from-json <file>`, as J95 did.
5. **`usage_from` is the lowest job number above every report that has no `Usage:` line.** Compute it on `main` at the time, so no old report is refused. This job's own number falls below it, but write the line anyway.
6. **`decisions_cite_job = true`.** It costs nothing and holds for both `docs/DECISIONS.md` and the row files J105 brings.
7. **`[gates] skip` stays empty, and `[tests] workers` stays 1.** Report the `timing:` line and any warning; do not tune the gate here.
8. **`exe.json` is regenerated, never hand-edited.** What it says about candidates is a result. A lost signature changes no `engine_sites` or `engine_facts` row in this job: it gets named.

## Deliverables
1. **The bump.** `python3 core/wsc.py core bump <tag>` on `job/J88`: one commit of `core`, `wsc.toml` and any re-rendered file under `.github/workflows/`. Do each UPGRADING.md section between the pins that asks for something, and name the ones that ask for nothing. Delete any game verb the bump names.
2. **The discovery steps, in this order.** `wsc discovery render`, then `wsc discovery check`, commit what changes. Then `python3 core/discovery/exe.py --games discovery/napoleon/games.json --out discovery/diff/exe.json`, then `wsc discovery render` and `wsc discovery check` again, and commit `discovery/diff/exe.json` with the README it moves. The row names one render; the second is needed because of the stale-README fact above.
3. **The re-check.** Keep the old `exe.json` from `main` and compare it with the new one on `detail.signatures`, with a scratch script that stays out of the repo. List every signature whose `class` or `napoleon_rva` changed. Then, for each one, test whether any of its old or new hits lies within 32 bytes of the `rva` of an `engine_sites` row, and grep `registries/engine_sites.jsonl` and `registries/engine_facts` for each lost name. The row's figure is 26 signatures losing a candidate class (19 `unique`, 7 `shared`), and W141's review found none near a site. Say whether your numbers match, and name any row that rests on a lost hit.
4. **The opt-ins in `wsc.toml`.** `[jobs] usage_from` (decision 5), `[policy] decisions_cite_job = true`, and `[policy] reviewer_code` as Open question 1 says. Before changing `reviewer_code`, run `python3 core/wsc.py policy --scan --rule A` over the whole history, and again with `--since <J78's merge commit>`, and paste both totals. The second covers few branches, so read the first for how often reviewers have done this. If it becomes `error`, add to the `CLAUDE.md` line "Reviewer fixes go on the job branch itself" that a `merge` over such a fix needs a newer round from a fresh session (rule A).
5. **Proof the rules are live.** `wsc jobs check` passes with `usage_from` set, and a test in `tests/` or a scratch run shows a report at or above `usage_from` with no `Usage:` line is refused. Run `python3 core/wsc.py gates` in full.

## Out of scope
- Anything under `core/`: a change the game needs is a W row (`warscape-core-change`), and any fault found goes in the report as a recommended row.
- `max_sessions`, `[audit]`, the `decide/` hook, `proposals` adoption (J104); the usage reader (J87); decision rows (J105); `gen_tables.py --exe` and any copy of an exe (J107, J78 deviation 1); `[tests] workers`; the `d3d9.map` release step (J78 deviation 2).
- Changing any `engine_sites` or `engine_facts` row, or chasing a lost signature with reverse engineering. Name it; a later job takes it.
- Launching the game, `pc_deploy.py` installs, and acceptance passes.

## Open questions
1. **Set `[policy] reviewer_code` to `error`?** The core has run with it since W40. At `warn`, a reviewer can change code and still merge it in the same round, so nobody fresh reads that fix, and Napoleon's reviewers do fix on the branch (J94, J96). At `error`, each such fix costs one more Opus round. recommended: `error`, because the row says to opt in to W27's review rules and the fix a reviewer writes is the code no one else has checked. default after: 2026-11-10.

## Kill criteria
- `git -C core diff --name-only <pin> v0.50.1` lists a path under `proxy/` or `harness/`, or `python3 core/proxy/tools/build_id.py --no-dirty` prints a different id before and after the bump: stop, commit nothing further, report which core change moved it (it would carry 20 passes; J85 can run them).
- `python3 core/wsc.py policy --branch job/J88 --base origin/main` names rule 79: stop and report the line.
- `exe.py` is refused by a session guard (J95's review hit this): do not copy an exe and do not go around the guard. Commit the rest, keep the row out of `review`, and report the one command left for Liam to run with `!` in a foreground session.
- `exe.py` changes a PE fact, a guard, patch or cfg site class, or any `rows` entry other than `signatures function`: stop and report the rows, because W141's review says only that row moves.
- `wsc discovery check` still fails after the second render: stop and paste its lines. `wsc discovery ui` needs the extract and exits 1 without it (W141), so do not try to rebuild the extract here.
- `gates` fails with a failed test, or fails a second time on the `tests` cap with Docker warm: stop and report the `timing:` lines.
- Over about 90 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J88/report.md`: `## What was built`, `## Evidence`, `## Deviations from the brief and why`, `## Open questions`, with a `Usage:` line. It must also say: the tag taken and whether it holds W32; the `git -C core diff --name-only` result for `proxy/` and `harness/`; the build id before and after; each UPGRADING.md section crossed and what it asked for; the `wsc discovery check` lines and the README diff, both rounds; the value of `usage_from` and how it was computed; the `--scan --rule A` result and the value of `reviewer_code`; the re-check table of deliverable 3 with any row resting on a lost hit; the `timing:` line. Then `wsc reg set jobs J88 status=review report=jobs/J88/report.md`, push, and open the draft pull request `wsc jobs next` printed.
