# Defense-in-Depth Validation

When you fix a bug caused by invalid data, adding validation at one place feels
sufficient. But a single check can be bypassed by different code paths,
refactoring, or mocks.

**Core principle:** Validate at EVERY layer data passes through. Make the bug
structurally impossible.

Single validation: "we fixed the bug." Multiple layers: "we made the bug
impossible." Different layers catch different cases: entry validation catches
most bugs, business logic catches edge cases, environment guards prevent
context-specific dangers, debug logging helps when other layers fail.

## The four layers

### Layer 1: Entry-point validation — reject invalid input at the API boundary
```typescript
function createProject(name: string, workingDirectory: string) {
  if (!workingDirectory || workingDirectory.trim() === '') {
    throw new Error('workingDirectory cannot be empty');
  }
  if (!existsSync(workingDirectory)) {
    throw new Error(`workingDirectory does not exist: ${workingDirectory}`);
  }
  if (!statSync(workingDirectory).isDirectory()) {
    throw new Error(`workingDirectory is not a directory: ${workingDirectory}`);
  }
}
```

### Layer 2: Business-logic validation — data makes sense for this operation
```typescript
function initializeWorkspace(projectDir: string, sessionId: string) {
  if (!projectDir) {
    throw new Error('projectDir required for workspace initialization');
  }
}
```

### Layer 3: Environment guards — prevent dangerous operations in specific contexts
```typescript
async function gitInit(directory: string) {
  if (process.env.NODE_ENV === 'test') {
    const normalized = normalize(resolve(directory));
    const tmpDir = normalize(resolve(tmpdir()));
    if (!normalized.startsWith(tmpDir)) {
      throw new Error(`Refusing git init outside temp dir during tests: ${directory}`);
    }
  }
}
```

### Layer 4: Debug instrumentation — capture context for forensics
```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  logger.debug('About to git init', { directory, cwd: process.cwd(), stack });
}
```

## Applying the pattern

When you find a bug:
1. **Trace the data flow** — where does the bad value originate? Where is it used?
2. **Map all checkpoints** — every point the data passes through.
3. **Add validation at each layer** — entry, business, environment, debug.
4. **Test each layer** — try to bypass layer 1, verify layer 2 catches it.

## Key insight

In the originating session all four layers proved necessary — different code
paths bypassed entry validation, mocks bypassed business-logic checks, platform
edge cases needed environment guards, and debug logging exposed structural
misuse. **Don't stop at one validation point.**

*Adapted from superpowers (MIT, © 2025 Jesse Vincent); see ATTRIBUTION.md.*
