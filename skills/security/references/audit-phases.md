# Audit Phases 2-11 (scope-dependent)

**Scope gate (read first).** Run ONLY the phases the resolved scope in
SKILL.md selected (0, 1, 12, 13 always run) — not a phase the scope didn't
pick just because its prose lives here. Bash blocks show WHAT to search for;
use the Grep tool.

### Phase 2: Secrets Archaeology

Scan **git history — known secret prefixes** (AKIA, `sk-ant-`, `sk_live_`, ghp_ /
gho_ / github_pat_, xoxb-/xoxp-/xapp-, `-----BEGIN ... PRIVATE KEY-----`,
Supabase `service_role` JWTs, generic password/secret/token/api_key):
```bash
git log -p --all -G "AKIA|ghp_|gho_|github_pat_|xoxb-|sk_live_|sk-ant-"
git log -p --all -G "password|secret|token|api_key" -- "*.env" "*.yml" "*.json" "*.conf"
```

**.env files tracked by git** (`git ls-files '*.env' '.env.*'`, excluding
`.example/.sample/.template`); confirm `.env` is gitignored. Also check
committed `wrangler.toml` `[vars]` and `vercel.json` for real secrets —
Cloudflare secrets belong in `wrangler secret`, Vercel's in project env
settings. **CI configs with inline secrets:** grep workflow files for
`password:|token:|secret:|api_key:` values not using `${{ secrets.* }}`.

**Severity:** CRITICAL — active secret patterns in git history. HIGH — .env
tracked by git; CI configs with inline credentials. MEDIUM — suspicious
`.env.example` values. **FP rules:** placeholders ("your_", "changeme",
"TODO") and test fixtures excluded (unless the same value appears in non-test
code). Rotated secrets still flagged — they were exposed. `.env.local`
gitignored is expected. The Supabase anon key is designed to be public — NOT
a finding (RLS protects the data; see Phase 9 A01). **Diff mode:** replace
`git log -p --all` with `git log -p <base>..HEAD`.

### Phase 3: Dependency Supply Chain

Goes beyond `npm audit` — actual supply-chain risk. Detect the package
manager; run whichever audit tool is available (`npm audit`, `pip-audit`,
`cargo audit`, ...). Note a missing tool as "SKIPPED — tool not installed"
(informational, not a finding) and continue with what IS available.

**Install scripts in production deps** (attack vector): for Node projects with
hydrated `node_modules`, check prod dependencies for `preinstall` /
`postinstall` / `install` scripts. **Lockfile integrity:** lockfiles exist AND
are tracked by git.

**Severity:** CRITICAL — known high/critical CVEs in direct deps. HIGH —
install scripts in prod deps; missing lockfile. MEDIUM — abandoned packages;
medium CVEs; lockfile untracked. **FP rules:** devDependency CVEs are MEDIUM
max. `node-gyp`/`cmake` install scripts are expected (MEDIUM not HIGH).
No-fix advisories without known exploits excluded. Missing lockfile in
library repos (not apps) is NOT a finding.

### Phase 4: CI/CD Pipeline Security

Check who can modify workflows and what secrets they can reach. For each
workflow file:
- Unpinned third-party actions (`uses:` without a SHA pin)
- `pull_request_target` (fork PRs get write access)
- Script injection via `${{ github.event.* }}` interpolated into `run:` steps
- Secrets exported as env vars (can leak in logs)
- CODEOWNERS protection on workflow files
- Deploy workflows (`wrangler`/`vercel deploy`): secrets held, triggers

