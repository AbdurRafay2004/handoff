---
name: verify-done
description: Use when about to claim work is complete, fixed, or passing — before committing, opening a PR, or telling the user it works. Requires running verification commands and confirming output first; evidence before assertions, always.
---

# Verify Done

Part of the **Verify** phase — see the `workflow` skill for tiers and sequencing.

Claiming work is complete without verification is dishonesty, not efficiency.

**The Iron Law: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

If you haven't run the verification command in this message, you cannot claim
it passes.

## Why this matters more here

The user reviews outcomes, not code. Evidence — command output, test summaries,
screenshots, preview URLs — is the only thing they can judge. An unverified
"done" that turns out broken doesn't just cost rework; it breaks the trust the
whole PM ↔ engineer division of labor depends on. One false "it works" costs
more than ten honest "it's not working yet"s.

## The gate function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: what command proves this claim?
2. RUN: the FULL command (fresh, complete)
3. READ: full output, exit code, failure count
4. VERIFY: does the output confirm the claim?
   - NO  → state the actual status, with the evidence
   - YES → state the claim WITH the evidence
5. ONLY THEN: make the claim

Skip any step = lying, not verifying.
```

## What each claim requires

| Claim | Requires | Not sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Typecheck clean | `tsc --noEmit`: exit 0 | Editor showed no squiggles |
| Linter clean | Linter output: 0 errors | Partial check |
| Build succeeds | Build command: exit 0 | Linter passing, logs look fine |
| Bug fixed | Original symptom re-tested: passes | Code changed, assumed fixed |
| Regression test works | Red-green verified (fails without fix, passes with) | Test passes once |
| Subagent completed | Diff inspected, changes verified | Agent reports "success" |
| Requirements met | Line-by-line checklist against spec/plan | Tests passing |

## Evidence for a non-coding reviewer

Every completion claim ships with evidence the user can judge directly:

- The exact commands run and their trimmed output (pass/fail counts, exit code).
- For UI changes: a screenshot or a preview URL they can click through.
- For behavior changes: what to do to see it working ("submit the form empty —
  you'll now see the error message").
- For T3 work: the checklist of spec requirements, each marked verified.

"The code looks correct" is not evidence. Show the thing working.

## Red flags — STOP

- "Should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Done!", "Perfect!")
- About to commit/push/PR without running verification
- Trusting a subagent's success report without checking the diff
- Partial verification presented as full
- Tired and wanting the work to be over
- ANY wording implying success without having run the check

## Rationalization prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler ≠ tests |
| "Agent said success" | Verify independently |
| "Partial check is enough" | Partial proves nothing |
| "Different words, so the rule doesn't apply" | Spirit over letter |

## Key patterns

```
✅ [run test command] [see: 34/34 pass] → "All tests pass."
❌ "Should pass now" / "Looks correct"

Regression test (red-green):
✅ Write → run (pass) → revert fix → run (MUST FAIL) → restore → run (pass)
❌ "I've written a regression test" (never seen red)

Requirements:
✅ Re-read plan → checklist → verify each → report gaps or completion
❌ "Tests pass, phase complete"
```

## When to apply

Before ANY success/completion claim or expression of satisfaction; before
committing, PR creation, or moving to the next task; before reporting a
subagent's work as done. Applies to paraphrases and implications, not just the
exact words.

Run the command. Read the output. THEN claim the result. Non-negotiable.

*Adapted from superpowers (MIT, © 2025 Jesse Vincent); see ATTRIBUTION.md.*
