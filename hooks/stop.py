#!/usr/bin/env python3
"""Stop hook (non-blocking nudge).

When a turn ends, check git for changed files. If project work changed but the
durable state wasn't updated, nudge:
  - STATUS.md / CHANGELOG.md not updated despite code/config changes.
  - A folder whose files changed has a CONTEXT.md that wasn't updated.

Pure nudge via additionalContext -- never blocks, never loops.
Only fires in repos that have .agent-orch/.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402
    read_stdin_json, project_root, has_agent_orch, emit, AGENT_DIR,
)


def changed_paths(root):
    """Return repo-relative paths of all changed/untracked files, or None on error."""
    try:
        out = subprocess.run(
            # -uall lists untracked files individually instead of collapsing
            # whole new directories to one entry (which would hide nested
            # CONTEXT.md folders and miss new files).
            ["git", "-C", root, "status", "--porcelain", "-uall"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
    except Exception:
        return None

    paths = []
    for line in out.stdout.splitlines():
        if len(line) < 4:
            continue
        entry = line[3:]
        if " -> " in entry:  # rename: "old -> new"
            entry = entry.split(" -> ", 1)[1]
        paths.append(entry.strip().strip('"'))
    return paths


def nearest_context_rel(rel_path, root):
    """Walk up a repo-relative changed file to find the nearest CONTEXT.md (repo-relative)."""
    d = os.path.dirname(rel_path)
    while True:
        candidate = os.path.join(d, "CONTEXT.md") if d else "CONTEXT.md"
        if os.path.isfile(os.path.join(root, candidate)):
            return candidate
        if not d:
            return None
        d = os.path.dirname(d)


def main():
    payload = read_stdin_json()
    root = project_root(payload)
    if not has_agent_orch(root):
        sys.exit(0)

    paths = changed_paths(root)
    if not paths:
        sys.exit(0)

    status_md = os.path.join(AGENT_DIR, "STATUS.md")
    changelog_md = os.path.join(AGENT_DIR, "CHANGELOG.md")
    changed_set = set(os.path.normpath(p) for p in paths)

    # Project work = any change outside .agent-orch/.
    work_changed = any(not p.startswith(AGENT_DIR + os.sep) for p in paths)

    notes = []
    if work_changed:
        if os.path.normpath(status_md) not in changed_set:
            notes.append("STATUS.md was not updated")
        if os.path.normpath(changelog_md) not in changed_set:
            notes.append("CHANGELOG.md was not updated (add an entry if the change is meaningful)")

    # CONTEXT.md freshness: folders with changes whose CONTEXT.md wasn't touched.
    stale_contexts = set()
    for p in paths:
        if p.startswith(AGENT_DIR + os.sep):
            continue
        ctx = nearest_context_rel(p, root)
        if ctx and os.path.normpath(ctx) not in changed_set:
            stale_contexts.add(ctx)

    if not notes and not stale_contexts:
        sys.exit(0)

    msg = ["agent-orch reminder — project files changed this turn:"]
    for n in notes:
        msg.append("  - " + n)
    for c in sorted(stale_contexts):
        msg.append("  - {} may need updating for the folder you edited".format(c))
    msg.append("Update durable state before wrapping up (see .agent-orch/BOOT.md).")
    emit("Stop", "\n".join(msg))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
