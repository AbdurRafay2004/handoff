---
title: Rewrite the Stop nudge for handoff quality, amend advice and resume tracking
status: done
priority: high
why_it_matters: The Stop nudge is what makes a session leave STATUS.md in a state a fresh session can continue from. Today it doesn't say what a handoff needs, it hands the agent a paragraph of amend conditions the hook could decide itself, and a resume or compact silently wipes the session's change tracking.
context: Split out of task-2026-11-17-stop-hook-handoff-nudge (Change 1) and task-2026-11-17-script-manual-agent-steps (candidate 5) after a backlog review, plus a baseline-reset bug that review found. All three edit the same Stop message or the session baseline, so they ship together. The large-session nudge (Change 2) stays in the inbox task.
added_at: 2026-11-17
id: task-2026-11-17-stop-message-rewrite
links:
  - hooks/stop.py
  - hooks/sessionstart.py
  - hooks/_common.py
  - tests/test_hooks.py
---

## Notes
- Handoff wording: the closing paragraph says STATUS.md must let a fresh
  session continue (in progress, exact next step, uncommitted or unverified
  work, decisions made only in chat) within its 25-line target.
- Amend advice: the hook decides. HEAD is an unpushed, non-merge commit made
  since the session baseline -> suggest amending it (hedged: "if it is yours").
  Session commits exist but HEAD is not amendable -> follow-up commit, don't
  amend. No session commits -> state rides in the next commit with the code.
- Resume/compact: SessionStart keeps an existing baseline for the same session
  id when `source` is `resume` or `compact`; `startup`, `clear` and a missing
  baseline still capture a fresh one.
- All three Stop loop-breakers stay as they are.

## Verification
- `python3 tests/test_hooks.py` green with new cases: handoff wording present;
  amend suggested for an unpushed session commit; not suggested for a merge
  commit or with no session commits; resume and compact keep the baseline;
  startup re-captures it.
