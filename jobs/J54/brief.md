# J54: CI skips a slow job whose input tree is unchanged; reviews see branch CI

Phase 1, tooling (pipeline audit 2026-10-31, items 1 and 3). Two fixes. (1) CI's `changes` job diffs against the merge base with main, so
once a branch touches an input set, every later push re-runs the slow jobs even when it only adds a report or a review: replaying
`tools/changed_inputs.py` over the 27 job branches (275 first-parent commits), harness-windows ran 119 of 206 times, proxy 163 of 234 and
viewer 72 of 93 on commits whose inputs were byte-identical to the parent (J22 review round 2: 5m50s of Windows runner for a `review.md`
push). Rule 79 for CI: a slow job that already passed on this exact input tree is skipped. (2) The pull request is created by the
reviewer at merge time, so `red_prs`, `tools/ci_notify.py` and the reviewer all start blind: J12 round 1 and J50 both say no pull
request existed yet, and J12 gave `merge` while the last five branch runs were red (41247714835: gates, proxy, viewer), costing a further
Opus session for two CI-fix commits. The pull request is opened when the job reaches review, and `jobs review` reads the branch's checks.

Model: Sonnet. CI YAML, Python tooling and tests in this repo; no engine, DLL or PC work. Budget about 120 tool calls; at the cap, stop,
commit, report what is left. Subagents are not needed. Waiting for CI belongs to GitHub: push and read the run once it has finished
(`gh run view <id>`), never a polling loop.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J54`). Read `docs/DECISIONS.md` (D21, D32, D33, D36), `docs/REVIEW.md` ("Output"),
  `docs/CI_FAILURES.md`, `.github/workflows/gates.yml` and `policy.yml` in full (their header comments are the contract: one run per
  commit since J42, a skipped job counts as passed for required checks and auto-merge), `tools/changed_inputs.py`, `tools/ci_notify.py`,
  `tools/pr_policy.py` (the `job/` rules), and in `tools/verbs/jobs.py`: `red_prs`, `failed_prs`, `build_steps`, `fix_steps`,
  `review_steps` and the `review`/`fix` path of `run()`. Tests: `changed_inputs` is tested today inside `tests/test_proxy_host.py` and
  `tests/test_harness_host.py`; put the new hash tests in their own `tests/test_changed_inputs.py`. Also `tests/test_jobs.py` and
  `tests/test_ci_notify.py`.
- Search before writing: `python3 core/wsc.py find changed inputs ci cache notify`. Extend `changed_inputs.py` and `jobs.py`; add no new
  tool for what they can do. Never change `core/`.
- `jobs/J41/report.md` (the input sets and the local route) and `jobs/J42/report.md` (one run per commit, the notifier) are the two jobs
  this one builds on.

## Target facts
Check each again before relying on it:
- `changes` checks out with `fetch-depth: 0` and no submodule; `core` is a gitlink, so `git ls-tree HEAD core` gives the pinned core
  commit without the submodule.
- `INPUTS` in `changed_inputs.py` is the one list of what feeds `proxy`, `harness` (harness-windows) and `viewer`; a workflow change is in
  all three sets; `proxy/runs/` and `viewer/runs/` are excluded (J42).
- `workflow_dispatch` runs exist only to run harness-windows with `-Only/-Repeat` (J19): they must never be skipped.
- GitHub Actions caches are scoped by branch: a run can restore caches written on its own branch or on the default branch (main), never on
  a sibling branch; entries unused for 7 days are evicted. Check this against GitHub's documentation and say what you found in the report.
- `proxy/README.md` and `viewer/README.md` name `gh run download <run id> -n proxy-d3d9-napoleon` / `-n viewer-wasm` as the fallback
  when Docker is down (D31): a skipped job uploads no artifact, so the fallback must still find the run that built those inputs.
- `policy` runs on `pull_request` and fails on a job branch until its `review.md` says `merge` and its row is `done`. Opening the pull
  request at review time would make every job in review show a red `policy` check (in `red_prs`, and a `ci_notify` comment) for the
  whole review: the decisions below avoid that.

## Decisions already made for this job
- **Tree hash per input set.** `changed_inputs.py` gains a function (and output lines `proxy_tree=<hash>`, `harness_tree=<hash>`,
  `viewer_tree=<hash>`) that hashes, for one set, the `git ls-tree -r --full-tree HEAD` entries whose path the set's regex matches (mode,
  object sha and path, sorted), plus the set's name and a version salt in the code (bump it to invalidate every marker). One function, used
  by CI and the tests; the existing `proxy=`/`harness=`/`viewer=` lines stay as they are.
- **The marker.** Each slow job, as its last step and only on success, writes a small file naming its run id, attempt, commit and tree hash
  and saves it with `actions/cache/save` under the key `ci-pass-<salt>-<set>-<tree hash>`. A `workflow_dispatch` run writes no marker.
- **The skip.** `changes` restores each set's key with `actions/cache/restore` and `lookup-only: true`; a slow job runs when its inputs
  changed against the base (as today) AND no marker exists for its tree hash; `workflow_dispatch` keeps forcing harness-windows. When a job
  is skipped for a marker, `changes` writes one line to the step summary naming the set, the hash and the run id that passed it (read the
  marker: restore it fully for a hit, it is tiny), so the D31 `gh run download` fallback still has a run to download from. Say this in
  `proxy/README.md` and `viewer/README.md` (one sentence each) and in the `gates.yml` header comment.
- **Fails safe.** A cache error, a missing hash or an unknown base runs the job. Never skip on main pushes for a hash written on another
  branch (the scoping already prevents it: say so in the comment, do not rely on it silently).
- **Draft pull request at review time.** `build_steps` and `fix_steps` end with: open the pull request if none exists, as a draft
  (`gh pr view job/<id>` first; else `gh pr create --draft --base main --head job/<id> --title "<id>: <title>"`, body = the report's first
  paragraph), never `gh pr merge`. `policy.yml` gets `types: [opened, synchronize, reopened, ready_for_review]` and its job runs only when
  the pull request is not a draft, so a job in review shows no red `policy`; `gates`, `proxy`, `viewer` and `harness-windows` still attach
  to the commit (push runs, J42), so the draft shows them and `ci_notify` comments on a red one. `docs/REVIEW.md` "Output" and
  `review_steps`: a `merge` verdict runs `gh pr ready job/<id>` before `gh pr merge job/<id> --auto --squash` (create the pull request
  first if none exists, as today); any other verdict leaves the draft open. D32 is unchanged in substance; no new decision row is needed.
- **`jobs review` reads the branch's checks.** After it picks the branch, it reads the head commit's check runs
  (`gh api repos/{owner}/{repo}/commits/{sha}/check-runs`, owner and repo from `gh repo view --json nameWithOwner` or the origin URL), and
  its steps name every check that failed or is still running, with its URL, above the review steps ("read docs/CI_FAILURES.md; a red
  required check is a blocker for a merge verdict"). `--offline`, a missing `gh` or an API error print one line saying the checks could not
  be read (never an exception, as `red_prs` does). `jobs fix` prints the same block.
- **Out of scope:** changing the input sets themselves; caching build outputs (only pass markers); skipping `gates`; the `policy` rules
  in `pr_policy.py`; anything in `core/`.

## Deliverables
1. `tools/changed_inputs.py`: the per-set tree hash and its output lines, its header updated.
2. `.github/workflows/gates.yml`: marker restore in `changes`, the combined `if:` on `proxy`, `viewer` and `harness-windows`, the
   marker save as each one's last step, the step-summary line, the header comment.
3. `.github/workflows/policy.yml`: draft pull requests skip `policy`; `ready_for_review` runs it.
4. `tools/verbs/jobs.py`: `build_steps` and `fix_steps` end with the draft pull request; `review_steps` and `docs/REVIEW.md` add
   `gh pr ready`; `jobs review` and `jobs fix` print the branch's failed and running checks. Update the `jobs.py` docstring.
5. Tests, at least: a `review.md`-only commit and a `proxy/runs/` commit give the same tree hash for every set as their parent; a change
   to a proxy input changes only the proxy hash; a workflow change changes all three; the salt changes every hash; the check-run reader
   with a fake `gh` (failed, running, all green, API error, offline); the review and fix steps name a red check; the build and fix steps
   contain the draft `gh pr create` and no `gh pr merge`.
6. CI proof on this branch: this branch changes the workflows, so its first push runs everything; then push a commit that changes only
   `jobs/J54/report.md` and show that run with `proxy`, `viewer` and `harness-windows` skipped for a marker and its summary naming the
   passing run. Quote both run ids. Then a replay over the 27 job branches with the new rule: how many slow-job runs each would have
   skipped (harness-windows, proxy, viewer) and the runner minutes saved, using the per-job durations in the row.
7. `python3 core/wsc.py gates` green.

## Kill criteria
- `actions/cache` cannot do an exact-key lookup without downloading, or its result cannot drive a job-level `if:`: stop the marker work
  (keep the hash, the draft pull request and the check reader), report what you found, and propose another store to Liam (an artifact
  lookup, a commit status keyed by tree hash).
- A skipped job stops counting as passed for a required check or for `gh pr merge --auto` (D32): stop and ask Liam.
- A draft pull request cannot carry the push-run checks or the notifier comment: keep the pull request non-draft only if `policy` can be
  kept green-or-skipped for a job in review without weakening `pr_policy.py`; otherwise stop and ask.
- Over about 120 tool calls: stop, commit, report what is left.

## Finish
Write `jobs/J54/report.md`: what was built, the cache-scoping finding, the two CI run ids and the replay numbers, the test list and the
gates result, deviations from this brief and why, open questions (for example whether `gates` itself should be skipped by the same rule).
Then `wsc reg set jobs J54 status=review report=jobs/J54/report.md`.
