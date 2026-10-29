# J42: CI reliability: no red check a branch did not cause

Phase 1. CI goes red after a branch looks green locally, and because a failed check leaves the pull request open (D32), merges stall
until someone notices. On 2026-10-29 alone: PR #50 (J15) went red three times in a row, once for a real bug only CI could see (the
wine smoke test still expected 0 engine sites) and twice for `harness-windows` timeouts on a commit whose twin run passed (the watcher
heartbeat; the update-rollback cases at 150 s and 30 s); `job/J7`, `job/J39`, `job/J21` and `job/J19` had red runs too; and every PR
failed `core_pin` after warscape-core cut v0.3.0 (fixed in the J41 review, run 40962535611). Make every red check
mean "this branch broke something", and make a red check on an open pull request impossible to miss.

Model: Sonnet (D15 default: workflow, PowerShell test and Python tooling work, no reverse engineering). Budget about 120 tool calls;
at the cap, stop, commit, report what is left. No subagents. CI waits go to the harness (`gh run watch` in a background shell, or fire
the runs and read them once later), never a polling loop of tool calls.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J42`). Read `docs/DECISIONS.md` D16, D21, D32, D33, D34 and `docs/REVIEW.md` "Merging".
- Read, don't rediscover: `.github/workflows/gates.yml` (jobs `changes`, `gates`, `proxy`, `harness-windows`, `policy`; the
  `concurrency` group and the `workflow_dispatch` inputs), `tools/changed_inputs.py` (the one input-set list, J41),
  `tests/test_proxy_host.py` (the local proxy route, J41), `proxy/tools/build.sh` (`smoke` needs wine; `--docker smoke` refuses today),
  `harness/tests/{Run-HostTests,Test-Integration,Test-Lib}.ps1` and `harness/README.md` Tests (`-Only`/`-Repeat`, which cases are not
  repeat-safe), `tools/pr_policy.py` (what each branch kind may change), `tools/verbs/jobs.py` (`next`, `review`, `view`).
- Reports and reviews: `jobs/J19/report.md` (the dispatch route, the race sweep table), `jobs/J41/report.md` and `jobs/J41/review.md`
  (later items 2 and 5), `jobs/J15/report.md` and `jobs/J15/review.md` (the PR #50 failures).

## Decisions already made for this job
- **The failure table comes first** and is the job's map: `docs/CI_FAILURES.md` (its one owner).
  Every failed `gates.yml` run from 2026-10-29 00:00 UTC up to the job's start (`gh run list -w gates.yml -L 300 --json ...`; the
  "last 100" window in the row has already moved) gets one row: run id, event, branch, commit, failed job and step, the first error
  line, and one class: **branch bug** (the commit was wrong), **CI-only test** (a check the branch could not run locally), **flaky**
  (the same commit passed in another run), **workflow** (CI itself was wrong: pins, fetch depth, concurrency, runner). Add a column
  naming the guard this job adds for that class, or "none: branch bug, CI did its job". A generator script is welcome (header and
  `tools` row) but the table is committed.
- **One run per commit.** A push to a branch with an open pull request starts two runs of the whole workflow today (`push` and
  `pull_request` have different `github.ref`s, so the concurrency group does not dedupe them). Make each commit run once. Constraints:
  a branch with no pull request yet still gets CI on push (job branches push early to claim the job); the pull request still shows
  every required check (`gates`, `proxy`, `harness-windows`, `policy`) on its head commit, so `gh pr merge --auto` still works (D32,
  D33); `main` still runs on push; no run auto-merge needs is ever cancelled. Pick the route, say why in the workflow header, and prove
  it with one pushed commit on an open PR (one run, all checks reported, run ids in the report).
- **Flaky harness cases are fixed at the race, never by a timeout alone.** For each flaky `harness-windows` case in the table, reproduce
  it with `gh workflow run gates.yml --ref job/J42 -f only='<case>' -f repeat=20` (J19's route), find what the test asserts before the
  watcher or updater has finished (J19's sweep table is the method), fix it in the test or the harness, with a unit guard where the
  rule can be checked statically (J19's `Handle-Hang` order check is the model). Raising a timeout is allowed only alongside the race
  fix and with the measured worst case in the report. If a case cannot be made repeat-safe, document why in the `Test-Integration.ps1`
  header (as J19 did) and run it once per dispatch.
- **Local parity: every CI check has a local route or a named warning.** Today the local `wsc gates` covers `gates` and (J41) the proxy
  host tests. Add:
  1. the wine smoke test: `build.sh --docker smoke` runs it in the same pinned container with wine installed (a `build.sh` change is
     allowed here), and `tests/test_proxy_host.py` runs it after `all` on the same routes, the same skip and fail-closed rules;
  2. the harness host tests on the PC: a local route that runs `harness/tests/Run-HostTests.ps1` under Windows PowerShell 5.1 when the
     harness input set changed (`changed_inputs.py --local`), as a repo test the full `tests` gate runs; on a host without Windows
     PowerShell it fails closed with the fix, with an opt-out env var named like `WSP_PROXY_TESTS` (`WSP_HARNESS_TESTS=skip`);
  3. `policy`: the local route already exists (`tools/pr_policy.py`); make `wsc jobs next` and `docs/REVIEW.md` steps name it if they
     do not.
  Anything that still cannot run locally is listed in the failure table's guard column as "CI-only, warned" and printed by the route
  that skips it.
- **Evidence commits do not run the slow jobs.** `proxy/runs/` is committed PC run evidence and matches `^proxy/` (J41 review later
  item 2): exclude it from the proxy input set in `tools/changed_inputs.py`, with a unit test, and say in the report which CI outputs
  change (none for a diff without `proxy/runs/`).
- **A red check on an open job or brief pull request is told, not polled for (D32, D34).** Two parts:
  1. a final workflow job, on `pull_request` only, `if: failure()` across the other jobs, that comments once on the PR naming the
     failed job, step and run URL, and the table class to check first (needs `pull-requests: write` on that job only);
  2. `wsc jobs next`, `jobs review` and `jobs view` read open pull requests with failed checks (`gh pr list --json
     headRefName,statusCheckRollup`, one call, `--offline` skips it) and print them first: "PR #n job/J<k>: <check> failed, run <url>".
     A session that starts work therefore sees it without anyone waiting.
- **No `core/` change.** A game-agnostic gate or a fix to the core (J41 review later item 5: `pin_problems` and a shallow submodule's
  foreign tags) goes to warscape-core as a PR and stops there; the pin bump is a later job, filed as an open question.
- Do not change what `gates`, `proxy` or `harness-windows` test, only when they run and how they report; any test fix is for a race.

## Deliverables
1. The failure table, every row classed and guarded.
2. `gates.yml`: one run per commit; the failure-comment job; header comments updated.
3. The harness race fixes with their unit guards, each proved by a `-Repeat 20` dispatch.
4. `build.sh --docker smoke`; `tests/test_proxy_host.py` runs it; the harness host-tests local route as a repo test; unit tests for the
   route choices (inputs unchanged, CI, Windows PowerShell present, absent, opt-out) with the probes injected, as J41 did.
5. `tools/changed_inputs.py` excludes `proxy/runs/`, with a test.
6. `wsc jobs next|review|view` list open pull requests with failed checks.
7. `harness/README.md` Tests, `proxy/README.md` Build and `docs/REVIEW.md` updated where a rule changed; `CLAUDE.md` only if a rule
   for every session changes.
8. The warscape-core PR, if one is needed (link in the report).

## Proof (each with the command and its output or run id in the report)
a) Each fixed flaky case: one dispatch `-f only='<case>' -f repeat=20` on the final code commit, green.
b) The whole `harness-windows` suite: 20 dispatch runs on the final code commit with no `-Only` (fire them together, read them once
   later), all green. The row asks for 20 green runs on main; main cannot carry the fixes before the merge, so the job branch head is
   the proof and the reviewer reruns a dispatch on main after merging (say so in the report).
c) One commit pushed to an open PR starts exactly one workflow run, which reports all four required checks.
d) A deliberately failing check on a throwaway PR (e.g. a `brief/` or `plan/` branch you close afterwards, or the J42 PR itself with a
   temporary failing commit, reverted) gets exactly one comment, and `wsc jobs next` prints it; revert, and the next run is green.
e) On the PC: the full `python3 core/wsc.py gates` runs the smoke test and the harness host tests when their inputs changed (times in
   the report); with no `proxy/` or `harness/` change both skip in under 2 s; `WSP_HARNESS_TESTS=skip` prints the warning.
f) The failure table shows a guard (or "branch bug") for every class.

## Kill criteria
- A flaky case does not fail once in 3 dispatches of `-Repeat 20`: stop chasing it, record the runs, class it "flaky, not reproduced",
  keep its timeout as is, and move on.
- No route for one run per commit keeps every required check on the PR head commit and CI on branches without a PR: stop after 2
  attempts, keep today's double run, report the options tried.
- The harness host tests cannot run from the `tests` gate within its 600 s timeout on the PC: keep the route as a separate command the
  gate names in a warning, and report the measured time; do not raise the core default.
- Any step would need the game or the watcher on the PC: it does not; stop and ask if one seems to.

## Finish
Write `jobs/J42/report.md`: what was built, the failure table's summary (counts per class, the guard for each), proof runs a) to f) with
commands, times and run ids, the core PR link if any, deviations from this brief and why, open questions (the pin-bump row if a core PR
was opened; the post-merge dispatch on main for the reviewer). Then `wsc reg set jobs J42 status=review report=jobs/J42/report.md`.
