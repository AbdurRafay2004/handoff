#!/usr/bin/env python3
"""Stop hook (nudge to keep durable state fresh).

Nudges when the agent made NEW repo changes this session but didn't update
STATUS / CHANGELOG, or left a folder's CONTEXT.md stale.

Three independent loop-breakers so it can never run away (the failure that
prompted this design):
  1. stop_hook_active  -> if we're already in a stop-triggered continuation, exit.
  2. session baseline  -> only consider changes NEW since SessionStart captured
                          the baseline, so pre-existing uncommitted dirt is ignored.
  3. nudge signature   -> never nudge twice for the same unresolved situation,
                          even if (1) doesn't fire for additionalContext continuations.

Only fires in repos that have .agent-orch/ and are git repos.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402
    read_stdin_json, project_root, has_agent_orch, emit, AGENT_DIR,
    git_status_codes, load_baseline, save_baseline,
    last_nudge_signature, set_nudge_signature, signature,
)

TASKS_ROOT_ALLOWED = ("WORKFLOW.md", "TEMPLATE.md")


def misfiled_tasks(root):
    """Task .md files sitting in tasks/ root instead of inbox|now|done; [] on error."""
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


def main():
    payload = read_stdin_json()

    # Loop-breaker 1: don't act while already continuing from a stop hook.
    if payload.get("stop_hook_active"):
        sys.exit(0)

    root = project_root(payload)
    if not has_agent_orch(root):
        sys.exit(0)

    codes = git_status_codes(root)
    if codes is None:  # not a git repo / git error -> freshness nudge disabled
        sys.exit(0)
    current_set = set(codes)
    session_id = payload.get("session_id")

    # Loop-breaker 2: compare to the session baseline. If SessionStart never
    # captured one (e.g. session predates this), establish it now and stay quiet
    # this turn -- we can't tell which changes are from this session yet.
    baseline = load_baseline(session_id)
    if baseline is None:
        save_baseline(session_id, current_set)
        sys.exit(0)

    new_changes = current_set - baseline
    new_work = [p for p in new_changes if not p.startswith(AGENT_DIR + os.sep)]
    if not new_work:
        sys.exit(0)

    status_md = os.path.normpath(os.path.join(AGENT_DIR, "STATUS.md"))
    changelog_md = os.path.normpath(os.path.join(AGENT_DIR, "CHANGELOG.md"))

    # STATUS is the floor; CHANGELOG rides with it. Once the agent has engaged
    # with durable state (STATUS is dirty), stop nagging about STATUS/CHANGELOG.
    notes = []
    if status_md not in current_set:
        notes.append("STATUS.md was not updated")
        if changelog_md not in current_set:
            notes.append("CHANGELOG.md was not updated (add an entry if the change is meaningful)")

    # MAP.md: only relevant when the session's new work added/removed/renamed
    # files (structural change), not on ordinary edits.
    map_md = os.path.normpath(os.path.join(AGENT_DIR, "MAP.md"))
    structural = [
        p for p in new_work
        if any(c in codes.get(p, "") for c in ("?", "A", "D", "R"))
    ]
    if structural and map_md not in current_set:
        notes.append("files were added/removed/renamed this session but MAP.md was "
                     "not updated (update it only if important files changed)")

    # Task files parked in tasks/ root instead of inbox|now|done.
    strays = misfiled_tasks(root)
    if strays:
        shown = ", ".join(strays[:5]) + (" …" if len(strays) > 5 else "")
        notes.append("task file(s) sitting in tasks/ root — move into inbox/, now/, "
                     "or done/ with matching frontmatter status: " + shown)

    stale = set()
    for p in new_work:
        ctx = nearest_context_rel(p, root)
        if ctx and ctx not in current_set:
            stale.add(ctx)

    if not notes and not stale:
        sys.exit(0)

    # Loop-breaker 3: never repeat the same nudge. Signature covers what changed
    # and what we'd nag about; identical situation -> stay silent.
    sig = signature("|".join(sorted(new_work)), "|".join(sorted(notes)), "|".join(sorted(stale)))
    if last_nudge_signature(session_id) == sig:
        sys.exit(0)
    set_nudge_signature(session_id, sig)

    msg = ["agent-orch reminder — you changed project files this session:"]
    msg += ["  - " + n for n in notes]
    msg += ["  - {} may need updating for the folder you edited".format(c) for c in sorted(stale)]
    msg.append("Update durable state before wrapping up (see .agent-orch/BOOT.md). "
               "State updates ride in the SAME commit as the code they describe — "
               "if you already committed and haven't pushed, `git commit --amend` "
               "the doc updates in rather than adding a docs-only commit. "
               "If no update is warranted, you can ignore this — it won't repeat for the same changes.")
    emit("Stop", "\n".join(msg))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
