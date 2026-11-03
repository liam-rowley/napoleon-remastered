## Round 1 (2026-11-02, branch job/J38 at e585522)

**Verdict: merge.**

Machines: CI on e585522 all required checks passed or skipped (gates pass); `tests.test_release` 22 ok and `tests.test_release_installer` 13 ok run locally on Windows (installer vs `pc_deploy.py` parity, refusals, check/repair, game update, redaction); `policy` refused only on the missing review and row, as the report says.

Read in depth: `release/core/installer/rr.ps1` install and uninstall (the only code that touches the real game folder). Staged sha256 checked before any copy, snapshot before the first write, foreign files at owned paths backed up first, temp-name-and-rename copy, removals are moves to the state folder (the one `Remove-Item` follows a hash-verified copy), uninstall exits 0 only on an empty snapshot diff, state is outside the game folder (D25), no exe write. The release builder's refusals (dirty tree, build id, unpinned DXVK, double ownership) and the manifest/owned-path checks match the brief. No `proxy/`, `harness/` or `core/` change, so rule 79 does not apply. Deviations in the report are named with reasons; shipping `ui_scale_2x` follows D42(4), and the PC sitting was left open with Liam's explicit choice ("Review it as is").

### Blockers
None.

### Should-fix
None.

### Later
1. **The PC acceptance sitting (brief steps b to f) is not done**: real-folder Install/Check, forced pass-through launch via the watcher, vanilla and mod-era save loads, a real support bundle, Repair then Uninstall with an identical snapshot. Until it runs, install on the real folder, Steam Verify survival and `dev.file_rules` with the release DLL (report deviations 3 and 6) are unproven. Queue a follow-up job (or a plan row) for it; do not publish a release before it.
2. The installer tests skip on Linux CI, so a regression in `rr.ps1` is only caught by `gates` on the PC; hooking them into `harness-windows` is a warscape-core change (report deviation 4).
3. `release/core` promotion job to warscape-core is not queued (`PROMOTIONS` entry is `None`).
4. Open owner questions stay open: unofficial-mod statement and own-code licence (the builder warns), a player key for `dev.file_rules`, antivirus reaction to `-ExecutionPolicy Bypass`.

No rule changes that other open job branches must meet.
