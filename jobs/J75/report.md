# J75 report: Rule 79 evidence: one exemption, unique evidence, append-only ledger, shas

Rule 79 in `tools/jobs_hooks.py` now checks that acceptance evidence is genuine, not only that it exists. Only `harness/acceptance/ledger.jsonl` is exempt, so a
branch that edits only `baseline.json` or `shots/` needs 20 passes. A counted line's pass file must be unique in the streak, parse as JSON, sit in the line's run
folder and agree with the line on `build_id`, `watcher`, `pass`, `passed`/`result` and the step names and results. Pass numbers must rise by one within a run. The
ledger diff against the merge base must be append-only, and a base `pass_*.json` must not be modified or deleted. Once the pinned core defines `LEDGER_SHA_FIELDS`
(core W9), the named shas are required, must match between line and file, and no shot sha may repeat; that check is off at the current pin (v0.10.0). Nine new
tests were red on the unchanged hook and are green after the change. The committed J30 streak still counts.

## What was built
- `tools/jobs_hooks.py`:
  - `acc_exempt`: exempts only `ledger.jsonl` (`path == ACC_LEDGER`). `runs/` folders and READMEs stay exempt.
  - New small named functions: `acc_sha_fields(root=None, src=None)` (finds `LEDGER_SHA_FIELDS` in the pinned `acceptance.py` with `ast`; the core's code is never
    run), `ledger_append_problems`, `pass_file_problems`, `evidence_problem` and `streak_problem`. New constants: `ACC_SHA_NAME`, `_PASS_FILE`, `_HEX`.
  - `acceptance_problems` reads as before. The append-only and pass-file errors are computed before the "nothing to count" return, so rewriting the ledger alone is
    refused. A streak break gives one cause in the existing message: `(the streak ends at pass N of <run>: <file> <rule>)`.
  - `collect_acceptance` adds four keys:
    - `read`: path to text at HEAD.
    - `base_ledger`: the ledger at `merge_base`, else `base`.
    - `sha_fields`: from `acc_sha_fields(root)`.
    - `runs_diff`: `git diff --name-status --no-renames <mb> HEAD -- harness/runs`.

    The `acc` shape stays backward compatible: a missing key means that input is not available.
  - `policy_problems`: a changed ledger or `pass_*.json` now also reaches the git reads. Docs-only changes still skip them.
  - Module and function docstrings are updated. The tools row is refreshed with `wsc reg add tools tools/jobs_hooks.py`.
- `tests/test_jobs_hooks.py`, beside `Rule79`:
  - `Rule79Evidence`, 7 tests: only the ledger is exempt (2a); 20 copies of one line count as 1 (2b); disagreeing evidence, one case per field and the run folder
    (2c); unparsable evidence and a repeated pass number (2c); append-only (2d); shas on and off, and `acc_sha_fields` on string sources (2f).
  - `Rule79Repo`, 2 tests on a throwaway git repo: base pass files are immutable (2e); `collect_acceptance` returns `read`, `base_ledger` and `sha_fields`, and 20
    valid lines give no error end to end (2g).
- `docs/REVIEW.md`: one sentence beside the rule 79 text, linking the hook.

Commits on `job/J75`: `ad126ea` (red tests), `3a4cbc4` (the hook change), `0a6e4b7` (merge of `origin/main`), then this report and the row.

## Evidence
**Step 1** (throwaway script, not committed), over the 311 committed lines (33 run folders named in the ledger, 59 under `harness/runs/`):
- Decision 2 rejects 0 lines. None has missing evidence, unparsable JSON, a field disagreement, reused evidence or a pass number out of sequence.
- The tail streak is `job/J30` on build `cb34c06baf42`, watcher 1.2.0: 20 lines count (passes 2-21 of `20261103_j30acc6`).
- Decision 3 over main's 13 commits that touch the ledger: 1 is not append-only, `ad22582` (J30, #164).
  - The base had 263 lines and the head 311. J30's merge of `origin/main` (`6ee33bd`, "ledger both sides") put J30's 18 earlier lines before J24's, at base line 215.
  - The PR head checked against its merge base (`55c57e0`) is not a prefix of it. Under the new rule, J30's PR would have been refused until its ledger was put
    in main-first order.
  - This is history: no live line is rejected, and every branch's base is now the current ledger. See Open questions 1.

