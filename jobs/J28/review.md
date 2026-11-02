# J28 review

## Round 1 (2026-11-02, branch job/J28 at 35274aa)

**Verdict: merge.**

Reviewed cold from the brief, the report, `docs/DECISIONS.md` and `git diff main...job/J28` (115 files), in a session that did not build
or fix the branch.

### Machines
- `python3 core/wsc.py gates`: 10 ok, 2 warn, 0 failed. The warnings are `hooks` (this clone's hooksPath is set as an absolute path)
  and `tests` (506 passed, 18 skipped for numpy, Pillow, capstone or the viewer build not being installed here). `tools/pr_policy.py`
  before this review refused only for the missing review and the row not being `done`; after this commit it is run again before the
  merge (below). `wsc jobs check`: 65 rows, ok.
- PR #125 at 35274aa: `gates` green; `proxy` skipped (the same DLL input tree already passed); `harness-windows` still running when
  this was written. The merge is queued on green, so a red `harness-windows` keeps it open (D32).
- `origin/main` is an ancestor of the branch. `core/proxy/tools/build_id.py` at HEAD gives `715e9dfc0727`: the build all 20 passes
  ran on. The core gitlink is `97bb17c`, which is tag `v0.8.0` exactly; the warscape-core PR branch head `5cac151` and the tag have no
  difference under `proxy/src`.

### Claims checked against evidence
- **Rule 79:** 21 ledger lines. Pass 1 of `20261102_j28acc` names `6e913ef90a70-dirty` (the previous launch's build: core backlog
  B26/B31). Passes 2 to 20 and pass 1 of `20261102_j28acc2` name `715e9dfc0727`, watcher 1.2.0, all `pass`: 20 in a row on the
  final build, as the report says.
- **Install and threads:** `raw/i_proxy.log` and `raw/b2_stall_proxy.log` show the install line with every operand, and
  `threads: Present N, the game window's procedure N`, then `engine thread (the Lua pump) is N`, all the same id in both launches.
  This backs the J29 claim that the Present tick may call `OrdersMove`.
- **Orders:** `c1_move` ok; `d4_army_line` `failed`, with unit 1 (the general) outside tolerance, matching "8 of 9";
  `f2_stale_ptr` and `f3_bad_width` `refused`; `g2_siege_move` ok, though the unit never moved (`settle.moved: false`, centre
  16.7 m behind a front read back exactly), which is the weak check the report names; `g7_siege_cliff` `failed` (facing,
  lateral and `moved` fields); `i2_halt` and `i3_square` ok; `i5`/`i6` wedge `failed` ("no effect read back"). Each matches the run
  README.
- **Last PC orders build:** the step i orders ran on `6e913ef90a70-dirty` (core `5fe1188` plus local edits). The only later DLL change
  (`5fe1188..5cac151`, `proxy/src`) swaps `s.men <= 0` for `UnitOrderable(s, why)`, which does the same check with an extra `s.ok`
  test on a state `UnitLocked` already proved. The final build was not given a non-idle order; I accept that for a refactor this
  small.

### Brief
Deliverables 1 to 9 are present or named as cut. Deviations named with a reason: one generic `OrdersCommand` in place of
`order_halt`/`order_formation`; front centre and width are destinations, so the arrival check uses the live centre and `moved`
(C17 proposed in the core); the settle uses the engine's `is_moving`; ids are army-list positions pinned to a pointer per call; no
sound observation (headless). No 20 against 20 pass, because `land_40` is not on `main` (checked: J46 not merged). The kill
criteria were not reached. Nothing outside scope: no detours, the formation ctor and push rows stay unused and unkeyed, ships and
campaign are marked unreachable in the route.

### Risk-first reading
I picked `core/proxy/src/orders.cpp` (engine calls in a 32-bit process, no SEH) and `proxy/napoleon/adapter.cpp` (every offset
the driver uses) and read them in full. The rest I skimmed.
- Every precondition is checked before the first engine call: key, install, engine thread, arguments, the unit decode,
  `UnitOrderable`, the owner, battle and queue chain, the ground chain, and `Executable` (inside the exe image) on every function.
  The ground projection is checked for x/z identity and a finite y before the Selection is built.
- Install refuses unless all 20 sites are accepted and the object sizes fit the stack buffers (0x44 <= 0x80, 0x74 <= 0x200). It also
  cross-checks the position getter's entity offset against the entity-table site.
- The selection's vector buffers are released with the engine's own free after the command dtor, whether or not AddUnit took the
  unit. `CommandLocked` also checks that the dispatcher cell holds the current battle.
- The adapter's operand comments match the install line in the proxy logs (owner global `010e418c`, `+0xf8`, `+0x28048`, `[owner+0x450]+0x20`,
  entities `+0xadc`, active `+0xae8`, army `+0x1ec`/`+0xf0`/`+0xf4`, men `+0x204`).

### Findings
No blockers and no should-fix items.

**Later**
1. `harness/runs/20261102_j28pc/raw/f1_offmap.json`: the off-map fixture fails through an exception string
   (`RuntimeError: step read ...`) with empty `settle`, `check` and `evidence`. The outcome is right, but the brief asks for
   `failed` "with the evidence". A unit that leaves its army during the settle should be a structured failure from the core's
   `harness/ctl.py`, carrying the last state read and the step. This is a core change, so it belongs in the warscape-core backlog.
2. `harness/runs/20261102_j28pc/README.md:52`: the "never moved" check added after g2 is proven only by the host fixture
   (`tests/test_ctl.py` `test_a_unit_that_never_moves_fails_although_the_destination_reads_back`). On the PC, g7 also fails on
   facing and lateral offset, so no PC run shows the `moved` field alone catching a unit. Re-run g2's exact order the next time
   `siege_small` is up (J29's runs).
3. `harness/napoleon/adapter.json` `ctl.routes.orders`: `land` and `siege` repeat the same `tolerance`, `commands` and `settle` blocks
   verbatim, so a measured change to one can silently miss the other. A shared block, or a check that they match, would stop that.
4. The route lists `wedge` (proven to fail on this map's units), plus `diamond` and `loose` (never run). `order <unit> wedge` will
   always report `failed` here. That is honest, but J29 should not offer it as a working formation until the argument or unit-type
   question is answered (report's open question).
5. `jobs/J28/report.md` Open questions offers the acceptance identity bug as a new core backlog candidate. It is already
   warscape-core `docs/BACKLOG.md` B26 (J40 review) and B31 (J8 fix round). Cite those rather than filing it a third time.

### Rules for other open branches
None. This branch adds `dev.orders` to `ctl.launch.keys`, so every later `ctl.py scene` launch (and the acceptance run) turns the key on.
Its idle cost stayed inside the baseline thresholds over the 20 passes.
