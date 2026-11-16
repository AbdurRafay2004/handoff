---
name: context-audit
description: Audit what loads into every session for this project — plugins, MCP servers, connectors, skills — find what the project doesn't use, and propose per-project disables. Use when the user asks why context is large, wants to trim plugins/connectors, or says "audit context".
---

# Context audit

Every enabled plugin adds its skill, agent, and command descriptions to every
session, and every MCP server connects at startup — whether or not this project
uses them. This skill measures that, judges it against what the project
actually is, and proposes turning off what isn't needed **here**. It changes
nothing until the user approves.

## 1. Inventory
Run the bundled read-only script, located at `../../scripts/context_inventory.py`
relative to this skill file (`<plugin-root>/scripts/`):

```sh
python3 <plugin-root>/scripts/context_inventory.py <project-root>
```

Add `--json` for structured output. It reports each Claude Code plugin with its
effective on/off state for this project and which settings file decided it,
an estimated per-session token cost of its descriptions, its MCP servers and
hooks; MCP servers configured outside plugins; personal and project skills;
and Codex plugins and MCP servers from `config.toml`. It prints names and sizes
only, never config values.

Then add what the script cannot see, from this session itself:
- **claude.ai connectors** and any MCP servers listed in your own tool list or
  system context, including servers that **failed to connect or need auth**
  (they slow every startup and add nothing).
- If the user pasted `/context` output, use its numbers over the estimates.

## 2. Judge each item against the project
Decide what the project actually uses from evidence, not names:
- `.handoff/context/TECH_STACK.md` and `MAP.md` when they exist.
- Otherwise the codebase: dependency manifests (`package.json`,
  `pyproject.toml`, `go.mod`, …), deploy config (`wrangler.toml`,
  `vercel.json`, `convex/`, `supabase/`), and test tooling.

Classify every enabled item as **used here**, **unused here**, or **unsure**
(name what would settle it). General-purpose tools (browser automation,
document or design skills, this plugin) are often used across tasks: mark them
unsure and ask, rather than calling them unused. Never mark something unused
just because this session hasn't called it.

## 3. Propose
Lead with the total that could be saved, then one row per proposed change:

| Item | Cost here | Verdict | Change |
|---|---|---|---|
| `name@marketplace` | ~N tokens, M MCP servers | unused here: no X in the repo | disable for this project |

Then list what you would keep and why, and the **unsure** items as questions.

Where each change goes:
- **Claude Code plugin, this project only (default):** set
  `"name@marketplace": false` under `enabledPlugins` in
  `<project>/.claude/settings.local.json` (personal, normally gitignored).
  Disabling a plugin also stops its MCP servers.
- **For the whole team:** the same key in `<project>/.claude/settings.json`
  (committed) — only if the user asks for team-wide.
- **Everywhere:** user settings (`~/.claude/settings.json`) — only if the
  user explicitly asks; say it affects every project.
- **MCP servers outside plugins:** project `.mcp.json` servers can be listed in
  `disabledMcpjsonServers` in the same settings file; user or local-scope
  servers are removed with `claude mcp remove <name> -s <scope>` — propose the
  command, don't run it.
- **claude.ai connectors:** not in any local file. Point the user to the
  connector toggles in the app (claude.ai Settings → Connectors, or the
  session's connector menu in the desktop app).
- **Codex:** report only. Show the `config.toml` entry that would change
  (`enabled = false` under `[plugins."name"]` or `[mcp_servers.name]`), and let
  the user edit it.

## 4. Apply only what was approved
- Edit only the files and keys the user approved. Read the settings file
  first, merge into existing JSON (create `enabledPlugins` if absent), keep
  every other key, and write valid JSON. Create the file only if it's missing.
- Never print or copy config values (env, headers, tokens, URLs).
- Say that changes take effect in the **next** session, and how to undo one
  (set the key back to `true` or remove it).
