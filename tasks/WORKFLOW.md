# Task Workflow (plugin development)

This `tasks/` folder is the backlog for developing **this repo** — the handoff
plugin itself. It is a standalone copy of the handoff task convention and is
**not** part of the plugin's behavior or payload:

- It is not `templates/tasks/` (that is what `setup` copies into other repos).
- The hooks only inspect `.handoff/tasks/`, so nothing here is enforced or
  flagged automatically — keep placement tidy by hand.

Use it for durable follow-ups that should not disappear into chat history:
coarse, long-lived items, the "what to do", not the "how".

## Folders
- `inbox/` — new follow-ups, questions, defects, and cleanup ideas.
- `now/` — small active priority set.
- `done/` — completed or intentionally closed tasks.

Every task file lives inside one of those three folders. The `tasks/` root
contains ONLY this file and `TEMPLATE.md`.

## Task File Format
One markdown file per task with YAML frontmatter. See `TEMPLATE.md`.

**Required:** `title`, `status`, `priority`.
**Optional:** `why_it_matters`, `context`, `added_at`, `links`, `id`.

- `status`: `inbox` | `now` | `done`
- `priority`: `low` | `medium` | `high`
- Recommended filename: `YYYY-MM-DD-short-kebab-case-title.md`

## Rules
1. Check for an existing related task before creating a new one.
2. Folder and frontmatter `status` must match.
3. New ideas default to `inbox/`.
4. Keep `now/` small.
5. Move completed or intentionally closed work to `done/`.
6. Do not use tasks for release history; use the root `CHANGELOG.md`.
