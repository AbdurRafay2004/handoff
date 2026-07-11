#!/usr/bin/env python3
"""Smoke tests for the handoff hooks.

Each hook is executed exactly as Claude Code runs it: a JSON payload on stdin,
JSON (or silence) on stdout, exit 0 always. Tests build throwaway git fixture
repos and assert the documented behaviors, including the fail-safe invariants.

Run: python3 tests/test_hooks.py   (stdlib only, no framework)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks")
FAILURES = []


def run_hook(name, payload):
    """Pipe a payload through a hook; return (stdout, exit_code)."""
    proc = subprocess.run(
        [sys.executable, os.path.join(HOOKS, name)],
        input=json.dumps(payload), capture_output=True, text=True, timeout=30,
    )
    return proc.stdout.strip(), proc.returncode


def context_of(stdout):
    """Extract additionalContext from hook output, or None if silent."""
    if not stdout:
        return None
    return json.loads(stdout)["hookSpecificOutput"]["additionalContext"]


def check(label, cond):
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        FAILURES.append(label)


def make_repo(with_handoff=True):
    root = tempfile.mkdtemp(prefix="handoff-ci-")
    subprocess.run(["git", "init", "-q", root], check=True)
    subprocess.run(["git", "-C", root, "config", "user.email", "ci@test"], check=True)
    subprocess.run(["git", "-C", root, "config", "user.name", "ci"], check=True)
    if with_handoff:
        os.makedirs(os.path.join(root, ".handoff"))
        with open(os.path.join(root, ".handoff", "STATUS.md"), "w") as fh:
            fh.write("status body")
        with open(os.path.join(root, ".handoff", "RULES.md"), "w") as fh:
            fh.write("rules body")
        # Commit the scaffold so it reads as pre-existing clean state — an
        # uncommitted STATUS.md counts as "already updated" to the Stop hook.
        subprocess.run(["git", "-C", root, "add", ".handoff"], check=True)
        subprocess.run(["git", "-C", root, "commit", "-qm", "scaffold"], check=True)
    return root


def sid():
    return "ci-" + uuid.uuid4().hex[:8]


def main():
    repo = make_repo()
    bare = make_repo(with_handoff=False)

    # --- sessionstart ---
    out, code = run_hook("sessionstart.py", {"cwd": repo, "session_id": sid()})
    ctx = context_of(out)
    check("sessionstart: exit 0 with .handoff/", code == 0)
    check("sessionstart: injects STATUS + RULES", ctx is not None
          and "status body" in ctx and "rules body" in ctx)

    out, code = run_hook("sessionstart.py", {"cwd": bare, "session_id": sid()})
    check("sessionstart: exit 0 without .handoff/", code == 0)

    # --- pre_edit_context ---
    os.makedirs(os.path.join(repo, "src"))
    with open(os.path.join(repo, "src", "CONTEXT.md"), "w") as fh:
        fh.write("folder context here")
    s = sid()
    out, code = run_hook("pre_edit_context.py", {
        "cwd": repo, "session_id": s,
        "tool_input": {"file_path": os.path.join(repo, "src", "foo.ts")},
    })
    ctx = context_of(out)
    check("pre_edit: exit 0", code == 0)
    check("pre_edit: injects nearest CONTEXT.md",
          ctx is not None and "folder context here" in ctx)
    check("pre_edit: never emits a permissionDecision",
          "permissionDecision" not in out)

    out, _ = run_hook("pre_edit_context.py", {
        "cwd": repo, "session_id": s,
        "tool_input": {"file_path": os.path.join(repo, "src", "bar.ts")},
    })
    check("pre_edit: same CONTEXT.md injected once per session", out == "")

    out, code = run_hook("pre_edit_context.py", {
        "cwd": repo, "session_id": s,
        "tool_input": {"file_path": "/etc/passwd"},
    })
    check("pre_edit: ignores edits outside project root", out == "" and code == 0)

    # --- stop ---
    s = sid()
    run_hook("sessionstart.py", {"cwd": repo, "session_id": s})  # baseline
    out, code = run_hook("stop.py", {"cwd": repo, "session_id": s,
                                     "stop_hook_active": False})
    check("stop: silent when session made no changes", out == "" and code == 0)

    with open(os.path.join(repo, "src", "app.py"), "w") as fh:
        fh.write("print('new work')\n")
    out, code = run_hook("stop.py", {"cwd": repo, "session_id": s,
                                     "stop_hook_active": False})
    ctx = context_of(out)
    check("stop: nudges on new code without state update",
          code == 0 and ctx is not None and "STATUS" in ctx)

    out, _ = run_hook("stop.py", {"cwd": repo, "session_id": s,
                                  "stop_hook_active": False})
    check("stop: signature cooldown suppresses repeat nudge", out == "")

    out, code = run_hook("stop.py", {"cwd": repo, "session_id": s,
                                     "stop_hook_active": True})
    check("stop: stop_hook_active guard stays silent", out == "" and code == 0)

    # --- fail-safe invariant: malformed input never crashes any hook ---
    for name in ("sessionstart.py", "pre_edit_context.py", "stop.py"):
        proc = subprocess.run([sys.executable, os.path.join(HOOKS, name)],
                              input="not json{{{", capture_output=True,
                              text=True, timeout=30)
        check("{}: exit 0 on garbage stdin".format(name), proc.returncode == 0)

    shutil.rmtree(repo, ignore_errors=True)
    shutil.rmtree(bare, ignore_errors=True)

    print("\n{} checks, {} failed".format(
        len(FAILURES) and "some" or "all", len(FAILURES)))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
