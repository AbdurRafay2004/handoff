# Mocking

Mock at **system boundaries** only:

- External APIs (payment, email — third parties you don't control)
- Time and randomness
- Databases and filesystem — sometimes; prefer a test DB or local stand-in

Never mock your own classes, internal collaborators, or anything you control —
refactor it to be testable instead.

## Design boundaries for mockability

**1. Inject dependencies.** Pass external dependencies in rather than
creating them internally:

```typescript
// Easy to mock
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to mock — constructs its own boundary
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**2. Prefer SDK-style interfaces over generic fetchers.** One specific
function per external operation, not one generic function with conditionals:

```typescript
// GOOD: each function independently mockable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: mocking requires conditional logic inside the mock
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

Why the SDK shape wins: each mock returns one specific shape, test setup has
no conditionals, endpoint usage per test is obvious, types come per endpoint.

## Verify through the interface

Even with a real DB in the test, assert through the interface, not around it:

```typescript
// BAD: bypasses the interface to verify
test('createUser saves to database', async () => {
  await createUser({ name: 'Alice' });
  const row = await db.query('SELECT * FROM users WHERE name = ?', ['Alice']);
  expect(row).toBeDefined();
});

// GOOD: verifies through the interface
test('createUser makes user retrievable', async () => {
  const user = await createUser({ name: 'Alice' });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe('Alice');
});
```

*Adapted from mattpocock-skills (MIT, © 2026 Matt Pocock); see ATTRIBUTION.md.*
