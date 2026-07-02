---
name: plan
description: Use when a task is T2/T3 — before building a feature that spans multiple files or carries risk. Produces an implementation plan with exact files, complete code steps, and per-stage verification.
---

# Plan

Part of the **Plan** phase — see the `workflow` skill for tiers and sequencing.

Write implementation plans assuming the implementer has zero context for this
codebase and questionable taste. Document everything they need: which files to
touch per task, the code itself, how to test it, what to check. Bite-sized
tasks. DRY. YAGNI. Test-first where the tier demands it. Frequent commits.

## Tier scaling

- **T1:** skip this skill — no plan, just do the task.
- **T2:** short plan as bullets in chat — files to touch, order of work,
  verification step. No document.
- **T3:** written plan file the user approves BEFORE build starts. Trade-offs
  stated in plain product language. Save to `docs/plans/YYYY-MM-DD-<feature>.md`
  (user preferences override).

## Scope check

If the spec covers multiple independent subsystems, it should have been
decomposed during `brief`. If it wasn't, stop and suggest one plan per
subsystem — each producing working, testable software on its own.

## File structure first

Before defining tasks, map which files will be created or modified and what
each is responsible for. This locks in decomposition decisions.

- Each file gets one clear responsibility, with well-defined interfaces.
- Prefer smaller focused files; edits are more reliable when a file can be held
  in context at once.
- Files that change together live together — split by responsibility, not by
  technical layer.
- In existing codebases follow established patterns; if a file you're modifying
  has grown unwieldy, a split may be part of the plan.

## Task right-sizing

A task is the smallest unit that carries its own test cycle and could be
meaningfully accepted or rejected on its own. Fold setup, configuration, and
docs into the task whose deliverable needs them. Each task ends with an
independently testable deliverable.

**Each step is one action (2–5 minutes):** write the failing test — run it and
watch it fail — implement the minimal code — run tests and watch them pass —
commit.

## Plan document structure (T3)

```markdown
# [Feature] Implementation Plan

**Goal:** [one sentence]
**Tier:** T3 — [why: touches payments / auth / migration ...]
**Architecture:** [2–3 sentences]
**Tech stack:** [key technologies]

## Global constraints
[Project-wide requirements from the spec — version floors, naming rules,
platform requirements — one line each, exact values copied verbatim.
Every task implicitly includes this section.]

### Task N: [Component]
**Files:**
- Create: `exact/path/to/file.ts`
- Modify: `exact/path/to/existing.ts:123-145`
- Test: `tests/exact/path/to/file.test.ts`

**Interfaces:**
- Consumes: [exact signatures this task uses from earlier tasks]
- Produces: [exact names/types later tasks rely on]

- [ ] Step 1: Write the failing test        (show the actual test code)
- [ ] Step 2: Run it — expected: FAIL with [message]
- [ ] Step 3: Minimal implementation        (show the actual code)
- [ ] Step 4: Run tests — expected: PASS
- [ ] Step 5: Commit (exact `git add <files>` — never `git add -A`)
```

## No placeholders

These are plan failures — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "handle edge cases"
- "Write tests for the above" without the actual test code
- "Similar to Task N" — repeat the code; tasks may be read out of order
- Steps that describe what to do without showing how
- References to types or functions not defined in any task

Exact file paths always. Complete code in every code step. Exact commands with
expected output.

## Self-review

After writing the plan, check it against the spec with fresh eyes:

1. **Spec coverage** — every requirement maps to a task? List gaps, add tasks.
2. **Placeholder scan** — any pattern from the list above? Fix.
3. **Type consistency** — do names/signatures used in later tasks match what
   earlier tasks defined? `clearLayers()` in Task 3 but `clearFullLayers()` in
   Task 7 is a bug.

Fix inline; no re-review needed.

## Handoff

Execution mode is decided by the `workflow` tier, not by this skill: inline in
this session by default; subagents only when the `delegate` triggers apply.
For T3, present the plan to the user and get approval before building.

*Adapted from superpowers (MIT, © 2025 Jesse Vincent); see ATTRIBUTION.md.*
