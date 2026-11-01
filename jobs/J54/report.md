# J54 report: CI skips a slow job whose input tree is unchanged; reviews see branch CI

Built: CI's `changes` job now skips `proxy`, `viewer` and `harness-windows` when the same input tree already passed. Each slow job
saves a pass marker in `actions/cache`, keyed by a hash of its input set. The builder opens the job's pull request as a draft when
the job reaches review; `policy` skips drafts, and the reviewer's `gh pr ready` runs it. `jobs review` and `jobs fix` print every
check on the branch head that failed or is still running.

## What exists

1. **Tree hash per input set**, `tools/changed_inputs.py`: `tree_entries()` reads `git ls-tree -r --full-tree <ref>` as (path, mode
   object). `tree_hashes()` hashes, per set, the sorted entries its `INPUTS` regex matches, plus the set's name and `SALT` (now `'1'`).
   `core` is a gitlink, so its pinned commit is hashed without the submodule. The script now also prints `proxy_tree=`,
   `harness_tree=`, `viewer_tree=` (64 hex characters, empty when the tree cannot be read) and `tree_salt=`. The existing
   `proxy=`/`harness=`/`viewer=` lines are unchanged.
2. **`.github/workflows/gates.yml`**:
   - `changes` restores each changed set's key (`actions/cache/restore@v5`, `ci-pass-<salt>-<set>-<hash>`, `enableCrossOsArchive`).
     It does this only on a push, only for a set whose inputs changed against the base, and only when the hash is not empty.
   - A `run` step then gives the combined answer: a set runs when its inputs changed AND no readable marker (a `run=<digits>` line)
     exists. A skip writes one line to the step summary: the set, its tree hash, and the run, attempt and commit that passed it.
     For `proxy` and `viewer` the line also has the `gh run download <run> -n ...` command.
   - `proxy`, `viewer` and `harness-windows` end with two steps that run only on success of a push run: write
     `.ci-pass/<set>/marker.txt` (set, tree, run, attempt, commit), then `actions/cache/save@v5`. `harness-windows` writes it with
     `shell: bash` and saves it cross-OS, so the Linux `changes` job can restore it.
   - A `workflow_dispatch` run neither reads nor writes markers, and still forces `harness-windows`.
   - The header comment states the rule, the fail-safe cases and the cache scoping. `proxy/README.md` and `viewer/README.md` say
     where to download from when the job was skipped.
3. **`.github/workflows/policy.yml`**: `types: [opened, synchronize, reopened, ready_for_review]`, and the `policy` job has
   `if: github.event.pull_request.draft == false`. Its `notify` job needs `policy` and runs on `failure()`, so it is skipped too.
4. **`tools/verbs/jobs.py`**:
   - `draft_pr_step()` ends `build_steps` and `fix_steps`: `gh pr view job/<id>`, else `gh pr create --draft --base main --head
     job/<id> --title "<id>: <title>" --body "<first paragraph of the report>"`, and "never merge it". `fix_steps` takes the title
     from the branch's row.
   - `review_steps`, on a merge verdict: pr_policy ok, then `gh pr ready job/<id>`, then `gh pr merge job/<id> --auto --squash`.
     Any other verdict leaves the draft open.
   - `branch_checks()`: one `gh api repos/{owner}/{repo}/commits/<sha>/check-runs?per_page=100` call. gh fills owner and repo from
     the clone's origin. The endpoint's default `filter=latest` gives the newest run of each name.
     - It names every check that failed, was cancelled or is still running, with its URL, under "read docs/CI_FAILURES.md; a red
       required check is a blocker for a merge verdict".
     - Otherwise it prints one line: all green, no runs yet, `--offline`, an unknown head, or an error from gh (never an exception).
     - `jobs review` and `jobs fix` print it above their steps.
   - The module docstring says all of this.
5. **`docs/REVIEW.md`**: "Output" adds two rules: read the branch's CI before the verdict (a red required check blocks `merge`), and
   any verdict but `merge` leaves the draft open. "Merging" adds `gh pr ready` between `gh pr view`/`create` and `gh pr merge
   --auto`, and says a set is also skipped when the same input tree already passed.

## Cache scoping (checked 2026-11-01 against GitHub's "Dependency caching" reference)

- "Workflow runs can restore caches created in either the current branch or the default branch (usually `main`)"; pull request runs
  can also restore from the base branch; "Workflow runs cannot restore caches created for child branches or sibling branches".
