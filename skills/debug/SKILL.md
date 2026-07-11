---
name: debug
description: Use when encountering any bug, test failure, unexpected behavior, or performance regression — before proposing any fix. Root-cause discipline plus a feedback-loop method; applies at every tier.
---

# Debug

Part of the **Build/Verify** phases — see the `workflow` skill for tiers and sequencing.

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**The Iron Law: NO FIXES WITHOUT ROOT-CAUSE INVESTIGATION FIRST.**

Use for any technical issue — test failures, production bugs, unexpected behavior,
performance problems, build failures, integration issues. Especially when under
time pressure, when "just one quick fix" seems obvious, or when previous fixes
didn't work. Debugging discipline is tier-independent: a T1 bug still gets a root
cause (the process is fast for simple bugs).

## Phase 0 — Read the local context

Before exploring, read the nearest `CONTEXT.md` and `.agent-orch/` state if they
exist — a correct mental model of the modules involved beats an hour of tracing.

## Phase 1 — Build a feedback loop

**This is the skill; everything else is mechanical.** A **tight** pass/fail
signal that goes red on *this* bug is what bisection, hypotheses, and
instrumentation all consume. Without one, no amount of staring at code helps.
Spend disproportionate effort here.

Ways to construct one, roughly in order:

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against known-good.
4. **Headless browser script** (Playwright) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace** — save a real request/payload/event log, replay it in isolation.
6. **Throwaway harness** — minimal subset of the system exercising the bug path.
7. **Property/fuzz loop** — for "sometimes wrong output", run 1000 random inputs.
8. **Bisection harness** — bug appeared between two known states? Automate the check and `git bisect run` it.
9. **Differential loop** — same input through old vs new version, diff outputs.

Then **tighten it**: faster (cache setup, narrow scope), sharper (assert the
exact symptom, not "didn't crash"), deterministic (pin time, seed RNG, isolate
filesystem). A 2-second deterministic loop is a debugging superpower; a
30-second flaky one is barely better than none.

**Non-deterministic bugs:** raise the reproduction rate, don't chase a clean
repro — loop the trigger 100×, add stress, narrow timing windows. A 50%-flake
is debuggable; 1% is not.

**Loop criteria before proceeding:** red-capable (catches this specific bug),
deterministic, fast (seconds), runnable unattended — and you have run it at
least once. If you're reading code to build a theory before this exists, stop:
jumping straight to a hypothesis is the exact failure this skill prevents.

**Genuinely can't build one?** Say so explicitly, list what you tried, and ask
the user for a reproducing environment, a captured artifact (HAR, log dump,
recording), or permission to add temporary instrumentation. Don't hypothesize
without a loop.

## Phase 2 — Reproduce, minimise, investigate

Run the loop; watch it go red. Confirm it produces the failure **the user
described** — not a nearby different failure. Wrong bug = wrong fix.

**Minimise:** shrink to the smallest scenario that still goes red, cutting
inputs/callers/config one at a time and re-running after each cut. Done when
every remaining element is load-bearing. The minimal repro shrinks the
hypothesis space and becomes the regression test later.

**Investigate:**
- **Read error messages carefully** — stack traces completely; they often
  contain the exact answer. Note line numbers, paths, error codes.
- **Check recent changes** — git diff, recent commits, new dependencies,
  config or environment differences.
- **Multi-component systems** (CI → build → deploy, API → service → DB): before
  proposing anything, instrument each component boundary — log what enters and
  exits each layer, verify config propagation — run once, and let the evidence
  show WHERE it breaks before investigating WHY.
- **Error deep in the call stack?** Trace backward to the original trigger —
  see `references/root-cause-tracing.md`. Fix at the source, not the symptom.

**Pattern signatures** — check the symptom against known cause families first:

| Signature | Likely family — where to look |
|-----------|-------------------------------|
| Intermittent, timing-dependent | Race condition — concurrent access to shared state |
| Type/nil errors on values that "can't" be nil | Null propagation — missing guards on optionals |
| Inconsistent data, partial updates | State corruption — transactions, callbacks, hooks |
| Timeouts, unexpected response shapes | Integration failure — external calls, service seams |
| Works locally, fails in staging/prod | Configuration drift — env vars, flags, DB state |
| Old data, fixed by a cache clear | Stale cache — Redis, CDN, browser, framework cache |

## Phase 3 — Hypothesise (plural)

Generate **3–5 ranked hypotheses** before testing any. Single-hypothesis
generation anchors on the first plausible idea.

Each must be **falsifiable**: "If X is the cause, then changing Y will make the
bug disappear." If you can't state the prediction, it's a vibe — discard or
sharpen.

**Show the ranked list to the user before testing.** They often have domain
knowledge that re-ranks instantly ("we just deployed a change to #3"). Cheap
checkpoint; don't block on it if they're away.

