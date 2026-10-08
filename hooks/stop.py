#!/usr/bin/env python3
"""Stop hook (nudge to keep durable state fresh).

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

Only fires in repos that have .handoff/ and are git repos.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402
    read_stdin_json, project_root, has_handoff, emit, AGENT_DIR,
    git_status_codes, git_head, git_local_commit_codes, load_baseline,
    save_baseline, last_nudge_signature, set_nudge_signature, signature,
    read_file, session_marker_dir, marker_seen, marker_set, _short,
)

TASKS_ROOT_ALLOWED = ("WORKFLOW.md", "TEMPLATE.md")
STRUCTURAL_LETTERS = "?ADRCT"  # untracked/added/deleted/renamed/copied/typechange
STATUS_LINE_BUDGET = 40        # nudge threshold; the documented target is <=25
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

    codes = git_status_codes(root)
    if codes is None:  # not a git repo / git error -> freshness nudge disabled
        sys.exit(0)
    session_id = payload.get("session_id")

    # Loop-breaker 2: compare to the session baseline. If SessionStart never
    # captured one (e.g. session predates this), establish it now and stay quiet
    # this turn -- we can't tell which changes are from this session yet.
    base = load_baseline(session_id)
    if base is None:
        save_baseline(session_id, git_head(root), codes)
        sys.exit(0)
    base_sha, base_codes = base

    # Session-changed = local-only commits since baseline HEAD (upstream
    # commits from pull/merge don't count as this session's work) + dirty
    # paths whose status code is new or changed since baseline. Legacy
    # baselines carry code "" = "present, code unknown" — those paths are
    # pre-existing dirt and must not be counted.
    committed = git_local_commit_codes(root, base_sha) or {}
    session_changed = dict(committed)
    for p, c in codes.items():
        bc = base_codes.get(p)
        if bc is None:
            session_changed[p] = c
        elif bc != "" and bc != c:
            session_changed[p] = c

    new_work = [p for p in session_changed
                if not p.startswith(AGENT_DIR + os.sep)]

    # An open T3 gate must be surfaced even when the session made no changes
    # (e.g. an autonomous loop idling at the gate) — check before the
    # no-new-work exit. Everything else requires new work.
    gate = read_file(os.path.join(root, AGENT_DIR, "GATE"))
    if not new_work and not gate:
        sys.exit(0)

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

    if not notes and not stray_note and not stale:
        sys.exit(0)

    # Loop-breaker 3: never repeat the same nudge. Signature covers what changed
    # and what we'd nag about; identical situation -> stay silent. Strays enter
    # the signature by their file list, independent of whether the note shows.
    sig = signature("|".join(sorted(new_work)), "|".join(sorted(notes)),
                    "|".join(sorted(strays)), "|".join(sorted(stale)))
    if last_nudge_signature(session_id) == sig:
        sys.exit(0)
    set_nudge_signature(session_id, sig)
    if stray_note:
        notes.append(stray_note)

    msg = ["handoff reminder — you changed project files this session:"]
    msg += ["  - " + n for n in notes]
    msg += ["  - {} may need updating for the folder you edited".format(c) for c in sorted(stale)]
    msg.append("Update durable state before wrapping up (see .handoff/BOOT.md). "
               "State updates ride in the SAME commit as the code they describe — "
               "if you already committed, haven't pushed, AND the last commit is your "
               "own work from this session (not a merge or someone else's), "
               "`git commit --amend` the doc updates in; otherwise a follow-up commit "
               "is acceptable. "
               "If no update is warranted, you can ignore this — it won't repeat for the same changes.")
    emit("Stop", "\n".join(msg))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
