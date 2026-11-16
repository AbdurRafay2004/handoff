---
title: Let a session write a linked overflow handoff file when STATUS.md cannot hold it
status: done
priority: medium
why_it_matters: A long or messy session carries more for the next session than STATUS.md's 25-line limit allows, such as what was tried and failed, decisions made only in chat, and where each workstream stands. Today that either gets squeezed into STATUS.md or is lost, which is a main cost of restarting a large session. A linked overflow file would keep STATUS.md small and cost almost nothing at session start, because only a one-line pointer is injected.
context: Proposed by the user, then refined in discussion. It pairs with task-2026-11-17-stop-hook-handoff-nudge, where the large-session nudge would tell the agent to update STATUS.md and, if the content does not fit, to write an overflow file and link it. The existing places stay as they are. Work still to be done belongs in tasks/now/, history belongs in CHANGELOG.md, and the overflow file is only for ephemeral session knowledge.
added_at: 2026-11-17
id: task-2026-11-17-overflow-handoff-files
links:
  - tasks/inbox/2026-11-17-stop-hook-handoff-nudge.md
  - templates/STATUS.md
  - templates/BOOT.md
  - hooks/stop.py
---

## Notes
**Decided (2026-11-17 review):**
- SessionStart lists `.handoff/handoffs/*.md` itself, with each file's age taken
  from its date prefix, instead of a hand-kept pointer in STATUS.md. It reaches
  existing installs and can never dangle, so no missing-pointer Stop check.
- One file per workstream, `YYYY-MM-DD-topic.md`; delete once absorbed (git
  keeps history); no `handoffs/done/`. Files older than 14 days are marked
  "verify before trusting".
- The STATUS template's "How to keep this file" block moves to BOOT.md, so
  STATUS.md has room for content (new installs only).
- The Stop nudge names the folder as the place for detail that won't fit.

- Design direction (to judge further before building): a handoff file lives in a
  `.handoff/handoffs/` folder and is named with a date and short topic, such as
  `2026-11-17-pricing-rework.md`. Do not use sequential numbers: unlike
  migrations, order is not the point, and two sessions running at once could
  pick the same number.
- STATUS.md points only to the current handoff files, never to old ones, and
  stays within its 25-line limit. The one-line pointer is the only start-of-session
  cost; the file itself is read on demand, in line with the context budget rule in
  BOOT.md.
- Lifecycle, to keep context from rotting: once a new session has absorbed a
  handoff it deletes the file or moves it to `handoffs/done/`. Git history keeps
  it either way. A stale handoff that the next session trusts is the main risk.
- Narrow trigger: write one only when STATUS.md truly cannot hold the content.
  If agents write one every session, the folder fills with notes nobody reads.
- Open questions: single overwritten file versus one file per workstream; whether
  the Stop hook should flag a STATUS.md pointer to a file that no longer exists
  or one that has been absorbed; whether the template, BOOT.md and the setup
  skill all need to mention the folder.
- The plugin is public: any change to templates or hooks needs tests, a
  CHANGELOG.md entry and a version bump. Hooks must stay stdlib-only.

## Verification
- Run `python3 tests/test_hooks.py` — still green, with new cases for a
  STATUS.md pointer to a missing handoff file and for a handoff folder that is
  absent (stays silent).
- Check that STATUS.md stays within 25 lines when it contains the pointer.
- Manual check — in a large session, ask for a handoff: STATUS.md stays short,
  an overflow file holds the detail, and a fresh session reads it only when needed
  and then removes or archives it.
