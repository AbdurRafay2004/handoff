#!/usr/bin/env python3
"""PreToolUse hook (Claude file tools and Codex apply_patch).

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


def edited_paths(payload, root):
    """Claude paths are root-relative; Codex patch paths are cwd-relative.

    Only parse apply_patch's file headers, never shell commands or hunk text.
    Include both sides of moves, and every file in a multi-file patch.
    """
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    if payload.get("tool_name") != "apply_patch":
        path = tool_input.get("file_path") or tool_input.get("notebook_path")
        return [path] if isinstance(path, str) and path else []
    patch = tool_input.get("command")
    if not isinstance(patch, str):
        return []
    lines = patch.strip().splitlines()
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        return []
    cwd = os.path.abspath(payload.get("cwd") or root)
    paths = []
    for line in lines[1:-1]:
        for prefix in ("*** Add File: ", "*** Update File: ",
                       "*** Delete File: ", "*** Move to: "):
            if line.startswith(prefix):
                path = line[len(prefix):]
                if path:
                    path = os.path.abspath(os.path.join(cwd, path))
                    if path not in paths:
                        paths.append(path)
                break
    return paths


def misfiled_task_write(file_path, root):
    """Name of a task .md about to be written to tasks/ ROOT (not a subfolder), or None."""
    try:
        root_abs = os.path.realpath(root)
        fp = file_path if os.path.isabs(file_path) else os.path.join(root_abs, file_path)
        fp = os.path.realpath(fp)
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
        root_abs = os.path.realpath(root)
        if not os.path.isabs(file_path):
            file_path = os.path.join(root_abs, file_path)
        fp = os.path.realpath(file_path)
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
    if not payload:
        return
    root = project_root(payload)
    paths = edited_paths(payload, root)
    parts = []

    # Task files belong in inbox/now/done — catch a root-level write before it
    # lands. Corrected on EVERY attempt: the injection doesn't block the write,
    # and after a /compact the earlier correction is gone from context, so a
    # once-per-session cap would let repeat writes land unchallenged.
    sdir = session_marker_dir(payload.get("session_id"))
    for file_path in paths:
        stray = misfiled_task_write(file_path, root)
        if stray:
            parts.append(
                "handoff: `{}` is being written to `.handoff/tasks/` ROOT. Task "
                "files live in a status folder — write it to `tasks/inbox/` (new), "
                "`tasks/now/` (active), or `tasks/done/` (closed) instead, with the "
                "frontmatter `status` matching the folder. Only WORKFLOW.md and "
                "TEMPLATE.md live at the tasks/ root.".format(stray)
            )
        ctx_path = nearest_context_md(file_path, root)
        if not ctx_path:
            continue
        # Once per CONTEXT.md per session, including within a multi-file patch.
        marker = os.path.join(sdir, "ctx-" + _short(os.path.abspath(ctx_path)))
        if marker_seen(marker):
            continue
        body = read_file(ctx_path)
        if not body:
            continue
        marker_set(marker)
        rel = os.path.relpath(os.path.dirname(ctx_path), os.path.abspath(root))
        parts.append(
            "Local context for `{}/` (read before editing here) — from {}:\n\n{}".format(
                rel, os.path.relpath(ctx_path, os.path.abspath(root)), body
            )
        )
    emit("PreToolUse", "\n\n".join(parts))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