**Red** on the unchanged hook (tests at `ad126ea`): `Ran 51 tests ... FAILED (failures=18, errors=4)`. Failure lines:
- `ERROR: test_failing_fixture_shas_are_required_once_the_core_names_them ... AttributeError: module 'jobs_hooks' has no attribute 'acc_sha_fields'`
- `ERROR: test_failing_fixture_collect_reads_content_the_base_ledger_and_the_sha_fields ... KeyError: 'base_ledger'`
- `ERROR: test_failing_fixture_the_ledger_diff_is_append_only ... IndexError: list index out of range`
- `ERROR: test_failing_fixture_unparsable_evidence_and_a_repeated_pass_number_end_the_streak ... IndexError: list index out of range`
- `FAIL: test_failing_fixture_only_the_ledger_is_exempt ... AssertionError: True is not false`
- `FAIL: test_failing_fixture_twenty_copies_of_one_line_are_one_pass ... AssertionError: 0 != 1 : []`
- `FAIL: test_failing_fixture_evidence_that_disagrees_with_its_line_ends_the_streak (field='build_id'|'watcher'|'pass'|'passed'|'steps'|'step names'|'run') ... AssertionError: 0 != 1 : []` (7 subtests)
- `FAIL: test_failing_fixture_shas_are_required_once_the_core_names_them (case='missing'|'differs'|'not hex'|'shared shot') ... AssertionError: 0 != 1 : []` (4 subtests)
- `FAIL: test_failing_fixture_the_ledger_diff_is_append_only (branch=[A, B'] | [B] | [A] | [B, A, C]) ... AssertionError: 0 != 1 : []` (4 subtests)
- `test_failing_fixture_a_base_pass_file_is_immutable`, which is not listed above, also failed on the unchanged hook: the hook had no `runs_diff` check yet.

**Green:** `python3 -m unittest tests.test_jobs_hooks tests.test_acceptance tests.test_discovery_gate tests.test_usage_reader tests.test_build_id` reports `Ran 135 tests ... OK`.

**Step 5** (real ledger, no commit). `collect_acceptance` on this branch gave active True, build `cb34c06baf42`, watcher 1.2.0, `sha_fields` None and `runs_diff` [].
- A baseline-only change on `job/J75` is refused:
  `['rule 79: this branch changes harness/acceptance/baseline.json but harness/acceptance/ledger.jsonl holds 0 consecutive acceptance passes on build cb34c06baf42, watcher 1.2.0 (the streak ends at a line of another branch: pass 21 was run for job/J30) (need 20): run `python3 core/harness/acceptance.py run` on the final build']`
- With `branch=job/J30`, build `cb34c06baf42` and a change to `proxy/napoleon/adapter.cpp`, the result is `[]`: the honest 20 passes still count. A baseline-only
  change on the same inputs also gives `[]`.

**Sha fields:** `LEDGER_SHA_FIELDS` is absent at the pin (v0.10.0, `core/harness/acceptance.py`), so the sha check is off and Decisions 1-4 apply.
Line for the warscape-core W9 backlog: "W9: define a module-level `LEDGER_SHA_FIELDS` tuple in `harness/acceptance.py` naming the shot, kit, DLL and watcher sha fields
written to both the ledger line and the pass file; Napoleon's rule 79 (J75) turns its sha check on when the pinned core carries it."

