---
title: Evaluate which manual agent steps should become scripts
status: done
priority: low
why_it_matters: Several Handoff steps are deterministic but are written as prose or embedded shell snippets that an agent re-does by hand each time. Each repeat costs tokens and risks a slightly different result. Scripts would make them cheaper and consistent, but each one is more code to maintain in a public plugin, so none is approved yet.
context: Found while reviewing BOOT.md, the setup and ship skills, and the Stop hook. The repo's only scripts today are the three hooks, hooks/_common.py and the tests. CI already checks that the three manifest versions match, so that one needs nothing. Judgement work (CHANGELOG and STATUS wording, the setup discovery pass, tier and sentinel decisions) is not a candidate.
added_at: 2026-11-17
id: task-2026-11-17-script-manual-agent-steps
links:
  - tasks/WORKFLOW.md
  - skills/setup/SKILL.md
  - skills/ship/SKILL.md
  - hooks/stop.py
  - templates/BOOT.md
---

## Outcome (2026-11-17)
Judged and closed. 1 lint: built as task-2026-11-17-handoff-lint (VERSION check
cut; SessionStart already does it). 2 task move: dropped (two tool calls; lint
catches mismatches). 3 setup file work: deferred, runs once per repo; reopen as
its own task if setup proves error-prone. 4 deploy detection: dropped (a few
`ls` lines in the ship skill). 5 amend decision: shipped in
task-2026-11-17-stop-message-rewrite (v2.3.0).

## Notes
**Judge further before doing any of these.** This task records candidates, not
decisions. For each one, decide whether it is worth the maintenance cost, how it
works on both Claude Code and Codex, and whether a script or a skill instruction
is the better home. Close this task, or split the approved items into their own
tasks, once that judgement is done.

Candidates, strongest first:
1. Lint command (`handoff lint`): checks STATUS.md is within 25 lines, task
   folder and frontmatter status match, paths listed in MAP.md still exist, no
   leftover `<PROJECT_NAME>`-style placeholders in BOOT.md, and the VERSION
   stamp matches the plugin. Catches drift the hooks currently miss.
2. Task move: moves a task file between inbox/, now/ and done/ with `git mv` and
   rewrites its frontmatter `status` so the two never disagree.
3. Setup file work: copies `templates/` to `.handoff/`, writes the VERSION
   stamp, and fills the project name, type and stack placeholders. The agent
   keeps the discovery pass that drafts STATUS, MAP and TECH_STACK.
4. Deploy-target detection: one script that holds the detection order the ship
   skill says matters (data targets first, then Cloudflare, Vercel, and so on)
   instead of snippets the agent re-types.
5. Amend decision: the Stop hook already has the session-start commit and local
   commit list, so it could compute "safe to amend or not" (unpushed, own work,
   not a merge) and send one line instead of a paragraph of conditions. This
   edits the same hook message as task-2026-11-17-stop-hook-handoff-nudge, so
   coordinate the two.
   **Moved** to task-2026-11-17-stop-message-rewrite (tasks/now/).

Constraints to keep in mind: hooks must stay stdlib-only (CI enforces it), and
anything that writes files must stay advisory or be explicitly invoked, never
silent.

## Verification
- For each approved item, a split-out task with its own regression tests, and
  `python3 tests/test_hooks.py` still green.
- Manual check — for each approved script, run it in a real repo and confirm it
  matches what the agent did by hand.
