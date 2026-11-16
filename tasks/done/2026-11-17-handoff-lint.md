---
title: Add an on-demand handoff lint script, run from the setup skill
status: done
priority: medium
why_it_matters: Drift the hooks can't see (task status mismatches, dead MAP.md paths, leftover placeholders, CONTEXT.md notes that fell behind their folder) accumulates silently and makes the injected memory misleading. A deterministic, read-only check makes it cheap and consistent to catch.
context: Merges candidate 1 of task-2026-11-17-script-manual-agent-steps with items 1-2 of task-2026-11-17-context-md-drift-checks after the 2026-11-17 backlog review. Delivery - a stdlib script at <plugin-root>/scripts/handoff_lint.py, located by the setup skill the same way it already locates templates/, so no new skill description and it works on Claude Code and Codex. No hook changes.
added_at: 2026-11-17
id: task-2026-11-17-handoff-lint
links:
  - scripts/handoff_lint.py
  - skills/setup/SKILL.md
  - tests/test_hooks.py
---

## Notes
- Checks: task folder vs frontmatter status and strays in tasks/ root; MAP.md
  backticked paths that no longer exist; leftover `<UPPER_CASE>` placeholders;
  STATUS.md over its 25-line target; CONTEXT.md files with files added or
  removed in their folder, or 10+ commits there, since they were last updated;
  CONTEXT.md backticked paths that no longer exist.
- Read-only. Exit 0 clean, 1 findings, 2 nothing to lint.
- Dropped: VERSION check (SessionStart does it), CONTEXT.md creation prompt.

## Verification
- `python3 tests/test_hooks.py` green with a case per check, a clean repo, a
  repo without .handoff/, and a read-only check.
- Run it on a real repo with .handoff/ and confirm the findings are real.
