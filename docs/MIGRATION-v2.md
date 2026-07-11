# Migrating a repo from agent-orch (v1.x) to handoff (v2.0.0)

At v2.0.0 the plugin was renamed from `agent-orch` to `handoff`, and the
scaffold directory changed from `.agent-orch/` to `.handoff/`. Repos set up
under the old name are silently dormant — the hooks no longer see them.

**First, on your machine (once, not per repo):**

```
/plugin uninstall agent-orch@agent-orch
/plugin marketplace remove agent-orch
/plugin marketplace add AbdurRafay2004/handoff
/plugin install handoff@handoff
```

**Then, in each old repo**, paste the prompt below into a Claude Code session.

---

## Copy-paste migration prompt

```text
Migrate this repository from agent-orch (v1.x) to handoff (v2.0.0). This is a
mechanical rename migration — do not redesign, rewrite, or "improve" any file
content beyond what is listed. Follow these steps exactly and in order.

1. PRECONDITIONS — check, and stop with a clear message if any fails:
   - A directory named `.agent-orch/` exists at the repo root.
   - No directory named `.handoff/` exists (if one does, stop: this repo is
     already migrated or half-migrated — report what you found and ask).
   - `git status` is clean, or the only changes are ones I told you about.
     If there is unrelated uncommitted work, stop and ask before proceeding.

2. RENAME the directory with git so history is preserved:
   git mv .agent-orch .handoff

3. VERSION STAMP: overwrite `.handoff/VERSION` with exactly:
   2.0.0

4. INTERNAL REFERENCES: inside `.handoff/` only, replace old-name references
   in text: every `.agent-orch` becomes `.handoff`, every remaining
   `agent-orch` becomes `handoff` (check RULES.md, BOOT.md, STATUS.md, MAP.md,
   CHANGELOG.md, docs/, tasks/, context/). Do not touch anything outside
   `.handoff/` in this step.

5. CLAUDE.md FALLBACK BLOCK: the repo's root `CLAUDE.md` (or `AGENTS.md`)
   contains a fallback block written by agent-orch setup that references
   `.agent-orch/` paths and the agent-orch name. Update that block only —
   same replacements as step 4. Leave every other part of the file untouched.

6. LEFTOVER CHECK: search the whole repo (excluding .git/) for the string
   `agent-orch`. The only acceptable remaining hits are historical entries in
   `.handoff/CHANGELOG.md` and task files under `.handoff/tasks/done/` —
   history stays as written. Fix anything else you find.

7. COMMIT everything from steps 2-6 as ONE commit:
   chore: migrate .agent-orch to .handoff (plugin renamed at v2.0.0)
   Stage only the files this migration changed. Do not push unless I say so.

8. VERIFY and show me evidence:
   - `ls .handoff/` shows the expected tree (STATUS.md, RULES.md, tasks/, ...).
   - `git log --oneline -1` shows the migration commit.
   - The leftover check from step 6 comes back clean.
   Then tell me to start a fresh session so the SessionStart hook picks up
   `.handoff/` — this session started before the rename and won't have it
   loaded.
```

---

## Notes

- The migration is safe to run on a clone: everything is in git, one commit,
  fully revertible.
- After migrating, the first fresh session should open with STATUS + RULES
  auto-loaded again. If it doesn't, check that the handoff plugin (not
  agent-orch) is installed and enabled.
