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
    marker_seen, marker_set, emit, _short,
)


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