- Entries not accessed in over 7 days are evicted; the repository limit is 10 GB by default, oldest last access goes first.
- An existing key cannot be overwritten ("You cannot change the contents of an existing cache"). A second save of a passed tree (a
  rerun) only logs a warning.
- Cross-OS restore needs `enableCrossOsArchive` on both sides (the cache version stamps the path and compression, and Windows-only
  unless that flag is set). Both sides set it here. Run 1 below shows that the marker saved on Windows was found by the Linux job.
- So a main push only sees markers written on main, and a job branch sees its own markers plus main's. The brief's facts hold.
  `gates.yml`'s header says so.

## Evidence

- **Run 1, `41285549133`** (commit `29a6c71`, the first workflow change): every job ran and passed (`proxy` 1m53s, `viewer` 4m37s,
  `harness-windows` 5m48s). It saved three markers, all `refs/heads/job/J54`:
  - `ci-pass-1-proxy-ec96f486…`, 367 B
  - `ci-pass-1-viewer-02e98a99…`, 383 B
  - `ci-pass-1-harness-3253c0a0…`, 333 B, saved from Windows

  (`gh api repos/{owner}/{repo}/actions/caches?key=ci-pass-`)
- **Run 2, `41286632065`** (commit `92eef49`, `jobs.py` and a second workflow edit, which changes all three hashes): every job ran
  and passed again (`proxy` 1m54s, `viewer` 4m23s, `harness-windows` 5m14s). It saved three new markers (`ci-pass-1-proxy-efca5880…`,
  `-viewer-b58f133a…`, `-harness-5a28f316…`), which equal `python3 tools/changed_inputs.py` run locally at that commit.
- **Run 3, `41287008303`** (commit `63d719d`: `jobs/J54/report.md` and the J54 row, none of them an input): `changes` and `gates`
  passed, and `proxy`, `viewer` and `harness-windows` were skipped for a marker. The step summary of `changes`:
  - `` `harness` skipped: its input tree 5a28f316… already passed in run 41286632065 (attempt 1, commit 92eef49…) ``
  - `` `proxy` skipped: its input tree efca5880… already passed in run 41286632065 (…); its build: `gh run download 41286632065 -n proxy-d3d9-napoleon` ``
  - `` `viewer` skipped: its input tree b58f133a… already passed in run 41286632065 (…); its build: `gh run download 41286632065 -n viewer-wasm` ``

  The whole run took 35 s (run 2: 5m24s).
- **Draft pull request #96**, opened by the new build step. `policy` run `41287024794` (`pull_request`, opened as a draft):
  `policy` skipped, `notify` skipped.
