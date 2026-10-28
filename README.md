# Napoleon: Total War Remastered

A no-touch remaster of Napoleon: Total War: modern battle controls, a complete RmlUi interface that scales from 1080p to 4K,
pushed-out draw distances with cascaded shadows, and DXVK. `Napoleon.exe` is never modified on disk; everything ships as a proxy
`d3d9.dll`, packs and loose files.

Built mostly by AI agents. **This repo is the single source of truth**; the claude.ai Project docs, the review pages and the PC game
folder are generated from it or deployed from it, never edited.

## Start here
| File | What |
|---|---|
| `CLAUDE.md` | Rules for every chat and agent. Read first. |
| `docs/DECISIONS.md` | Every decision, dated, one line each. Append only. |
| `docs/plans/PLAN.md` | Goals, scope, phases and gates. |
| `docs/plans/UI_PIPELINE.md` | How a UI screen goes from concept to verified in game. |

## Related repos
- `liam-rowley/warscape-core` (private): the shared core (harness, registries, CLI, review viewer, game-agnostic tools); split in `docs/plans/PLAN.md` section 4.
- `liam-rowley/empire-remastered`: the first game. Its learnings and `docs/plans/PIPELINE_V2.md` are this plan's evidence base.
  Empire is not modified by Napoleon work; it moves onto the shared core later, at a quiet time.
