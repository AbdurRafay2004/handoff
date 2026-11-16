# Changelog

## 2.7.0 — 2026-11-17

- Add the `context-audit` skill: it inventories what loads into every session
  for this project (plugins with their effective on/off state and which
  settings file decided it, an estimated per-session cost of their skill,
  agent and command descriptions, MCP servers, hooks, personal and project
  skills, and Codex plugins and MCP servers), judges each against the
  project's actual stack, and proposes per-project disables in
  `.claude/settings.local.json`. It edits only after approval; Codex is
  report-only; claude.ai connectors are pointed to the app's toggles.
- Add `scripts/context_inventory.py`, the read-only stdlib inventory behind it.
  It prints names, scopes and sizes only, never config values such as env,
  headers, tokens or URLs, and tolerates missing or malformed config files.
- Add regressions for enablement precedence, local-scope installs, inline and
  file-based plugin MCP servers, every Claude MCP scope, Codex TOML sections,
  secret redaction, malformed files and read-only behavior.

## 2.6.0 — 2026-11-17

- Add a large-session handoff reminder to the Stop hook. When the session's
  context crosses 200k tokens, and again at each further 200k, the agent is
  asked once to make STATUS.md (and, if needed, a `.handoff/handoffs/` note)
  enough for a fresh session, then tell the user a new session would be
  cheaper. It fires even on discussion-only turns.
- Context size comes from the transcript's latest main-thread usage record
  (Claude Code `message.usage`; Codex `token_count`), not file size, so
  compaction and subagent usage don't inflate it. A missing or unreadable
  transcript skips the reminder without output.
- Keep all three Stop loop-breakers; the reminder adds its own per-step marker
  and combines with the freshness nudge into one message when both apply.
- Add regressions for thresholds, repeats, both transcript formats, sidechain
  records, bad transcripts, `stop_hook_active`, and non-git repos.

## 2.5.0 — 2026-11-17

- Add `scripts/handoff_lint.py`, a read-only drift check the setup skill runs
  on "check handoff": task folder vs frontmatter status and strays in the
  tasks/ root, MAP.md and CONTEXT.md paths that exist nowhere in the repo
  (shorthand matched by suffix), leftover `<UPPER_CASE>` placeholders,
  STATUS.md over 25 lines, and CONTEXT.md notes whose folder had files added
  or removed, or 10+ commits, since they were last committed. Exit 0 clean,
  1 findings, 2 nothing to lint. No hook changes.
- CI's stdlib-only import scan now covers `scripts/` too.
- Add regressions for each check, nested CONTEXT.md ownership, shorthand
  paths, a clean repo, a repo without `.handoff/`, and read-only behavior.

## 2.4.0 — 2026-11-17

- Add session handoffs: when STATUS.md can't hold what the next session needs,
  write `.handoff/handoffs/YYYY-MM-DD-topic.md`. SessionStart lists open
  handoffs in one line with their age (no file contents, at most five shown) and
  flags ones older than 14 days to verify. Delete a handoff once absorbed.
- The Stop nudge names the handoffs folder for detail that won't fit STATUS.md.
- Move the STATUS.md upkeep rules from the template into BOOT.md ("Keeping
  STATUS.md"), cutting the injected STATUS template from 23 to 13 lines. New
  installs only; existing STATUS.md files are untouched.
- Add regressions for the listing (absent, empty, ages, stale flag, cap,
  non-markdown files, a non-directory path) and the Stop wording.

## 2.3.0 — 2026-11-17

- The Stop nudge now says what a handoff needs: STATUS.md must let a fresh
  session continue (work in progress, exact next step, uncommitted or
  unverified work, chat-only decisions) within its 25-line target.
- Replace the paragraph of amend conditions with one computed line: commit the
  state with pending code; otherwise amend only when HEAD is an unpushed,
  non-merge commit made since the session started; otherwise a follow-up commit.
- Keep the session's change-tracking baseline on `resume` and `compact`, so
  earlier session work still gets the end-of-turn reminder. All three Stop
  loop-breakers are unchanged.
- Add regressions for the wording, each amend case, and baseline handling per
  session source.

## 2.2.0 — 2026-11-17

- Add a risk-tier reminder to the SessionStart injection in repos with
  `.handoff/`: state T1/T2/T3 before development work and load the `workflow`
  skill for T2/T3. Reaches existing installs with no template refresh; repos
  without `.handoff/` still get only the one-time setup tip.
- Add regressions for the reminder's presence and its absence without `.handoff/`.

## 2.1.2 — 2026-10-14

- Extend the existing Stop hook with a default reminder to commit completed,
  verified session changes, including Handoff-only work and changes remaining
  after documentation updates. No extra hook, model call, staging or auto-commit.
- Preserve user instructions, unrelated work, approval gates and all three Stop
  loop-breakers. Clean trees and pre-existing dirt alone stay silent.
- Add subprocess regressions for staged, unstaged, untracked and Handoff-only
  changes, gate priority, cooldown, clean trees and read-only hook behavior.

## 2.1.1 — 2026-10-08

- Combine the T2 brief and plan into one proposal and approval. Reuse approval
  already given for the same scope and approach; keep separate T3 approvals.
- Add guidance for clear, connected explanations to the workflow and default
  RULES, preserving useful technical detail and the user's requested depth.
- Align the brief, plan, and workflow docs, and explain how existing repos can
  adopt the communication rules without overwriting their project rules.

## 2.1.0 — 2026-10-08

- Add a Codex manifest alongside the Claude manifest, using the same skills,
  hooks, templates, and marketplace.
- Read all file headers in Codex `apply_patch` inputs, including moves, and
  inject each affected folder's notes once per session.
- Find the git root when the host starts in a subfolder; resolve patch paths
  against the actual working directory. Ignore paths that escape through symlinks.
- Emit the supported Stop continuation response for both hosts, preserving
  the active-hook guard, session baseline, and signature cooldown.
- Support Codex's `PLUGIN_DATA` directory, silent malformed-input handling,
  host-specific setup fallbacks, and portable workflow instructions.
- Expand subprocess regression coverage for both hook contracts.
