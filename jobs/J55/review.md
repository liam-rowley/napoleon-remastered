# J55 review

## Round 1 (2026-11-01, branch job/J55 at 0cd1915)

**Verdict: merge.**

Fresh session; did not build or fix this branch. Read the brief, the report, `docs/REVIEW.md` and the diff (290 files, 13 outside
`registries/`).

### Machines
- CI on `0cd1915`: `gates`, `proxy`, `harness-windows` and `changes` green; `viewer` skipped. `policy` is red only for "no review yet"
  and "row not `done`", which this round answers. `python3 tools/pr_policy.py --branch job/J55 --base origin/main` locally gives the
  same two reasons. Rule 79 no longer fires, since J58 merged.
- `python3 core/wsc.py gates` locally: 11 ok. The `tests` gate failed with 1 failure and 11 errors, none from this branch:
  - 11 `test_pc_deploy.Deploy` errors: `pc_deploy: refusing: tasklist: Napoleon.exe is running`. The game was running on the PC
    (the J8 session); see later item 2.
  - `test_job_sh.JobSh.test_ctl_without_an_ini_uses_the_registered_default` fails the same way in a clean `origin/main` worktree,
    so it is pre-existing and local; see later item 3.
- The branch's own tests pass: `python3 -m unittest tests.test_registry_merge tests.test_pr_policy tests.test_jobs`, 121 tests, OK.

### Claims against evidence
- Core PR [liam-rowley/warscape-core#11](https://github.com/liam-rowley/warscape-core/pull/11) is MERGED as `d4c2677`. `git -C core
  describe --tags --exact-match` gives `v0.6.0`, and the `core_pin` gate says "core 0.6.0 as pinned (tag v0.6.0), unmodified". The
  version deviation (v0.6.0, not v0.5.0, because J40 took v0.5.0) is named in the report and correct.
- No `registries/*.md` is tracked. `registries/` holds `jobs/`, `tools/`, `engine_facts/` and six `.jsonl` files. `wsc.toml` has
  `[views] commit = false` and `[storage] dir = ["jobs", "tools", "engine_facts"]`. `.gitattributes` drops the `linguist-generated`
  line and keeps `registries/*.jsonl merge=union`, which cannot match the per-row files. `_scratch/` was already ignored.
- `wsc jobs check`: 58 rows, ok. `wsc find J55` hits `jobs J55 [review]`. `wsc jobs view --no-open --offline` reports 58 jobs. All
  three run on the new layout.
- Stale references: `git grep` for `jobs.jsonl|tools.jsonl|engine_facts.jsonl|registries/*.md|jobs.md` outside earlier jobs' briefs,
  reports and run READMEs (history) finds only the deliberate pre-J55 fallbacks in `pr_policy.py`, `jobs.py` and their tests.
  `.github/` names no registry path.
- I did not re-run the measurement: its script was not committed, as the report says. The table is consistent with the merge
  shas I spot-checked (J50 `2a94296` and J51 `4a7f087` are the heads of their review worktrees). The lasting check is
  `tests/test_registry_merge.py`, which passes.

### Brief
All five deliverables are present. The decisions are followed: opt-in switches, a reversible Windows-safe file name rule, indented
canonical form with the reason given, `reg migrate`, the three registries moved and the rest kept, `PLAN` list on the new path, and
brief branches limited to their own row file. Kill criteria were respected: rule 79 was not weakened and went to J58 instead. The
three deviations are named with reasons.

### Risk-first: `tools/pr_policy.py`
I read this one in depth because it is the merge gate: a misread row either blocks every merge or lets an unreviewed job through.
- `rows_at(ref)` uses `ls-tree` on `<ref>:registries/jobs`. A missing tree raises `CalledProcessError` (`git()` is `check=True`), and
  the code then falls back to the JSONL. The `cat-file --batch` parse steps over header, size and the trailing LF correctly. The input
  names come from `ls-tree`, so a `missing` line cannot occur.
- `check()` compares only the two `{id: row}` dicts (`other_rows_changed`, `head_rows.get(jid)`). The rules are therefore identical for
  either layout, and for a pre-J55 base with a per-id head, which is this PR's own case. `test_pr_policy.py` covers that mixed case and
  still refuses a change to another row.
- `jobs.py` `branch_rows` still makes one batch (per-id spec first, JSONL second, first present wins), with a test for a pre-J55 branch.

### Findings

**Blocker:** none.

**Should-fix:** none.

**Later:**
1. **Open job branches cut before J55 need one transition merge (this merge changes the layout they must meet).** `job/J8` (queued,
   being built now) changes `registries/tools.jsonl`, `engine_facts.jsonl`, `config_keys.jsonl` and their `.md` views against its base.
   After J55 merges, merging `main` into it gives modify/delete conflicts on `tools.jsonl`, `engine_facts.jsonl` and the views. To
   resolve: take main's side (delete the old files and views), then re-add J8's rows (`wsc reg add tools <path>` for each changed tool
   header, and `wsc reg add engine_facts --json ...` for each new fact). `config_keys.jsonl` stays JSONL and merges as before. The
   failure is guarded: keeping a JSONL copy beside the per-row folder is a core error ("a second copy in the storage the repo does not
   declare"), so the gates fail rather than silently keeping two copies. A `wsc reg` helper that folds a pre-J55 branch's JSONL rows
   into per-row files would make this one step. That is worth a core backlog row only if more than J8 is caught, and J8 is the only
   in-flight job branch today.
2. `tests/test_pc_deploy.py` `Deploy` (11 tests) errors instead of skipping when the game is running on the PC. `InstallPacks` in the
   same suite already skips with "a game is running". The local `tests` gate fails for as long as a PC session plays. This predates
   J55. The fix is the same `skipIf` guard.
3. `tests/test_job_sh.py:173` `test_ctl_without_an_ini_uses_the_registered_default` fails locally on `main` too, with empty stderr where
   `/c/napoleon_remastered_pc/ctl` is expected. This predates J55 and is local to Windows Git Bash.
4. Open questions 2 to 4 in the report (moving `assets` and the small registries, Empire, row delete B25) stand as written. None
   blocks this merge.