**Severity:** CRITICAL — `pull_request_target` + checkout of PR code; script
injection via `${{ github.event.*.body }}` in `run:`. HIGH — unpinned
third-party actions; secrets as env vars without masking. MEDIUM — missing
CODEOWNERS. **FP rules:** first-party `actions/*` unpinned = MEDIUM not HIGH.
`pull_request_target` without PR-ref checkout is safe (precedent #11).
Secrets in `with:` blocks (not `env:`/`run:`) are handled by the runtime.

### Phase 5: Infrastructure Shadow Surface

Find shadow infrastructure with excessive access. **Dockerfiles:** missing
`USER` directive (runs as root), secrets passed as `ARG`, `.env` copied into
images, undocumented exposed ports.

**Config files with prod credentials:** grep configs for connection strings
(`postgres://`, `mysql://`, `mongodb://`, `redis://`) excluding
localhost/127.0.0.1/example.com; staging/dev configs referencing prod;
Cloudflare Worker bindings / Convex deploy configs wiring prod resources into
non-prod environments. **IaC:** Terraform `"*"` in IAM actions/resources,
hardcoded secrets in `.tf`/`.tfvars`; K8s privileged, hostNetwork, hostPID.

**Severity:** CRITICAL — prod DB URLs with credentials committed; `"*"` IAM on
sensitive resources; secrets baked into images. HIGH — root containers in
prod; staging with prod DB access; privileged K8s. MEDIUM — missing USER
directive; undocumented exposed ports. **FP rules:** local-dev
`docker-compose.yml` with localhost = not a finding (precedent #12).
Terraform `"*"` in read-only `data` sources excluded. K8s manifests under
`test/`/`dev/`/`local/` with localhost networking excluded.

### Phase 6: Webhook & Integration Audit

Find inbound endpoints that accept anything. **Webhook routes:** find
webhook/hook/callback route files; check each for signature verification
(signature, hmac, verify, digest, x-hub-signature, stripe-signature, svix).
Routes with NO verification are findings. Convex `httpAction` endpoints and
Next.js route handlers receiving third-party webhooks need the same check.

**TLS verification disabled:** `verify.*false`, `VERIFY_NONE`,
`InsecureSkipVerify`, `NODE_TLS_REJECT_UNAUTHORIZED.*0`. **OAuth scopes:**
find OAuth configs; flag overly broad scopes.

**Verification (code-tracing only):** trace the handler to see if signature
verification exists anywhere in the middleware chain (parent router,
middleware stack, API gateway). Never send live HTTP requests.

**Severity:** CRITICAL — webhooks without any signature verification. HIGH —
TLS verification disabled in prod code; overly broad OAuth scopes. MEDIUM —
undocumented outbound data flows to third parties. **FP rules:** TLS disabled
in test code excluded. Internal service-to-service webhooks on private
networks = MEDIUM max. Endpoints behind a gateway that verifies signatures
upstream are NOT findings — but require quoted evidence.

### Phase 7: LLM & AI Security

Grep for: user input flowing into system prompts or tool schemas (string
interpolation near system-prompt construction); unsanitized LLM output
rendered via `dangerouslySetInnerHTML`/`v-html`/`innerHTML`/`.html()`/`raw()`;
tool calling without validation (`tool_choice`, `tools=`, `functions=`);
hardcoded AI API keys (`sk-`); `eval`/`exec`/`new Function` on LLM output.

**Beyond grep:** trace user-content flow into prompts/tool schemas; RAG
poisoning (can retrieved documents steer behavior?); are LLM tool calls
validated before execution?; is LLM output treated as trusted?; can a user
trigger unbounded LLM calls (cost attack — financial risk, not DoS)?

**Severity:** CRITICAL — user input in system prompts; unsanitized LLM output
as HTML; eval of LLM output. HIGH — missing tool-call validation; exposed AI
API keys. MEDIUM — unbounded LLM calls; RAG without input validation.
**FP rules:** user content in the user-message position is NOT prompt
injection (precedent #13) — only flag when it enters system prompts, tool
schemas, or function-calling contexts.

### Phase 8: Skill Supply Chain

Scan installed agent skills/hooks for malicious patterns — published skills
have a documented rate of security flaws and outright malice (Snyk
ToxicSkills research). **Tier 1 — repo-local (automatic):** scan
`.claude/skills/`, hooks config, and plugin dirs for network exfiltration
(`curl`, `wget`, `fetch`, http URLs near data reads); credential access
(`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `process.env` harvesting); prompt
injection ("IGNORE PREVIOUS", "system override", "disregard", "forget your
instructions"). **Tier 2 — global (ask first):** scanning `~/.claude/`
skills, hooks, and user settings reads files outside the repo — ask the user
before including it.

**Severity:** CRITICAL — credential exfiltration; prompt injection in skill
files. HIGH — suspicious network calls; overly broad tool permissions.
MEDIUM — skills from unverified sources without review. **FP rules:** skills
this repo itself ships and has reviewed are trusted (exclusion #22).
Legitimate `curl` (tool downloads, health checks) needs context — flag only
when the URL is suspicious or credentials ride along. SKILL.md files are
executable prompt code, never "just docs" (exclusion #15).

### Phase 9: OWASP Top 10 Assessment

Targeted analysis per category; scope greps to detected stacks.

- **A01 Broken Access Control:** missing auth on routes; direct object
  references (can user A read user B's rows by changing an ID?);
  horizontal/vertical privilege escalation. *Supabase:* RLS is the authz
  surface — enumerate tables, confirm RLS enabled with correct policies,
  `service_role` server-side only. *Convex:* every exported function is
  public — confirm `ctx.auth` checks.
- **A02 Cryptographic Failures:** weak crypto (MD5, SHA1, DES, ECB); secrets
  hardcoded vs env-managed; sensitive data encrypted at rest/in transit.
- **A03 Injection:** SQL via string interpolation; command injection
  (`system`, `exec`, `spawn`, `popen`); template injection (`eval`,
  `html_safe`, `raw()`); LLM prompt injection → Phase 7.
- **A04 Insecure Design:** rate limits on auth endpoints; account lockout;
  business logic validated server-side.
- **A05 Security Misconfiguration:** CORS wildcards in prod; CSP headers;
  debug mode / verbose errors in production.
- **A06 Vulnerable Components:** → Phase 3.
- **A07 Auth Failures:** session creation/storage/invalidation; password
  policy; MFA for admin; JWT expiration and refresh rotation.
- **A08 Integrity Failures:** → Phase 4 for pipelines; deserialization inputs
  validated; integrity checks on external data.
- **A09 Logging/Monitoring Failures:** auth events, authz failures, and admin
  actions logged; logs tamper-protected. (Absence alone is not a finding —
  exclusion #16; report as posture notes.)
- **A10 SSRF:** URL construction from user input; internal reachability from
  user-controlled URLs; outbound allowlists.

### Phase 10: STRIDE Threat Model

For each major component from Phase 0: **S**poofing (impersonate a
user/service?), **T**ampering (modify data in transit/at rest?),
**R**epudiation (audit trail?), **I**nformation disclosure (data leaks?),
**D**enial of service (per exclusion #1), **E**levation of privilege.

### Phase 11: Data Classification

Classify all data handled: **RESTRICTED** (breach = legal liability:
credentials, payment data, PII — where stored, how protected, retention);
**CONFIDENTIAL** (breach = business damage: API keys, trade secrets, behavior
data); **INTERNAL** (logs, config in errors); **PUBLIC** (marketing, docs).

*Adapted from gstack (MIT, © Garry Tan); see ATTRIBUTION.md.*
