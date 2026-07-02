# Deepening

How to deepen a cluster of shallow modules safely, given its dependencies.
Uses the `design` skill's vocabulary: module, interface, seam, adapter.

## Dependency categories

Classify the candidate's dependencies first — the category determines how the
deepened module is tested across its seam.

**1. In-process** — pure computation, in-memory state, no I/O. Always
deepenable: merge the modules and test through the new interface directly.
No adapter needed.

**2. Local-substitutable** — dependencies with local test stand-ins (PGLite
for Postgres, an in-memory filesystem). Deepenable when the stand-in exists;
test with the stand-in running in the suite. The seam stays internal — no
port at the module's external interface.

**3. Remote but owned (ports & adapters)** — your own services across a
network boundary (internal APIs, microservices). Define a **port** (interface)
at the seam; the deep module owns the logic and the transport is injected as
an adapter. Tests use an in-memory adapter, production an HTTP/gRPC/queue
one — the logic sits in one deep module even though it's deployed across a
network.

**4. True external (mock)** — third-party services (Stripe, Twilio) you don't
control. The deepened module takes the dependency as an injected port; tests
provide a mock adapter.

## Internal vs external seams

A deep module can have internal seams — private to its implementation, used
only by its own tests — alongside the external seam at its interface. Don't
expose an internal seam through the interface just because tests use it; that
trades depth for test convenience.

## Testing strategy: replace, don't layer

- Once tests exist at the deepened module's interface, the old unit tests on
  the swallowed shallow modules are waste — delete them.
- Write the new tests at the deepened interface: the interface is the test
  surface. Assert on observable outcomes, not internal state.
- Tests should survive internal refactors. If a test must change when the
  implementation changes, it's testing past the interface.

*Adapted from mattpocock-skills (MIT, © 2026 Matt Pocock); see ATTRIBUTION.md.*