Also compare against working examples: find similar code that works in the same
codebase, read reference implementations completely (don't skim), and list every
difference, however small — don't assume "that can't matter."

> A broad search for those examples (vs. a couple of targeted greps) is a
> delegate trigger — ask the user delegate-or-inline first (`delegate` skill).

## Phase 4 — Instrument and test hypotheses

- Each probe maps to a specific prediction. **One variable at a time.**
- Prefer a **debugger/REPL breakpoint** over logs; targeted logs at the
  boundaries that distinguish hypotheses over "log everything and grep".
- **Tag every debug log** with a unique prefix (e.g. `[DEBUG-a4f2]`) — cleanup
  becomes a single grep. Untagged logs survive; tagged logs die.
- **Performance regressions:** logs are usually wrong. Establish a baseline
  measurement (timing harness, profiler, query plan), then bisect. Measure
  first, fix second.
- Hypothesis confirmed → Phase 5. Refuted → next hypothesis. **Don't stack
  fixes on top of failed fixes.**
- When you don't know, say "I don't understand X" — don't pretend, research.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only at a **correct seam**:
one that exercises the real bug pattern as it occurs at the call site. A
too-shallow seam (unit test that can't replicate the triggering chain) gives
false confidence. **If no correct seam exists, that is itself a finding** —
document it and flag the architecture (see `design`), or hand off to
`architecture` for a structured scan.

1. Turn the minimised repro into a failing test at that seam (see `tdd`).
2. Watch it fail. 3. Apply ONE fix addressing the root cause — no "while I'm
here" improvements. 4. Watch it pass. 5. Re-run the Phase 1 loop against the
original un-minimised scenario, and the full test suite.

After the root cause is fixed, consider validating at every layer the bad data
passed through so the bug becomes structurally impossible — see
`references/defense-in-depth.md`.

**If the fix doesn't work:** STOP and count. Under 3 attempts → return to
Phase 2 with the new information. **3+ failed fixes → the problem is
architectural, not tactical.** Signs: each fix reveals new coupling elsewhere,
fixes require massive refactoring, new symptoms keep appearing. Stop fixing
symptoms and question the pattern itself — discuss with the user before any
fourth attempt. This is not a failed hypothesis; it's a wrong architecture.
Offer the escalation explicitly: **A)** continue with a genuinely new, named
hypothesis; **B)** escalate for architectural review — invoke the
`architecture` skill (proactive friction scan → candidate cards → decision);
**C)** instrument and wait — catch it live. Three *refuted hypotheses* in a
row is the same signal.

## Phase 6 — Cleanup + post-mortem

Before declaring done (then run `verify-done`):

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or the missing seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (grep the prefix)
- [ ] Throwaway harnesses deleted
- [ ] The winning hypothesis stated in the commit message — the next debugger learns

Close with a compact report — it doubles as the commit-message body:
```
DEBUG REPORT
Symptom:    what was observed
Loop:       the Phase 1 feedback loop used
Root cause: what was actually wrong
Fix:        what changed (file:line)
Evidence:   red → green output proving it
```

Then ask: **what would have prevented this bug?** If the answer is
architectural, note it in `.agent-orch/` state or the backlog — after the fix
is in, when you know the most.

## Red flags — stop and return to Phase 1

- "Quick fix for now, investigate later" / "Just try changing X and see"
- Multiple changes at once, then run tests
- "It's probably X, let me fix that" / proposing solutions before tracing data flow
- "One more fix attempt" when already 2+ deep
- Each fix reveals a new problem in a different place
- The user pushes back with "is that actually happening?" or "stop guessing" —
  you assumed without verifying; go back to evidence.

## Common rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too; the process is fast for them. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "I'll write the test after confirming the fix" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked; causes new bugs. |
| "I see the problem, let me fix it" | Seeing symptoms ≠ understanding the root cause. |
| "One more fix attempt" (after 2+) | 3+ failures = architectural problem. Question the pattern. |

## When investigation finds no root cause

If it's truly environmental, timing-dependent, or external: document what you
investigated, implement appropriate handling (retry, timeout, clear error),
add monitoring for next time. But 95% of "no root cause" is incomplete
investigation.

## References

- `references/root-cause-tracing.md` — trace bugs backward through the call stack to the original trigger
- `references/defense-in-depth.md` — validate at every layer so the bug becomes impossible
- `references/condition-based-waiting.md` — replace arbitrary timeouts with condition polling (flaky tests)

*Adapted from superpowers (MIT, © 2025 Jesse Vincent), mattpocock-skills (MIT, © 2026 Matt Pocock), and gstack (MIT, © Garry Tan); see ATTRIBUTION.md.*
