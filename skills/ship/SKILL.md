---
name: ship
description: Use when work is verified and ready to leave the machine — branch/PR/merge/deploy/smoke-check. Triggers on "ship it", "deploy", "merge the PR", "push this", "release", "go live", "cutover". Covers git hygiene, PR and merge discipline, deploy-target detection (Cloudflare Workers/Pages via wrangler, Vercel, Convex, Supabase), post-deploy smoke checks, and the T3 launch runbook with rollback criteria.
---

# Ship

Part of the **Ship** phase — see the `workflow` skill for tiers and sequencing.

Shipping is the phase where mistakes become public and expensive. The rule that
governs everything below: **every ship step ends with evidence a non-coding PM
can judge** — a PR URL, green CI, a deploy URL, smoke-check output, a
screenshot. Never "deployed, should be fine." Show the thing.

## Tier scaling

| Tier | Ship process | Evidence at the end |
|---|---|---|
| **T1** | branch → commit → PR → merge. Deploy only if the change is user-visible or the user asks. | PR URL + green CI |
| **T2** | T1 + deploy + single-pass smoke check on the live URL. | Deploy URL + smoke output |
| **T3** (money/auth/data/migrations) | Full runbook: **rollback criteria written BEFORE deploying**, staged rollout, post-deploy monitoring, T+24h check. See [references/launch-runbook.md](references/launch-runbook.md). | Runbook with each gate checked + live evidence |

Never enter Ship without a passing Verify phase (`verify-done`). Shipping does
not re-litigate verification — but it does re-run it when code changes (below).

## Git hygiene

- **Never `git add -A` or `git add .`.** Stage only the files you changed for
  this task, by explicit path. Unrelated dirt in the working tree stays out of
  your commit — it belongs to another change or to nobody.
- **Bisectable commits.** Group the diff into logical units, one coherent change
  per commit (not one file per commit). Order so dependencies land first:
  1. Infrastructure: config, migrations, route/schema additions
  2. Data layer and services (with their tests)
  3. UI: components, pages, styles (with their tests)
  4. Docs/changelog last
  A module and its test file travel in the same commit. Each commit must be
  independently valid — no broken imports, no references to code that doesn't
  exist yet. Small diffs (<50 lines across <4 files) can be a single commit.
- **Every commit revertible.** `git revert <sha>` on any single commit should
  cleanly undo one logical change. If a schema change and dependent code can't
  be reverted independently, note that in the commit body — it changes the
  rollback plan.
- **Never force push.** Never rewrite pushed history. Plain `git push` only.
  Sole exception: scrubbing a leaked secret from history (see `security`), with
  the user's explicit approval — rotate the secret first.

## PR / merge discipline

**Merge the base branch BEFORE the final test run.** Tests must run against the
merged state, not your stale branch:

```sh
git fetch origin <base> && git merge origin/<base> --no-edit
```

Auto-resolve only trivial conflicts (lockfiles, changelog ordering). Anything
ambiguous: stop and use the `resolving-merge-conflicts` skill (installed
separately) — never guess a conflict resolution.

**Verification gate — no completion claims without fresh verification evidence.**
If ANY code changed after the last test run (review fixes, conflict resolution),
re-run the tests and paste fresh output. "Should work now" → run it. "I'm
confident" → confidence is not evidence. "I tested earlier" → code changed since
then. Stale output is not acceptable; trivial changes break production too.

**Readiness gate (before merge):**
- Failing tests or failing CI → **blocker**. Never merge red.
- Merge conflicts (`gh pr view --json mergeable`) → blocker until resolved.
- Stale durable state → **warning, not blocker**: if the diff adds features but
  `.agent-orch/STATUS.md` / `CHANGELOG.md` weren't touched, flag it and offer to
  update before merging.
- PR body accuracy: compare the body against `git log <base>..HEAD --oneline`.
  A PR body describing last week's version of the change is a warning — fix it,
  the PM reads the PR body, not the diff.

**Post-fail invariant — after ANY non-zero exit from `gh pr merge`, query PR
state before doing anything else. Never blind-retry the merge:**

```sh
gh pr view --json state,mergeCommit,autoMergeRequest,mergedAt
```

- `state == MERGED` → the server-side merge actually succeeded (or a concurrent
  merge landed). Say "PR is merged on GitHub", capture the merge SHA, move on.
- `state == OPEN` and `autoMergeRequest` non-null → merge queue / auto-merge is
  processing. Expected — poll `gh pr view --json state` (30s interval), don't
  re-merge.
- `state == OPEN` and `autoMergeRequest` null → genuine failure. Surface the
  merge stderr AND the current PR state, then stop for the user.
- `state == CLOSED` → closed without merging. Stop.

Hard rule: never call `gh pr merge` a second time after a failure. Server state
is authoritative; a blind retry can double-merge or mask what happened.

## Deploy-target detection

Detect the target from config files in the repo root. **Order matters: data
layer deploys before the frontend that depends on it.**

```sh
ls convex 2>/dev/null && echo "TARGET:convex"
ls supabase/migrations 2>/dev/null && echo "TARGET:supabase-migrations"
ls wrangler.jsonc wrangler.toml 2>/dev/null && echo "TARGET:cloudflare"
(ls vercel.json 2>/dev/null || ls -d .vercel 2>/dev/null) && echo "TARGET:vercel"
```

