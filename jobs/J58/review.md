# J58 review

## Round 1 (2026-11-01, branch job/J58 at 5551bc1)

**Verdict: merge.**

Reviewed cold in a fresh session (not the builder). Rule 79 now judges a `core` pin move on `git -C core diff` between the merge base's
pin and the head's, counts only `proxy/` and `harness/` paths that are not `acc_exempt`, and fails closed with a fetch hint when the pins
cannot be compared. Every brief deliverable is present and the decisions are followed. One should-fix (renames) is fixed on the branch.

### Machines
- CI on `job/J58` at 5551bc1: all 8 checks passed or were skipped (`wsc jobs review`).
- `python3 -m unittest tests.test_pr_policy`: 36 tests OK (35 from the branch plus the one added below).
- `python3 core/wsc.py gates` and `python3 tools/pr_policy.py --branch job/J58 --base origin/main`: gates 11 ok, 1 warn (local skips: no numpy/Pillow, no
  viewer.wasm), 0 failed; before this review, policy's only refusals were the missing review and the row not `done`.

### Claims against evidence
- J55 claim (deliverable 4), checked independently without the report's scratch worktree: with this branch's `pr_policy.py`,
  `core_pin_diff(<merge base of origin/main and origin/job/J55>, 'origin/job/J55')` returns 11 core paths and `rule79_path` counts none
  of them (run here 2026-11-01, after the rename fix too). That matches the brief's target fact (`git -C core diff --stat v0.5.0 v0.6.0`
  lists no proxy/ or harness/ path). The quoted J55 refusals in the report are J55's own (no review, row not `done`).
- `policy.yml`: the report says the base pin is very likely already present with `fetch-depth: 0` and added the fetch step anyway, and
  names that as a deviation. Agreed: the step is a `cat-file -e` no-op when the commit is there, and a gap still reaches pr_policy's
  fail-closed message. No token or branch-protection change (kill criterion 1 not hit).

### Brief
- Fail closed: a missing gitlink at either ref, or a `git diff` error (missing pin commit, no submodule), returns a str and the pin counts;
  `core_diff=None` also counts (`acceptance_problems`). Tested.
- The branch cannot switch the rule off with a file: `core_pin_diff` reads only gitlinks and core commits; `acceptance_active` is still
  read from the base. `INPUTS` is not restated. `saves/` does not count (tested).
- Risk-first reading: `core_pin_diff` and the `acceptance_problems` change, since a wrong answer there lets a DLL change merge with no
  PC acceptance run. Skimmed the tests' fixture and `main()` wiring.

### Findings
- **should-fix (fixed in 61d8d87):** `tools/pr_policy.py` `core_pin_diff` ran `git diff --name-only`, which follows renames and lists
  only the new path. A core bump that moves `proxy/src/a.cpp` to `docs/a.cpp` (a DLL input removed) listed only `docs/a.cpp`, so rule 79
  counted nothing and the bump needed no passes. Now `--no-renames`; new test
  `CorePin.test_failing_fixture_a_file_moved_out_of_the_cores_proxy_is_refused` fails without the flag (`'proxy/src/a.cpp' not found in
  ['docs/a.cpp']`) and passes with it.
- **later:** `tools/pr_policy.py:289` (`main()`, this repo's own `changed`) uses the same `git diff --name-only` and has the same gap for
  this repo's `proxy/` and `harness/`: a rename out of them shows only the new path. Pre-existing and outside J58's scope (D14); it also
  feeds every other branch-kind rule, so it wants its own job with a test per rule that reads `changed`.
- **later:** report open question 2 (`show()` reads `core/...` through the script's repo, `core_pin_diff` through the checkout): agreed,
  same tree in CI and locally; no action now.
- **note for J55:** J55 and J58 both edit the `acc = {...}` lines in `main()`; J55's merge after this one will conflict there (the report
  names the mechanical resolution). No rule other open branches must newly meet.
