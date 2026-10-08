#!/usr/bin/env python3
"""Smoke tests for the handoff hooks.

Each hook is executed as Claude Code and Codex run it: a JSON payload on stdin,
JSON (or silence) on stdout, exit 0 always. Tests build throwaway git fixture
repos and assert the documented behaviors, including the fail-safe invariants.

Run: python3 tests/test_hooks.py   (stdlib only, no framework)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks")
FAILURES = []
CHECKS = 0
TEST_ROOT = tempfile.TemporaryDirectory(prefix="handoff-tests-")


def hook_env(overrides=None):
    """Isolate fixtures from installed plugin settings and persistent markers."""
    env = dict(os.environ)
    for key in ("CLAUDE_PROJECT_DIR", "CLAUDE_PLUGIN_DATA", "PLUGIN_DATA"):
        env.pop(key, None)
    env.update({"TMPDIR": TEST_ROOT.name,
                "PLUGIN_DATA": os.path.join(TEST_ROOT.name, "data")})
    env.update(overrides or {})
    return env


def run_hook(name, payload, env=None):
    """Pipe a payload through a hook; return (stdout, exit_code)."""
    proc = subprocess.run(
        [sys.executable, os.path.join(HOOKS, name)],
        input=json.dumps(payload), capture_output=True, text=True, timeout=30,
        env=hook_env(env),
    )
    return proc.stdout.strip(), proc.returncode


def context_of(stdout):
    """Extract context or a Stop continuation reason, or None if silent."""
    if not stdout:
        return None
    result = json.loads(stdout)
    return result.get("reason") or result["hookSpecificOutput"]["additionalContext"]


def check(label, cond):
    global CHECKS
    CHECKS += 1
    print(("PASS  " if cond else "FAIL  ") + label)
    if not cond:
        FAILURES.append(label)


def make_repo(with_handoff=True):
    root = tempfile.mkdtemp(prefix="repo-", dir=TEST_ROOT.name)
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


def codex_edge_checks(repo):
    def patch_hook(patch, session=None, cwd=None, env=None):
        return run_hook("pre_edit_context.py", {
            "cwd": cwd or repo, "session_id": session or sid(),
            "tool_name": "apply_patch", "tool_input": {"command": patch},
        }, env=env)

    for action in ("Add", "Update", "Delete"):
        patch = "*** Begin Patch\n*** {} File: src/file with spaces.py\n*** End Patch".format(action)
        out, code = patch_hook(patch)
        check("codex: {} header supports spaces".format(action), code == 0
              and "folder context here" in (context_of(out) or ""))

    os.makedirs(os.path.join(repo, "lib"))
    with open(os.path.join(repo, "lib", "CONTEXT.md"), "w") as fh:
        fh.write("destination folder context")
    patch = ("*** Begin Patch\n*** Update File: src/old.py\n"
             "*** Move to: lib/new.py\n@@\n-old\n+new\n"
             "*** Add File: src/second.py\n+pass\n"
             "*** Add File: .handoff/tasks/misfiled.md\n+task\n*** End Patch")
    session = sid()
    out, code = patch_hook(patch, session)
    ctx = context_of(out) or ""
    check("codex: multi-file move loads source and destination once", code == 0
          and ctx.count("folder context here") == 1
          and ctx.count("destination folder context") == 1)
    check("codex: task warning does not hide other patch contexts", "tasks/inbox/" in ctx)
    out, _ = patch_hook(patch, session)
    check("codex: repeated patch repeats task correction but not contexts",
          "tasks/inbox/" in (context_of(out) or "")
          and "folder context here" not in out and "destination folder context" not in out)

    # Outside paths cannot consume the valid context's per-session marker.
    outside = tempfile.mkdtemp(prefix="outside-", dir=TEST_ROOT.name)
    with open(os.path.join(outside, "CONTEXT.md"), "w") as fh:
        fh.write("OUTSIDE MUST NOT LOAD")
    os.symlink(outside, os.path.join(repo, "escape"))
    patch = ("*** Begin Patch\n*** Add File: " + os.path.join(outside, "new.py")
             + "\n*** Add File: ../" + os.path.basename(outside)
             + "/other.py\n*** Add File: escape/symlink.py\n*** End Patch")
    out, code = patch_hook(patch)
    check("codex: absolute, traversal, and symlink escapes ignored", code == 0 and out == "")
    out, code = patch_hook("*** Begin Patch\n*** Add File: " + repo + "\n*** End Patch")
    check("codex: project root is not treated as a file", code == 0 and out == "")
    for patch in ("not a patch", "*** Begin Patch\n*** Add File: src/a.py", ""):
        out, code = patch_hook(patch)
        check("codex: incomplete/non-patch input stays silent", code == 0 and out == "")
    out, code = run_hook("pre_edit_context.py", {
        "cwd": repo, "session_id": sid(), "tool_name": "Bash",
        "tool_input": {"command": "*** Begin Patch\n*** Add File: src/a.py\n*** End Patch"},
    })
    check("codex: shell text is never parsed as a patch", code == 0 and out == "")

    # Git is the boundary: nested repos don't inherit a parent's handoff.
    nested = os.path.join(repo, "nested")
    subprocess.run(["git", "init", "-q", nested], check=True)
    out, code = run_hook("sessionstart.py", {"cwd": nested, "session_id": sid()})
    check("codex: nested repo does not load parent memory", code == 0
          and "status body" not in out and "no handoff project memory" in out)

    # Linked worktrees use a .git file rather than a .git directory.
    worktree = os.path.join(TEST_ROOT.name, "linked-worktree")
    subprocess.run(["git", "-C", repo, "worktree", "add", "--detach", "-q", worktree], check=True)
    os.makedirs(os.path.join(worktree, "deep"))
    out, code = run_hook("sessionstart.py", {"cwd": os.path.join(worktree, "deep"), "session_id": sid()})
    check("codex: worktree subfolder discovers its own memory", code == 0
          and "status body" in (context_of(out) or ""))

    # Codex-native data dir wins over the backwards-compatible alias.
    native = os.path.join(TEST_ROOT.name, "native-data")
    legacy = os.path.join(TEST_ROOT.name, "legacy-data")
    bare = make_repo(with_handoff=False)
    out, _ = run_hook("sessionstart.py", {"cwd": bare, "session_id": sid()},
                      env={"PLUGIN_DATA": native, "CLAUDE_PLUGIN_DATA": legacy})
    check("codex: persistent tip uses PLUGIN_DATA", bool(out)
          and os.path.isdir(native) and not os.path.exists(legacy))
    out, _ = run_hook("sessionstart.py", {"cwd": bare, "session_id": sid()},
                      env={"PLUGIN_DATA": native})
    check("codex: setup tip stays once per repo", out == "")

    # Claude's explicit root still wins; its file paths remain root-relative.
    out, code = run_hook("pre_edit_context.py", {
        "cwd": outside, "session_id": sid(), "tool_input": {"file_path": "src/file.py"},
    }, env={"CLAUDE_PROJECT_DIR": repo})
    check("claude: explicit root and relative file tools preserved", code == 0
          and "folder context here" in (context_of(out) or ""))
    out, code = run_hook("pre_edit_context.py", {
        "cwd": repo, "session_id": sid(), "tool_input": {"notebook_path": "src/file.ipynb"},
    })
    check("claude: notebook context preserved", code == 0
          and "folder context here" in (context_of(out) or ""))


def packaging_checks():
    root = os.path.dirname(os.path.abspath(HOOKS))
    with open(os.path.join(root, ".claude-plugin", "plugin.json")) as fh:
        claude = json.load(fh)
    with open(os.path.join(root, ".codex-plugin", "plugin.json")) as fh:
        codex = json.load(fh)
    with open(os.path.join(root, ".claude-plugin", "marketplace.json")) as fh:
        entry = json.load(fh)["plugins"][0]
    check("packaging: versions agree across both hosts and marketplace",
          claude["version"] == codex["version"] == entry["version"])
    check("packaging: both hosts use shared skills and default hook discovery",
          claude["skills"] == codex["skills"] == "./skills/"
          and "hooks" not in claude and "hooks" not in codex)
    with open(os.path.join(HOOKS, "hooks.json")) as fh:
        config = json.load(fh)["hooks"]
    matcher = config["PreToolUse"][0]["matcher"]
    check("packaging: matcher covers both hosts' file tools",
          all(re.search(matcher, tool) for tool in
              ("Edit", "Write", "MultiEdit", "NotebookEdit", "apply_patch"))
          and not re.search(matcher, "Bash"))
    # Execute the registered command, with spaces in the installed root path.
    installed = os.path.join(TEST_ROOT.name, "plugin with spaces")
    shutil.copytree(HOOKS, os.path.join(installed, "hooks"))
    for event, name in (("SessionStart", "sessionstart.py"),
                        ("PreToolUse", "pre_edit_context.py"), ("Stop", "stop.py")):
        command = config[event][0]["hooks"][0]["command"]
        proc = subprocess.run(command, shell=True, input="{}", text=True,
                              capture_output=True, timeout=30,
                              env=hook_env({"CLAUDE_PLUGIN_ROOT": installed,
                                            "PLUGIN_ROOT": installed}))
        check("packaging: {} command resolves a spaced plugin path".format(name),
              proc.returncode == 0 and proc.stdout == "" and proc.stderr == "")


def stop_contract_checks():
    repo = make_repo()
    os.makedirs(os.path.join(repo, "subfolder"))
    session = sid()
    payload = {"cwd": os.path.join(repo, "subfolder"), "session_id": session,
               "hook_event_name": "Stop", "turn_id": "turn-1", "stop_hook_active": False}
    run_hook("sessionstart.py", dict(payload, source="startup"))
    with open(os.path.join(repo, ".handoff", "GATE"), "w") as fh:
        fh.write("T3 plan approval: waiting for the user's ruling\n")
    out, code = run_hook("stop.py", payload)
    result = json.loads(out) if out else {}
    check("stop: open gate continues once even with no code changes", code == 0
          and result.get("decision") == "block" and "gate is OPEN" in result.get("reason", ""))
    out, code = run_hook("stop.py", payload)
    check("stop: unchanged gate has a cooldown", code == 0 and out == "")
    os.remove(os.path.join(repo, ".handoff", "GATE"))

    with open(os.path.join(repo, "app.py"), "w") as fh:
        fh.write("pass\n")
    subprocess.run(["git", "-C", repo, "add", "app.py"], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-qm", "session work"], check=True)
    out, code = run_hook("stop.py", payload)
    check("stop: committed session work still continues from subfolder", code == 0
          and "STATUS.md was not updated" in (context_of(out) or ""))
    for name in ("STATUS.md", "CHANGELOG.md", "MAP.md"):
        with open(os.path.join(repo, ".handoff", name), "w") as fh:
            fh.write("state updated for new app.py\n")
    out, code = run_hook("stop.py", payload)
    check("stop: updating required durable state ends the reminder", code == 0 and out == "")
    out, code = run_hook("stop.py", dict(payload, session_id=sid()))
    check("stop: absent baseline stays silent", code == 0 and out == "")


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

    # Codex's documented apply_patch input carries the patch in command.
    patch = "*** Begin Patch\n*** Add File: src/new.py\n+pass\n*** End Patch"
    out, code = run_hook("pre_edit_context.py", {
        "cwd": repo, "session_id": sid(), "tool_name": "apply_patch",
        "tool_input": {"command": patch},
    })
    check("codex: patch injects nearest context", code == 0
          and "folder context here" in (context_of(out) or ""))
    check("codex: patch never changes permissions", "permissionDecision" not in out)

    # cwd may be a subfolder; memory lives at git root, patch paths use cwd.
    out, code = run_hook("sessionstart.py", {
        "cwd": os.path.join(repo, "src"), "session_id": sid(), "source": "startup",
    })
    check("codex: subfolder session loads repo memory", code == 0
          and "status body" in (context_of(out) or ""))
    out, code = run_hook("pre_edit_context.py", {
        "cwd": os.path.join(repo, "src"), "session_id": sid(),
        "tool_name": "apply_patch",
        "tool_input": {"command": "*** Begin Patch\n*** Update File: app.py\n@@\n-old\n+new\n*** End Patch"},
    })
    check("codex: relative patch paths resolve against cwd", code == 0
          and "folder context here" in (context_of(out) or ""))

    out, code = run_hook("pre_edit_context.py", {
        "cwd": repo, "session_id": sid(), "tool_name": "apply_patch",
        "tool_input": {"command": "*** Begin Patch\n*** Add File: .handoff/tasks/oops.md\n+task\n*** End Patch"},
    })
    check("codex: patch warns on task at tasks root", code == 0
          and "tasks/inbox/" in (context_of(out) or ""))

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
    stop_result = json.loads(out)
    check("stop: uses supported continuation schema for both hosts",
          stop_result.get("decision") == "block"
          and isinstance(stop_result.get("reason"), str)
          and "hookSpecificOutput" not in stop_result)

    out, _ = run_hook("stop.py", {"cwd": repo, "session_id": s,
                                  "stop_hook_active": False})
    check("stop: signature cooldown suppresses repeat nudge", out == "")

    out, code = run_hook("stop.py", {"cwd": repo, "session_id": s,
                                     "stop_hook_active": True})
    check("stop: stop_hook_active guard stays silent", out == "" and code == 0)

    codex_edge_checks(repo)
    packaging_checks()
    stop_contract_checks()

    # --- fail-safe invariant: malformed input never crashes any hook ---
    for name in ("sessionstart.py", "pre_edit_context.py", "stop.py"):
        for raw in ("not json{{{", "[]", "null", "42", '"text"', "{}"):
            proc = subprocess.run([sys.executable, os.path.join(HOOKS, name)],
                                  input=raw, capture_output=True, env=hook_env(),
                                  text=True, timeout=30)
            check("{}: malformed/empty payload is silent ({})".format(name, raw),
                  proc.returncode == 0 and proc.stdout == "" and proc.stderr == "")

    shutil.rmtree(repo, ignore_errors=True)
    shutil.rmtree(bare, ignore_errors=True)

    print("\n{} checks, {} failed".format(CHECKS, len(FAILURES)))
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
