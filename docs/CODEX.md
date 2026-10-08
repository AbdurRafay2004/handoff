# Codex compatibility

handoff supports Claude Code and local Codex desktop/CLI with one shared set
of skills, templates, and Python hooks. Python 3.8+ and git must be available
where the hooks execute. No MCP server or Python packages are required.

## Install and try it

For this checkout, use the absolute path to your clone:

```sh
codex plugin marketplace add /absolute/path/to/handoff
codex plugin add handoff@handoff
```

For a published release, replace the path with `AbdurRafay2004/handoff`.
Codex reads the existing `.claude-plugin/marketplace.json`; a second marketplace
catalog is unnecessary. `.codex-plugin/plugin.json` declares the Codex package,
while `.claude-plugin/plugin.json` continues to declare the Claude package.
Both discover `hooks/hooks.json` by default and share `skills/`.

1. Install from the marketplace in the desktop Plugins UI or CLI.
2. Review and trust the handoff hook definitions. In the CLI, use `/hooks`.
   Installation alone does not trust hooks. Changed definitions require review
   again; don't bypass trust to diagnose an install.
3. Start a new chat in a target repo and ask **“set up handoff”**. Existing
   `.handoff/` users can ask to refresh the fallback instructions instead.
4. Confirm setup created or updated `AGENTS.md` with the memory fallback.
   Codex does not automatically read `CLAUDE.md`.
5. Start another chat: STATUS and RULES should appear automatically. A native
   patch in a folder with `CONTEXT.md` should load that folder's notes once.

Local plugin installs use a cached copy. After changing this checkout, refresh
or reinstall it through the host and start a new chat; editing the source
alone does not update a running chat's installed plugin.

## What changed

| Seam | Claude Code | Codex |
|---|---|---|
| File input | `file_path` / `notebook_path` | `tool_name: apply_patch`, patch in `tool_input.command` |
| Relative file paths | Project root | Hook `cwd` for patches |
| Project root | `CLAUDE_PROJECT_DIR`, when set | Git root discovered from `cwd`; supports worktrees |
| Persistent markers | `CLAUDE_PLUGIN_DATA` | `PLUGIN_DATA`, with Claude alias fallback |
| Hook executable paths | `CLAUDE_PLUGIN_ROOT` | Codex also supplies the Claude alias |
| Instructions without hooks | `CLAUDE.md` | `AGENTS.md` |
| Stop reminder | `decision: block` + `reason` | Same response |

`PreToolUse` only adds context; it never allows, denies, or rewrites an edit.
The patch parser reads file headers for adds, updates, deletes, and moves.
It collects every affected folder, deduplicates context within a patch and
session, and ignores paths outside the project, including symlink escapes.
Task-folder corrections remain visible on every attempt.

For `Stop`, `decision: block` asks the host for one more model turn with the
reminder in `reason`. It does not deny a tool. The old
`hookSpecificOutput.additionalContext` response is not the supported Stop
continuation contract. All three loop-breakers remain: `stop_hook_active`,
the session git baseline, and the unresolved-reminder signature cooldown.

Skills use the tools available in the current host. Claude-only question,
review, or scheduling commands have explicit fallbacks; user and host
instructions still take precedence over the workflow.

## Troubleshooting and limits

- **No hooks fire:** confirm the installed copy is current, hooks are enabled,
  the project is trusted where required, and the hook definitions are trusted.
  Managed policy can disable non-managed hooks.
- **Session memory works but folder notes do not:** use native `apply_patch`.
  Shell edits, including running an `apply_patch` executable through Bash,
  do not provide structured file input to this hook.
- **Cloud-orchestrated ChatGPT Work:** bundled command hooks do not execute,
  even when some tools run locally. Skills and manual memory instructions can
  still help; don't treat that as automatic hook support.
- **Public plugin directory:** plugins with lifecycle hooks must be distributed
  through manual Codex installation; they are not eligible for public directory
  submission with those hooks included.
- **Existing change-tracking limits:** compaction captures a new baseline;
  already-pushed commits and same-status edits to pre-existing dirty files may
  be missed. Git command timeouts and errors skip the affected check quietly.

## Verification

```sh
python3 tests/test_hooks.py
```

This exercises the hooks as subprocesses with both hosts' payloads, temporary
git repos, and isolated marker directories. It proves the hook contract and
regressions; it does not certify every desktop/CLI release or a trusted live
installation. Perform the installation steps above for host acceptance.

Local validation on 2026-10-08: Codex CLI 0.160.0's `plugin/read` API read this
checkout through the shared marketplace and recognized the Codex manifest,
all 15 skills, and all three hooks. This was read-only package discovery;
no plugin was installed and no hook trust was changed.

Official references (checked 2026-10-08):

- [Hook events, input/output schemas, aliases, and trust](https://learn.chatgpt.com/docs/hooks)
- [Plugin manifests, marketplaces, and hook distribution](https://developers.openai.com/plugins/build/plugins)
- [Claude plugin conversion and directory restrictions](https://developers.openai.com/plugins/guides/submit-claude-plugin)
