---
name: architecture
description: Scan the codebase for architectural friction and propose deepening opportunities as candidate cards, then interrogate the chosen one into a decision. Two entry points — proactive, when the user asks "improve the architecture" or "why is this codebase painful to work in"; reactive, when the debug skill's "3+ failed fixes = architectural problem" rule hands off here. Inherently T2/T3; the outcome is a decision plus a plan.
---

# Architecture

Part of the **Plan/Build** phases — see the `workflow` skill for tiers and sequencing.

Surface architectural friction and propose **deepening opportunities** — refactors
that turn shallow modules into deep ones. The aim is leverage, locality, and
testability. This is inherently **T2/T3** work: the outcome is a *decision and a
plan*, executed via the `plan` skill — never an immediate rewrite.

## Two entry points

1. **Proactive** — the user asks to improve the architecture, or asks why this
   codebase is painful to change, navigate, or test.
2. **Reactive** — the `debug` skill hands off here under its rule that **3+ failed
   fixes on the same bug signals an architectural problem**. Start the friction
   scan in the neighbourhood of the failed fixes.

## Vocabulary and prior decisions

- Use the `design` skill's glossary exactly — **module**, **interface**, **depth**,
  **seam**, **leverage**, **locality** — in every suggestion. Don't drift into
  "component," "service," "API," or "boundary."
- Read the project's domain glossary and context notes in `.handoff/context/`
  and any ADRs in `docs/adr/` **before** scanning. Domain language names good
  seams; ADRs record decisions this skill should not re-litigate.
- Name things in domain terms: if the glossary defines "Order," talk about
  "the Order intake module" — not "the FooBarHandler."

## Process

### 1. Friction scan

Walk the codebase organically — don't follow rigid heuristics; note where you
*experience* friction:

- Where does understanding one concept require **bouncing between many small
  files**? That comprehension cost is the friction itself.
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have **pure functions been extracted just for testability**, while the real
  bugs hide in how they're called (no locality)?
- Where do tightly-coupled modules **leak across their seams**?
- Which parts are **untestable through their current interface** — no seam to test at?

Apply the **deletion test** to anything you suspect is shallow: would deleting it
*concentrate* complexity, or just move it? "Yes, concentrates" is the signal you want.

The scan MAY be delegated to a read-only subagent per the `delegate` skill —
context-flooding search is its #1 trigger; you need the conclusions, not the file dumps.

### 2. Present candidates as markdown cards

Present findings directly in chat as plain markdown — one card per candidate:

```markdown
## Candidate: <domain-term name>

**Strength:** Strong | Worth exploring | Speculative

**Files:** `path/one.py`, `path/two.py`

**Problem:** One or two sentences — what hurts, in friction terms
(bouncing, shallowness, no locality, untestable seam).

**Proposed solution:** Plain English — what would change. No interfaces yet.

**Benefits:** In terms of locality, leverage, and how tests would improve.

**Before → After:**
- Before: caller → helperA → helperB → helperC (concept smeared across 4 files)
- After:  caller → DeepModule (one seam, one place to test)
```

- **Recommendation strength** is one of `Strong`, `Worth exploring`, `Speculative`.
- **Before → After** is a compact text sketch (arrows, indented trees, or a short
  bullet pair) — enough to show the shallowness and the deepening. No HTML, no
  diagram files, nothing written to disk.
- **ADR conflicts:** if a candidate contradicts an existing ADR, surface it *only*
  when the friction is real enough to warrant revisiting the decision, and mark it
  clearly: *"contradicts ADR-0007 — but worth reopening because…"*. Don't list
  every theoretical refactor an ADR forbids.

End with a **Top recommendation**: which candidate to tackle first, and one
sentence on why.

Do NOT propose interfaces yet. Ask the user: **"Which of these would you like
to explore?"**

### 3. Pick one → interrogate → decide

Once the user picks a candidate, run the `brief` skill's interrogation on it —
walk the design tree together: constraints, dependencies, the shape of the
deepened module, what sits behind the seam, which tests survive. To explore
alternative interfaces for the deepened module, lean on the `design` skill.

Side effects happen inline as decisions crystallize:

- **Naming a deepened module after a concept not in the glossary?** Add the term
  to the domain notes in `.handoff/context/`. Sharpened a fuzzy term mid-
  conversation? Update it right there.
- **User rejects the candidate with a load-bearing reason?** Offer to record it —
  in `.handoff/context/LEARNINGS.md` as a `pitfall` entry ("rejected: X
  because Y") or as an ADR in `docs/adr/` — framed as:
  *"Want me to record this so future architecture scans don't re-suggest it?"*
  Only offer when a future explorer would actually need the reason; skip
  ephemeral ones ("not worth it right now") and self-evident ones.
- **Candidate accepted?** The decision goes to the `plan` skill for an
  implementation plan at the appropriate tier. This skill's job ends at the
  decision.

---

*Adapted from mattpocock-skills (MIT, © 2026 Matt Pocock); see ATTRIBUTION.md.*
