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
- Read `jobs/J78/report.md` (`## Deviations from the brief and why`, `## Open questions
Answered by Liam on 2026-11-07, "Follow recs". Recorded here because `docs/DECISIONS.md` has no room until J105 brings row files. Start on this; none is open.
1. Set `[policy] reviewer_code` to `error`? **Answer: yes, `error`.** At `warn` a reviewer can change code and merge it in the same round, so nobody fresh reads that fix, and Napoleon's reviewers do fix on the branch (J94, J96). Each such fix now costs one more Opus round.

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
