---
name: setup
description: Scaffold the handoff project-memory system into THIS repository (new or existing) — copies the template tree into .handoff/, then runs a guided discovery pass that drafts a real STATUS, MAP, TECH_STACK, and PRODUCT from the actual codebase and confirms with the user before saving. Use when the user says "set up handoff", "initialize handoff", "add project memory", or when a repo has no .handoff/ and the user wants one. Run once per repo.
---

# Set up handoff in this repo

Scaffold the durable project-memory system, then populate it from the real
codebase so it ships useful — not blank. **Discovery drafts; the user confirms
before anything is saved.** Never invent project facts (RULES rule 5).

## 0. Locate templates & detect existing install
- The template tree is bundled with this plugin at `../../templates/` relative
  to this skill file (i.e. `<plugin-root>/templates/`). Resolve that absolute path.
- Check whether `.handoff/` already exists in the project root:
  - **Exists** → do NOT overwrite. Tell the user it's already set up; offer to
    *refresh* specific files (e.g. re-run discovery for STATUS/MAP/TECH_STACK)
    or seed a CONTEXT.md. Stop here unless they choose a refresh.
  - **Absent** → continue.

## 1. Copy the template tree
Copy the bundled `templates/` into the project as `.handoff/`, preserving
structure (BOOT, RULES, STATUS, MAP, CHANGELOG, context/, docs/ with
SKILL-WORKFLOW.md, tasks/ with inbox/now/done). Keep the `.gitkeep` files.
Do not edit RULES' universal section.
Write the current plugin version into `.handoff/VERSION` (single line) — the
SessionStart hook uses it for template-drift detection.
Read the version from `.codex-plugin/plugin.json` in Codex or
`.claude-plugin/plugin.json` in Claude Code; use the available manifest if only
one is packaged.

## 2. Guided discovery (read the repo — do not guess)
Read what actually exists, quietly:
- Build/manifest files: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`,
  `composer.json`, `Gemfile`, Makefile, CI config, framework config files.
- Top-level directory layout and the largest/most-central source folders.
- `git log --oneline -20` and current branch for recent direction.
- Any existing README for product intent.
Derive: project name, type, primary stack, common commands (build/dev/test/lint),
deploy target, and the **verify commands** for RULES rule 10.

## 3. Draft, then CONFIRM before saving
Present concise drafts for the user to correct:
- **STATUS.md** — Current State (where the repo stands now), Active Work (none
  unless evident), Blockers (none unless evident). Keep ≤ 25 lines.
- **context/TECH_STACK.md** — stack, commands, env vars, deploy, verify commands.
- **MAP.md** — entry points, key directories, where to make common changes.
- **context/PRODUCT.md** — only if a README/product intent is discoverable;
  otherwise leave the template prompts and say so.
- Replace the `<PROJECT_NAME>/<PROJECT_TYPE>/<PRIMARY_STACK>` placeholders in BOOT.md.
**Wait for the user's confirmation/edits. Only then write the files.** For
anything you cannot determine from the repo, leave the template prompt in place
rather than inventing — and tell the user what you left blank.

## 4. Seed folder-level CONTEXT.md (offer, then confirm)
Identify the 1–3 folders with the most local architecture or conventions a
future session should read before editing (e.g. a design-system dir, a core
domain module). Propose a short CONTEXT.md for each (structure, conventions,
gotchas — not a file listing). Save only the ones the user approves. These are
auto-injected by the PreToolUse hook on first edit in that folder.

## 5. Host-specific fallback instructions
The plugin's hooks load full state when installed, but a clone opened WITHOUT
the plugin needs a minimal fallback. In the project root:
- In Codex, append the block to `AGENTS.md`; in Claude Code, use `CLAUDE.md`.
  Create the host's file if absent, even if the other host's file exists:
  Codex does not automatically read `CLAUDE.md`.
- Preserve all existing instructions. If both files exist, keep the same
  handoff block in both. Don't duplicate a block already present in a file.
- The block:

```markdown
## Project memory (handoff)
This repo uses handoff. With the plugin installed, the SessionStart hook
auto-loads `.handoff/STATUS.md` + `RULES.md`. If hooks are off, read those
two first. Hard rules (always apply):
- Preserve user work; never delete/overwrite/revert changes unless asked.
- Never `git add -A` / `git add .` for a scoped commit — stage only what you changed.
- Verify with the commands in `.handoff/context/TECH_STACK.md` before claiming done.
- Update `.handoff/STATUS.md` + `CHANGELOG.md` whenever code or config changes —
  before committing, in the same commit as the change.
```

## 6. Finish
In Codex, explain that plugin hooks must be reviewed and trusted before they
run; use the host's hook review UI (`/hooks` in the CLI). Installing the plugin
alone does not trust its hooks. If hooks are disabled, unavailable, or the
conversation is cloud-orchestrated ChatGPT Work, the fallback instructions
provide manual memory; don't promise automatic hooks there. See `docs/CODEX.md`
at the plugin root.

Tell the user: setup is complete; with hooks enabled and trusted,
the SessionStart hook will load STATUS+RULES
from the next session; the PreToolUse hook injects any folder's CONTEXT.md on
edit; the Stop hook nudges state updates. They can edit `.handoff/*` directly
anytime. Re-run this skill only to refresh discovery or start over.
Also tell them the repo now has a tiered 6-phase workflow — point them at
`.handoff/docs/SKILL-WORKFLOW.md` and the `workflow` skill.

Add a dated line to `.handoff/CHANGELOG.md`: "Project initialized with handoff."
