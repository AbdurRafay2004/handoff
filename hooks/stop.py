#!/usr/bin/env python3
"""Stop hook (nudge to keep durable state fresh and commit finished work).

Nudges when the agent made NEW repo changes this session — committed or
uncommitted — but didn't update STATUS / CHANGELOG / MAP, left a folder's
CONTEXT.md stale, parked task files in the tasks/ root, let STATUS.md bloat,
touched sentinel (T3-shaped) paths, or has an open T3 gate.

"This session" = (commits made since the session-start HEAD) plus (dirty paths
whose status code changed since session start). Pre-existing uncommitted dirt
is ignored; committing work no longer hides it from the hook.

Three independent loop-breakers so it can never run away (the failure that
prompted this design):
  1. stop_hook_active  -> if we're already in a stop-triggered continuation, exit.
  2. session baseline  -> only consider changes NEW since SessionStart captured
                          the baseline (HEAD sha + dirty codes).
  3. nudge signature   -> never nudge twice for the same unresolved situation,
                          even if the host omits stop_hook_active.

Large-session handoff: once per LARGE_SESSION_STEP of context (from the
transcript's latest usage record), ask for a handoff a fresh session can
continue from, even with no repo changes. It has its own per-step marker and
runs only after the stop_hook_active guard; any transcript problem skips it.

Commit reminders also cover new uncommitted .handoff/ edits, even after state
is updated. They are advisory: this hook never stages, commits, or pushes.
Only fires in repos that have .handoff/ and are git repos.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402
    read_stdin_json, project_root, has_handoff, emit, AGENT_DIR,
    git_status_codes, git_head, git_local_commit_codes, load_baseline,
    save_baseline, last_nudge_signature, set_nudge_signature, signature,
    git_amendable_head,
    read_file, session_marker_dir, marker_seen, marker_set, _short,
)

TASKS_ROOT_ALLOWED = ("WORKFLOW.md", "TEMPLATE.md")
STRUCTURAL_LETTERS = "?ADRCT"  # untracked/added/deleted/renamed/copied/typechange
STATUS_LINE_BUDGET = 40        # nudge threshold; the documented target is <=25
LARGE_SESSION_STEP = 200000   # nudge once per 200k tokens of context crossed
TRANSCRIPT_TAIL_BYTES = 4 * 1024 * 1024  # usage records sit near the end
DEFAULT_SENTINELS = ("migration", "auth", ".env", "stripe", "billing",
                     "payment", "schema", "secret")


def nearest_context_rel(rel_path, root):
    """Nearest ancestor CONTEXT.md (repo-relative) for a changed file, or None."""
    d = os.path.dirname(rel_path)
    while True:
        candidate = os.path.join(d, "CONTEXT.md") if d else "CONTEXT.md"
        if os.path.isfile(os.path.join(root, candidate)):
            return os.path.normpath(candidate)
        if not d:
            return None
        d = os.path.dirname(d)


def misfiled_tasks(root):
    """Task .md files sitting in tasks/ root instead of a status folder; [] on error."""
    found = []
    try:
        tasks_dir = os.path.join(root, AGENT_DIR, "tasks")
        for name in sorted(os.listdir(tasks_dir)):
            if (name.endswith(".md") and name not in TASKS_ROOT_ALLOWED
                    and os.path.isfile(os.path.join(tasks_dir, name))):
                found.append(name)
    except Exception:
        pass
    return found


def sentinel_patterns(root):
    """Per-repo sentinel list (.handoff/SENTINELS, one pattern per line) or defaults."""
    body = read_file(os.path.join(root, AGENT_DIR, "SENTINELS"))
    if body:
        pats = tuple(l.strip().lower() for l in body.splitlines()
                     if l.strip() and not l.startswith("#"))
        if pats:
            return pats
    return DEFAULT_SENTINELS


def sentinel_hit(path, pats):
    """True if a path matches a sentinel pattern on whole-token boundaries.

    Bare substring matching false-positives badly ("auth" in docs/authors.md,
    ".env" in .envrc). Alphanumeric patterns must equal a whole path token
    (singular or plural); dotted patterns like ".env" must equal a whole path
    segment or be its dotted prefix (.env.local yes, .envrc no).
    """
    path_l = path.lower()
    tokens = None
    for pat in pats:
        if any(not (c.isalnum()) for c in pat):
            for seg in path_l.split("/"):
                if seg == pat or seg.startswith(pat + "."):
                    return True
        else:
            if tokens is None:
                tokens = set(re.split(r"[^a-z0-9]+", path_l))
            if pat in tokens or pat + "s" in tokens:
                return True
    return False


def large_session_tokens(payload):
    """Context size of the session's latest main-thread model call, or None.

    Reads the tail of the host transcript: Claude Code assistant records carry
    message.usage (input + cache read + cache creation = context sent); Codex
    rollouts carry event_msg/token_count with last_token_usage.input_tokens.
    File size is NOT used: transcripts keep growing after /compact.
    """
    path = payload.get("transcript_path")
    if not isinstance(path, str) or not path:
        return None
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - TRANSCRIPT_TAIL_BYTES))
            tail = fh.read().decode("utf-8", errors="replace")
    except Exception:
        return None
    for line in reversed(tail.splitlines()):
        if '"usage"' not in line and '"token_count"' not in line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if not isinstance(rec, dict):
            continue
        try:
            msg = rec.get("message")
            if rec.get("type") == "assistant" and not rec.get("isSidechain") \
                    and isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
                u = msg["usage"]
                n = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens",
                                                      "cache_creation_input_tokens"))
                if n > 0:
                    return n
            pl = rec.get("payload")
            if rec.get("type") == "event_msg" and isinstance(pl, dict) \
                    and pl.get("type") == "token_count":
                n = int(((pl.get("info") or {}).get("last_token_usage") or {})
                        .get("input_tokens") or 0)
                if n > 0:
                    return n
        except Exception:
            continue
    return None


def large_session_note(payload, session_id):
    """(marker_path, note) when the context crossed a new LARGE_SESSION_STEP, else None.

    Fires once per step per session (own marker, independent of the nudge
    signature), with or without repo changes, so a handoff is written before
    the user restarts a big session.
    """
    tokens = large_session_tokens(payload)
    if not tokens or tokens < LARGE_SESSION_STEP:
        return None
    step = tokens // LARGE_SESSION_STEP
    marker = os.path.join(session_marker_dir(session_id), "large-{}".format(step))
    if marker_seen(marker):
        return None
    note = ("handoff: this session's context is about {}k tokens. Before the user "
            "leaves or restarts, make sure a fresh session can continue from the repo "
            "alone: STATUS.md covers what is in progress, the exact next step, anything "
            "uncommitted or unverified, and decisions made only in chat; detail that "
            "won't fit goes in .handoff/handoffs/YYYY-MM-DD-topic.md. Commit those state "
            "updates under the usual rules (skip the edits if STATUS.md already does "
            "this). Then tell the user in one line that this session is large and a "
            "fresh session would continue more cheaply.").format(tokens // 1000)
    return marker, note


def main():
    payload = read_stdin_json()
    if not payload:
        return

    # Loop-breaker 1: don't act while already continuing from a stop hook.
    if payload.get("stop_hook_active"):
        sys.exit(0)

    root = project_root(payload)
    if not has_handoff(root):
        sys.exit(0)

    large = large_session_note(payload, payload.get("session_id"))
    fresh = freshness_message(root, payload.get("session_id"))
    if not large and not fresh:
        sys.exit(0)
    if large:
        marker_set(large[0])
    emit("Stop", "\n\n".join(part for part in (fresh, large and large[1]) if part))


def freshness_message(root, session_id):
    """The state-freshness / commit nudge text, or None when there is nothing new."""
    codes = git_status_codes(root)
    if codes is None:  # not a git repo / git error -> freshness nudge disabled
        return None

    # Loop-breaker 2: compare to the session baseline. If SessionStart never
    # captured one (e.g. session predates this), establish it now and stay quiet
    # this turn -- we can't tell which changes are from this session yet.
    base = load_baseline(session_id)
    if base is None:
        save_baseline(session_id, git_head(root), codes)
        return None
    base_sha, base_codes = base

    # Session-changed = local-only commits since baseline HEAD (upstream
    # commits from pull/merge don't count as this session's work) + dirty
    # paths whose status code is new or changed since baseline. Legacy
    # baselines carry code "" = "present, code unknown" — those paths are
    # pre-existing dirt and must not be counted.
    committed = git_local_commit_codes(root, base_sha) or {}
    session_changed = dict(committed)
    session_dirty = {}
    for p, c in codes.items():
        bc = base_codes.get(p)
        if bc is None:
            session_changed[p] = c
            session_dirty[p] = c
        elif bc != "" and bc != c:
            session_changed[p] = c
            session_dirty[p] = c

    new_work = [p for p in session_changed
                if not p.startswith(AGENT_DIR + os.sep)]

    # An open T3 gate must be surfaced even when the session made no changes
    # (e.g. an autonomous loop idling at the gate) — check before the
    # no-new-work exit. Everything else requires new work.
    gate = read_file(os.path.join(root, AGENT_DIR, "GATE"))
    if not new_work and not session_dirty and not gate:
        return None

    # A durable-state file counts as updated if it changed this session
    # (dirty-code change or local commit) OR is currently dirty at all — a
    # file that was already dirty at baseline and was edited again this
    # session keeps the same porcelain code, so plain dirtiness must count.
    updated = set(session_changed) | set(codes)
    status_md = os.path.normpath(os.path.join(AGENT_DIR, "STATUS.md"))
    changelog_md = os.path.normpath(os.path.join(AGENT_DIR, "CHANGELOG.md"))
    map_md = os.path.normpath(os.path.join(AGENT_DIR, "MAP.md"))

    # STATUS is the floor; CHANGELOG rides with it. Once the agent has engaged
    # with durable state, stop nagging about STATUS/CHANGELOG. All state notes
    # require new work; the GATE note alone does not.
    notes = []
    strays = []
    stray_note = None
    stale = set()
    if new_work:
        if status_md not in updated:
            notes.append("STATUS.md was not updated")
            if changelog_md not in updated:
                notes.append("CHANGELOG.md was not updated (add an entry if the change is meaningful)")

        # MAP.md: only relevant when the session's new work added/removed/renamed
        # files (structural change), not on ordinary edits.
        structural = [p for p in new_work
                      if any(ch in session_changed.get(p, "") for ch in STRUCTURAL_LETTERS)]
        if structural and map_md not in updated:
            notes.append("files were added/removed/renamed this session but MAP.md was "
                         "not updated (update it only if important files changed)")

        # STATUS bloat: it is injected every session, so size drift is a
        # per-session token tax (documented target is <=25 lines).
        status_body = read_file(os.path.join(root, status_md))
        if status_body:
            n_lines = status_body.count("\n") + 1
            if n_lines > STATUS_LINE_BUDGET:
                notes.append("STATUS.md is {} lines (target <=25) — prune it; history "
                             "belongs in CHANGELOG.md, follow-ups in tasks/".format(n_lines))

        # Sentinel paths: money/auth/data/migrations are T3 by definition. This
        # is advisory — it forces the tier question into the transcript.
        pats = sentinel_patterns(root)
        hits = sorted({p for p in new_work if sentinel_hit(p, pats)})
        if hits:
            shown = ", ".join(hits[:4]) + (" …" if len(hits) > 4 else "")
            notes.append("this session touched sentinel paths ({}) — such changes are T3 "
                         "by definition (money/auth/data/migrations): confirm the T3 gates "
                         "(approved plan, tdd, security review) were applied, or state why "
                         "this is genuinely not T3".format(shown))

        # Task files parked in tasks/ root instead of a status folder. The note
        # is SHOWN at most once per session per stray-set (they are often
        # pre-existing), but the stray-set always participates in the signature
        # so suppressing the note can't defeat the cooldown.
        strays = misfiled_tasks(root)
        if strays:
            smarker = os.path.join(session_marker_dir(session_id),
                                   "strays-" + _short("|".join(strays)))
            if not marker_seen(smarker):
                marker_set(smarker)
                shown = ", ".join(strays[:5]) + (" …" if len(strays) > 5 else "")
                stray_note = ("task file(s) sitting in tasks/ root — move into a status "
                              "folder (inbox/, now/, done/) with matching frontmatter "
                              "status: " + shown)

        for p in new_work:
            ctx = nearest_context_rel(p, root)
            if ctx and ctx not in updated:
                stale.add(ctx)

    # Open T3 gate: machine-readable stall marker (see the workflow skill).
    # Surfaced even with no new work; repeats for an unchanged situation are
    # deduped by the signature cooldown like every other note.
    if gate:
        first = gate.splitlines()[0][:200]
        notes.append("a T3 gate is OPEN (.handoff/GATE): \"{}\" — do not proceed "
                     "past it; wait for the user's ruling. Autonomous goals/loops must "
                     "idle at this gate. Delete .handoff/GATE once the user has "
                     "ruled".format(first))

    if session_dirty and not gate:
        notes.append("commit completed, verified changes within your authorized scope, "
                     "including required Handoff documentation. Respect explicit instructions not to commit; "
                     "leave unfinished or blocked work uncommitted and briefly explain why. "
                     "Stage only intended changes, preserving unrelated user work and staged changes. "
                     "Do not push. This reminder does not authorize bypassing approval gates")

    if not notes and not stray_note and not stale:
        return None

    # Loop-breaker 3: never repeat the same nudge. Signature covers what changed
    # and what we'd nag about; identical situation -> stay silent. Strays enter
    # the signature by their file list, independent of whether the note shows.
    sig = signature("|".join(sorted(set(new_work) | set(session_dirty))), "|".join(sorted(notes)),
                    "|".join(sorted(strays)), "|".join(sorted(stale)))
    if last_nudge_signature(session_id) == sig:
        return None
    set_nudge_signature(session_id, sig)
    if stray_note:
        notes.append(stray_note)

    msg = ["handoff reminder — you changed project files this session:"]
    msg += ["  - " + n for n in notes]
    msg += ["  - {} may need updating for the folder you edited".format(c) for c in sorted(stale)]
    # Uncommitted code still pending -> state goes in with that commit, so
    # amend advice only applies once all session code is committed.
    pending_code = any(not p.startswith(AGENT_DIR + os.sep) for p in session_dirty)
    amend_sha = (git_amendable_head(root, base_sha)
                 if committed and not pending_code else None)
    if amend_sha:
        commit_advice = ("HEAD ({}) is an unpushed, non-merge commit from this session: "
                         "if it is your work, `git commit --amend` the state updates "
                         "into it.".format(amend_sha))
    elif committed and not pending_code:
        commit_advice = ("HEAD can't safely be amended (pushed, a merge, or not from "
                         "this session): use a follow-up commit.")
    else:
        commit_advice = "State updates ride in the same commit as the code they describe."
    msg.append("Update durable state before wrapping up (see .handoff/BOOT.md). "
               "STATUS.md must let a fresh session continue: what is in progress, the "
               "exact next step, anything uncommitted or unverified, and decisions made "
               "only in chat — within its ~25-line target; detail that won't fit goes in .handoff/handoffs/YYYY-MM-DD-topic.md. " + commit_advice + " "
               "If no update is warranted, ignore this — it won't repeat for the same changes.")
    return "\n".join(msg)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
