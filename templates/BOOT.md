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
4. `.handoff/skills/` — if this directory exists, check it before starting
   a complex task; it holds project-local workflows earlier sessions recorded

## Read on demand — only when the task needs it

- `MAP.md` — to locate important files
- `context/PRODUCT.md` — product goals, users, workflows, domain terms
- `context/TECH_STACK.md` — commands, env vars, setup, deploy, verification
- `context/LEARNINGS.md` — recorded patterns/pitfalls from past sessions
  (created by the `learn` skill on first use)
- `<dir>/CONTEXT.md` — local architecture; read before editing inside a folder
  that has one *(the PreToolUse hook injects it automatically on first edit)*
- `CHANGELOG.md` — when recent history matters
- `handoffs/` — overflow notes from earlier sessions; SessionStart lists them
  when any exist, so read only the one for the work you continue

**Context budget rule:** if a file is not useful in most sessions, it does not
belong in the default read path. Do not load archived docs, done tasks, or old
changelog entries unless the current task needs them.

## After every session — update in this order, BEFORE your final commit

State updates ride in the **same commit** as the code they describe. Update
docs first, then commit once — never commit code and follow with a docs-only
commit. If you already committed: amend ONLY when the commit is unpushed AND
is your own work from this session (never a merge commit or someone else's);
otherwise a follow-up commit is acceptable.

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
   something durable (see the `learn` skill; it creates the file on first use)
9. `<dir>/CONTEXT.md` — create or update when a folder gains local architecture
   or conventions future sessions should read before editing there
10. `.handoff/skills/<name>/SKILL.md` — create when you established a
    project-specific workflow future sessions need (major error recovered,
    non-obvious procedure, recurring task shape)

After required updates, commit completed, verified changes within your authorized
scope unless the user instructed otherwise. Stage only intended changes; preserve
unrelated user work and staged changes. Leave unfinished or blocked work
uncommitted and briefly explain why. Do not push without separate authorization.
The Stop hook reminds you by default; it never stages or commits for you.

## Keeping STATUS.md

- Fixed slots only: Current State, Active Work (what is in progress plus its
  immediate next action), Blockers. The "next step" lives inside Active Work.
- Write there ONLY if the edit changes one of: current state / what am I
  actively working on / what is blocking / what is the next step. Otherwise it
  goes to `CHANGELOG.md` (something that happened), `tasks/` (future work), or
  memory (a durable fact about the user).
- A fresh session must be able to continue from it: what is in progress, the
  exact next step, anything uncommitted or unverified, decisions made only in chat.
- Target 25 lines or fewer. If it grows past that, prune into `CHANGELOG.md` / `tasks/`.
- Does NOT belong there: "fixed a typo", "ran tests", per-file edit logs,
  anything already in CHANGELOG/tasks, long rationales.

## Session handoffs (overflow)

When a session leaves more for the next one than STATUS.md can hold — what was
tried and failed, decisions made only in chat, where each workstream stands —
write `handoffs/YYYY-MM-DD-topic.md`, one file per workstream, and keep STATUS.md
short. Only then: if every session writes one, nobody reads them.

- Not for future work (`tasks/`) or history (`CHANGELOG.md`) — only session
  knowledge the next session needs to pick up.
- SessionStart lists open handoffs with their age; no pointer in STATUS.md needed.
- Once a session has absorbed a handoff (acted on it or moved what lasts into
  STATUS/tasks/CHANGELOG), delete the file — git keeps the history. Treat one
  older than two weeks as possibly stale and verify it before trusting it.

## Non-Negotiables

The project's hard rules live in `RULES.md` (auto-loaded each session). This
file is procedure, not law — see `RULES.md` for what must never be broken.
