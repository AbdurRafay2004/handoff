---
title: Put a risk-tier reminder in the SessionStart injection so the workflow is not skipped
status: done
priority: high
why_it_matters: The workflow skill only runs when the model chooses to load it from a one-line description among about 70 skills, and nothing Handoff injects at session start mentions it. Users report they must type /workflow every time or the tier step is skipped. The tier decision is the cheapest and most valuable part of the pipeline, so it should not depend on that choice.
context: Found while reviewing the whole workflow system. The SessionStart hook injects STATUS.md, RULES.md and a pointer to on-demand files, but never says to declare a tier before development work. The Stop hook only flags sentinel paths after the work is done. A short tier line in the session-start text (about 150 tokens per session) is cheaper than loading the full skill, and a trivial task would never need the skill at all.
added_at: 2026-11-17
id: task-2026-11-17-tier-line-in-session-start
links:
  - hooks/sessionstart.py
  - skills/workflow/SKILL.md
  - templates/RULES.md
  - docs/SKILL-WORKFLOW.md
---

## Notes
- Add a compact reminder to the text the SessionStart hook injects: declare the
  tier (T1, T2 or T3) before any development task, and load the `workflow` skill
  for T2 and up. Consider including the three-row tier table so a T1 task needs
  no skill load.
- It must work on both Claude Code and Codex, and must not repeat on `resume`,
  `clear` or `compact` in a way that wastes tokens.
- Related cleanup to judge: the communication rules now appear in RULES.md
  (injected every session), in the `workflow` skill, and in
  docs/SKILL-WORKFLOW.md. Decide whether to keep one copy and point to it.
- Interim workaround already applied in PaperTight: one line in that project's
  CLAUDE.md asking for the tier to be declared per `handoff:workflow`.
- This changes injected text for every user of the public plugin: add a
  CHANGELOG.md entry and a version bump.

## Verification
- Run `python3 tests/test_hooks.py` — still green, with a new case checking the
  tier reminder is present in the SessionStart output for a repo with `.handoff/`.
- Check that a repo without `.handoff/` still gets only the one-time setup nudge.
- Manual check — start a fresh session without typing /workflow and ask for a
  small change: the agent declares a tier before editing.
