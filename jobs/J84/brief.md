# J84: plan/ merges itself on green CI: the hook stops denying it

Phase 1, Liam 2026-11-05, maximum priority (D62, which replaces D50's `plan/` half). The PreToolUse hook `tools/claude_hook.py` denies an agent's `gh pr merge` of a `plan/` or `meta/` branch (J76, D50).
D62: `plan/` branches merge themselves on green CI like `brief/` (D33); `meta/` stays Liam's. This job is the hook change alone, with the wording that describes it. It does not wait for J78, and the audit's
narrowed rules (`plan/` loses `CLAUDE.md`, `docs/REVIEW.md` and the core's docs; row edits limited) are J103's, not this job's: do not add them here.

Model: Sonnet medium (D15): one stdlib Python module, its corpus and a few doc lines; no reverse engineering, shader, DLL or crash work. Budget about 40 tool calls; at about 25 calls without a green corpus, stop, commit, report what is left.
No subagents, no game launch, `needs_pc` is false.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J84`). Read `docs/DECISIONS.md` D33, D50, D53 and D62, and the header and the merge section of `tools/claude_hook.py` (`merge_msg`, `merge_reason`, `branch_msg`).
- The hook is `tools.claude_hook` in the tools registry (`python3 core/wsc.py find claude_hook`); its test is `tests/test_claude_hook_corpus.py` (the `merge` family and `Messages.test_every_family_names_its_route`).
- Never edit `core/`. Never edit `.claude/settings.json` (not needed). Decision rows are Liam's: do not edit `docs/DECISIONS.md`.

## Deliverables
1. **Hook.** In `merge_reason` (`tools/claude_hook.py`, the final `re.match(r'^(?:plan|meta)/', branch)`), deny only `meta/`; a `plan/` branch is allowed. Everything else in the merge guard stays exactly as it is:
   a pull request number, URL or no target is still resolved with `gh pr view` and an unresolvable one is still denied (the `gh pr merge 12` case now resolves to `plan/x` in the corpus and becomes allowed, while a number that resolves to `meta/` stays denied);
   `gh api` merges (`/pulls/N/merge`, `mergePullRequest`, `enablePullRequestAutoMerge`) stay denied; the remote-branch delete guard for `main`, `plan/`, `meta/`, `job/` and `brief/` stays.
2. **Message and header.** `merge_msg` says only Liam merges `meta/` branches (D50, still true for `meta/`) and that `plan/`, `job/` and `brief/` branches merge with `gh pr merge <branch> --auto --squash` once their rules are met; the file's header lines 3 and 5 say `meta/` only, with D62 for `plan/`.
   The unresolvable-target message keeps its "name the branch" hint.
3. **Corpus.** In `tests/test_claude_hook_corpus.py`: the `plan/x` merge cases become allowed (`gh pr merge plan/x --auto --squash`, `refs/heads/plan/x`, `plan/x -R liam-rowley/warscape-core`, and the `PRS` fixture's `plan/x` numbers and URL), keep every `meta/` case denied (`meta/x`, `origin/meta/x`, `bash -c`, `nice gh pr merge liam:meta/x`, the `None` target that resolves to `meta/y`), keep `gh api` and unresolvable cases denied,
   add `gh pr merge plan/J84 --auto --squash` and a PowerShell form as allowed, and fix `test_every_family_names_its_route` (the `'D50'`/`'Liam'` expectations now use a `meta/` command). Run the whole corpus; the sanity set from J76 (`git status`, `git commit ... --trailer`, `git push`, `gh pr view`, `python3 core/wsc.py jobs check`) still allows.
4. **Prose, one owner per topic.** `CLAUDE.md`: the two lines that say `plan/` waits for J84 or Liam ("While you work", the "Launch and kill" Guard line) now say D62 is in force: `plan/` merges itself on green CI, `meta/` by Liam only (D50); the Guard line lists `meta/` only.
   Add to `CLAUDE.md` the step that a `plan/` branch queues its own merge: after pushing, `python3 core/wsc.py policy --branch plan/<name> --base origin/main` (must say ok), open the pull request, then `gh pr merge plan/<name> --auto --squash`, no waiting or polling, as `brief/` does (D33); put it where `brief/` is described, in one sentence.
   Update the other living copies of the old claim and nothing else: `grep -rn "plan/" docs/REVIEW.md README.md docs/plans/PLAN.md registries/tools/tools.claude_hook.json` and fix lines that still say Liam merges `plan/` (REVIEW.md "Merging" has one; leave its rule for `meta/` and for the core). Do not change `docs/REVIEW.md` any other way.
5. **Gates.** `python3 core/wsc.py gates` passes; `python3 core/wsc.py policy --branch job/J84 --base origin/main` is ok. If the policy check refuses a file this job must change, stop and report the file and the rule (kill criterion).

## Out of scope
- J103's narrowed rules, `core/`, `.claude/settings.json`, `docs/DECISIONS.md`, the `policy.py` branch-kind rules (`plan/` is already a branch kind there), any other hook rule.
- Reviewing or merging `job/J84`: an independent session does that (D32).

## Kill criteria
- The corpus cannot be made green in 3 edit rounds, or the change would let a `meta/` merge through (any `meta/` case allowed): stop, commit, report.
- Any tool call is refused by a deny rule: stop and report the call and the rule.

## Finish
Write `jobs/J84/report.md` (headings `## What was built`, `## Deviations from the brief and why`, `## Open questions`): the corpus counts before and after, the `gates` and `policy` output, the living copies of the old claim that were fixed.
Then `wsc reg set jobs J84 status=review report=jobs/J84/report.md`, push `job/J84` and open a draft pull request. Do not merge it.
