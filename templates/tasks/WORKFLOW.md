# Task Workflow

Use `tasks/` for durable follow-ups that should not disappear into chat history.
This is the project backlog — coarse, long-lived items across sessions. For
*executing* a single non-trivial item, write an implementation plan; for slicing
a big feature into a queue, an issue pipeline is the right tool. Tasks here are
the "what to do", not the "how".

## Folders
- `inbox/` — new follow-ups, questions, defects, and cleanup ideas.
- `now/` — small active priority set.
- `done/` — completed or intentionally closed tasks.

**Placement is not optional:** every task file lives inside one of those three
folders. The `tasks/` root contains ONLY this file and `TEMPLATE.md` — never
write a task file next to them. (The hooks flag root-level task files.)

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
6. Do not use tasks for detailed implementation history; use `CHANGELOG.md`.
