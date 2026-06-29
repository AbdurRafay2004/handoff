# Skill Workflow — what to reach for, when

A map for orchestrating skills from many sources (agent-orch, superpowers,
mattpocock, frontend-design, rampstack) without them turning into noise.

## Three layers

- **State** — `agent-orch` (this plugin). Automatic; loads the right context at
  the right moment.
- **Process** — superpowers, mattpocock. *How* you work.
- **Domain** — frontend-design, rampstack. *Execution* of specific work.

These don't compete; they stack. agent-orch loads state, a process skill governs
behavior, a domain skill does the work.

## Default flow for a task

1. **Start** — agent-orch auto-loads STATUS + RULES. For a new feature/idea, pin
   the design first: `superpowers:brainstorming` (open-ended) or `grilling`
   (stress-test a plan you already have).
2. **Plan** — `superpowers:writing-plans` turns the design into bite-sized steps.
3. **Build** — execute with TDD (`superpowers:test-driven-development` or
   `mattpocock:tdd`); `superpowers:systematic-debugging` when stuck;
   `frontend-design` for UI.
4. **Finish** — `superpowers:verification-before-completion` +
   `requesting-code-review`; agent-orch's Stop hook nudges STATUS / CHANGELOG /
   CONTEXT.md updates before you wrap.
5. **Backlog** — capture follow-ups in agent-orch `tasks/` (the durable spine).

## Occasional / opt-in

- **Big feature** → slice it with Matt's `/to-prd` → `/to-issues` → `/triage` →
  `/implement` (use the Local Markdown tracker; no GitHub needed).
- **Messy app codebase** → `mattpocock:improve-codebase-architecture`
  (+ `codebase-design`, `domain-modeling`) to make it AI-navigable.
- **Marketing / SEO / brand / content push** → enable rampstack per-project, then
  disable it again.

## Two rules of thumb

- Reach for **one** process skill per phase — don't stack them.
- Keep **one** of each spine: one task system (agent-orch `tasks/`), one meaning
  for `CONTEXT.md`. Overlapping systems are what create noise.
