## Round 1 (2026-11-02, branch job/J53 at fcb8fca)

**Verdict: merge.**

Checked: `wsc gates` (11 ok, 1 warn = skipped numpy/capstone/wasm tests on this machine, 0 failed), CI 8/8 green, `test_play_pack`, `test_mod_packs` (10 ok), and the report's claims against `upscale/runs/2026-11-02_j53/README.md` (job ids, per-role table, snapshots identical, six shots, 676 KB; I opened `a_land.jpg`: HUD, unit cards, portrait and flags at vanilla size, nothing blank).
Brief: every deliverable present; no change to `core/`, `proxy/`, `harness/` (rule 79 not triggered); held-back rules, vanilla-path guard, config keys and `mod_packs` as decided; deviations (`play.py` for `play.sh`, early pack checks, `dev.skip_intro=1`, Opus) are named with reasons.
Risk-first reading: `upscale/pc/play.py` (writes the game folder, uninstall ordering) and `pack.py` `play_plan`/`held_back_reason`. The order (record + snapshot first, packs out, then `pc_deploy uninstall`, then diff, non-zero unless identical) matches the brief; refusals come before the first change; the record is written before the first change so a half install can be undone.

### Blocker
None.

### Should-fix
None.

### Later
1. `upscale/pc/play.py` has never run on the real game folder (the agent route cannot; it is host-tested on a fake folder). Liam's first install is its real test; `uninstall` exits non-zero and prints the diff if anything differs. Open question 3 (hook exemption so an agent can run the exact command) is worth a brief if Liam wants it exercised before then.
2. Report open question 1 (watcher/`job.sh lock` unaware of `<state>\play\play.json`) is a real hazard: a forgotten play install is picked up by the next agent job. Needs a core change, so a `needs_brief` row.
3. `uninstall` does not refuse while an agent holds the game lock (install does); harmless in practice, add if the lock check is ever shared.
4. Held-back loading screens (28 files) and memory use are unproven; Liam's play test and a follow-up probe settle them.
