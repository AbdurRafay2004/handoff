#!/usr/bin/env python3
"""SessionStart hook.

If the project has .agent-orch/  -> inject STATUS (full) + RULES (full) + a
one-line pointer to the on-demand docs (BOOT/MAP/context/tasks).

If it does NOT -> inject a one-time, self-suppressing nudge to run setup, then
write a per-repo marker so it never nags that repo again. Silent thereafter.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402
    read_stdin_json, project_root, agent_base, has_agent_orch, read_file,
    data_dir, marker_seen, marker_set, emit, _short,
)

POINTER = (
    "\n\n----- agent-orch pointer -----\n"
    "RULES + STATUS above are auto-loaded. Read on demand only when the task needs it:\n"
    "  .agent-orch/BOOT.md (session procedure + end-of-session updates),\n"
    "  .agent-orch/MAP.md, .agent-orch/context/PRODUCT.md, .agent-orch/context/TECH_STACK.md,\n"
    "  .agent-orch/tasks/ (durable backlog), .agent-orch/CHANGELOG.md, and any <dir>/CONTEXT.md.\n"
    "Update STATUS.md + CHANGELOG.md whenever code or configuration changes."
)


def main():
    payload = read_stdin_json()
    root = project_root(payload)

    if has_agent_orch(root):
        base = agent_base(root)
        parts = []
        for name in ("STATUS.md", "RULES.md"):
            body = read_file(os.path.join(base, name))
            if body:
                parts.append("===== .agent-orch/{} =====\n{}".format(name, body))
        if not parts:
            sys.exit(0)
        context = (
            "Project context auto-loaded from .agent-orch (read before acting):\n\n"
            + "\n\n".join(parts)
            + POINTER
        )
        emit("SessionStart", context)
        return

    # No .agent-orch — nudge once per repo, then stay silent forever.
    marker = os.path.join(data_dir(), "seen-" + _short(os.path.abspath(root)))
    if marker_seen(marker):
        sys.exit(0)
    marker_set(marker)
    emit(
        "SessionStart",
        "This repo has no agent-orch project memory. To enable durable STATUS, "
        "RULES, MAP, a task backlog, and folder-level CONTEXT.md, run the "
        "agent-orch setup skill (say \"set up agent-orch\" or /agent-orch:setup). "
        "This tip shows only once for this repo.",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
