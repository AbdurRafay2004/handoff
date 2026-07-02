# Root Cause Tracing

Bugs often manifest deep in the call stack (git init in wrong directory, file
created in wrong location, database opened with wrong path). Your instinct is to
fix where the error appears, but that's treating a symptom.

**Core principle:** Trace backward through the call chain until you find the
original trigger, then fix at the source.

**Use when:** the error happens deep in execution (not at the entry point), the
stack trace shows a long call chain, it's unclear where invalid data originated,
or you need to find which test/code triggers the problem.

## The Tracing Process

### 1. Observe the symptom
```
Error: git init failed in ~/project/packages/core
```

### 2. Find the immediate cause
```typescript
await execFileAsync('git', ['init'], { cwd: projectDir });
```

### 3. Ask: what called this?
```typescript
WorktreeManager.createSessionWorktree(projectDir, sessionId)
  → called by Session.initializeWorkspace()
  → called by Session.create()
  → called by test at Project.create()
```

### 4. Keep tracing up — what value was passed?
- `projectDir = ''` (empty string!)
- Empty string as `cwd` resolves to `process.cwd()` — the source directory!

### 5. Find the original trigger
```typescript
const context = setupCoreTest(); // Returns { tempDir: '' }
Project.create('name', context.tempDir); // Accessed before beforeEach!
```

## Adding stack traces

When you can't trace manually, add instrumentation:

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  console.error('DEBUG git init:', {
    directory,
    cwd: process.cwd(),
    nodeEnv: process.env.NODE_ENV,
    stack,
  });
  await execFileAsync('git', ['init'], { cwd: directory });
}
```

**Critical:** use `console.error()` in tests (a logger may be suppressed).
Log BEFORE the dangerous operation, not after it fails. Include context:
directory, cwd, environment variables, timestamps. `new Error().stack` shows
the complete call chain.

Run and capture:
```bash
npm test 2>&1 | grep 'DEBUG git init'
```

Analyze the traces: look for test file names and line numbers, and identify the
pattern (same test? same parameter?).

## Finding which test causes pollution

If something appears during tests and you don't know which test: bisect. Run
the suite one test file at a time (script the loop), checking for the polluting
artifact after each, and stop at the first polluter.

## Real example: empty projectDir

**Symptom:** `.git` created in `packages/core/` (source code).

**Trace chain:** `git init` ran in `process.cwd()` ← empty cwd ← WorktreeManager
got empty projectDir ← Session.create() passed empty string ← test accessed
`context.tempDir` before beforeEach ← setup returns `{ tempDir: '' }` initially.

**Root cause:** top-level variable initialization accessing an empty value.
**Fix:** made tempDir a getter that throws if accessed before beforeEach.
**Also added defense-in-depth** (see `defense-in-depth.md`): validation at
entry, business-logic, environment-guard, and instrumentation layers.

**NEVER fix just where the error appears.** Trace back to the original trigger.

*Adapted from superpowers (MIT, © 2025 Jesse Vincent); see ATTRIBUTION.md.*
