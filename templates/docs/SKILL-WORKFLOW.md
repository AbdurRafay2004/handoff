# Skill Workflow — what to reach for, when

How handoff skills compose: handoff owns state AND process. The workflow
layer replaces any external process packs — one sequencer, no competing ones.

## Three layers

- **State** — handoff memory (`.handoff/`: STATUS, RULES, CONTEXT.md,
  tasks, LEARNINGS). Automatic via hooks.
- **Process** — the `workflow` skill + its technique skills. Tier-driven;
  `workflow` alone decides sequencing and how much ceremony a task gets.
- **Domain / services** — stack- and domain-specific skills. They trigger on
  their own; they are services, not pipeline.

## The one rule that replaces everything else

**Declare the tier, then let the tier decide the process.**

| Tier | What | Process |
|---|---|---|
| T1 | copy, styling, small edits | inline → typecheck+lint → done. No brief, no plan, no agents. |
| T2 | normal features | short brief in chat → bullet plan → build → tests on affected path → review → evidence |
| T3 | money, auth, user data, migrations | written spec the user approves → plan the user approves → TDD → security → full verify → runbook ship → retro |

If heavy process lands on a light task: say "this is T1". That ruling stands.

## The pipeline, phase by phase

1. **Brief** — `handoff:brief`. Questions one at a time, code cited `path:line`, the user's approval on the spec.
2. **Plan** — `handoff:plan` (T2/T3); `handoff:design` when interfaces/seams are the question.
3. **Build** — inline by default. `handoff:tdd` (T3 mandatory);
   `handoff:delegate` ONLY for context-flooding work or true parallelism.
   Bug → `handoff:debug`; 3+ failed fixes → `handoff:architecture`.
4. **Verify** — typecheck/lint/tests/build, then code review (T2+),
   `handoff:browser-qa`, `handoff:security` + `/security-review` (T3).
   Gate: `handoff:verify-done` — evidence the user can judge, including
   the Spec check (is it what was asked?).
5. **Ship** — `handoff:ship`. Branch → PR → merge → deploy → smoke check.
   T3: launch runbook with rollback criteria set BEFORE deploying.
6. **Learn** — `handoff:learn` (T3/incidents only). CHANGELOG + LEARNINGS.md;
   RULES.md only when the user explicitly accepts a new rule.

## When X happens, reach for Y

| Situation | Reach for |
|---|---|
| Something's broken / test fails | `handoff:debug` — no fixes before root cause |
| 3+ fixes failed | `handoff:architecture` |
| "Is it actually done?" | `handoff:verify-done` |
| Deploy / release / go live | `handoff:ship` |
| Codebase feels painful | `handoff:architecture` (proactive scan) |
| QA the site in a browser | `handoff:browser-qa` |
| Full security audit | `handoff:security` (diff-only: `/security-review`) |
| Search/build would flood context | `handoff:delegate` |
| New repo | `handoff:setup`, then `setup-pre-commit` + `git-guardrails-claude-code` (if installed; one-time hardening) |
| Watch a deploy / recurring check | `/loop` (self-paced) — or `schedule` if unattended |
| Grind the backlog / drive work to done | `/goal` with a measurable condition (tiers still gate T3) |
| Merge conflict mid-ship | `resolving-merge-conflicts` (if installed) |

## Time operators — goal, loop, schedule (built-in)

Not phases — they run phases *across time*:

- **`/goal <condition>`** — *keep working until WHAT?* Persistent objective, auto-checked, clears when met. Add a bound ("…or stop after 20 turns").
- **`/loop`** — *re-run WHEN, while attended?* Interval or self-paced; session-scoped.
- **`schedule`** — *run WHEN, unattended?* Cloud cron, 1h minimum.

**Tier guardrail:** an autonomous goal/loop may drive T1/T2 to completion, but a
T3 approval gate ALWAYS outranks the goal — it stops and waits for the user.
Never let "empty the backlog" self-approve money/auth/data work.

## Rules of thumb

- **One sequencer.** `workflow` owns order and ceremony; other skills contribute
  technique. A skill running its own workflow is a bug in the skill.
- **Evidence over claims.** The user judges demos, test output, and preview
  URLs — never "the code looks right".
- **One of each spine:** one task system (`.handoff/tasks/`), one meaning
  for `CONTEXT.md`, one learnings file (`.handoff/context/LEARNINGS.md`).
- **Keep STATUS.md ≤ 25 lines** — it is injected every session; drift is a token tax.
