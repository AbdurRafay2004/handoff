# Status

Snapshot of the present, not a log. Overwrite it; never append history here.

## How to keep this file
- Fixed slots only: Current State, Active Work (what is in progress plus its
  immediate next action), Blockers. The "next step" lives inside Active Work.
- Write here ONLY if the edit changes one of: current state / what am I actively
  working on / what is blocking / what is the next step. Otherwise it goes to
  `CHANGELOG.md` (something that happened), `tasks/` (future work), or memory
  (a durable fact about the user).
- Target 25 lines or fewer. If it grows past that, prune into `CHANGELOG.md` / `tasks/`.
- Does NOT belong here: "fixed a typo", "ran tests", per-file edit logs, anything
  already in CHANGELOG/tasks, long rationales.

## Current State
- `<one or two lines describing where the project stands>`

## Active Work
- `<what is in progress, plus its immediate next action — or "none">`

## Blockers
- `<what is blocking progress — or "none">`
