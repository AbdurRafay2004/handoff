---
name: learn
description: Use at the end of T3 work, after an incident/rollback, or when the user asks for a retro — turns what happened into recorded learnings that live in the repo (CHANGELOG entry, typed LEARNINGS.md entries, follow-up tasks, and — only with explicit user approval — new RULES).
---

# Learn

Part of the **Learn** phase — see the `workflow` skill for tiers and sequencing.

Work that ends without a recorded lesson gets re-learned the hard way. This
skill closes the loop: reconstruct what actually happened (from git, not
memory), find the cause, record what it taught us, and hand the user — a PM
building development judgment — one thing they can carry forward.

## Tier scaling — most work does NOT get a retro

| Situation | What Learn means |
|---|---|
| **T1 / T2** | One `CHANGELOG.md` line + a `STATUS.md` update. Done. Do **not** run a retro; that would be ceremony the tier doesn't warrant. Only add a LEARNINGS.md entry if something genuinely surprising surfaced. |
| **T3 completed** | Full retro (below), even when it went well — lessons from success calibrate what to repeat. |
| **Incident / rollback / user asks for a retro** | Full retro, regardless of tier. |

## The retro method

### 0. Anti-hallucination guard — verify before analyzing

The retro is built from git history, never from what you remember doing.
Before analyzing anything:

```sh
git log --since="<window>" --format="%h|%ai|%s" --stat
```

- Confirm the commits you're about to discuss **actually exist** in that
  output. Never analyze a commit you cannot see the hash of.
- If the window returns zero or suspiciously few commits, **stop and ask**
  the user to confirm the date range or the branch — do not fabricate a
  coherent-sounding narrative from nothing.
- If the retro is about a specific incident, locate the exact commits
  involved (`git log --follow <file>`, `git show <hash>`) and quote them.

### 1. Blameless framing

Analyze systems, not people. Assume every decision was reasonable given what
was known at the time; ask "why was that decision reasonable?" not "who
messed up?" — the fix that matters is the one that makes the next attempt
succeed. Blameless does not mean toothless: action items still get owners
and dates, and hard truths still get said.

### 2. Timeline → root cause → contributing factors → action items

1. **Timeline** — reconstruct from commit timestamps, messages, and the
   session's own record. What happened, in order, with evidence for each step.
2. **Root cause** — five whys until you hit a system-level answer (a "why"
   that ends at a person is not deep enough; keep going to the process or
   check that was missing).
3. **Contributing factors** — what didn't cause it but made it worse or
   removed a safety net: missing test, skipped `verify-done` evidence, a bug
   patched without `debug` root-causing, docs that lied.
4. **What went well** — 1–2 specific things, anchored in actual commits
   ("the feature flag meant the rollback was one line"), plus one specific
   growth opportunity framed as leveling-up, not criticism.
5. **Action items** — specific, sized, closeable. "Improve testing" is not
   an action item; "add a webhook-ordering test to `src/billing/`" is.

### 3. Trend awareness

Before writing new entries, read the existing `.agent-orch/context/LEARNINGS.md`
and recent `CHANGELOG.md`. If this retro's pitfall already has an entry, that
is the finding: a **repeat** — raise its confidence, say so out loud, and
propose a stronger fix (often a RULES.md candidate) instead of logging a
duplicate.

## Where outputs land

All durable output goes into the repo's `.agent-orch/` tree so it travels
with the code:

| Output | Destination |
|---|---|
| What shipped / what broke, one dated line | `.agent-orch/CHANGELOG.md` |
| Typed learnings (schema below) | `.agent-orch/context/LEARNINGS.md` |
| A new invariant ("never X", "always Y") | `.agent-orch/RULES.md` — **only** after proposing it and the user explicitly accepts. Never write RULES unilaterally. |
| Action items that outlive this session | `.agent-orch/tasks/inbox/` (one file per follow-up) |
| Current state change | `.agent-orch/STATUS.md` |

A full retro writeup can be shown in chat; the durable residue is the files
above. No JSON snapshots, no home-directory state — if it isn't committed,
it didn't happen.

## LEARNINGS.md entry format

One line per learning, **newest first**, under a single `# Learnings` heading.
Create the file on first use.

```
- YYYY-MM-DD [type/confidence] insight — files-or-area (source)
```

- **type** — `pattern` (reusable approach that worked), `pitfall` (what not
  to do and why), `preference` (something the user stated they want).
- **confidence** — `low` / `med` / `high`. Be honest: verified in code =
  high; single observation = med; inference = low. User-stated preferences
  are always high.
- **source** — provenance: the commit hash, retro, or session that taught it.
  This is what makes an entry checkable later.

Rejected design/refactor options (from `architecture`) are recorded as type
`pitfall` ("rejected: X because Y") — or as an ADR when the three ADR
criteria hold.

Examples:

```
- 2026-07-01 [pitfall/high] Stripe webhooks arrive out of order; never derive state transitions from event sequence — src/billing/webhooks.ts (rollback retro, commit 4f2a9c1)
- 2026-06-21 [pattern/med] Default-off feature flag + smoke check made the search rollout a one-line revert; reuse for risky UI work — src/flags.ts (T3 retro, commit b81d2e0)
- 2026-06-14 [preference/high] User wants preview URLs, not screenshots, as ship evidence (user-stated, session 2026-06-14)
```

### Maintenance — every time you touch the file

- **Staleness**: for entries whose files you can check cheaply, verify the
  referenced file/code still exists. If it's gone, delete the entry or
  rewrite it against what replaced it.
- **Conflicts**: if a new learning contradicts an old one, do not add a
  second line — resolve it. Rewrite the old entry with today's date, the new
  insight, and adjusted confidence, noting the reversal if it's instructive.
- **Promotion**: an entry that keeps proving true is a RULES.md candidate —
  propose it to the user.
- Keep the file skimmable: one line each, prune ruthlessly. Fifty sharp
  entries beat five hundred stale ones.

## Teach the PM one thing

End every retro by answering, in plain product language, one question:

> **"What would have prevented this?"** (or, for a success: *"what made this
> go smoothly, that we should do on purpose next time?"*)

One takeaway, two or three sentences, no jargon — the kind of judgment a PM
can apply to the *next* brief ("migrations are T3 even when they look small";
"ask for the rollback plan before approving anything touching billing").
That sentence is the actual product of this skill; the files are its memory.

---

*Adapted from gstack (MIT, © Garry Tan) and rampstack-skills (MIT, © 2026 RampStack Co.); see ATTRIBUTION.md.*
