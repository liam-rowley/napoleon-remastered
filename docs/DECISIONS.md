# Decisions

One line per decision: date, who, the decision, and whether it is reversible. **Append only**; a reversal is a new dated line that names
the one it replaces. Detail lives in the doc that owns the topic, never here.

| # | Date | Who | Decision | Reversible |
|---|---|---|---|---|
| D1 | 2026-10-28 | Liam | Goals: modern battle controls (Alt+drag moves the selection, Alt+Ctrl+drag rotates it), UI that scales from 1080p to 4K and stays crisp, imposter and LOD distances pushed out (buildings, trees, ships, …), better shadows, DXVK for performance. `docs/plans/PLAN.md` section 1. | yes |
| D2 | 2026-10-28 | Liam | **No-touch:** `Napoleon.exe` is never modified on disk. Runtime patching and detours from the proxy DLL are allowed. | no |
| D3 | 2026-10-28 | Liam | Tooling first: fast game load, a ready library of battles, sieges, naval battles and saves agents can load quickly, and scripted camera control are built before feature work, not grown per job as on Empire. | yes |
| D4 | 2026-10-28 | Liam | The repo is the single source of truth; deterministic gates wherever possible; registries (tools, assets, UI elements, …) each carry extra fields (tools: when to use; UI elements: status synced with the design review). | no |
| D5 | 2026-10-28 | Liam | UI scale is a player-facing **slider**. UI art (HUD, icons, …) is upscaled to be 4K-suitable. | yes |
| D6 | 2026-10-28 | Liam | **Every screen is RmlUi**; no native screens remain. | yes |
| D7 | 2026-10-28 | Liam | Fonts are handled the same way as on Empire (RmlUi screens use TTFs through FreeType; see `docs/plans/UI_PIPELINE.md` for engine-drawn text). | yes |
| D8 | 2026-10-28 | Liam | Napoleon gets its **own design language** (not Empire's re-themed). | yes |
| D9 | 2026-10-28 | Liam | RmlUi again, with a reworked concept-to-build process (`docs/plans/UI_PIPELINE.md`). Liam reviews designs by playing them (clicking, switching tabs), rarely by editing, so the design canvas becomes a review surface and agents own the source. | yes |
| D10 | 2026-10-28 | Liam | **Shared core repo now.** Napoleon builds on it from the start; Empire is not modified yet and is refactored onto the core later, at a quiet time. | yes |
| D11 | 2026-10-28 | Liam | **One game at a time:** Napoleon and Empire work never run in parallel (one PC, one game lock, one usage budget). | yes |
| D12 | 2026-10-28 | Liam | Shadows: higher resolution **and cascaded**, to remove the slicing artefacts and the blob shadows. | yes |
| D13 | 2026-10-23 | Liam | NVIDIA only (decided on Empire for both games, `empire-remastered/docs/plans/PIPELINE_V2.md` section 1). | yes |
