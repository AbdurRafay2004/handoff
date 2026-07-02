#!/usr/bin/env python3
"""PreToolUse hook (Edit/Write/MultiEdit/NotebookEdit).

When the file about to be edited lives inside (or under) a folder that has a
CONTEXT.md, inject that nearest CONTEXT.md so the agent reads local architecture
BEFORE editing there. De-duplicated to once per CONTEXT.md per session.

Injects additionalContext ONLY -- no permissionDecision -- so it never alters
the normal edit-permission flow (no silent auto-approve).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402
    read_stdin_json, project_root, read_file, session_marker_dir,
    marker_seen, marker_set, emit, _short, AGENT_DIR,
)

TASKS_ROOT_ALLOWED = ("WORKFLOW.md", "TEMPLATE.md")


def misfiled_task_write(file_path, root):
    """Name of a task .md about to be written to tasks/ ROOT (not a subfolder), or None."""
    try:
        root_abs = os.path.abspath(root)
        fp = file_path if os.path.isabs(file_path) else os.path.join(root_abs, file_path)
        fp = os.path.abspath(fp)
        tasks_root = os.path.normpath(os.path.join(root_abs, AGENT_DIR, "tasks"))
        if os.path.normpath(os.path.dirname(fp)) != tasks_root:
            return None
        name = os.path.basename(fp)
        if name.endswith(".md") and name not in TASKS_ROOT_ALLOWED:
            return name
    except Exception:
        return None
    return None


def nearest_context_md(file_path, root):
    """Walk up from the edited file's dir to root; return path of nearest CONTEXT.md.

    Only acts on files inside the project root; a relative file_path is resolved
    against the root (not the hook's cwd).
    """
    try:
        root_abs = os.path.abspath(root)
        if not os.path.isabs(file_path):
            file_path = os.path.join(root_abs, file_path)
        fp = os.path.abspath(file_path)
        # Ignore edits outside the project root (e.g. /tmp, $HOME).
        try:
            if os.path.commonpath([fp, root_abs]) != root_abs:
                return None
        except ValueError:  # different drives (Windows) -> not in project
            return None
        # A path equal to the root itself has no parent inside the project —
        # without this guard the walk would start at the root's PARENT and
        # read a CONTEXT.md from outside the repo.
        if os.path.normpath(fp) == os.path.normpath(root_abs):
            return None
        d = os.path.dirname(fp)
        # Stay within the project root.
        while True:
            candidate = os.path.join(d, "CONTEXT.md")
            if os.path.isfile(candidate):
                return candidate
            if os.path.normpath(d) == os.path.normpath(root_abs):
                return None
            parent = os.path.dirname(d)
            if parent == d:  # reached filesystem root
                return None
            d = parent
    except Exception:
        return None


def main():
    payload = read_stdin_json()
    root = project_root(payload)
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not file_path:
        sys.exit(0)

    # Task files belong in inbox/now/done — catch a root-level write before it
    # lands. Corrected at most once per file per session (repeat writes to the
    # same stray already got the message).
    stray = misfiled_task_write(file_path, root)
    if stray:
        sdir = session_marker_dir(payload.get("session_id"))
        tmarker = os.path.join(sdir, "taskroot-" + _short(stray))
        if marker_seen(tmarker):
            sys.exit(0)
        marker_set(tmarker)
        emit(
            "PreToolUse",
            "agent-orch: `{}` is being written to `.agent-orch/tasks/` ROOT. Task "
            "files live in a status folder — write it to `tasks/inbox/` (new), "
            "`tasks/now/` (active), or `tasks/done/` (closed) instead, with the "
            "frontmatter `status` matching the folder. Only WORKFLOW.md and "
            "TEMPLATE.md live at the tasks/ root.".format(stray),
        )
        return

    ctx_path = nearest_context_md(file_path, root)
    if not ctx_path:
        sys.exit(0)

    # Once per CONTEXT.md per session.
    sdir = session_marker_dir(payload.get("session_id"))
    marker = os.path.join(sdir, "ctx-" + _short(os.path.abspath(ctx_path)))
    if marker_seen(marker):
        sys.exit(0)

    body = read_file(ctx_path)
    if not body:
        sys.exit(0)
    marker_set(marker)

    rel = os.path.relpath(os.path.dirname(ctx_path), os.path.abspath(root))
    emit(
        "PreToolUse",
        "Local context for `{}/` (read before editing here) — from {}:\n\n{}".format(
            rel, os.path.relpath(ctx_path, os.path.abspath(root)), body
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
