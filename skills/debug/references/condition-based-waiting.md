# Condition-Based Waiting

Flaky tests often guess at timing with arbitrary delays, creating race
conditions where tests pass on fast machines but fail under load or in CI.

**Core principle:** Wait for the actual condition you care about, not a guess
about how long it takes.

**Use when:** tests have arbitrary delays (`setTimeout`, `sleep`), tests are
flaky (pass sometimes, fail under load), tests time out in parallel runs, or
you're waiting for async operations.
**Don't use when** testing actual timing behavior (debounce/throttle intervals) —
and always document WHY if an arbitrary timeout is genuinely needed.

## Core pattern

```typescript
// ❌ BEFORE: guessing at timing
await new Promise(r => setTimeout(r, 50));
const result = getResult();
expect(result).toBeDefined();

// ✅ AFTER: waiting for the condition
await waitFor(() => getResult() !== undefined);
const result = getResult();
expect(result).toBeDefined();
```

## Quick patterns

| Scenario | Pattern |
|----------|---------|
| Wait for event | `waitFor(() => events.find(e => e.type === 'DONE'))` |
| Wait for state | `waitFor(() => machine.state === 'ready')` |
| Wait for count | `waitFor(() => items.length >= 5)` |
| Wait for file | `waitFor(() => fs.existsSync(path))` |
| Complex condition | `waitFor(() => obj.ready && obj.value > 10)` |

## Implementation

```typescript
async function waitFor<T>(
  condition: () => T | undefined | null | false,
  description: string,
  timeoutMs = 5000
): Promise<T> {
  const startTime = Date.now();
  while (true) {
    const result = condition();
    if (result) return result;
    if (Date.now() - startTime > timeoutMs) {
      throw new Error(`Timeout waiting for ${description} after ${timeoutMs}ms`);
    }
    await new Promise(r => setTimeout(r, 10)); // poll every 10ms
  }
}
```

## Common mistakes

- **Polling too fast** (`setTimeout(check, 1)`) wastes CPU → poll every ~10ms.
- **No timeout** → loops forever; always include one with a clear error.
- **Stale data** — don't cache state before the loop; call the getter inside it.

## When an arbitrary timeout IS correct

```typescript
// Tool ticks every 100ms — need 2 ticks to verify partial output
await waitForEvent(manager, 'TOOL_STARTED'); // first: wait for the condition
await new Promise(r => setTimeout(r, 200));   // then: wait for timed behavior
// 200ms = 2 ticks at 100ms intervals — documented and justified
```

Requirements: first wait for the triggering condition; base the delay on known
timing (not guessing); comment explaining WHY.

*Adapted from superpowers (MIT, © 2025 Jesse Vincent); see ATTRIBUTION.md.*
