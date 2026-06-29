# agent-orch

Portable, hook-driven **project memory** for coding agents. Drop it into any
repo and the agent gains durable state across sessions — without bloating every
session's context.

The principle: **push the right context at the right moment, instead of hoping
the agent pulls it.** State that's always relevant is pushed every session;
everything else is loaded on demand, exactly when it's needed.

## What you get

| Piece | When it loads | Cost |
|---|---|---|
| `STATUS.md` + `RULES.md` | every session (SessionStart hook) | always-on, small |
| `BOOT.md`, `MAP.md`, `context/*`, `tasks/`, `CHANGELOG.md` | on demand | zero until read |
| folder-level `CONTEXT.md` | when you edit in that folder (PreToolUse hook) | zero until you edit there |
| state-update nudge | turn end, only if work changed (Stop hook) | one line, only when relevant |

In a repo **without** `.agent-orch/`, every hook stays dormant (the SessionStart
hook emits a single one-time "run setup" tip, then never again). Zero cost where
you don't use it.

## Install

```sh
# 1. Add this repo as a plugin marketplace (once)
/plugin marketplace add <your-org>/claude-agent-orch

# 2. Install + enable the plugin
/plugin install agent-orch@agent-orch
```

(Or point the marketplace at a local clone during development.)

## Use

In any repo where you want project memory:

```
set up agent-orch
```

The `setup` skill copies the template tree into `.agent-orch/`, runs a guided
discovery pass over your actual codebase to draft a real STATUS / MAP /
TECH_STACK / PRODUCT, confirms with you, optionally seeds folder-level
CONTEXT.md, and writes a thin-fallback block to `CLAUDE.md`. Run it once per repo.

From then on it's automatic — the hooks load state, inject local context on
edit, and nudge you to keep state fresh.

## Layout

```
.claude-plugin/
  marketplace.json     # registers the plugin
  plugin.json          # plugin manifest (skills + hooks)
hooks/
  hooks.json           # SessionStart, PreToolUse(Edit|Write), Stop
  _common.py           # shared, fail-safe helpers
  sessionstart.py      # load STATUS+RULES, or one-time setup nudge
  pre_edit_context.py  # inject nearest CONTEXT.md before editing in a folder
  stop.py              # git-aware state-update + CONTEXT.md freshness nudge
skills/setup/SKILL.md  # scaffold + guided discovery
templates/             # the .agent-orch/ tree copied into target repos
```

## Design notes

- **Hooks are fail-safe**: any error prints nothing and exits 0 — a hook bug can
  never break your session.
- **PreToolUse never changes permissions**: it injects `additionalContext` only,
  with no `permissionDecision`, so it can't silently auto-approve edits.
- **Stop can't loop**: a Stop-hook message causes one agent continuation, so the
  nudge has three independent loop-breakers — `stop_hook_active`, a session git
  baseline (only flags changes made *this* session, not pre-existing dirt), and a
  nudge-signature cooldown (never repeats the same unresolved nudge).
- **`.agent-orch/` is committed to the target repo** so memory travels with the
  code; the *plugin* (hooks/skill) is what each developer installs.

## Known limitations

By design, accepted trade-offs (all fail safe — they make the hook *quieter*, never broken):

- **Bash edits aren't covered by CONTEXT injection.** The PreToolUse hook matches
  `Edit`/`Write`, not `Bash` — files changed via `sed`/`cat >` won't trigger a
  CONTEXT.md inject (matching Bash would fire on every shell command).
- **Very large/slow repos:** the Stop hook's `git status` has a 10s timeout; past
  that the freshness nudge is silently skipped.
- **`/compact` re-baselines:** changes made before a compaction fold into the new
  baseline and won't be nudged afterward.
- **Non-git repos:** the Stop nudge is disabled (it needs git to diff).
- **Per-session marker files** accumulate in the OS temp dir (cleared on reboot).

## Layering with other skills

agent-orch is the **state/context** layer. It composes with — and does not
replace — process skills (planning, TDD, debugging) and domain skills. Its
`tasks/` is your durable **backlog**; pair it with an implementation-plan skill
for *executing* a single item, and an issue pipeline only for slicing a big
feature into a queue.

See [docs/SKILL-WORKFLOW.md](docs/SKILL-WORKFLOW.md) for a "what to reach for,
when" map across agent-orch, superpowers, mattpocock, frontend-design, and rampstack.
