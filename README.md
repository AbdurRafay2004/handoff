<div align="center">

# handoff

### Shift-change notes for your coding agent.

**Claude Code forgets everything when a session ends. handoff is the note the
last session leaves for the next one.**

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FAbdurRafay2004%2Fhandoff%2Fmain%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](https://github.com/AbdurRafay2004/handoff/blob/main/.claude-plugin/plugin.json)
[![CI](https://github.com/AbdurRafay2004/handoff/actions/workflows/ci.yml/badge.svg)](https://github.com/AbdurRafay2004/handoff/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/AbdurRafay2004/handoff?style=flat&logo=github)](https://github.com/AbdurRafay2004/handoff/stargazers)

A simple memory and workflow system for Claude Code.

</div>

---

## The problem

Every new Claude Code session starts from zero. It doesn't remember what you
built yesterday, what you decided against, or which folder has the tricky code.

The existing fixes have real downsides:

- **A giant CLAUDE.md** — everything loads every session, whether you need it
  or not. You pay for all of it, every time, and it keeps growing.
- **Memory servers and databases** — another thing to install, run, and keep
  alive. Your project's memory lives outside your project.
- **Hoping the agent figures it out** — it re-reads your codebase every
  session and reaches slightly different conclusions each time.

## What handoff does instead

It keeps memory in **plain markdown files, inside your repo, committed with
your code**. A few small hooks make sure the right file reaches the agent at
the right moment — and nothing more:

- When a session starts, the agent gets the current status and your project
  rules. That's it — a few hundred tokens, not thousands.
- When it's about to edit a file in a folder that has notes (`CONTEXT.md`),
  those notes get injected right then. Not before.
- When a session ends having changed code — committed or not — without
  updating the status, the agent gets reminded to bring the notes up to date,
  in the same commit as the code. It knows the difference between your
  session's work and dirt that was already there, and it never nags twice
  about the same thing.
- Unfinished work doesn't vanish with the session. Follow-ups, bugs, and ideas
  become small task files in a backlog inside the repo — written so that any
  future session can pick one up cold and know when it's done ([more
  below](#the-tasks-backlog)).

No server. No database. No dependencies — three Python hooks and one shared
helper file, standard library only. If a hook ever fails, it stays silent and
your session is unaffected. And since it's all just files in git, your memory
travels with the repo: every clone and every teammate gets it for free.

## Quick start

Inside Claude Code:

```sh
# 1. Add this repo as a plugin marketplace (once)
/plugin marketplace add AbdurRafay2004/handoff

# 2. Install the plugin
/plugin install handoff@handoff
```

Then, in any repo where you want memory:

```
set up handoff
```

Setup copies the file templates into `.handoff/`, reads your actual codebase
to draft the status, map, and tech notes, and **asks you to confirm before
saving anything** — it never invents facts about your project. Run it once per
repo. After that, everything is automatic.

## What ends up in your repo

```
.handoff/
  STATUS.md       # where the project stands right now (loaded every session)
  RULES.md        # your non-negotiables (loaded every session)
  MAP.md          # where important files live (read when needed)
  CHANGELOG.md    # what changed and why (read when needed)
  context/        # stable notes: product intent, tech stack
  tasks/          # a real backlog: inbox / now / done
```

Plus optional `CONTEXT.md` files in folders that need explaining — those load
only when the agent edits there.

The whole idea in one sentence: **the files that are always relevant are
pushed every session; everything else costs nothing until it's actually
needed.**

## The tasks backlog

This might be the best part of the whole system. Instead of follow-ups dying
in chat history, they live as small markdown files that move through three
folders:

```
tasks/inbox/   # new ideas, bugs, follow-ups land here
tasks/now/     # the small set you're actually working on
tasks/done/    # finished (or deliberately closed)
```

Each task is one file that carries everything a future session needs to pick
it up cold — no chat history required:

```markdown
---
title: Fix flaky checkout test
status: now
priority: high
why_it_matters: Blocks every release; CI reruns waste ~20 min a day.
context: Fails only when the cart has a discount code. Started after #142.
---

## Notes
- Repro: run checkout.spec.ts with SEED=7

## Verification
- npx vitest checkout.spec.ts — passes 10/10 runs
```

Notice the `Verification` section: a task states how to prove it's done, so
whoever (or whatever session) finishes it knows when to stop.

The hooks quietly keep this tidy. If the agent tries to write a task file to
the `tasks/` root instead of a status folder, it gets corrected *before the
file lands* — and again at the end of the turn if any strays remain. Skills
feed the backlog too: debugging leaves architectural findings there, and
retrospectives file their action items as tasks instead of letting them
evaporate.

## Guard rails you'll appreciate later

A few small mechanisms that don't show up until they save you:

- **Approval gates that hold.** Risky work (T3) stops at a `.handoff/GATE`
  file with the question awaiting your answer. While that file exists the
  agent won't proceed — even an autonomous loop just idles there until you
  rule.
- **Risky paths get flagged automatically.** Touch anything matching
  migrations, auth, billing, `.env` and the like, and the end-of-turn check
  asks whether this was treated with the care it deserves. The pattern list
  is per-repo configurable via `.handoff/SENTINELS`.
- **Status bloat is policed.** `STATUS.md` loads every session, so it's a tax
  if it grows. Past 40 lines the agent gets told to prune it (target: 25).
- **Clones without the plugin still work.** Setup writes a small fallback
  block into your `CLAUDE.md`, so a teammate who hasn't installed handoff
  still gets the core rules and knows where the notes live.
- **Stale installs get noticed.** Setup stamps `.handoff/VERSION`; when the
  plugin moves ahead of an install, you're told instead of drifting silently.

## The workflow part

handoff also ships a set of skills that give the agent a sane way of working.
The core one, `workflow`, sorts every task into a tier:

| Tier | Example | What the agent does |
|---|---|---|
| **T1** | fix a typo, tweak styling | just edits it, checks it compiles, done |
| **T2** | a normal feature | short plan, build, test what changed, review |
| **T3** | money, auth, user data, migrations | written plan you approve, tests first, security review, proof it works |

So a two-line fix never gets buried in ceremony, and a payment change never
skips review. Thirteen companion skills cover the techniques: writing a brief,
planning, debugging properly, TDD, shipping, security audits, browser QA, and
more — including `grill-me`, which interrogates your plan until you've both
thought it through.

These skills are adapted from open-source work by Jesse Vincent, Matt Pocock,
Garry Tan, and RampStack Co. — see [ATTRIBUTION.md](ATTRIBUTION.md). One
deliberate change: the `workflow` skill alone decides the process, so the
skills never fight each other over sequencing. If you install handoff,
disable the original packs to avoid duplicate instructions.

## Honest limitations

- Files edited through shell commands (`sed`, `cat >`) don't trigger the
  folder-notes injection — only real Edit/Write tool calls do.
- On very large repos, git commands in the hooks time out after 10 seconds;
  when that happens the affected check quietly skips that turn.
- `/compact` resets the session's change tracking — work done before a
  compaction may not get the end-of-turn reminder afterward.
- Work you've already pushed doesn't trigger the reminder (deliberate: the
  hook would rather stay quiet than nag about published commits), and the
  very first turn after adopting the hooks is silent while it takes its
  baseline.
- The risky-path flagging is pattern matching, not a security scanner — it
  catches `migrations/`, misses cleverly-named danger.
- Repos without git don't get the end-of-session reminder (it needs git to
  see what changed).
- Only Claude Code for now.

Every limitation fails quiet, never broken.

## Development

```sh
# run the same tests CI runs
python3 tests/test_hooks.py
```

No build step. Ground rules for contributions: hooks stay standard-library
only, hooks stay fail-safe (silent exit on any error), and the `workflow`
skill alone owns process. The full invariants are in [CLAUDE.md](CLAUDE.md).

## Star history

<a href="https://star-history.com/#AbdurRafay2004/handoff&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=AbdurRafay2004/handoff&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=AbdurRafay2004/handoff&type=Date" />
    <img alt="Star history chart" src="https://api.star-history.com/svg?repos=AbdurRafay2004/handoff&type=Date" />
  </picture>
</a>

## License

[MIT](LICENSE) © Rafay. Adapted portions credited in
[ATTRIBUTION.md](ATTRIBUTION.md).