- **Run 4, `41287792800`** (commit `e30d612`, which changes `jobs/J54/report.md` only: the brief's proof commit): `changes` and
  `gates` passed, and `proxy`, `viewer` and `harness-windows` were skipped. The summary has the same three lines as run 3, naming run
  `41286632065` and its `gh run download` commands. The whole run took 38 s.
- **The two run ids the brief asks for:** `41286632065` ran everything and wrote the markers; `41287792800` skipped all three for
  those markers.
- **Replay** (script: the scratchpad copy of `replay_j54.py`, method below). It covers every `origin/job/*` branch but J54: 27
  branches, 282 first-parent commits (the audit counted 275; J40 has had more commits since). Each commit is taken oldest first after
  the branch's merge base with today's `origin/main`.
  - Old rule: a set runs when its inputs differ from that base.
  - New rule: the same, minus every commit whose set tree hash already ran earlier on that branch.

  | job | old rule runs | identical to parent | new rule runs | skipped | runner minutes saved (row's durations) |
  |---|---|---|---|---|---|
  | harness-windows | 209 | 117 | 91 | 118 | 712 (6m02s each) |
  | proxy | 241 | 163 | 78 | 163 | 340 (2m05s each) |
  | viewer | 93 | 70 | 23 | 70 | 191 (2m44s each) |
  | **total** | | | | **351** | **1243 (20.7 h)** |

  This is an upper bound: it assumes every earlier run passed, and a failed or cancelled run writes no marker. Main's markers are not
  counted: a branch tree that matches main's is already "unchanged" against the merge base. The new rule skips more than "identical to
  parent" for harness-windows (118 against 117), because a tree that comes back (a revert) is skipped too.

## Tests

- `tests/test_changed_inputs.py` (new, 12 tests on a throwaway git repo with a `core` gitlink):
  - a `review.md`-only commit, a `report.md`-only commit and a `proxy/runs/` or `viewer/runs/` commit keep every hash
  - a proxy input (`proxy/napoleon/...`, `registries/engine_sites.jsonl`) changes only the proxy hash
  - a harness or viewer input changes only its own hash
  - a workflow change changes all three; a core pin bump changes proxy and harness; a mode change counts
  - the salt changes every hash
  - an unreadable tree or a git that cannot start gives empty hashes
  - `main()` prints the seven key lines in order
- `tests/test_jobs.py`:
  - `BranchChecks` (6 tests, fake `gh`): failed, cancelled and running checks are named with their URL and green ones are not; all
    green is one line; no runs yet; an API error, a missing `gh` and bad JSON each give one line; `--offline` and an unknown head make
    no call; `run()` for `review` and for `fix` prints the red check above its steps.
  - `Steps`: build and fix steps contain `gh pr view` and the draft `gh pr create`, and no `gh pr merge` or `gh pr ready`; review steps
    put pr_policy, then `gh pr ready`, then `gh pr merge --auto`, and leave the draft open otherwise.
- `python3 -m unittest tests.test_jobs tests.test_ci_notify tests.test_changed_inputs`: 90 tests, OK.
- `python3 core/wsc.py gates` (2026-11-01, at `63d719d`): 11 ok, and `tests` FAILED, with 8 to 11 errors depending on the moment.
  All of them are `tests.test_pc_deploy.Deploy` cases, and every one is the same refusal: "pc_deploy: refusing: tasklist:
  Napoleon.exe is running". Another session's J40 acceptance passes were starting and stopping the game on this PC during the job.
  The remaining 420 tests pass. CI, with no game running, ran the same `test_pc_deploy` green in `harness-windows` (runs 1 and 2).
  The pre-push `gates --fast` was green on every push.

## Deviations

- **One full restore per set instead of `lookup-only` plus a second restore.** `actions/cache/restore` with only `key` (no
  `restore-keys`) is already an exact-key lookup. A miss, the common case, downloads nothing. A hit downloads a file of a few hundred
  bytes, which the summary line needs anyway. `lookup-only` would add three steps and save nothing. The kill criterion's question
  still has a yes: `lookup-only` exists in `actions/cache/restore@v5` ("Check if a cache entry exists ... without downloading"), and
  `cache-hit` drives the job-level `if:` through the `run` step's outputs (run 3 shows it).
- **Owner and repo come from `gh`'s own `{owner}/{repo}` placeholders**, which gh fills from the clone's origin. This is the brief's
  "or the origin URL" route, done by gh, with no second call.
- **Cancelled counts as red** in `branch_checks` (as "did not finish"): on the head commit, a cancelled required check blocks the
  merge just as a failure does. `failed_prs` is unchanged.
- **`actions/cache@v5`**, the newest v5 (5.1.0, 2026-06-26; v6 exists but nothing here needs it).

## Open questions

- **The `gh pr ready` window.** A draft's `synchronize` gives the head a *skipped* `policy`, and skipped counts as passed.
  `gh pr ready` queues a real `policy` run on the same head a few seconds later. If `gh pr merge --auto` sees the pull request as
  mergeable in that window, it can merge before that run reports. The review steps run `python3 tools/pr_policy.py` locally first
  (it must say ok), so the rule is still checked once. A stricter fix would be to push the review commit only after `gh pr ready`,
  so the new head never had a skipped `policy`. That would make every review show a transient red `policy` on the old head. Liam
  decides whether that trade is worth it.
- **Should `gates` be skipped by the same rule?** Its inputs are the whole tree, so its hash would change on every commit except a
  pure rerun. Probably not worth it (40 s).
- **Main.** Main pushes can only find markers written on main, so a squash merge always reruns the slow jobs on main once. That is
  correct (main has a new tree) and cheap; nothing proposed.
- **`tests.test_pc_deploy.Deploy` depends on the real game being closed.** The tests use a fake game folder, but `pc_deploy.py`'s
  game-closed guard runs `tasklist` for the real `Napoleon.exe`, so the local `tests` gate fails whenever the game runs on the PC
  (the gates line above). A fix belongs in the core: tests passing `--assume-closed`, or a stubbed process check. It would be a
  warning for `docs/BACKLOG.md` in warscape-core. Not done here (`core/` is out of scope).
