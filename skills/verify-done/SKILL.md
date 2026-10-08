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
| Requirement match | Diff vs brief, line by line | Tests passing |

## The Spec check

"It works" and "it's what was asked" are different claims. Verify both, on
separate axes:

- **Spec axis** — does the diff match what was asked? The spec source is the
  `brief` output (or the plan file from `plan`). Walk the diff against it line
  by line and report: (a) requirements missing or partial, (b) behavior nobody
  asked for (scope creep), (c) requirements that look implemented but wrong.
- **Standards axis** — does the code follow this repo's conventions
  (AGENTS.md/CLAUDE.md, folder CONTEXT.md, documented standards)?

Report the axes separately and **never rerank across them**: passing tests
cannot excuse a missed requirement, and a faithful diff cannot excuse a
convention break. A change can pass one axis and fail the other — merging the
reports lets one axis mask the other. If there is no brief or plan, say "no
spec available" in the report; don't invent one.

At T3, the two axes MAY run as parallel subagents (see `delegate`) so neither
pollutes the other's context; aggregate their findings without merging.

## QA tiers (anything with a browser surface)

QA depth scales with the tier (see `workflow`). Evidence = the checks run and
their results, not "the page looked fine".

| Tier | Depth | Check |
|------|-------|-------|
| T1 | Minimal | Typecheck + lint + affected test; browser QA only if the change is user-visible (see `browser-qa` — it skips T1 by default) |
| T2 | Standard, ~10 min | Smoke + meta description and og/twitter tags; sane heading hierarchy; `lang` attribute and favicon; `target="_blank"` links have `noopener`; responsive at 375/768/1440px; primary user flow exercised end to end |
| T3 | Full, 30+ min | Standard + every form submits and validates; cross-browser (at least Chrome + Safari); internal and external links resolve; security headers (HSTS, X-Frame-Options, X-Content-Type-Options); HTTPS only, no mixed content; 404s return HTTP 404; analytics events fire; cache headers sane |

A failed check is fixed before "done" or reported as a known issue — never
silently shipped. For the recurring production failure modes (caching, env
vars, images, third-party integrations), check
[references/web-bug-patterns.md](references/web-bug-patterns.md).

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
✅ Re-read brief/plan → diff vs each line → report gaps or completion
❌ "Tests pass, phase complete"
```

## When to apply

Before ANY success/completion claim or expression of satisfaction; before
committing, PR creation, or moving to the next task; before reporting a
subagent's work as done. Applies to paraphrases and implications, not just the
exact words.

Run the command. Read the output. THEN claim the result. Non-negotiable.

*Adapted from superpowers (MIT, © 2025 Jesse Vincent), mattpocock-skills (MIT, © 2026 Matt Pocock), and rampstack-skills (MIT, © 2026 RampStack Co.); see ATTRIBUTION.md.*
