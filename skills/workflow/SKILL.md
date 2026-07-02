---
name: workflow
description: The operating pipeline for all development work — 6 phases (Brief, Plan, Build, Verify, Ship, Learn) with risk tiers that decide how much process a task gets. Use at the start of any development task to pick the tier and execution mode, when unsure whether a task needs a plan/tests/review, or when another skill needs the phase and tier vocabulary. This skill overrides any process embedded in other skills.
---

# Workflow

One pipeline for every project. The user is the product manager and architect:
they decide **what** and **why**, and judge results as evidence — working demos,
test output, preview URLs — never raw code. The agent is the senior engineer and
devops: it proposes, builds, verifies, ships, and always brings evidence to the gate.

**The tier decides the process — not the skill, not habit, not thoroughness for
its own sake.** When a heavier process is invoked on a lighter task, say so and
offer the lighter path before proceeding.

## Risk tiers

| Tier | What it covers | Process |
|---|---|---|
| **T1 — trivial** | copy, styling, config tweaks, small isolated edits | No plan. Edit inline → typecheck + lint → done. |
| **T2 — standard** | typical features, refactors within one area | Short plan (a few bullets, in-chat OK) → build inline → tests on the affected path → one review pass → evidence. |
| **T3 — risky** | money, auth, user data, migrations, deletes, cross-cutting changes | Written plan the user approves → TDD → security review → end-to-end verify → evidence at every gate. |

Declare the tier when starting a task. If the tier is wrong, the user corrects
it in one line ("this is T1") and that ruling stands.

## The six phases

1. **Brief** — user states what and why in product terms. Interrogate it briefly
   (skill: `brief`) — surface the 2–3 decisions that will hurt later, then stop.
   Gate: user says "yes, that's what I want."
2. **Plan** — propose the approach and declare the tier (skill: `plan`, T2/T3
   only). Trade-offs explained in plain language, as to a PM.
   Gate (T2/T3): user approves the plan.
3. **Build** — write the code. Inline by default; delegate to subagents only per
   the `delegate` skill's triggers (context pressure or true parallelism), never
   as ceremony. T3 builds test-first (skill: `tdd`). Bugs found along the way go
   through `debug`, not guess-and-patch.
4. **Verify** — non-negotiable, scaled by tier. Mechanical first: typecheck,
   lint, tests, build. Then T2+: code review pass; run the app and exercise the
   change. T3: security review, end-to-end verification. Before claiming done:
   skill `verify-done` — evidence before assertions, always.
   Gate: user judges the evidence (screenshots, test summary, preview URL) — the
   pipeline judged the code.
5. **Ship** — branch → PR → deploy → smoke-check the live result. Never
   `git add -A`; stage only what you changed. Every commit revertible.
6. **Learn** — update durable state (STATUS/CHANGELOG via agent-orch), plus one
   line: what did we learn / what nearly went wrong.

## Delegation (subagents)

Subagents exist to protect the main context window, not to add process.
Delegate when the `delegate` skill's triggers are met — a search/read that would
flood context, verbose build/test output, independent parallel tasks, or an
isolated T3 workstream. A 30-line change never needs an agent round-trip.

## Precedence

This pipeline outranks process instructions embedded in any other skill. Other
skills contribute technique (how to debug, how to write tests); this skill owns
sequencing, tiering, and how much ceremony a task deserves.
