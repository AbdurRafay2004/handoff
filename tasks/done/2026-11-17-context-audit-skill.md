---
title: Add a context-audit skill that finds unused plugins and MCP servers
status: done
priority: high
why_it_matters: In a real PaperTight session, MCP tools and skills cost about 24k tokens at start (14.4k tool definitions, 10k skill descriptions), while Handoff's own injection is only about 1.4k. Most of the context cost comes from enabled plugins and connectors the project never uses, and nothing in Handoff helps the user find them.
context: Proposed after reviewing a /context breakdown (86k of 1M used). The skill audits and proposes; it never changes settings on its own, because editing settings is a configuration change that needs the user's approval. Hooks cannot read the /context numbers, so this stays a skill, not a SessionStart hook, and avoids a recurring nag.
added_at: 2026-11-17
id: task-2026-11-17-context-audit-skill
links:
  - hooks/sessionstart.py
  - skills/setup/SKILL.md
---

## Outcome (2026-11-17)
Shipped in v2.7.0 as `skills/context-audit/` plus `scripts/context_inventory.py`.

## Reassessment (2026-11-17): Do
The first review said Defer/Drop. Checking real config on the user's machine
reversed that:
- **Measurable, not guesswork.** Skill descriptions are read from each
  installed plugin's `skills/*/SKILL.md`, so their per-session cost can be
  estimated per plugin. In this repo (stdlib Python, no backend): convex
  (17 skills, ~1.2k tokens), cloudflare (~0.6k) and paddle (~0.5k) are enabled
  globally, plus playwright; all four also start MCP servers each session
  (paddle-sandbox fails auth every start). That is ~2.3k tokens plus four
  connections with no use here.
- **On-mission.** Handoff's core idea is the context budget (push only what is
  always relevant), and it already knows the project's stack from
  `.handoff/context/TECH_STACK.md`, which is what makes "unused here" decidable.
  No other tool has that per-project view.
- **Cheap to carry.** One more skill description (~50 tokens with a tight
  description) against kilotokens saved per session.
- **Safe lever exists.** Claude Code honours `enabledPlugins` per project:
  `"name@marketplace": false` in `.claude/settings.local.json` (personal,
  gitignored) or `.claude/settings.json` (shared with the team). Plugin MCP
  servers go with their plugin.

Still true from the first review: claude.ai connectors aren't in local
settings (report them, point to the app's connector toggle; don't edit); MCP
tool-definition cost is mostly deferred now, so count servers and connection
failures rather than estimating tool tokens; on Codex (`~/.codex/config.toml`
`[plugins.*]`, `[mcp_servers.*]`) report only.

Design: a stdlib `scripts/context_inventory.py` (deterministic, names and
sizes only, never env values or tokens) plus a short skill that judges each
item against TECH_STACK.md and the codebase, proposes per-project disables
(defaulting to `settings.local.json`), and edits only after approval.

- New skill (working name `handoff:context`) that lists what is enabled for the
  current project: plugins, MCP servers and connectors, from project and user
  settings and `.mcp.json`.
- It compares that list against what the project actually uses (the stack
  described in `.handoff/context/TECH_STACK.md`, and the codebase if that is
  thin), then reports what looks unused and which settings change would turn
  each item off, with rough token cost where it can be estimated.
- It proposes changes and waits for approval before editing any settings file.
- Host-aware: `enabledPlugins` is a Claude Code setting, so on Codex the skill
  only reports and does not suggest settings edits.
- Out of scope for this task: a hook-based warning, a "tools this project
  needs" section in the templates, and a size limit on Handoff's own injection.

## Verification
- Run the skill in a repo with several unused plugins enabled — it lists them
  and names the settings change, and no settings file changes until approved.
- Run it on a host without `enabledPlugins` support — it reports only, with no
  edit suggestions.
- Run `python3 tests/test_hooks.py` in this repo — still green.
