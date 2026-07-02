# T3 Launch Runbook

For money/auth/user-data/migration changes and public go-lives. Read top to
bottom; each step ends with evidence the user (a non-coding PM) can judge.
Scale honestly — a solo launch skips the roles table, never the rollback
criteria or the verification windows.

## 1. Rollback criteria — write these FIRST

Before any deploy command runs, write into the plan (or PR body):

**Automatic rollback triggers** (no debate — trigger fires, you roll back):
- Error rate above N× normal, sustained past the smoke-check debounce
- A named critical flow (checkout, signup, login — name it) is broken
- Any data-integrity issue (wrong writes, missing rows, failed migration)
- A security hole discovered post-deploy

**Discretionary triggers** (flag to the user, they decide):
- Load time or Core Web Vitals degraded beyond ~2× baseline
- Customer-facing error patterns without a clear cause

**Rollback procedure, written and tested:** the exact commands —
`git revert <merge-sha>` (or revert PR), plus the platform rollback
(`wrangler rollback` / `vercel rollback` / re-deploy previous). For Convex or
Supabase schema changes: a down migration or backup/restore path, because
reverting code does not revert schema. **Test the procedure on staging/preview
before launch.** Untested rollback is hope, not procedure.

## 2. Pre-launch checklist

- [ ] Verify phase complete: tests green on the merged state, `verify-done` passed
- [ ] Built-in `/security-review` on the diff; the `security` skill for a full pre-launch audit (T3 launches) (auth, secrets, injection, RLS/authz)
- [ ] Accessibility pass on changed UI (keyboard, contrast, labels)
- [ ] Migration files reviewed line by line; down path exists
- [ ] Backup/export of current production state (DB dump, previous deployment ID)
- [ ] Rollback criteria (§1) written and the procedure tested
- [ ] Baseline captured: prod URL status, console error count, load time, key metric
- [ ] DNS cutover only: TTL lowered to 300s, 48–72h before the window
- [ ] Launch window sane: not Friday evening, not before a holiday, user reachable

Gate: show the checklist to the user with each box ticked. They call go/no-go.

## 3. Cutover sequence

Verify each step before starting the next — errors propagate.

1. Announce start to the user; note the timestamp
2. Run database/schema migrations first (`npx convex deploy`,
   `supabase db push`) — backward-compatible with the OLD frontend still live
3. Verify migrations: query the schema, hit one function/endpoint
4. Deploy backend/worker — **staged**: `wrangler versions upload` then
   `wrangler versions deploy` at a small percentage; or Vercel preview deploy
5. Smoke-check the staged slice (SKILL.md policy: delta vs baseline,
   2-check debounce)
6. Ramp to 100% (`wrangler versions deploy` full / `vercel deploy --prod` or
   promote) only after the staged slice is clean
7. DNS cutover if applicable: change records, then verify propagation
   (`dig +short <domain>` from a public resolver) before proceeding
8. Full smoke check on the final production URL
9. Report to the user: live URL, screenshot, timing of each step

## 4. Verification — T+0 to T+24h

**First hour:**
- Critical user flows exercised end-to-end on production (the named flows from §1)
- No error-rate spike (platform logs: `wrangler tail`, Vercel logs,
  Convex dashboard, Supabase logs/advisors)
- Load time within ~1.5× baseline
- Analytics/tracking events firing, emails/notifications sending (if in scope)

**T+24h check — part of the ship, schedule it explicitly:**
- No accumulating error patterns in platform logs
- Core Web Vitals stable vs baseline
- Key business metric (from the brief) not regressed
- Report to the user: "T+24h: errors X, load Y, metric Z vs baseline B"

## 5. Measure against the brief

The brief said this change would move something. After the launch settles
(days–weeks, not hours), check:

1. **Adoption** — are the intended users reaching it?
2. **Outcome** — did the metric the brief named actually move?
3. **Side effects** — did anything move that shouldn't have?

Don't declare success on the launch-day spike; judge the stable trend. If the
metric didn't move, the diagnosis is usually reach (nobody was told) or
usability — not "the feature failed." Feed the answer into the Learn phase
(STATUS/CHANGELOG update).

## 6. If it goes wrong

Match the finding to the §1 triggers. Automatic trigger → execute the tested
rollback immediately, verify the old version is healthy, then investigate.
Discretionary → present evidence (error text, screenshot, metric) and the
rollback option to the user; they decide. After any rollback: the merge revert
lands on the base branch, the feature branch survives for the fix, and the
incident's one-line lesson goes into the Learn phase.

---

*Adapted from gstack (MIT, © Garry Tan) and rampstack-skills (MIT, © 2026 RampStack Co.); see ATTRIBUTION.md.*
