# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

This repo **is a Claude Code plugin** named `agent-orch`. It is not an application.
It ships a hook-driven **project-memory** system plus an owned **development
workflow layer** that other repos install. There is no build step, no dependency
tree, and no test framework — the deliverable is Python hook scripts (stdlib
only), a skill set, and a template tree.

The skill set (v1.2.0+): `setup` (scaffolding), `workflow` (the 6-phase,
risk-tiered pipeline — the constitution that owns sequencing), and twelve
technique skills (`brief`, `plan`, `design`, `tdd`, `debug`, `architecture`,
`delegate`, `verify-done`, `security`, `browser-qa`, `ship`, `learn`) forked
from MIT-licensed superpowers, mattpocock-skills, gstack, and rampstack-skills
with all cross-pack orchestration stripped (see `ATTRIBUTION.md`). When editing
a technique skill, never reintroduce pack-style enforcement preambles or
cross-skill process handoffs — `workflow` alone decides sequencing and tiering.

Do not confuse the two layers:

- **The plugin** (`hooks/`, `skills/`, `.claude-plugin/`) — what a developer installs
  into their Claude Code. Editing here changes behavior for every repo that uses it.
- **The `templates/` tree** — the *payload* the `setup` skill copies into a target
  repo as `.agent-orch/`. This is committed to the target repo so memory travels with
  the code. Editing here changes what newly-set-up repos get; it does **not** affect
  already-set-up repos.

## Runtime model (how the pieces connect)

Everything is driven by three hooks registered in `hooks/hooks.json` (auto-loaded
because it lives at `hooks/hooks.json` — the plugin manifest deliberately does **not**
declare a `hooks` field; see commit 514a6dc). Each hook is a thin `python3` entry that
imports shared logic from `hooks/_common.py`:

- **`sessionstart.py`** (SessionStart) — if the target repo has `.agent-orch/`, injects
  `STATUS.md` + `RULES.md` in full plus an on-demand pointer, captures a git baseline
  for the session (**HEAD sha + dirty paths with status codes** — so the Stop hook sees
  committed work too), and checks `.agent-orch/VERSION` against the plugin version
  (template-drift nag; missing stamp nags once per repo). If no `.agent-orch/`, emits a
  **one-time** "run setup" tip per repo (marker file in `~/.cache/agent-orch/`) and stays
  silent forever after.
- **`pre_edit_context.py`** (PreToolUse: Edit/Write/MultiEdit/NotebookEdit) — walks up
  from the file being edited to find the nearest `CONTEXT.md` and injects it once per
  session; also corrects task files about to be written to the `tasks/` ROOT (they
  belong in `inbox|now|done`). Injects `additionalContext` **only** — never a
  `permissionDecision` — so it can't silently auto-approve edits.
- **`stop.py`** (Stop) — nudges when the session made new repo changes (**committed or
  uncommitted** — session-changed = commits since baseline HEAD + dirty paths whose
  code changed) but didn't update durable state: `STATUS.md` / `CHANGELOG.md` /
  `MAP.md` (structural changes only) / a folder's `CONTEXT.md`. Also flags: task files
  stranded in the `tasks/` root (shown once per session per stray-set), `STATUS.md`
  over 40 lines, **sentinel paths** (auth/migration/billing/… — configurable via
  `.agent-orch/SENTINELS`, forces the T3 question into the transcript), and an open
  `.agent-orch/GATE` (machine-readable T3 stall). The nudge instructs that state
  updates ride in the SAME commit as the code (amend only if unpushed AND the last
  commit is this session's own work).

The push/pull principle behind all of it: always-relevant state (STATUS+RULES) is
**pushed** every session; everything else (`BOOT.md`, `MAP.md`, `context/*`, `tasks/`,
`CHANGELOG.md`, folder `CONTEXT.md`) is **pulled on demand**, zero cost until read.

## Invariants — do not break these when editing hooks

These are the load-bearing correctness properties. Most of the git history is fixing
regressions against them.

1. **Fail-safe always.** Every hook wraps `main()` so any exception prints nothing and
   exits 0. A hook bug must never break a user's session. New code paths must preserve this.
2. **`_common.py` helpers swallow errors** (return `None`/`{}`/default) rather than raise.
   Keep that contract; callers assume it.
3. **`stop.py` has three independent loop-breakers** — do not remove any:
   `stop_hook_active` guard, the **session git baseline** (only flags changes made *this*
   session, not pre-existing dirt), and the **nudge-signature cooldown** (never repeats the
   same unresolved nudge). Removing one risks an infinite Stop-continuation loop.
4. **PreToolUse injects context only, no permission decision.**
5. **Path safety in `pre_edit_context.py`:** edits outside the project root are ignored,
   relative paths resolve against the project root (not the hook's cwd), and the walk-up
   stops at the root. Preserve these checks (commit df0a81e).
6. **Changes under `.agent-orch/` are excluded** from the Stop hook's "new work" set, so
   updating state doesn't itself trigger a nudge.

## Working / testing the hooks

There is no test runner, linter, or CI. Hooks are plain `python3` reading a JSON payload
on stdin and emitting a JSON `hookSpecificOutput` on stdout. Test one by piping a payload:

```sh
# SessionStart against a target repo that has .agent-orch/
echo '{"cwd":"/abs/path/to/target-repo","session_id":"t1"}' | python3 hooks/sessionstart.py

# PreToolUse — nearest CONTEXT.md for a file about to be edited
echo '{"cwd":"/abs/path/to/target-repo","session_id":"t1","tool_input":{"file_path":"src/foo.ts"}}' | python3 hooks/pre_edit_context.py

# Stop — needs a baseline first (run sessionstart with the same session_id, then make
# a change); after that, a second identical run stays silent (signature cooldown).
echo '{"cwd":"/abs/path/to/target-repo","session_id":"t1","stop_hook_active":false}' | python3 hooks/stop.py
```

No output + exit 0 is the common (correct) result — most invocations are intentionally
silent. Session state (git baseline, nudge signature, per-CONTEXT.md dedup markers) lives
in `<tmp>/agent-orch-session-<hash>/`; delete that dir to reset a "session" between tests.

Keep hooks **stdlib-only** — no third-party imports. `templates/` is markdown plus
`.gitkeep` files only.

## The setup skill

`skills/setup/SKILL.md` is the guided-discovery flow (`set up agent-orch` /
`/agent-orch:setup`). Its contract: copy `templates/` → `.agent-orch/`, read the real
codebase to *draft* STATUS/MAP/TECH_STACK/PRODUCT, **confirm with the user before saving**
(never invent project facts — RULES rule 5), optionally seed folder `CONTEXT.md`, and
append a thin-fallback block to the target repo's `CLAUDE.md` (for clones opened without
the plugin). It must refuse to overwrite an existing `.agent-orch/` (offer refresh instead).

## Releasing

`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` both carry the version —
**bump both together** (never hardcode the current number in docs; check the manifests).
Release-bump commit subjects follow `type: summary (vX.Y.Z)`; non-release commits omit
the version suffix. The marketplace registration reads GitHub, not the local clone —
a release is only live after `git push`.

## Further reading

- `README.md` — install/use, design notes, and the documented **known limitations**
  (Bash edits bypass CONTEXT injection, `git status` 10s timeout, `/compact` re-baselining,
  non-git repos disable the Stop nudge).
- `docs/SKILL-WORKFLOW.md` — how agent-orch (the state/context layer) composes with other
  skill families rather than replacing them.
