# Skill Workflow — what to reach for, when

Personal map for the post-v1.2.0 setup: agent-orch owns state AND process;
everything else is a domain tool it calls. superpowers + mattpocock are
**disabled** — their value was forked into agent-orch's skills (see
ATTRIBUTION.md). Don't re-enable them; that reintroduces competing sequencers.

## Three layers (updated)

- **State** — agent-orch memory (`.agent-orch/`: STATUS, RULES, CONTEXT.md,
  tasks, LEARNINGS). Automatic via hooks.
- **Process** — agent-orch `workflow` + its technique skills. Mine, owned,
  tier-driven. `workflow` alone decides sequencing and how much ceremony a
  task gets.
- **Domain / services** — frontend-design, cloudflare, supabase, dataviz,
  rampstack (client-service library: SEO, brand, content, growth). Execution
  of specific work; the pipeline calls them, they never run the pipeline.

## The one rule that replaces everything else

**Declare the tier, then let the tier decide the process.**

| Tier | What | Process |
|---|---|---|
| T1 | copy, styling, small edits | inline → typecheck+lint → done. No brief, no plan, no agents. |
| T2 | normal features | short brief in chat → bullet plan → build → tests on affected path → review → evidence |
| T3 | money, auth, user data, migrations | written spec I approve → plan I approve → TDD → security → full verify → runbook ship → retro |

If heavy process lands on a light task: say "this is T1". That ruling stands.

## The pipeline, phase by phase

1. **Brief** — `agent-orch:brief`. Questions one at a time, code cited
   `path:line`, my approval on the spec.
2. **Plan** — `agent-orch:plan` (T2/T3). Premise challenged first; spikes for
   unknowns; `agent-orch:design` when interfaces/seams are the question.
3. **Build** — inline by default. `agent-orch:tdd` (T3 mandatory).
   `agent-orch:delegate` ONLY for context-flooding work or true parallelism.
   `frontend-design` for UI. Bug → `agent-orch:debug`; 3+ failed fixes →
   `agent-orch:architecture`.
4. **Verify** — typecheck/lint/tests/build, then `/code-review` (T2+),
   built-in `verify`/`run` to drive the app, `simplify` once green,
   `agent-orch:browser-qa` for real-browser QA, `agent-orch:security` +
   `/security-review` (T3). Gate: `agent-orch:verify-done` — evidence I can
   judge, including the Spec check (is it what I asked?).
5. **Ship** — `agent-orch:ship`. Branch → PR → merge → deploy (knows wrangler /
   Vercel / Convex-before-frontend / Supabase migrations) → smoke check. T3:
   launch runbook with rollback criteria set BEFORE deploying.
6. **Learn** — `agent-orch:learn` (T3/incidents only). CHANGELOG + LEARNINGS.md;
   RULES.md only when I explicitly accept a new rule.

## When X happens, reach for Y

| Situation | Reach for |
|---|---|
| Something's broken / test fails | `agent-orch:debug` — no fixes before root cause |
| 3+ fixes failed | `agent-orch:architecture` |
| "Is it actually done?" | `agent-orch:verify-done` |
| Deploy / release / go live | `agent-orch:ship` |
| Codebase feels painful | `agent-orch:architecture` (proactive scan) |
| QA the site in a browser | `agent-orch:browser-qa` |
| Full security audit | `agent-orch:security` (diff-only: `/security-review`) |
| Search/build would flood context | `agent-orch:delegate` |
| New repo (mine or client) | `agent-orch:setup`, then `setup-pre-commit` + `git-guardrails-claude-code` (one-time hardening) |
| Watch a deploy / recurring check | `/loop` (self-paced) — or `schedule` if unattended |
| Grind the backlog / drive work to done | `/goal` with a measurable condition (tiers still gate T3) |
| Nightly client-site QA | `schedule` + `agent-orch:browser-qa` |
| Merge conflict mid-ship | `resolving-merge-conflicts` |

## Time operators — goal, loop, schedule (built-in)

Not phases — they run phases *across time*. Pick by the question:

- **`/goal <condition>`** — *keep working until WHAT?* Persistent objective,
  auto-checked each turn by a fast model, clears when met. Best:
  `/goal tasks/now/ is empty` (backlog grinder), `/goal all tests pass and
  lint is clean`. Add a bound: "…or stop after 20 turns".
- **`/loop`** — *re-run WHEN, while I'm at the machine?* Fixed interval
  (`/loop 5m check the deploy`) or self-paced (prompt only — usually cheaper,
  can Monitor instead of poll). Session-scoped; dies with a new conversation.
- **`schedule`** — *run WHEN, while I'm gone?* Cloud cron, machine off, 1h
  minimum. Best: nightly `browser-qa` against client production sites.

**Tier guardrail:** an autonomous goal/loop may drive T1/T2 to completion, but
a T3 approval gate ALWAYS outranks the goal — it stops and waits for me.
Never let "empty the backlog" self-approve money/auth/data work.

## Occasional / opt-in

- **Client marketing/SEO/brand/content work** → rampstack families, per
  engagement. They're services, not pipeline.
- **Post-launch marketing clip** → `social-showcase-video`.
- **Writing** → writing-fragments / writing-beats / writing-shape / edit-article.

## Rules of thumb (updated)

- **One sequencer.** `workflow` owns order and ceremony; every other skill
  contributes technique. If a skill starts running its own workflow, that's a
  bug in the skill — fix the skill, don't obey it.
- **Evidence over claims.** I judge demos, test output, and preview URLs —
  never "the code looks right".
- **One of each spine:** one task system (`.agent-orch/tasks/`), one meaning
  for `CONTEXT.md`, one learnings file (`.agent-orch/context/LEARNINGS.md`).
- **Versions ship via git push** — the marketplace reads GitHub, not the local
  clone. Bump both manifests, commit, PUSH, then `/plugin marketplace update`.
- **Keep STATUS.md ≤ 25 lines.** It's injected every session; drift here is
  the single biggest measured token leak (502 lines ≈ 12k tokens/session on
  Retail-OS before pruning).
