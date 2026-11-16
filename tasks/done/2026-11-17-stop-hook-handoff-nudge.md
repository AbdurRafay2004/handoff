---
title: Make the Stop hook prompt a next-session handoff, including in very large sessions
status: done
priority: high
why_it_matters: Users leave a session for an hour and come back to a 400-500k token context. Continuing there is expensive, so they want to open a fresh session, but they cannot tell whether the last response left STATUS.md in a state a new session can continue from. Today the Stop hook only nudges when git shows new changes, so a discussion-only turn gets no handoff prompt at all.
context: Found while reviewing hooks/stop.py. Two changes belong together. (1) When the hook already fires, its message should also tell the agent that STATUS.md must let a fresh session continue. (2) The hook should also fire once when the session transcript gets very large, even with no new repo changes, so the handoff is written before the user restarts. The nudge stays advisory, never writes files itself, and keeps all three loop-breakers (stop_hook_active, session baseline, nudge signature). Out of scope: a stale-STATUS.md check based on file age, and a nudge on every turn, which would cost tokens and churn STATUS.md.
added_at: 2026-11-17
id: task-2026-11-17-stop-hook-handoff-nudge
links:
  - hooks/stop.py
  - hooks/_common.py
  - tests/test_hooks.py
  - templates/BOOT.md
---

## Outcome (2026-11-17)
Change 1 shipped in v2.3.0; Change 2 shipped in v2.6.0. Decisions: context
size comes from the transcript's latest main-thread usage record (Claude
`message.usage`, Codex `token_count`), not file size; fires once per 200k-token
step (200k, 400k, ...) with its own marker; works with no repo changes and in
non-git repos; skipped silently when the transcript is missing or unreadable.

- **Change 1 moved** to task-2026-11-17-stop-message-rewrite (tasks/now/).
  This task now holds only Change 2, the large-session nudge, on hold until
  that release shows whether better handoff wording is enough.
- Change 1, handoff wording: extend the existing Stop nudge so it says STATUS.md
  must let a fresh session continue. It should cover what is in progress, the
  exact next step, anything uncommitted or unverified, and decisions made only
  in chat. It must still respect STATUS.md's size target (25 lines) and keep
  history in CHANGELOG.md and follow-ups in tasks/.
- Change 2, large-session nudge: the hook payload on Claude Code should carry a
  transcript file path (not yet used anywhere in this repo — confirm it first).
  When the transcript passes a size threshold (starting point about 200k
  tokens, estimated from file size), fire once per threshold crossing even if
  git shows no new work. The message tells the agent to write a complete
  handoff and tell the user the session is large and a fresh one may be cheaper.
- Open question: whether Codex sends the same transcript path. If it does not,
  the large-session nudge must be skipped quietly on Codex, never error.
- Open question: the exact threshold, and whether a second nudge should fire at
  a higher threshold.
- The plugin is public, so this changes hook behavior for every user: add a
  CHANGELOG.md entry and a version bump, and note the new nudge in the docs.

## Verification
- Run `python3 tests/test_hooks.py` — still green, including the new cases below.
- Add subprocess regressions covering: handoff wording present when the hook
  fires; large transcript with no repo changes fires once; the same large
  transcript does not fire twice; small transcript stays silent; missing or
  unreadable transcript path stays silent; a clean tree with a small transcript
  stays silent; `stop_hook_active` still exits immediately.
- Manual check — in a real session with a large transcript, end a
  discussion-only turn: the agent writes STATUS.md and says the session is large.
