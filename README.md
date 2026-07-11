<div align="center">

# handoff

### Shift-change notes for your coding agent.

**Every session, your agent wakes up with amnesia. handoff is the note the
last shift left behind.**

[![Version](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FAbdurRafay2004%2Fhandoff%2Fmain%2F.claude-plugin%2Fplugin.json&query=%24.version&label=version&color=blue)](https://github.com/AbdurRafay2004/handoff/blob/main/.claude-plugin/plugin.json)
[![CI](https://github.com/AbdurRafay2004/handoff/actions/workflows/ci.yml/badge.svg)](https://github.com/AbdurRafay2004/handoff/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/AbdurRafay2004/handoff?style=flat&logo=github)](https://github.com/AbdurRafay2004/handoff/stargazers)

Hook-driven **project memory** + a **risk-tiered development workflow** for
Claude Code. Drop it into any repo and the agent gains durable state across
sessions — without bloating every session's context.

</div>

---

## Why

Coding agents forget everything between sessions. The usual fixes are bad in
opposite directions: stuff everything into `CLAUDE.md` (pays a token tax on
every single session) or hope the agent rediscovers context on its own (it
won't, or it will — differently each time).

handoff's principle: **push the right context at the right moment, instead of
hoping the agent pulls it.**

| State | When it loads | Cost |
|---|---|---|
| `STATUS.md` + `RULES.md` | every session (SessionStart hook) | always-on, small |
| `BOOT.md`, `MAP.md`, `context/*`, `tasks/`, `CHANGELOG.md` | on demand | zero until read |
| folder-level `CONTEXT.md` | the moment the agent edits in that folder (PreToolUse hook) | zero until then |
| state-update nudge | turn end, only if the session changed code (Stop hook) | one line, only when relevant |

In a repo **without** `.handoff/`, every hook stays dormant (one one-time
"run setup" tip, then silence forever). Zero cost where you don't use it.

## Quick start

```sh
# 1. Add this repo as a plugin marketplace (once)
/plugin marketplace add AbdurRafay2004/handoff

# 2. Install + enable the plugin
/plugin install handoff@handoff
```

Then, in any repo where you want project memory:

```
set up handoff
```

The `setup` skill copies the template tree into `.handoff/`, runs a guided
discovery pass over your actual codebase to draft a real STATUS / MAP /
TECH_STACK / PRODUCT, **confirms with you before saving anything**, optionally
seeds folder-level CONTEXT.md, and writes a thin-fallback block to `CLAUDE.md`
(so clones opened without the plugin still work). Run it once per repo.

From then on it's automatic — the hooks load state, inject local context on
edit, and nudge the agent to keep state fresh. `.handoff/` is committed to
your repo, so memory travels with the code: every clone, every teammate, every
CI checkout gets the same handoff.

## How it works

Three Python hooks (stdlib-only, no dependencies), all fail-safe:

```
.claude-plugin/
  marketplace.json     # registers the plugin
  plugin.json          # plugin manifest (skills; hooks auto-load from hooks/hooks.json)
hooks/
  hooks.json           # SessionStart, PreToolUse(Edit|Write|MultiEdit|NotebookEdit), Stop
  _common.py           # shared, fail-safe helpers
  sessionstart.py      # load STATUS+RULES, capture git baseline, version-drift check
  pre_edit_context.py  # inject nearest CONTEXT.md; catch task files written to tasks/ root
  stop.py              # session-aware nudges: state, MAP, strays, STATUS size,
                       # sentinel (T3) paths, open GATE
skills/                # setup + the workflow layer (15 skills)
templates/             # the .handoff/ tree copied into target repos
tests/                 # hook smoke tests (run in CI)
```

- **`sessionstart.py`** injects `STATUS.md` + `RULES.md` in full, plus a pointer
  to the on-demand docs. It also captures a git baseline (HEAD + dirty paths) so
  the Stop hook can tell *this session's* work apart from pre-existing dirt.
- **`pre_edit_context.py`** walks up from the file being edited to the nearest
  `CONTEXT.md` and injects it — once per session per file. Architecture notes
  arrive exactly when the agent is about to touch that code.
- **`stop.py`** nudges at turn end if the session changed code but didn't update
  durable state — and instructs that state updates ride in the **same commit**
  as the code they describe. It also flags sentinel paths (auth / billing /
  migrations — forces the risk-tier question into the transcript) and surfaces
  an open T3 approval gate.

## The workflow layer

Alongside memory, the plugin ships an owned development pipeline. The
`workflow` skill defines six phases — **Brief → Plan → Build → Verify → Ship →
Learn** — with risk tiers that decide how much process a task gets:

| Tier | Covers | Process |
|---|---|---|
| **T1 — trivial** | copy, styling, config tweaks | edit → typecheck → done |
| **T2 — standard** | typical features and refactors | short plan → build → tests on the affected path → review |
| **T3 — risky** | money, auth, user data, migrations | approved written plan → TDD → security review → end-to-end evidence |

A 2-line edit never pays for a migration's ceremony. T3 gates are
machine-readable (`.handoff/GATE`) so autonomous loops idle at approval points
instead of blowing through them.

Thirteen companion skills carry the technique: `brief`, `plan`, `design`,
`tdd`, `debug`, `architecture`, `delegate`, `verify-done`, `security`,
`browser-qa`, `ship`, `learn`, and `grill-me` (relentless plan interrogation
on demand). Sequencing lives in ONE place — `workflow` — and the other skills
contribute technique, not process.

These skills are adapted from MIT-licensed work by Jesse Vincent
(superpowers), Matt Pocock (mattpocock-skills), Garry Tan (gstack), and
RampStack Co. (rampstack-skills) — see [ATTRIBUTION.md](ATTRIBUTION.md). All
cross-pack orchestration was deliberately stripped; if you run this workflow
layer, disable the original packs to avoid competing instructions.

## Design principles

- **Fail-safe, always.** Any hook error prints nothing and exits 0 — a hook bug
  can never break your session. CI asserts this on every PR.
- **PreToolUse never touches permissions.** It injects `additionalContext`
  only — it cannot silently auto-approve an edit.
- **Stop can't loop.** Three independent loop-breakers: the `stop_hook_active`
  guard, the session git baseline, and a nudge-signature cooldown that never
  repeats the same unresolved nudge.
- **State rides with the code.** `.handoff/` is committed; updates belong in
  the same commit as the change they describe.

## Known limitations

Accepted trade-offs — each makes a hook *quieter*, never broken:

- **Bash edits aren't covered by CONTEXT injection.** The PreToolUse hook
  matches `Edit`/`Write`, not `Bash` — files changed via `sed`/`cat >` won't
  trigger a CONTEXT.md inject.
- **Very large/slow repos:** the Stop hook's `git status` has a 10s timeout;
  past that the freshness nudge is silently skipped.
- **`/compact` and `--resume` re-baseline:** changes made before a compaction
  fold into the new baseline; only their uncommitted remainder is nudged after.
- **Non-git repos:** the Stop nudge is disabled (it needs git to diff).
- **Per-session marker files** accumulate in the OS temp dir (cleared on reboot).

## Development

No build step, no dependencies. The hooks are plain `python3` reading JSON on
stdin:

```sh
# run the test suite CI runs
python3 tests/test_hooks.py

# poke a hook by hand
echo '{"cwd":"/abs/path/to/repo","session_id":"t1"}' | python3 hooks/sessionstart.py
```

Ground rules for contributions: hooks stay **stdlib-only**, every hook stays
**fail-safe** (exit 0 on any error), `templates/` stays markdown-only, and the
`workflow` skill alone owns sequencing — technique skills never embed process.
See [CLAUDE.md](CLAUDE.md) for the full invariants.

## Layering with other skills

handoff is the **state/context + workflow** layer. It composes with — and does
not replace — domain skills (frontend design, Supabase, etc.). Its `tasks/` is
your durable backlog; the `workflow` skill owns how a single item gets
executed. See [docs/SKILL-WORKFLOW.md](docs/SKILL-WORKFLOW.md) for a "what to
reach for, when" map.

## Star history

<a href="https://star-history.com/#AbdurRafay2004/handoff&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=AbdurRafay2004/handoff&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=AbdurRafay2004/handoff&type=Date" />
    <img alt="Star history chart" src="https://api.star-history.com/svg?repos=AbdurRafay2004/handoff&type=Date" />
  </picture>
</a>

## License

[MIT](LICENSE) © Rafay — adapted portions credited in
[ATTRIBUTION.md](ATTRIBUTION.md).