**Convex (`convex/` dir)** — deploy BEFORE the frontend deploy:
`npx convex deploy`. Schema and function changes must be live before the
frontend that calls them. A Convex schema change is a migration → **this is T3**
(reverting frontend code does not revert the schema; plan the down path first).

**Supabase (`supabase/migrations/`)** — review every pending migration file
before pushing, then `supabase db push` (or apply via the Supabase MCP tools).
Database migrations are **always T3**: irreversible-by-default, so the rollback
plan (down migration or backup/restore) is written before pushing.

**Cloudflare Workers/Pages (`wrangler.jsonc` / `wrangler.toml`)** —
`wrangler deploy` (Workers) or `wrangler pages deploy` (Pages). For a T3 gradual
rollout on Workers: `wrangler versions upload` then
`wrangler versions deploy` to split traffic by percentage between old and new.
Rollback: `wrangler rollback` (Workers) or re-deploy the previous version.

**Vercel (`vercel.json` / `.vercel/`)** — two modes; check which this repo uses:
- Git-push-triggered: merging to the production branch deploys. Grab the
  preview/production URL from the PR checks — that URL is the evidence.
- CLI: `vercel deploy` for a preview, `vercel deploy --prod` to promote.
  Prefer verifying the preview URL before promoting.
- Rollback: `vercel rollback` or promote the previous deployment in the
  dashboard.

**First deploy of a repo = dry run first.** Detect the target, echo the exact
commands, account/project, and environment you're about to hit, and confirm with
the user before running anything. Then record the confirmed setup (platform,
commands, prod URL, staging URL if any) in `.agent-orch/context/DEPLOY.md` (or
the repo's CLAUDE.md if no `.agent-orch/`) — and fingerprint it: on later ships,
if the deploy config files or CI deploy workflows changed since that record,
re-confirm instead of assuming the old understanding still holds.

**No target detected?** Ask. Never guess a deploy command against production.

## Smoke-check policy (post-deploy)

Single pass — this is a check, not a monitoring daemon. Scale to what changed:

| What changed | Check |
|---|---|
| Config only | `curl -sf <url> -o /dev/null -w "%{http_code}"` — expect 200 |
| Backend | curl key endpoints + check response bodies; browser console errors |
| Frontend (any) | Load the page (Playwright/browser tool): console errors, real content rendered (not blank/error page), screenshot |

**Policy (this is the load-bearing part):**
- **Delta vs baseline, not absolutes.** Compare against pre-deploy state. A page
  that had 3 console errors before the deploy and has 3 after is not a finding.
  One NEW error is. When practical, capture the baseline (status, console error
  count, load time) before deploying.
- **Debounce: 2 consecutive checks before acting.** A single failed check
  30–60s after deploy may be cache/CDN propagation. Re-check once before
  declaring a problem. A finding that persists across 2 consecutive checks is
  real.
- **Severity → action:**
  - **CRITICAL** — site down, 5xx on the main page, deploy unreachable → roll
    back now, investigate after.
  - **HIGH** — new console errors, a core flow broken → investigate
    immediately; roll back if not resolved quickly.
  - **MEDIUM** — load time >2x baseline → flag it, fix forward.
  - **LOW** — new 404 on a non-critical link → note in the report, fix forward.
- **Evidence, always:** the deploy URL plus the actual curl output / error text
  / screenshot path. The PM judges "here's the live URL and here's what I saw",
  not "smoke check passed."

**Revert is always an escape hatch.** At every failure point, name it as an
option: `git revert <merge-sha>` (a revert PR if the base branch is protected)
plus the platform rollback command from the detection section. Say what the
revert does in plain language. Remember: reverting code never reverts a Convex
or Supabase schema change — that's the reason migrations are T3.

## Launch runbook (T3)

For money/auth/data/migrations or a public go-live, the full procedure lives in
[references/launch-runbook.md](references/launch-runbook.md). The
non-negotiables:

- **Rollback criteria are written BEFORE deploying** — automatic triggers
  (error rate, broken critical flow, data integrity) and who decides. Decisions
  made calmly in advance, not debated during an incident.
- **Test the rollback procedure before you need it.** An untested rollback is
  hope, not a procedure.
- Pre-launch checklist includes a `security` skill review and an accessibility
  pass on changed UI.
- Staged rollout by default (gradual Worker versions, preview-then-promote on
  Vercel, feature flag if one exists) — not big-bang.
- DNS cutover (if any): lower TTL 48–72h ahead; verify propagation before
  declaring done.
- **T+24h check is part of the ship**, not an optional follow-up. The task isn't
  done at deploy time.
- Measure against the brief: did the thing the change was supposed to improve
  actually improve? Don't declare victory on the launch-day spike.

## Repo onboarding (one-time per new client repo)

The first time you ship from a repo that has no pre-commit hooks or git
guardrails, run the `setup-pre-commit` skill (format/typecheck/test on commit)
and the `git-guardrails-claude-code` skill (blocks destructive git commands)
once (user-installed skills — skip if unavailable). Every later ship in that
repo inherits the safety net.

---

*Adapted from gstack (MIT, © Garry Tan) and rampstack-skills (MIT, © 2026 RampStack Co.); see ATTRIBUTION.md.*
