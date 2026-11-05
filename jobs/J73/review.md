## Round 1 (2026-11-04, branch job/J73 at 6cd2f6a)
**Verdict: merge.**

Checked: the diff of tools/jobs_hooks.py by hand against the report's mapping, and the unit tests (144 ran, OK, 1 skipped).
`policy` refused only for the missing review and the row status, which this review fixes.

- **No rule loosened.** The old `kind != 'job'` early return is replaced by a shortcut that returns [] only when there is no recorded acceptance fact, no rule79_path in `changed` and no `core` in `changed`. That is exactly the input for which `acceptance_problems` returns [] (it also returns [] when acc is falsy), so every input that failed before still fails, and brief/plan/meta/'' now fail too. `acc_exempt`, `acceptance_active`, the counting loop and the ledger format are untouched.
- **wsc.toml.** Only `core` and `registries/*` leave meta, and `viewer/pins.json` joins the proxy input set. `registries/jobs/*` stays.
- **Risk-first read:** `show` and `_core_policy`. `policy.show` does the same `git show ref:path` and returns None on failure, and the `core/` submodule fallback is kept.
- **Replaced assertions** match the report: the brief -> [] assertion, the source-line grep test, and the legacy-set tests (git half kept, hash half added). Nothing is relaxed.

### Blockers
None.

### Should-fix
None.

### Later
- Deviation 1 is accepted: the meta-glob equality test compares per kind, not per glob. It cannot catch a single over-wide glob whose reach another glob already covers. W23's segment matcher closes this.
- `tools/*`, `wsc.toml` and `.gitmodules` stay in meta (open question 1), so until W23 and J76 land a `meta/` branch can still rewrite a rule. Liam merges `meta/` branches (D50).
- Merging this makes core pin bumps (J64, J78) `job/` branches that meet rule 79. Open job branches that bump the pin on `meta/` or `plan/` must move to `job/`.
