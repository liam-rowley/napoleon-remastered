# J93: Liam decides: player install on the real folder, and the held-back screens

Phase 5, a sitting with Liam at the PC plus one small code change. Source: the Later sweep (`docs/audits/LATER_TRIAGE_2026-11-04.md`, J53 review
Later 1, 3 and 4). `upscale/pc/play.py` (J53, scale mode J66) has only run on a fake game folder; its first run on the real folder is the
next thing Liam does by hand and nothing else waits on it. The watcher-side hazard (a forgotten play install is picked up by the next agent
job) is core BACKLOG line B79 and is not this job.

Model: Opus, reason: Liam's Opus across the board (`D261107-5dc6`); Python edit and a guided PC sitting, no engine work. Budget about 120 tool calls; at the cap, stop, commit,
push, report what is left. No subagents. Waiting and polling belong to the harness.

## Start
- Follow `CLAUDE.md` (Jobs: branch `job/J93`). Read `jobs/J53/brief.md`, `jobs/J53/report.md` and `jobs/J53/review.md` (Later 1, 3, 4), then
  `docs/DECISIONS.md` D38 (held-back rule), D40 and D55.
- Code: `upscale/pc/play.py` (`install`, `uninstall`, `status`, `lock_holder`, `common_refusals`) and `tests/test_play.py`. Tool ids by
  `python3 core/wsc.py find play`; the packs come from `python3 core/wsc.py upscale pack --play` (or `uiscale build` for `--scale 2`).
- The game is started only by Liam from Steam in this job: it is a play test, not a watcher run, so no `job.sh` launch happens.

## Part 1: the code change (no PC, do first)
`install` refuses while an agent job holds the game lock (`common_refusals` calls `lock_holder`); `uninstall` does not. Make `uninstall`
refuse the same way, with the same message, sharing the one check (do not copy it). Keep the existing refusal for a running game.
Add tests in `tests/test_play.py` for: lock fresh (refuses, nothing moved), lock older than 1200 s (proceeds), no lock file (proceeds).
`python3 core/wsc.py gates --fast` stays green. Only `upscale/pc/play.py`, its tests and the tools row header change.

## Part 2: the sitting with Liam
Ask before starting. Check first that no agent holds the lock (`bash core/harness/job.sh status`) and that the game is closed.
Dry look: `python3 upscale/pc/play.py status` and `python3 core/wsc.py setup`. Then put each decision to Liam in this order, record his
answer verbatim in the report, and do what the answer says. Defaults are recommendations; Liam's answer wins.

### Decision 1: when to run the first real install
- Options: (a) now, in this sitting; (b) later, the agent only prepares and checks (`status`, packs built, `pc_deploy.py status` clean).
- Default: (a), because the fake-folder tests cannot show a real-folder surprise and uninstall is non-zero on any difference.
- On (a): take a snapshot note (file count of the game folder from `play.py status`), run `play.py install` with the roles from Decision 2,
  show Liam the printed plan, wait for him to launch from Steam. On (b): stop after the checks, write the exact commands into the report.

### Decision 2: which art to install
- Options: (a) the default four roles at 2.5x (`install`); (b) `--all` minus the held-back screens (adds `loading_screen`, `event_picture`,
  42 % of the extra bytes); (c) `--scale 2` (whole vanilla UI at 2x for 4K, D40) if the J66 pack exists.
- Default: (a) for a first real run, because it is the smallest change to the folder; (c) next if he plays at 4K.
- Agent: build the packs if missing (`upscale pack --play --roles ...` or `uiscale build`), then install the chosen set.

### Decision 3: the 28 held-back loading screens (6 DXT sides not a multiple of 4, 23 over 4096 px, `2.dds` in both)
- Options: (a) keep them out (vanilla art, game safe); (b) a probe job tries them: a new `needs_brief` row on a `plan/` branch, because the
  engine may crash or draw garbage; (c) include them for one play test with the crash-dump and log folders checked straight after.
- Default: (a) now; file (b) only if Liam says the 28 screens are visibly missing during play. Never (c) without Liam saying it twice.
- Agent: on (b), write the row description (probe a non-multiple-of-4 DXT and a texture over 4096 px under the watcher), do not build it here.

### Decision 4: how Liam judges the result after the play test
- Options: (a) he tells the agent in chat what looked wrong or slow, and the agent records it; (b) the agent also reads the proxy log and
  `dumps\` after he quits (always done) and reports numbers; (c) a memory figure: Task Manager peak working set of `Napoleon.exe` read by
  Liam at the main menu, in a land battle and on the campaign map, three numbers.
- Default: (a) plus the always-on log and dump read, plus (c) because J53 never measured memory and the scene JSONs carry no figure.
- Agent: write the three numbers, the log verdict, the dump count (expect 0) and Liam's words into the report; no pass/fail invented.

### Decision 5: uninstall now or keep the install
- Options: (a) uninstall straight after the test; (b) keep it installed for more play and uninstall at the end of the day.
- Default: (a). Reason: a forgotten install is picked up by the next agent job until B79 lands.
- Agent: on (a) run `python3 upscale/pc/play.py uninstall` and report its exit code and printed diff; it must end "identical". On (b) write
  in the report that the install is live, and say it again as the first line of the report.

## Deliverables
1. The Part 1 change and tests, merged with the job.
2. `jobs/J93/report.md`: each decision with Liam's answer and the date, the commands run, the install and uninstall output (exit codes,
   the "identical" line or the diff), the three memory numbers, log verdict, dump count, and what Liam saw of the held-back screens.
3. Rows or briefs the answers produce (Decision 3b) proposed in the report's open questions, never queued by this job.

## Kill criteria
- `uninstall` exits non-zero or prints a diff on the real folder: stop, do not repeat, do not delete anything by hand, report the diff
  and let Liam decide (the packs are in `<state>\_to_delete`). Never run git or write in the game folder yourself.
- Any crash dump after the first launch: stop, collect the dump and log names, uninstall, report; do not relaunch.
- The exe check fails (`wsc setup`, `pc_deploy.py status`): stop and report; never touch the exe.

## Open questions
- Whether `uninstall` should also move the lock check into `pc_deploy.py` for every caller: left to core BACKLOG B79 with the watcher side.

## Finish
Write `jobs/J93/report.md` with the headings `wsc jobs check` requires (what was built, evidence with run ids, deviations from the brief
and why, open questions), then `wsc reg set jobs J93 status=review report=jobs/J93/report.md`. Every commit carries the
`Claude-Session` trailer.
