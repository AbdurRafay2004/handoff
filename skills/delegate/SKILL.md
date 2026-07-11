---
name: delegate
description: Use when a task would flood the main context window — broad searches, verbose test/build output, 2+ independent parallel tasks, or an isolated large workstream. How to hand work to subagents well, and when not to.
---

# Delegate

Part of the **Build** phase — see the `workflow` skill for tiers and sequencing.

Subagents exist to **protect the main context window** and exploit **true
parallelism** — not to add process. Every dispatch costs a full agent
spin-up: the agent re-reads context, explores, works, and reports. Spend that
cost only when it buys something.

## Triggers — delegate when (and only when)

1. **Context-flooding search/read:** answering requires sweeping many files
   but you only need the conclusion, not the file contents.
2. **Verbose output:** test suites, builds, long logs — where only the
   summary matters in the main session.
3. **True parallelism:** 2+ genuinely independent tasks with no shared state
   and no sequential dependency.
4. **Isolated large workstream (T3):** big enough that a fresh, focused
   context outperforms a crowded one.

When a trigger fires, **stop and call `AskUserQuestion`**: name the task, why it
triggered, a suggested model tier, and delegate-or-inline as options. Never
decide silently in either direction. This applies at the trigger point, whenever
it fires — including in the middle of another skill's process. (Doesn't apply to
the anti-triggers below.)

**Anti-triggers — do it inline instead:**
- Small, sequential, or interdependent work.
- A 30-line change never needs an agent round-trip.
- Never delegate "to follow process" — an implementer+reviewer pair per tiny
  task turns 15 minutes of work into 8 round-trips of ceremony.
- Exploratory debugging where you don't yet know what's broken — you need the
  full picture in one context.
- Related failures (fixing one might fix the others): investigate together
  first.

## Writing the dispatch prompt

A subagent inherits none of your session. You construct exactly what it needs:

1. **Focused scope** — one clear problem domain. "Fix all the tests" loses the
   agent; "fix agent-tool-abort.test.ts" keeps it on target.
2. **Self-contained context** — paste the error messages, name the files, one
   line on where this fits in the project, interfaces/decisions it can't
   discover itself, and your resolution of any known ambiguity.
3. **Constraints** — "do NOT change production code", "fix tests only",
   "don't just increase timeouts — find the real issue."
4. **Expected return** — say exactly what to report back: "return a summary of
   root cause and changes", a structured result, a file path. The agent's
   final message is your only deliverable from it.
5. **Exact values live in one place.** If the work follows a plan, point the
   agent at its task text rather than paraphrasing requirements — paraphrase
   drift is how implementations diverge from spec.

## Coordination rules

- **One writer per file.** Never let two concurrent agents edit the same
  files or share mutable state; parallel writers = merge conflicts.
- **Parallel dispatches go in one message;** one per message = sequential.
  Sequential dependencies mean you wanted one agent, not two.
- **Match model to task** when dispatching: mechanical single-file work → a
  fast cheap model; multi-file integration → standard; architecture/judgment →
  the most capable. Turn count beats token price — a too-weak model taking 3×
  the turns costs more than a stronger one.
- **Handle agent status honestly:** if an agent reports it's blocked or needs
  context, change something (context, model, task size) before re-dispatching —
  never force a retry of the same failure.

## Integrating results

- **Verify, don't trust.** An agent's "success" report is a claim, not
  evidence — check the diff, run the affected tests yourself (see
  `verify-done`). Agents can make systematic errors.
- Read each summary; check for conflicts between concurrent agents' changes;
  run the full affected suite after integrating.
- **One fixer for all findings, not one per finding.** If review/verification
  surfaces multiple issues, dispatch a single fix agent with the complete
  list — per-finding fixers each rebuild context and re-run suites.

## Checkpoint economics

A **checkpoint** is a human-in-the-loop decision point — a subagent reporting
back to you, or you presenting a tier gate to the user. Two rules:

- **Push right.** Defer a checkpoint as late as it will go, so whoever waits
  is asked once, late, with maximum work already done. A subagent that comes
  back to ask what it could have discovered itself wasted its dispatch; a T3
  approval gate should arrive with the plan complete, not in fragments.
- **Arrive decision-ready.** A checkpoint presents a synthesized decision,
  never raw output: what was produced, why, the recommendation, a pointer to
  the artifact. Demand this shape in the dispatch prompt's "expected return";
  produce it yourself at the user's tier gates.

*Checkpoint vocabulary adapted from a personal workflow-design skill (loop-me).*

## Review scaling

Independent review passes (a separate reviewer agent over the diff) are a
**T3 tool** — worth it for money/auth/data/migration work. They are not a
default. For T1/T2, mechanical verification (typecheck, tests, lint) plus your
own read of the diff is the right-sized gate.

*Adapted from superpowers (MIT, © 2025 Jesse Vincent); see ATTRIBUTION.md.*
