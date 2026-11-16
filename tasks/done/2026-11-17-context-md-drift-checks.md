---
title: Detect stale or missing folder CONTEXT.md files
status: done
priority: medium
why_it_matters: A folder's CONTEXT.md is read before every first edit there, so a stale one misleads the agent while looking trustworthy. Today the only countermeasure is an advisory Stop-hook note, which cannot catch edits made outside agent sessions or notes that have been stale for months.
context: Found while checking what protects CONTEXT.md from drift. What exists now - the pre_edit_context hook injects the nearest CONTEXT.md once per session on first edit, and the Stop hook flags it as "may need updating" when a file in its folder changed this session and the CONTEXT.md did not. Gaps - the note is advisory and flags every edit including trivial ones; it fires once per set of changes; it only sees changes made during an agent session with hooks on, so hand edits never trigger it; only the nearest CONTEXT.md counts, so a parent folder is never checked; nothing compares a CONTEXT.md's age to its folder's latest change; and nothing creates one when a folder grows, because BOOT.md says only to create one when a folder gains local architecture or conventions, with no threshold.
added_at: 2026-11-17
id: task-2026-11-17-context-md-drift-checks
links:
  - hooks/stop.py
  - hooks/pre_edit_context.py
  - templates/BOOT.md
  - tasks/inbox/2026-11-17-script-manual-agent-steps.md
---

## Outcome (2026-11-17)
Closed after review. Items 1 (age check, with a threshold: files added or
removed, or 10+ commits since the note was updated) and 2 (path check) moved
into task-2026-11-17-handoff-lint. Item 3 (creation prompt) dropped: it would
create notes nobody keeps up to date. The advisory Stop-hook note stays.

## Notes
**Judge further before building any of these.** Decide whether each is worth the
maintenance cost and whether it belongs in a script, the existing lint idea, or
CI. Candidates, in the order I would take them:
1. Age check: list every CONTEXT.md that is older than the newest code change in
   its folder, using git history. It would catch drift from hand edits and old
   sessions. It could run on demand or in CI. **This item could be folded into
   the `handoff lint` command** proposed in task-2026-11-17-script-manual-agent-steps
   (candidate 1) as one more check, instead of becoming a separate script.
2. Path check: confirm that the files and folders a CONTEXT.md mentions still
   exist, like the MAP.md path check proposed in the same task.
3. Creation prompt: a rough nudge to create a CONTEXT.md when a folder passes a
   file-count threshold. Judge this one carefully, because it risks creating
   notes nobody keeps up to date.
- Keep the existing advisory Stop-hook note. These checks add coverage; they do
  not replace it.
- Hooks must stay stdlib-only, and anything that writes files must be explicitly
  invoked, never silent. The plugin is public, so any change needs tests, a
  CHANGELOG.md entry and a version bump.

## Verification
- Run `python3 tests/test_hooks.py` — still green, with new cases for each
  approved check.
- Manual check — in a repo with a CONTEXT.md, change a file in its folder by
  hand without touching the CONTEXT.md: the age check lists it. Update the
  CONTEXT.md: the list is empty again.
- Manual check — rename a file that a CONTEXT.md mentions: the path check
  reports the broken reference.
