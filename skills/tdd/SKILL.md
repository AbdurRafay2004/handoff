---
name: tdd
description: Use when building any T3 feature or bugfix, recommended for T2 on the affected path — write the failing test before the implementation, one behavior at a time, through public interfaces.
---

# TDD

Part of the **Build** phase — see the `workflow` skill for tiers and sequencing.

**Tier rule:** mandatory for T3 (money, auth, user data, migrations);
recommended for T2 on the affected path; skipped for T1 (copy/styling). Within
its tier, the discipline is absolute: **no production code without a failing
test first.** Bug fixes always get a failing test reproducing the bug, at any
tier — a fix without a test doesn't stick.

## Philosophy

Tests verify **behavior through public interfaces**, not implementation
details. Code can change entirely; tests shouldn't.

**Good tests** are integration-style: they exercise real code paths through
public APIs and read like a specification — "user can checkout with valid
cart" tells you exactly what capability exists. They survive refactors because
they don't care about internal structure.

**Bad tests** are coupled to implementation: they mock internal collaborators,
test private methods, or verify through side channels (querying the database
directly instead of using the interface). The warning sign: the test breaks
when you refactor but behavior hasn't changed.

**Core proof:** if you didn't watch the test fail, you don't know it tests the
right thing. A test written after the code passes immediately — and passing
immediately proves nothing.

## Anti-pattern: horizontal slices

**Do not write all tests first, then all implementation.** Bulk-written tests
test *imagined* behavior — the shape of data structures rather than
user-facing behavior — and become insensitive to real changes.

```
WRONG (horizontal):  RED: test1..test5  →  GREEN: impl1..impl5
RIGHT (vertical):    test1→impl1, test2→impl2, test3→impl3 ...
```

Vertical slices via **tracer bullets**: one test → one implementation →
repeat. Each test responds to what the previous cycle taught you.

## Workflow

### 1. Plan the behaviors

Read the nearest `CONTEXT.md` / `.agent-orch/context/` so test names match the
project's domain language. Then, before any code:

- Confirm with the user what interface changes are needed.
- Confirm which behaviors to test — **you can't test everything**; focus on
  critical paths and complex logic, not every edge case. (This is the PM
  decision: which failures are expensive?)
- Look for deep-module opportunities — small interface, deep implementation
  (see `design`).
- List behaviors, not implementation steps.

### 2. Tracer bullet

Write ONE test confirming ONE thing about the system. Watch it fail. Write
minimal code to pass. This proves the path works end-to-end.

### 3. Incremental loop

For each remaining behavior: RED → verify it fails for the right reason →
GREEN → verify it passes → next.

- One test at a time; only enough code to pass the current test.
- Don't anticipate future tests; no speculative features.
- **Verify RED is mandatory.** If the new test passes immediately, it's
  testing existing behavior — fix the test. If it errors (rather than fails),
  fix the error until it fails correctly.
- **Verify GREEN completely:** the new test passes, all other tests still
  pass, output pristine. Test fails → fix the code, not the test.

### 4. Refactor (only on green)

Extract duplication, improve names, deepen modules (move complexity behind
simple interfaces). Run tests after each refactor step. **Never refactor while
RED.** Don't add behavior.

## Good vs bad tests

```typescript
// ✅ Clear name, real behavior, one thing
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };
  const result = await retryOperation(operation);
  expect(result).toBe('success');
  expect(attempts).toBe(3);
});

// ❌ Vague name, tests the mock, not the code
test('retry works', async () => {
  const mock = jest.fn()
    .mockRejectedValueOnce(new Error())
    .mockResolvedValueOnce('success');
  await retryOperation(mock);
  expect(mock).toHaveBeenCalledTimes(2);
});
```

- One behavior per test; "and" in the name means split it.
- Real code over mocks — mock only what's unavoidable (network, clock, true
  externals). If you must mock everything, the code is too coupled: inject
  dependencies instead. Boundary rules and mock-friendly interface design:
  `references/mocking.md`.
- Testing mock behavior instead of real behavior is the classic false
  positive: the suite goes green while the product is broken.

## Per-cycle checklist

```
[ ] Test describes behavior, not implementation
[ ] Test uses the public interface only
[ ] Test would survive an internal refactor
[ ] Watched it fail, for the expected reason
[ ] Minimal code to pass; nothing speculative
[ ] All tests green, output pristine
```

## Common rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. The test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost. Keeping unverified code is debt. |
| "Test is hard to write" | Listen to it: hard to test = hard to use. Simplify the interface. |
| "TDD will slow me down" | Test-first is faster than debugging after. |

## When stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test it | Write the wished-for API; write the assertion first. |
| Test too complicated | The design is too complicated. Simplify the interface. |
| Must mock everything | Code too coupled — inject dependencies. |
| Test setup huge | Extract helpers; still complex → simplify the design. |

*Adapted from mattpocock-skills (MIT, © 2026 Matt Pocock) and superpowers (MIT, © 2025 Jesse Vincent); see ATTRIBUTION.md.*
