# Project Agent Bootstrap

On-demand operating manual for AI-agent sessions. The SessionStart hook
auto-loads `RULES.md` + `STATUS.md` every session; read this file when you need
the read path for deeper docs or the end-of-session procedure. If hooks are
off, read `RULES.md` and `STATUS.md` first.

**Project:** `<PROJECT_NAME>`
**Type:** `<PROJECT_TYPE>`
**Primary stack:** `<PRIMARY_STACK>`

## On-Demand Read Path
RULES + STATUS arrive automatically. Pull these only when the task needs them:

- `MAP.md` — to locate important files.
- `context/PRODUCT.md` — product goals, users, workflows, domain terms.
- `context/TECH_STACK.md` — commands, env vars, setup, deploy, verification.
- `<dir>/CONTEXT.md` — local architecture; read before editing inside a folder
  that has one. (The PreToolUse hook injects it automatically on first edit there.)
- `tasks/now/` — when continuing active work.
- `tasks/WORKFLOW.md` — when creating, moving, or closing durable tasks.
- `CHANGELOG.md` — when recent history matters.

## Context Budget Rule
If a file is not useful in most sessions, it does not belong in the default
read path. Read optional docs on demand. Do not load archived docs, done tasks,
provider docs, or old changelog entries unless the current task needs them.

## End-of-Session Updates
Update only what changed:

1. `STATUS.md` — whenever state changed; keep it a concise snapshot, not a log.
2. `CHANGELOG.md` — meaningful code, behavior, architecture, ops, or docs changes.
3. `tasks/` — new, moved, or closed follow-ups.
4. `MAP.md` — only if important files were added, removed, moved, or repurposed.
5. `RULES.md` — only when the user explicitly establishes a stable non-negotiable.
6. `context/PRODUCT.md` — scope, users, workflows, or domain language changed.
7. `context/TECH_STACK.md` — stack, commands, env vars, deploy, or verification changed.
8. `<dir>/CONTEXT.md` — create/update when a folder gains local architecture or
   conventions future sessions should read before editing there.

## Non-Negotiables
The project's hard rules live in `RULES.md` (auto-loaded each session). This
file is procedure, not law — see `RULES.md` for what must never be broken.
