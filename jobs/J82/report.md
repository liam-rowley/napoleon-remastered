# J82 report: Review Later sweep and housekeeping

Written by the orchestrator from the builder subagent's hand-back (the harness refuses a subagent's write of a report file); the text is
the builder's own apart from this note and the model line. Model: the orchestrator launched the builder with model Sonnet (the row's
model). Commits on `job/J82`: 0d8e053 (housekeeping) and d8b05b9 (the triage record).

## What was built
- **Counts.** The counting rule is in `docs/audits/LATER_TRIAGE_2026-11-04.md`.
  - A Later block is any of these: a "Later" or "Still open (later...)" heading, a bold `**Later` line, or an inline `- **later:**`
    item. A bullet is a top-level list item, and nested bullets belong to their parent.
  - Result: 240 bullets in 54 reviews, and all 54 reviews have a block.
  - The audit's 135 in 28, and the heading-only scan's 139 in 29, missed the bold-line blocks and the second and third blocks of
    fix-round reviews.
- **Fates.** Every bullet has exactly one:
  - already done: 107, each cited;
  - dropped: 53, each with its reason;
  - a core BACKLOG line: 29 bullets in 19 lines (B64 to B82), plus B83 and B84 from the Empire learnings;
  - a needs_brief row: 51 bullets in 10 rows.
  - 107 + 53 + 29 + 51 = 240.
- **The step 7 check.**
  - The record has 240 table rows, and the counting script counts 240 bullets.
  - No fate cell is empty.
  - No needs_brief row is on `job/J82`: `git diff origin/main -- registries` is empty.
- **The plan branch** `plan/later-triage-2026-11-04` (commit 8362716), pushed separately for Liam to merge (D50). Ten needs_brief rows:

  | Row | Scope |
  |---|---|
  | J89 | Lua probe follow-ups to J78 and stale comments (carries 20 passes) |
  | J90 | console guard for `transport_to_hlci` and the diplomacy getter stall (Opus: crash bisecting) |
  | J91 | harness adapter follow-ups |
  | J92 | orders route follow-ups |
  | J93 | Liam decides: player install |
  | J94 | tools, tests and gates small fixes |
  | J95 | discovery small fixes |
  | J96 | upscaler guards and uiscale probes |
  | J97 | viewer housekeeping |
  | J98 | start-up soak (an Empire learning) |

  - `wsc jobs check` on that branch: 98 rows, ok. `wsc policy --branch plan/later-triage-2026-11-04 --base origin/main`: ok (10 files).
- **The core branch** `plan/backlog-from-napoleon-later` in warscape-core (commit 39339a8), pushed separately.
  - It adds B64 to B84 to `docs/BACKLOG.md`: 19 lines from the bullets, plus B83 (`%~dp0`) and B84 (PowerShell alias shadowing) from
    the Empire learnings.
  - `wsc policy`: ok. `wsc gates --fast`: 13 ok.
  - `docs/BACKLOG.md` came to 30,606 bytes against the 30,720-byte `doc_size` cap, so the lines were shortened to fit. The next lines
    added there need the file split first.
- **Housekeeping** (0d8e053):
  - **a. The `summary.json` ignore rule.** `.gitignore` gains `harness/runs/*/summary.json`.
    - `git check-ignore -v harness/runs/20261101_j23x/summary.json` prints `.gitignore:32:harness/runs/*/summary.json`.
    - `git ls-files harness/runs | grep -c summary.json` still gives 7: the tracked files stay tracked.
    - The rule does not match J24's `ladder_ctl_summary.json`.
  - **b. The live policy route.** In `tools/ci_failures.py`, `GUARDS["policy"]` now names
    `python3 core/wsc.py policy --branch <kind>/<id> --base origin/main`.
    - `docs/CI_FAILURES.md` was regenerated for 2026-10-29T00:00:00Z to 22:20:00Z: 7 insertions and 7 deletions, all of them guard
      cells.
    - The six "Run python tools/pr_policy.py" run cells stay, as history.
    - `tests.test_ci_failures`: 3 ok.
  - **c. `test_ctl_without_an_ini_uses_the_registered_default`.** The cause is in the test, not the core.
    - The registered default for `dev.ctl_dir` is the real `C:\napoleon_remastered_pc\ctl`, so the old test wrote a `ping` request
      into the live state folder.
    - On the PC, whatever answers requests there (a running game with `dev.ctl=1`) turns the expected rc 124 and stderr into a plain
      answer with empty stderr. On CI the folder does not exist.
    - The fix touches the test only. It builds a temporary game root with a temporary registered default and passes it through
      `WSP_GAME_ROOT`, and it now asserts rc 124 and the withdrawn `.cmd.expired` on every OS.
    - It passes alone and in the full gates.
    - The old body was not run, because that would touch the real state folder. The cause is therefore inferred from the code and the
      five reviews, not seen as an rc and stderr.
- **Empire learnings.** All three are in `../empire-remastered/docs/learnings/LEARNINGS_HARNESS.md`, read only:
  - `%~dp0` in watcher cmd jobs: core B83.
  - PowerShell alias shadowing: core B84.
  - The start-up soak: row J98.
  - `&` in save names is core W25, cited.
- **The record.** `docs/audits/LATER_TRIAGE_2026-11-04.md` (d8b05b9) holds the counting rule, the fate summary, the details of the plan
  and core branches, the housekeeping outcome, the Empire learnings, and the 240-row table with one row per bullet.

## Deviations from the brief and why
- **Branch names.** The plan rows are on `plan/later-triage-2026-11-04`, not `plan/later-sweep-2026-11`, and the core lines on
  `plan/backlog-from-napoleon-later`, not `backlog/j82-later-sweep`. The orchestrator's prompt named both. The BACKLOG lines are shortened
  to fit the 30 KB cap.
- **Core judged at v0.22.0.** Core-side bullets are judged against warscape-core main (v0.22.0), because napoleon pins v0.10.0.
  "Already done" for them cites core files and lines, not shas; the fixes reach napoleon with row J64.
- **Checked by grep only.** Some "already done" and "dropped" cells were read by grep, not by running the code; each such cell names the
  file and line. Spot-check these: J62-L3, J41-L1, J14-L1, J20-L3, J46-L3.
- **`test_ctl_without_an_ini` was not run in its old form**, so there is no red-then-green (see c above).
- **A file was briefly placed inside `core/`.** An edited `job.sh` was copied into `core/harness` for a read-only probe of how `ctl_dir`
  resolves, then deleted. `git status` in `core/` is clean, and nothing in `core/` is committed.
- **Ten rows.** Question 2 of the brief asked for about 10 to 15.

## Open questions
The brief's defaults were taken; each stays open for Liam.
1. One job for the triage. Taken, and the budget held (about 60 tool calls).
2. Rows grouped by owning area. Taken: ten rows.
3. The seven tracked `harness/runs/*/summary.json` stay tracked. Taken.
4. Scope calls become rows that start "Liam decides:". Taken for J93; J91 item 1 and J96 items 1 to 3 hold such calls inside their rows.
5. A suggested decision, for Liam to sign if he wants it (J82 may not edit DECISIONS.md): a Later bullet gets its fate in the review
   itself (a row, a BACKLOG line or a dated drop), enforced by core W32's later registry. When W32 reaches napoleon, rows J89 to J97 and
   the trigger lines of B64 to B84 move into it.
6. Liam pushes the decision on the plan branch: he merges it (D50).
