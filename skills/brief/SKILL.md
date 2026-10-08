---
name: brief
description: Use when starting a new feature or product request — clarifies scope and decisions before implementation. Supplies a short summary for T2's combined brief/plan review or a written spec for T3. Depth scales with risk tier.
---

# Brief

Part of the **Brief** phase — see the `workflow` skill for tiers and sequencing.

Turn an idea into clear scope through collaborative dialogue. The
user speaks as PM/architect (what and why); you interrogate as the senior
engineer until the 2–3 decisions that would hurt later are settled — scope,
edge cases, failure paths — then stop asking. Don't design the universe.

## Tier scaling

- **T1 (trivial):** skip this skill entirely. Just do the task.
- **T2 (standard):** ask targeted questions only where requirements are unclear.
  Draft a 3–6 line scope summary for the workflow's combined brief/plan review.
  No separate brief sign-off and no document needed.
- **T3 (risky — money/auth/data/migrations):** full interrogation, written spec,
  explicit approval before planning.

## The process

**Understand the context first.** Check current project state — files, docs,
recent commits, `.handoff/` state if present. If a question can be answered
by exploring the codebase, explore the codebase instead of asking.

> If that exploration turns broad (vs. a few targeted greps), it's a delegate
> trigger — ask the user delegate-or-inline first (`delegate` skill).

**Read the code before you ask.** Before asking anything the code could
answer, gather at least one piece of evidence — grep the symbol, read the
file — and cite `path:line` in the question itself: not "does this touch the
database?" but "`orders/service.ts:142` writes to `orders` directly — new
column there, or a separate table?" Grounded questions get grounded answers.
If you truly find nothing, say what you searched and proceed as greenfield.

**Assess scope before refining details.** If the request describes multiple
independent subsystems ("build a platform with chat, billing, and analytics"),
flag it immediately and help decompose into sub-projects: what are the
independent pieces, how do they relate, what order? Then brief the first
sub-project. Each sub-project gets its own brief → plan → build cycle.

**Ask questions one at a time.** Multiple questions at once are bewildering.
Prefer multiple choice when possible; open-ended is fine too. For each question,
provide your recommended answer — the user corrects a recommendation faster
than they produce an answer from scratch. Focus on purpose, constraints,
success criteria, and what happens when things fail (empty states, bad input,
the payment that doesn't go through).

**T3 depth — interrogate relentlessly.** Walk down each branch of the design
tree, resolving dependencies between decisions one by one, until you reach
shared understanding. Stress-test the plan's premises, not just its details.

**Propose 2–3 approaches** with trade-offs, in plain product language. Lead
with your recommendation and why. YAGNI ruthlessly — strike features the goal
doesn't need.

**Present the design, scaled to complexity** — a few sentences for simple
work, sections for nuanced work (architecture, components, data flow, error
handling, testing). For T2, collect feedback in the combined brief/plan review
rather than asking for approval of each section. For T3, validate major
sections incrementally. Go back and clarify when something doesn't make sense.

**Design for isolation and clarity.** Break the system into units with one
clear purpose each, communicating through well-defined interfaces. For each
unit: what does it do, how do you use it, what does it depend on? If you can't
change a unit's internals without breaking consumers, the boundaries need work.
Smaller, well-bounded units are also easier to build reliably — a file that
grows large is usually doing too much.

**In existing codebases:** follow established patterns. Where existing code has
problems that affect this work, include targeted improvements in the design —
but don't propose unrelated refactoring.

## Writing the spec (T3)

Open with a one-line **impact/effort call** (high-impact/low-effort → do now;
low-impact/high-effort → question the spec itself) so the reader knows whether
the work earns its cost. Give every requirement **testable acceptance
criteria** — numbered, pass/fail, no subjective language:

- ✅ "Expired orders return HTTP 410 for all 4 user roles"
- ❌ "The feature works correctly" / "edge cases are handled"

Save to `docs/specs/YYYY-MM-DD-<topic>.md` (user preferences override) and
self-review it with fresh eyes:

1. **Placeholder scan** — any "TBD"/"TODO"/vague requirements? Fix them.
2. **Internal consistency** — do sections contradict each other?
3. **Scope check** — focused enough for a single plan, or needs decomposition?
4. **Ambiguity check** — could any requirement be read two ways? Pick one,
   make it explicit.

Fix issues inline, then ask the user to review the spec before proceeding.
For T3, get spec approval before planning.

## Key principles

- One question at a time; multiple choice preferred; recommendation attached.
- Explore the codebase instead of asking what it can answer.
- YAGNI ruthlessly. Explore 2–3 alternatives before settling.
- Validate unclear decisions early; avoid separate section approvals for T2.
- Surface failure paths early; they are where specs go wrong.
- Stop when the load-bearing decisions are settled.

*Adapted from superpowers (MIT, © 2025 Jesse Vincent), mattpocock-skills (MIT, © 2026 Matt Pocock), gstack (MIT, © Garry Tan), and rampstack-skills (MIT, © 2026 RampStack Co.); see ATTRIBUTION.md.*
