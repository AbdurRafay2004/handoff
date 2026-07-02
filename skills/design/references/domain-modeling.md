# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is
the *active* discipline — challenging terms, inventing edge-case scenarios,
and writing the glossary and decisions down the moment they crystallise.
(Merely *reading* existing vocabulary is not this skill; this is for when
you're changing the model, not consuming it.)

## Where the model lives

- **Glossary:** `.agent-orch/context/DOMAIN.md` if the repo uses agent-orch
  project memory (create it when the first term is resolved); otherwise a
  root-level `CONTEXT.md`. The glossary is a glossary and nothing else —
  totally devoid of implementation details; not a spec, scratch pad, or
  decision log.
- **Architectural decisions:** `docs/adr/NNNN-<slug>.md` — create the
  directory when the first ADR is needed. Create files lazily; only when you
  have something to write.

## During the session

**Challenge against the glossary.** When the user uses a term that conflicts
with the recorded language, call it out immediately: "Your glossary defines
'cancellation' as X, but you seem to mean Y — which is it?"

**Sharpen fuzzy language.** When a term is vague or overloaded, propose a
precise canonical one: "You're saying 'account' — do you mean the Customer or
the User? Those are different things."

**Discuss concrete scenarios.** Stress-test domain relationships with specific
scenarios that probe edge cases and force precision about the boundaries
between concepts.

**Cross-reference with code.** When the user states how something works, check
whether the code agrees. Surface contradictions: "Your code cancels entire
Orders, but you just said partial cancellation is possible — which is right?"

**Update the glossary inline.** When a term is resolved, record it right
there — don't batch.

## Offer ADRs sparingly

Only offer to create an ADR when ALL three hold:

1. **Hard to reverse** — changing your mind later costs something real.
2. **Surprising without context** — a future reader would ask "why this way?"
3. **A real trade-off** — genuine alternatives existed and one was chosen for
   specific reasons.

If any is missing, skip the ADR. A minimal ADR records: context, the decision,
the alternatives considered, and the consequences accepted.

*Adapted from mattpocock-skills (MIT, © 2026 Matt Pocock); see ATTRIBUTION.md.*
