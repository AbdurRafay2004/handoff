# Rules

Non-negotiables for this project. Auto-loaded every session. Update this file
only when a rule is stable, project-wide, and explicitly accepted by the user.
Keep temporary preferences in task notes or `STATUS.md`.

## Universal Non-Negotiables
These ship with handoff and apply regardless of stack.

### Process
1. Don't read or modify unrelated parts of the repo unless the task requires it.
2. Don't delete, overwrite, or revert user changes unless explicitly asked.
3. Prefer small, focused changes that match existing architecture and naming.
4. Never `git add -A` / `git add .` for a scoped commit — stage only files you changed.
5. Don't assume project behavior that isn't documented or visible in code.
6. Ask before turning an unclear preference into a permanent rule.
7. On a delegate trigger (broad search/mapping, verbose output, parallel or
   isolated work), stop and ask delegate-or-inline via the host's available
   question tool (or a short chat question) with a
   suggested model tier — never decide silently, even mid-skill. Small,
   sequential, or interdependent edits stay inline without asking. (See the
   `delegate` skill.)

### State
8. Update `STATUS.md` and `CHANGELOG.md` whenever code or configuration changed —
   BEFORE committing, so state rides in the same commit as the code it describes.
   Never add a trailing docs-only commit; amend if not yet pushed.
9. Use `tasks/` for durable follow-ups, not chat history. Task files live in
   `tasks/inbox/`, `tasks/now/`, or `tasks/done/` — never in the `tasks/` root.

### Safety
10. Never hardcode secrets, credentials, or environment-specific values.

### Verification
11. Verify behavior with the project's verify commands (see `context/TECH_STACK.md`)
    before reporting completion.

## Project-Specific Rules
<!-- Populated by `/handoff:setup` discovery and as the user establishes rules.
     Examples: build system, design tokens, content sources, API contracts,
     framework conventions, breakpoints. Keep each rule short enough to apply
     during normal work. -->

_None yet._

## Source of Truth
- `BOOT.md` — session workflow and end-of-session procedure (on-demand).
- `STATUS.md` — current repo state and next steps (auto-loaded).
- `CHANGELOG.md` — meaningful change history.
- `MAP.md` — where important files live.
- `context/*.md` — stable project and stack context.
- `<dir>/CONTEXT.md` — local architecture for a specific folder.
- `tasks/` — durable future work and follow-ups.

## Change Control
- Add a new rule only when it prevents repeated mistakes or protects a real invariant.
- If a rule becomes obsolete, replace it and record the reason in `CHANGELOG.md`.
