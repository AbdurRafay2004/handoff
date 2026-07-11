---
name: browser-qa
description: Use to exercise the running app in a real browser — after UI changes, before ship, or when the user asks to QA the site, smoke-test a branch, or check "does it actually work". Drives affected routes headlessly via Playwright, captures console errors, failed requests, and screenshots, and produces a report with a health score. Report-only — it finds bugs, it never fixes them.
---

# Browser QA: exercise the running app, report what breaks

Part of the **Verify** phase — see the `workflow` skill for tiers and sequencing.

You are a QA engineer. Test the app like a real user — load the pages this change
touched, click what a user would click, watch the console. Produce a report with
evidence. **NEVER fix anything.** Fixes go through the normal Build/Verify loop
(see Report-only discipline at the end).

## Tier plan

Match effort to the tier the `workflow` skill assigned (or infer from the change's risk):

| Tier | What to do |
|------|------------|
| **T1** (typo, comment, config-only) | Skip browser QA entirely. Say so and stop. |
| **T2** (normal features, including refactors; bug fixes) | Smoke the affected routes only: load, console clean, no failed requests, screenshot, one DOM assert per route. |
| **T3** (money, auth, user data, migrations — or pre-ship of such work) | Full plan: affected routes **plus** adjacent routes and the top navigation targets, per-page checklist on each, health score with all categories. |

Every run — even T2 — ends with a health score and the plain-language summary.

## Scope: derive routes from the diff

Test what changed, not the whole site. From `git diff main...HEAD --name-only` and
`git log main..HEAD --oneline`, map changed files to routes:

> A multi-route QA run is token-heavy — a delegate trigger. Ask the user
> delegate-or-inline before running it (`delegate` skill).

| Changed file | Routes to test |
|---|---|
| Route/page file (`app/**/page.tsx`, `pages/foo.tsx`, `src/pages/foo.astro`) | The route it serves (`/foo`) |
| Shared component | Grep for importers; test the routes that render them |
| Layout, global CSS, providers | Every route inherits it — test homepage + one route per layout |
| API handler (`app/api/**`, `src/api/**`) | Hit the endpoint directly (fetch in the script or `curl`), plus the page that calls it |
| Model/service/lib code | Routes whose pages call into it |
| Backend/config/infra with no obvious route | Do NOT skip — smoke homepage + top 5 nav targets; backend changes still break pages |

Cross-reference commit messages to understand *intent*: what is this change supposed
to do? Verify it does that, not just that pages load.

## Driving the browser

**Prefer the built-in `verify` and `run` skills** when available in this environment:
`run` knows how to launch this project's app; `verify` drives a changed flow end-to-end.
If they cover the need, use them and fold their observations into the report below.

Otherwise, drive Chromium yourself via Playwright through Bash.

**1. Get the app running.** Check common dev ports first — Next.js `:3000`,
Vite `:5173`, Astro `:4321`:

```bash
for p in 3000 5173 4321; do curl -sf -o /dev/null "http://localhost:$p" && echo "UP :$p"; done
```

If nothing is up, start `npm run dev` in the background, wait for the ready line,
and note the port. If the port can't be determined, ask the user for the URL.

**2. Check Playwright is available.**

```bash
node -e "require.resolve('playwright')" 2>/dev/null && echo READY || echo MISSING
```

If MISSING, ask the user once: "Browser QA needs Playwright (dev-only dependency).
OK to run `npm i -D playwright && npx playwright install chromium`?" Wait for a yes
before installing. Never install silently.

**3. Set up an evidence directory** in the session scratchpad (never inside the repo):

```bash
QA_OUT="$SCRATCHPAD/browser-qa-$(date +%Y%m%d-%H%M%S)"   # use this session's scratchpad dir
mkdir -p "$QA_OUT"
```

**4. Write the smoke script** to `$QA_OUT/qa-smoke.mjs` and run it with the route list:

```js
// qa-smoke.mjs — node qa-smoke.mjs <baseURL> [path ...]   (QA_OUT=screenshot dir)
import { chromium } from 'playwright';
const [base, ...paths] = process.argv.slice(2);
const routes = paths.length ? paths.map(p => new URL(p, base).href) : [base];
const out = process.env.QA_OUT || '.';
const browser = await chromium.launch();
const page = await browser.newPage();
const findings = [];
page.on('console', m => { if (m.type() === 'error') findings.push(`[console] ${page.url()} :: ${m.text()}`); });
page.on('pageerror', e => findings.push(`[exception] ${page.url()} :: ${e.message}`));
page.on('requestfailed', r => findings.push(`[netfail] ${r.url()} :: ${r.failure()?.errorText}`));
page.on('response', r => { if (r.status() >= 400) findings.push(`[http ${r.status()}] ${r.url()}`); });
for (const url of routes) {
  const res = await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 })
    .catch(e => { findings.push(`[nav] ${url} :: ${e.message}`); return null; });
  if (!res) continue;
  const slug = new URL(url).pathname.replace(/\W+/g, '-').replace(/^-|-$/g, '') || 'home';
  await page.screenshot({ path: `${out}/${slug}.png`, fullPage: true });
  const body = (await page.textContent('body')) ?? '';
  if (!body.trim()) findings.push(`[blank] ${url} :: body rendered empty`);
  console.log(`VISITED ${url} -> ${slug}.png (status ${res.status()})`);
}
await browser.close();
console.log(findings.length ? findings.join('\n') : 'NO FINDINGS');
```

```bash
QA_OUT="$QA_OUT" node "$QA_OUT/qa-smoke.mjs" http://localhost:3000 / /pricing /dashboard
```

**Per-route DOM asserts and interactions:** extend a copy of the script for the
specific change — e.g. `await page.getByText('Saved!').waitFor({ timeout: 5000 })`
after clicking submit, or `page.getByRole('button', { name: 'Add' }).click()` then
re-screenshot. One throwaway script per flow is fine; they all live in `$QA_OUT`.
For SPAs, click links in-page rather than only `goto` — client-side routing bugs
don't show up on direct navigation. After every screenshot, Read the file so the
user sees it inline.

## Per-page checklist (T3; for T2 do steps 1, 5, and one item of 2)

1. **Loads** — 2xx, no blank body, screenshot looks like a page, not an error.
2. **Interactive elements** — click buttons/links/controls a user would use. Do they do what they say?
3. **Forms** — fill and submit; try empty and one invalid input. Errors shown clearly?
4. **States** — empty, loading, error, overflow (long text).
5. **Console + network** — zero new JS errors or failed requests after interactions.
6. **Navigation** — paths in and out work; browser back doesn't break the app.
7. **Responsive** (if the change touched layout) — re-run at `viewport: { width: 375, height: 812 }`.
8. **Accessibility** — interactive elements are keyboard-reachable (Tab order works); images have alt text.
9. **Performance** — page is interactive under ~3s on the dev server; no single request over 2MB.
10. **Content** — no lorem/placeholder text or broken images.

Spend depth where users spend time: homepage, dashboard, checkout, search — not
the terms-of-service page.

## Evidence tiers

Label every finding with how you know it:

- **Verified** — reproduced twice; screenshot + console/network excerpt attached. Full weight in scoring.
- **Observed** — seen once with evidence captured, not re-reproduced. Counts, note the uncertainty.
- **Assumed** — inferred from the diff or a lone log line, never seen in the browser. List under "Unverified concerns", **excluded from the health score**.

Never report an issue with no evidence at all. Retry once before documenting so a
fluke doesn't become a finding. Never put real credentials in the report — `[REDACTED]`.

## Prioritize by WTF-likelihood

Order testing and the report by how likely a *real user* is to hit the problem:
first click on the homepage > a form everyone submits > a keyboard trap in a rarely
opened modal. Self-regulate the same way: when the last several findings are all
low-severity edge cases no user would plausibly hit, stop exploring — you're done,
write the report. Depth over breadth: 5–10 well-evidenced issues beat 20 vague ones.

## Health score

Severity (see per-finding deductions): **critical** = blocks a core workflow / data
loss; **high** = major feature broken, no workaround; **medium** = works but
noticeably wrong, workaround exists; **low** = cosmetic.

Each category starts at 100. Deduct per Verified/Observed finding:
critical −25, high −15, medium −8, low −3 (floor 0). Console: 0 errors → 100,
1–3 → 70, 4–10 → 40, more → 10. Links: −15 per broken link.

| Category | Weight | | Category | Weight |
|---|---|---|---|---|
| Functional | 20% | | Links | 10% |
| Console | 15% | | Visual | 10% |
| UX | 15% | | Performance | 10% |
| Accessibility | 15% | | Content | 5% |

`score = Σ (category_score × weight)` — round to an integer out of 100.

## Report

Markdown, written as you go (don't batch findings). Include: date, base URL, branch,
tier, routes visited, evidence dir (`$QA_OUT`). Then per-route:

```markdown
### Route: /pricing
- **[high · Verified] Plan selector does nothing on click**
  Evidence: $QA_OUT/pricing-after-click.png · console: `TypeError: plans is undefined (pricing.tsx:42)`
  Repro: load /pricing → click "Pro" → nothing happens, error in console.
```

End every report with — written for a non-expert reader, no jargon:

```markdown
## Health score: NN/100

## Top 3 things a user would hit
1. **Plain-language sentence** describing what a user experiences, and where.
2. ...
3. ...
```

If nothing is broken, say so plainly: score, routes covered, "no user-facing issues found".

## Report-only discipline

- This skill **finds**; it does not fix. Do not edit source files, do not "quickly patch" anything, do not put suggested code in the report (naming the suspect area is fine).
- Fixes go through the normal Build/Verify loop: diagnose with the `debug` skill, **one commit per fix**, add a regression test for each fix, then re-run `browser-qa` on the affected routes to confirm — before `ship`.
- Test as a user, not a developer: reading source is for *scoping routes only*, never for judging "that probably works".
- Keep all screenshots and scripts in `$QA_OUT`; never commit evidence into the repo.

---
*Adapted from gstack (MIT, © Garry Tan); see ATTRIBUTION.md.*
