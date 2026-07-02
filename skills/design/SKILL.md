---
name: design
description: Use when designing or improving a module's interface, deciding where a seam goes, making code more testable or navigable, or pinning down domain terminology. Provides the deep-module vocabulary other skills lean on.
---

# Design

Part of the **Plan/Build** phases — see the `workflow` skill for tiers and sequencing.

Design **deep modules**: a lot of behaviour behind a small interface, placed at
a clean seam, testable through that interface. The aim is leverage for callers,
locality for maintainers, and testability for everyone. Mostly T2/T3 territory.

## Glossary

Use these terms exactly — consistent language is the whole point.

**Module** — anything with an interface and an implementation. Deliberately
scale-agnostic: a function, class, package, or tier-spanning slice.
*Avoid*: unit, component, service.

**Interface** — everything a caller must know to use the module correctly:
the type signature, but also invariants, ordering constraints, error modes,
required configuration, performance characteristics. *Avoid*: API, signature
(too narrow — type-level surface only).

**Implementation** — what's inside a module. Distinct from **Adapter**: a
thing can be a small adapter with a large implementation (a Postgres repo) or
a large adapter with a small implementation (an in-memory fake).

**Depth** — leverage at the interface: how much behaviour a caller (or test)
can exercise per unit of interface they must learn. **Deep** = lots of
behaviour behind a small interface; **shallow** = interface nearly as complex
as the implementation.

**Seam** *(Michael Feathers)* — a place where you can alter behaviour without
editing in that place; where a module's interface lives. Where to put the seam
is its own design decision, distinct from what goes behind it.
*Avoid*: boundary (overloaded with DDD's bounded context).

**Adapter** — a concrete thing satisfying an interface at a seam. Describes
*role*, not substance.

**Leverage** — what callers get from depth: one implementation pays back
across N call sites and M tests.

**Locality** — what maintainers get from depth: change, bugs, knowledge, and
verification concentrate in one place. Fix once, fixed everywhere.

## Deep vs shallow

```
Deep (aim for this):            Shallow (avoid):
┌───────────────┐               ┌───────────────────────────────┐
│ Small interface│              │        Large interface        │
├───────────────┤               ├───────────────────────────────┤
│               │               │      Thin implementation      │
│ Deep implemen- │              └───────────────────────────────┘
│ tation        │
└───────────────┘
```

When designing an interface, ask: can I reduce the number of methods? simplify
the parameters? hide more complexity inside?

## Principles

- **Depth is a property of the interface, not the implementation.** A deep
  module can be internally composed of small, swappable parts — they just
  aren't part of the interface. Internal seams (private, used by the module's
  own tests) can coexist with the external seam.
- **The deletion test.** Imagine deleting the module. If complexity vanishes,
  it was a pass-through. If complexity reappears across N callers, it was
  earning its keep.
- **The interface is the test surface.** Callers and tests cross the same
  seam. If you want to test *past* the interface, the module is probably the
  wrong shape.
- **One adapter means a hypothetical seam; two adapters means a real one.**
  Don't introduce a seam unless something actually varies across it.
- **Design it twice.** For a non-obvious interface, sketch 2–3 radically
  different shapes before committing, and compare on depth, locality, and
  seam placement. The first design is rarely the best one.

## Designing for testability

1. **Accept dependencies, don't create them.**
   ```typescript
   // Testable
   function processOrder(order, paymentGateway) {}
   // Hard to test
   function processOrder(order) { const gateway = new StripeGateway(); }
   ```
2. **Return results, don't produce side effects.**
   ```typescript
   // Testable
   function calculateDiscount(cart): Discount {}
   // Hard to test
   function applyDiscount(cart): void { cart.total -= discount; }
   ```
3. **Small surface area.** Fewer methods = fewer tests; fewer params = simpler
   setup.

## Relationships

A **Module** has exactly one **Interface**. **Depth** is measured against that
interface. A **Seam** is where the interface lives; an **Adapter** sits at a
seam and satisfies the interface. Depth produces **Leverage** for callers and
**Locality** for maintainers.

## Rejected framings

- **Depth as implementation-lines ÷ interface-lines**: rewards padding.
  Use depth-as-leverage.
- **"Interface" = the TypeScript `interface` keyword / public methods**: too
  narrow — interface includes every fact a caller must know.
- **"Boundary"**: say **seam** or **interface**.

## UI component checklist

A component isn't designed until, per component, you've named its **states**
(default, hover, focus, active, disabled, loading, error, empty — each needs
visual *and* a11y treatment), its **variants** as a managed enum set (not
boolean-prop explosions), its **props API** (minimal required props; children
over content-props; composition over configuration), and its **a11y** path
(semantic elements, keyboard navigable, visible focus, ARIA only where HTML
falls short).

## Going deeper

When the work involves pinning down domain terminology, recording an
architectural decision, or stress-testing concept boundaries, see
`references/domain-modeling.md`.

To deepen a cluster of shallow modules safely, see `references/deepening.md`.

*Adapted from mattpocock-skills (MIT, © 2026 Matt Pocock) and rampstack-skills (MIT, © 2026 RampStack Co.); see ATTRIBUTION.md.*