**No rule loosened.** Each removed line in `git diff origin/main -- tools/jobs_hooks.py`, and where its check lives now:
- Module `purpose:` line: the same text plus J75's rules.
- `acc_exempt` docstring and `path.startswith('harness/acceptance/')`: narrowed to `path == ACC_LEDGER`, which is stricter.
- `acceptance_problems` docstring: rewritten, keeping every earlier rule and adding the J75 keys and rules.
- `if not code: return []`: now `return errs`, which is `[]` unless the new append-only or pass-file errors fire.
- `n, unproved, foreign = 0, None, None`: the same names plus `bad, used, last`.
- `n += 1`: now `last, n = r, n + 1`, after the new `streak_problem` gate.
- `if n >= ACC_NEEDED: return []`: now `return errs`.
- `why` ending `... if foreign else ''`: the same branches plus one for `bad`.
- `return [f'rule 79: ...`: now `return errs + [f'rule 79: ...`, with the message unchanged.
- The last line of the `collect_acceptance` dict: the same keys plus `read`, `base_ledger`, `sha_fields` and `runs_diff`.
- `policy_problems` docstring and shortcut: the same condition, widened with `or p == ACC_LEDGER or _PASS_FILE.match(p)`, so more changes reach the check.

No assertion in `Rule79`, `CorePin` or `tests/test_acceptance.py` was removed, changed or relaxed. None needed replacing: no existing test asserted that
`baseline.json` was exempt.

**Gates and policy:**
- `python3 core/wsc.py gates --fast`: 13 ok, 0 warn, 0 failed (the pre-push hook on each push, including the push of this report).
- Full `python3 core/wsc.py gates` (builder, before this report): 12 ok, 1 warn, 1 failed in 320 s; the failure was only `jobs check` because the row named this
  report before it existed. With the report committed, `jobs check` passes; CI's gates run on the draft PR is the full run of record.
- `python3 core/wsc.py policy --branch job/J75 --base origin/main` prints no rule 79 line; its remaining refusals are the review and the row not yet `done`,
  which the reviewer adds.

## Deviations from the brief, and why
- **The builder stopped on a refused tool call.** Its Write of `jobs/J75/report.md` was refused by the harness ("Subagents should return findings as text, not write
  report files"). Under the kill criterion it stopped and did not retry another way, reverted the `status=review` row it had set, and returned this text to the
  orchestrating session (same session id), which committed it, set the row and opened the draft PR. Everything else (Steps 1-7) was done before the stop.
- **Some rules run without content.** Uniqueness, pass-number sequence and run folder are checked even when `acc` has no `read`, because they need only the line.
  Only the content rules (parse, field agreement, shas) need `read`, as the docstring says. The older `led` fixtures satisfy all three, so no existing test changed.
- **Which fields are shot shas.** Every name in `sha_fields` that contains `shot` is treated as a shot sha (unique across the streak). The core has not named its
  fields; this is the narrowest reading of Decision 5.
- **An unreachable merge base fails closed.** `runs_diff` uses `_git` with `check=True`, so `policy` fails loudly rather than skipping Decision 4.
- **Where the scratch scripts went.** The Step 1 script was written under `_scratch/j75/`, then moved out of the repo to `$TEMP` after a first test run that
  failed for an unrelated reason: the stale tools row. Step 5 ran from the session scratchpad. Neither is committed.

## Open questions
Brief questions 1 and 2 took the recommendation (D56): an edit to `baseline.json` costs 20 passes but is not forbidden; a pin without `LEDGER_SHA_FIELDS` turns the
sha check off and adds one line to the W9 backlog.

1. **Merging main into a branch with passes.** J30 resolved its ledger conflict with its own lines first (`6ee33bd`). The append-only rule now refuses that order,
   and the error says "when merging main, put main's lines first". Should `job.sh` or a `wsc` helper do the ledger merge (base lines, then the branch's), so an
   agent cannot get the order wrong? That would be a core item.
2. **Repeated shot shas.** A deterministic scene can produce byte-identical shots in different passes, and the "shot sha must not repeat across the streak" rule
   would then refuse honest passes. Should the rule cover only non-deterministic steps, or a per-pass composite sha (for example, one that includes the pass's
   start time)? Core W9 should settle this when it names the fields.

Left for later jobs:
- Core W9: writing the shas, refusing a reused run id at run time, the watcher-sha preflight.
- J80: the baseline-content rule.
- Core W23 (with J78): CI loading the base's hook instead of the head's.
