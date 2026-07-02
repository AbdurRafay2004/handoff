# Project Agent Bootstrap

On-demand operating manual for AI-agent sessions. The SessionStart hook
auto-loads `RULES.md` + `STATUS.md` every session; read this file when you need
the read path for deeper docs or the end-of-session procedure. If hooks are
off, read `RULES.md` and `STATUS.md` first.

**Project:** `<PROJECT_NAME>`
**Type:** `<PROJECT_TYPE>`
**Primary stack:** `<PRIMARY_STACK>`

## Every session — read in this order

1. `RULES.md` — non-negotiables, never skip *(auto-loaded)*
2. `STATUS.md` — current state and next steps *(auto-loaded)*
3. `tasks/now/` — when continuing active work; `tasks/WORKFLOW.md` when
   creating, moving, or closing tasks
4. `.agent-orch/skills/` — if this directory exists, check it before starting
   a complex task; it holds project-local workflows earlier sessions recorded

## Read on demand — only when the task needs it

- `MAP.md` — to locate important files
- `context/PRODUCT.md` — product goals, users, workflows, domain terms
- `context/TECH_STACK.md` — commands, env vars, setup, deploy, verification
- `context/LEARNINGS.md` — recorded patterns/pitfalls from past sessions
- `<dir>/CONTEXT.md` — local architecture; read before editing inside a folder
  that has one *(the PreToolUse hook injects it automatically on first edit)*
- `CHANGELOG.md` — when recent history matters

**Context budget rule:** if a file is not useful in most sessions, it does not
belong in the default read path. Do not load archived docs, done tasks, or old
changelog entries unless the current task needs them.

## After every session — update in this order, BEFORE your final commit

State updates ride in the **same commit** as the code they describe. Update
docs first, then commit once — never commit code and follow with a docs-only
commit (if you already committed and haven't pushed, amend).

1. `CHANGELOG.md` — required for every meaningful code/behavior/config change
   (detail lives here)
2. `STATUS.md` — whenever state changed; concise snapshot, not a log (≤25 lines)
3. `tasks/` — new follow-ups → `inbox/`; status changes → move the file between
   `inbox/` / `now/` / `done/`. **Task files never sit in the `tasks/` root.**
4. `MAP.md` — only if important files were added, removed, moved, or repurposed
5. `RULES.md` — only when the user explicitly establishes a stable non-negotiable
6. `context/PRODUCT.md` — only if scope, users, workflows, or domain language changed
7. `context/TECH_STACK.md` — only if stack, commands, env vars, or deploy changed
8. `context/LEARNINGS.md` — a typed one-line entry when a session taught
   something durable (see the `learn` skill)
9. `<dir>/CONTEXT.md` — create or update when a folder gains local architecture
   or conventions future sessions should read before editing there
10. `.agent-orch/skills/<name>/SKILL.md` — create when you established a
    project-specific workflow future sessions need (major error recovered,
    non-obvious procedure, recurring task shape)

## Non-Negotiables

The project's hard rules live in `RULES.md` (auto-loaded each session). This
file is procedure, not law — see `RULES.md` for what must never be broken.
