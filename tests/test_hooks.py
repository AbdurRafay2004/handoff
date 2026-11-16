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
    lint = os.path.join(root, "skills", "setup", "..", "..", "scripts", "handoff_lint.py")
    check("packaging: setup skill's relative lint path resolves", os.path.isfile(lint))
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



def commit_reminder_checks():
    for mode in ("unstaged", "staged", "untracked", "handoff-only"):
        repo = make_repo()
        app = os.path.join(repo, "app.py")
        with open(app, "w") as fh:
            fh.write("original\n")
        subprocess.run(["git", "-C", repo, "add", "app.py"], check=True)
        subprocess.run(["git", "-C", repo, "commit", "-qm", "baseline"], check=True)
        # Unrelated user work must remain untouched and must not trigger alone.
        with open(os.path.join(repo, "user.txt"), "w") as fh:
            fh.write("user work\n")
        payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
        run_hook("sessionstart.py", payload)
        out, code = run_hook("stop.py", payload)
        check("commit: pre-existing dirt stays silent (" + mode + ")", code == 0 and not out)
        target = (os.path.join(repo, ".handoff", "RULES.md") if mode == "handoff-only"
                  else os.path.join(repo, "new.py") if mode == "untracked" else app)
        with open(target, "a") as fh:
            fh.write("session work\n")
        for name in ("STATUS.md", "CHANGELOG.md", "MAP.md"):
            with open(os.path.join(repo, ".handoff", name), "w") as fh:
                fh.write("updated state\n")
        if mode == "staged":
            subprocess.run(["git", "-C", repo, "add", "app.py"], check=True)
        before = subprocess.check_output(["git", "-C", repo, "status", "--porcelain"])
        head = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"])
        out, code = run_hook("stop.py", payload)
        reason = context_of(out) or ""
        check("commit: reminds after docs updated (" + mode + ")", code == 0
              and "commit completed, verified changes" in reason
              and "explicit instructions not to commit" in reason
              and "unrelated" in reason and "Do not push" in reason)
        check("commit: hook never stages or commits (" + mode + ")",
              before == subprocess.check_output(["git", "-C", repo, "status", "--porcelain"])
              and head == subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"]))
        out, code = run_hook("stop.py", payload)
        check("commit: unchanged reminder does not repeat (" + mode + ")", code == 0 and not out)
        out, code = run_hook("stop.py", dict(payload, stop_hook_active=True))
        check("commit: continuation guard remains silent (" + mode + ")", code == 0 and not out)
        with open(os.path.join(repo, ".handoff", "GATE"), "w") as fh:
            fh.write("Awaiting approval\n")
        out, code = run_hook("stop.py", payload)
        reason = context_of(out) or ""
        check("commit: open gate takes priority (" + mode + ")", code == 0
              and "gate is OPEN" in reason and "commit completed, verified changes" not in reason)
        os.remove(os.path.join(repo, ".handoff", "GATE"))
        subprocess.run(["git", "-C", repo, "add", "app.py", ".handoff"], check=True)
        if mode == "untracked":
            subprocess.run(["git", "-C", repo, "add", "new.py"], check=True)
        subprocess.run(["git", "-C", repo, "commit", "-qm", "completed work"], check=True)
        out, code = run_hook("stop.py", payload)
        check("commit: unrelated dirt after commit stays silent (" + mode + ")", code == 0 and not out)
        os.remove(os.path.join(repo, "user.txt"))
        out, code = run_hook("stop.py", payload)
        check("commit: clean tree stays silent (" + mode + ")", code == 0 and not out)

def git(repo, *args):
    subprocess.run(["git", "-C", repo] + list(args), check=True,
                   capture_output=True)


def write(repo, rel, text="pass\n"):
    with open(os.path.join(repo, rel), "w") as fh:
        fh.write(text)


def stop_message_checks():
    # Unpushed, non-merge session commit at HEAD -> amend is suggested, and the
    # handoff wording is present.
    repo = make_repo()
    payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
    run_hook("sessionstart.py", dict(payload, source="startup"))
    write(repo, "app.py")
    git(repo, "add", "app.py")
    git(repo, "commit", "-qm", "session work")
    ctx = context_of(run_hook("stop.py", payload)[0]) or ""
    check("stop msg: handoff wording present", "fresh session" in ctx
          and "exact next step" in ctx and "decisions made only in chat" in ctx)
    check("stop msg: amend suggested for unpushed session commit",
          "git commit --amend" in ctx)

    # Session commit plus still-uncommitted code -> state rides with that code.
    write(repo, "more.py")
    ctx = context_of(run_hook("stop.py", payload)[0]) or ""
    check("stop msg: pending code beats amend advice",
          "same commit" in ctx and "--amend" not in ctx)

    # Pushed HEAD -> no amend advice.
    repo = make_repo()
    remote = tempfile.mkdtemp(prefix="remote-", dir=TEST_ROOT.name)
    git(remote, "init", "-q", "--bare")
    git(repo, "remote", "add", "origin", remote)
    payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
    run_hook("sessionstart.py", dict(payload, source="startup"))
    write(repo, "app.py")
    git(repo, "add", "app.py")
    git(repo, "commit", "-qm", "session work")
    git(repo, "push", "-q", "origin", "HEAD")
    write(repo, os.path.join(".handoff", "STATUS.md"), "state after push\n")
    ctx = context_of(run_hook("stop.py", payload)[0]) or ""
    check("stop msg: pushed HEAD is not amended", "commit completed" in ctx
          and "--amend" not in ctx)

    # No session commits -> state rides in the next commit, no amend advice.
    repo = make_repo()
    payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
    run_hook("sessionstart.py", dict(payload, source="startup"))
    write(repo, "app.py")
    ctx = context_of(run_hook("stop.py", payload)[0]) or ""
    check("stop msg: uncommitted work gets same-commit advice, no amend",
          "same commit" in ctx and "--amend" not in ctx)

    # Merge commit at HEAD -> never suggest amending it.
    repo = make_repo()
    main_branch = subprocess.run(["git", "-C", repo, "rev-parse", "--abbrev-ref", "HEAD"],
                                 capture_output=True, text=True).stdout.strip()
    payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
    run_hook("sessionstart.py", dict(payload, source="startup"))
    git(repo, "checkout", "-qb", "feature")
    write(repo, "feature.py")
    git(repo, "add", "feature.py")
    git(repo, "commit", "-qm", "feature")
    git(repo, "checkout", "-q", main_branch)
    write(repo, "app.py")
    git(repo, "add", "app.py")
    git(repo, "commit", "-qm", "main work")
    git(repo, "merge", "-q", "--no-ff", "-m", "merge feature", "feature")
    ctx = context_of(run_hook("stop.py", payload)[0]) or ""
    check("stop msg: merge commit at HEAD is not amended",
          "STATUS.md was not updated" in ctx and "--amend" not in ctx
          and "follow-up commit" in ctx)

    # resume/compact keep the session baseline; startup/clear re-capture it.
    for source, keeps in (("resume", True), ("compact", True),
                          ("startup", False), ("clear", False)):
        repo = make_repo()
        payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
        run_hook("sessionstart.py", dict(payload, source="startup"))
        write(repo, "app.py")
        run_hook("sessionstart.py", dict(payload, source=source))
        out, code = run_hook("stop.py", payload)
        nudged = "STATUS.md was not updated" in (context_of(out) or "")
        check("baseline: {} {} earlier session work".format(
            source, "keeps" if keeps else "re-captures"), code == 0 and nudged == keeps)

    # A resume with no stored baseline (e.g. tmp was wiped) still captures one.
    repo = make_repo()
    payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
    run_hook("sessionstart.py", dict(payload, source="resume"))
    write(repo, "app.py")
    out, code = run_hook("stop.py", payload)
    check("baseline: resume without a stored baseline captures one",
          code == 0 and "STATUS.md was not updated" in (context_of(out) or ""))


def handoffs_checks():
    import datetime
    today = datetime.date.today().isoformat()
    repo = make_repo()
    payload = {"cwd": repo, "session_id": sid(), "source": "startup"}
    ctx = context_of(run_hook("sessionstart.py", payload)[0]) or ""
    check("handoffs: absent folder adds nothing", "handoffs/" not in ctx)

    hdir = os.path.join(repo, ".handoff", "handoffs")
    os.makedirs(hdir)
    ctx = context_of(run_hook("sessionstart.py", dict(payload, session_id=sid()))[0]) or ""
    check("handoffs: empty folder adds nothing", "handoffs/" not in ctx)

    write(hdir, today + "-pricing-rework.md", "detail\n")
    write(hdir, "2020-01-01-old-thing.md", "detail\n")
    write(hdir, "undated.md", "detail\n")
    write(hdir, "notes.txt", "ignored\n")
    ctx = context_of(run_hook("sessionstart.py", dict(payload, session_id=sid()))[0]) or ""
    check("handoffs: lists each .md file", today + "-pricing-rework.md" in ctx
          and "2020-01-01-old-thing.md" in ctx and "undated.md" in ctx)
    check("handoffs: ignores non-markdown files", "notes.txt" not in ctx)
    check("handoffs: today's file is marked today", today + "-pricing-rework.md (today)" in ctx)
    check("handoffs: old file is flagged to verify",
          "2020-01-01-old-thing.md (" in ctx and "verify before trusting" in ctx)
    check("handoffs: still injects STATUS + RULES", "status body" in ctx and "rules body" in ctx)

    for i in range(8):
        write(hdir, "{}-topic-{}.md".format(today, i))
    ctx = context_of(run_hook("sessionstart.py", dict(payload, session_id=sid()))[0]) or ""
    check("handoffs: long list is capped", "more" in ctx and ctx.count("topic-") <= 5)

    # Stop names the folder as the place for detail that won't fit.
    repo = make_repo()
    p2 = {"cwd": repo, "session_id": sid(), "stop_hook_active": False}
    run_hook("sessionstart.py", dict(p2, source="startup"))
    write(repo, "app.py")
    ctx = context_of(run_hook("stop.py", p2)[0]) or ""
    check("handoffs: Stop names the overflow folder", ".handoff/handoffs/" in ctx)

    # A .handoff/handoffs that is a file, not a folder, must not break SessionStart.
    repo = make_repo()
    write(repo, os.path.join(".handoff", "handoffs"), "not a dir\n")
    out, code = run_hook("sessionstart.py", {"cwd": repo, "session_id": sid()})
    check("handoffs: non-directory path is ignored", code == 0
          and "status body" in (context_of(out) or ""))


LINT = os.path.join(os.path.dirname(HOOKS), "scripts", "handoff_lint.py")


def run_lint(repo):
    proc = subprocess.run([sys.executable, LINT, repo], capture_output=True,
                          text=True, timeout=60, env=hook_env())
    return proc.stdout, proc.returncode


def lint_checks():
    # Clean scaffold -> exit 0.
    repo = make_repo()
    out, code = run_lint(repo)
    check("lint: clean repo exits 0", code == 0 and "no issues" in out)

    # No .handoff/ -> exit 2, nothing to lint.
    out, code = run_lint(make_repo(with_handoff=False))
    check("lint: repo without .handoff exits 2", code == 2)

    repo = make_repo()
    h = os.path.join(repo, ".handoff")
    for d in ("tasks/inbox", "tasks/now", "tasks/done", "src/sub"):
        os.makedirs(os.path.join(h if d.startswith("tasks") else repo, d), exist_ok=True)
    write(h, "tasks/now/mismatch.md", "---\ntitle: x\nstatus: inbox\npriority: low\n---\n")
    write(h, "tasks/inbox/fine.md", "---\ntitle: y\nstatus: inbox\npriority: low\n---\n")
    write(h, "tasks/stray.md", "---\ntitle: z\nstatus: inbox\n---\n")
    write(h, "tasks/WORKFLOW.md", "workflow\n")
    write(repo, "src/app.py")
    write(h, "MAP.md", "# Map\n- `src/app.py` — entry\n- `src/gone.py` — removed\n"
          "- `<path>` — placeholder\n- `npm run dev`\n- `https://example.com/a.js`\n"
          "- `src/` — source\n- version `2.4.0`\n"
          "- `sub/` — shorthand under src, and `.py` files\n")
    write(h, "BOOT.md", "**Project:** `<PROJECT_NAME>`\n")
    write(h, "STATUS.md", "".join("line {}\n".format(i) for i in range(30)))
    write(repo, "src/CONTEXT.md", "Entry is `app.py`; helpers in `helper.py`.\n")
    write(repo, "src/sub/CONTEXT.md", "sub notes\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "setup")
    write(repo, "src/new.py")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "add file in src")
    write(repo, "src/sub/only_sub.py")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "add file in src/sub")
    before = subprocess.run(["git", "-C", repo, "status", "--porcelain"],
                            capture_output=True, text=True).stdout

    out, code = run_lint(repo)
    check("lint: findings exit 1", code == 1)
    check("lint: task status mismatch", "mismatch.md" in out and "fine.md" not in out)
    check("lint: stray task in tasks root", "stray.md" in out and "WORKFLOW.md" not in out)
    check("lint: missing MAP path", "src/gone.py" in out)
    check("lint: existing and non-path MAP tokens ignored",
          "src/app.py" not in out and "npm run dev" not in out
          and "example.com" not in out and "2.4.0" not in out and "`<path>`" not in out
          and "`sub/`" not in out and "`.py`" not in out)
    check("lint: leftover placeholder", "<PROJECT_NAME>" in out)
    check("lint: STATUS over target", "STATUS.md is 30 lines" in out)
    check("lint: CONTEXT.md behind its folder", "src/CONTEXT.md" in out and "added or removed" in out)
    check("lint: nested CONTEXT.md owns its subfolder", "src/sub/CONTEXT.md" in out
          and out.count("src/CONTEXT.md:") <= 2)
    check("lint: missing CONTEXT path", "helper.py" in out and "`app.py`" not in out)
    after = subprocess.run(["git", "-C", repo, "status", "--porcelain"],
                           capture_output=True, text=True).stdout
    check("lint: read-only", before == after)

    # 10+ commits in a folder without structural change also flags.
    repo = make_repo()
    os.makedirs(os.path.join(repo, "lib"))
    write(repo, "lib/CONTEXT.md", "notes\n")
    write(repo, "lib/a.py", "0\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "lib")
    for i in range(10):
        write(repo, "lib/a.py", "{}\n".format(i + 1))
        git(repo, "commit", "-qam", "edit {}".format(i))
    out, code = run_lint(repo)
    check("lint: many commits since CONTEXT.md flags", code == 1
          and "lib/CONTEXT.md" in out and "10 commits" in out)


def claude_transcript(path, tokens, sidechain_tokens=None):
    lines = [{"type": "user", "message": {"role": "user", "content": "hi"}},
             {"type": "assistant", "isSidechain": False, "message": {"usage": {
                 "input_tokens": 2, "cache_creation_input_tokens": 1000,
                 "cache_read_input_tokens": tokens - 1002, "output_tokens": 50}}}]
    if sidechain_tokens:
        lines.append({"type": "assistant", "isSidechain": True, "message": {"usage": {
            "input_tokens": sidechain_tokens, "output_tokens": 5}}})
    lines.append({"type": "system", "content": "x" * 2000})
    with open(path, "w") as fh:
        fh.write("\n".join(json.dumps(l) for l in lines) + "\n")


def large_session_checks():
    repo = make_repo()
    tpath = os.path.join(repo, "..", "t-" + uuid.uuid4().hex[:6] + ".jsonl")
    payload = {"cwd": repo, "session_id": sid(), "stop_hook_active": False,
               "transcript_path": tpath}
    run_hook("sessionstart.py", dict(payload, source="startup"))

    claude_transcript(tpath, 50000)
    out, code = run_hook("stop.py", payload)
    check("large: small transcript, clean tree stays silent", code == 0 and out == "")

    claude_transcript(tpath, 250000)
    out, code = run_hook("stop.py", payload)
    ctx = context_of(out) or ""
    check("large: crossing 200k fires with no repo changes", code == 0
          and json.loads(out or "{}").get("decision") == "block"
          and "250k tokens" in ctx and "fresh session" in ctx
          and "you changed project files" not in ctx)
    out, code = run_hook("stop.py", payload)
    check("large: same step does not fire twice", code == 0 and out == "")
    claude_transcript(tpath, 330000)
    out, code = run_hook("stop.py", payload)
    check("large: growth within the step stays silent", code == 0 and out == "")
    claude_transcript(tpath, 420000)
    out, code = run_hook("stop.py", payload)
    check("large: crossing 400k fires again", "420k tokens" in (context_of(out) or ""))
    claude_transcript(tpath, 999000)
    out, code = run_hook("stop.py", dict(payload, stop_hook_active=True))
    check("large: stop_hook_active still exits first", code == 0 and out == "")

    # Combined with ordinary freshness notes -> one message carrying both.
    write(repo, "app.py")
    claude_transcript(tpath, 650000)
    ctx = context_of(run_hook("stop.py", payload)[0]) or ""
    check("large: combines with the freshness nudge",
          "STATUS.md was not updated" in ctx and "650k tokens" in ctx)

    # Subagent (sidechain) usage is not this session's context.
    p2 = dict(payload, session_id=sid())
    claude_transcript(tpath, 40000, sidechain_tokens=300000)
    out, _ = run_hook("stop.py", p2)
    check("large: sidechain usage is ignored", out == "" or "tokens" not in (context_of(out) or ""))

    # Codex rollout format.
    repo = make_repo()
    cpath = os.path.join(repo, "..", "c-" + uuid.uuid4().hex[:6] + ".jsonl")
    with open(cpath, "w") as fh:
        fh.write(json.dumps({"type": "session_meta", "payload": {"id": "x"}}) + "\n")
        fh.write(json.dumps({"type": "event_msg", "payload": {"type": "token_count", "info": {
            "last_token_usage": {"input_tokens": 230000, "cached_input_tokens": 200000},
            "model_context_window": 258400}}}) + "\n")
    p3 = {"cwd": repo, "session_id": sid(), "stop_hook_active": False,
          "turn_id": "t1", "transcript_path": cpath}
    run_hook("sessionstart.py", dict(p3, source="startup"))
    ctx = context_of(run_hook("stop.py", p3)[0]) or ""
    check("large: Codex token_count record fires", "230k tokens" in ctx)

    # Missing, unreadable, garbage or absent transcript -> silent.
    repo = make_repo()
    base = {"cwd": repo, "stop_hook_active": False}
    gpath = os.path.join(repo, "..", "g-" + uuid.uuid4().hex[:6] + ".jsonl")
    with open(gpath, "w") as fh:
        fh.write("not json\n{\"usage\": 5}\n")
    for label, extra in (("missing path", {"transcript_path": "/nonexistent/x.jsonl"}),
                         ("garbage file", {"transcript_path": gpath}),
                         ("non-string path", {"transcript_path": 42}),
                         ("no transcript_path", {})):
        p4 = dict(base, session_id=sid(), **extra)
        run_hook("sessionstart.py", dict(p4, source="startup"))
        out, code = run_hook("stop.py", p4)
        check("large: {} stays silent".format(label), code == 0 and out == "")

    # Non-git repo with .handoff/: the large nudge still works.
    plain = tempfile.mkdtemp(prefix="plain-", dir=TEST_ROOT.name)
    os.makedirs(os.path.join(plain, ".handoff"))
    write(plain, os.path.join(".handoff", "STATUS.md"), "s\n")
    ppath = os.path.join(plain, "t.jsonl")
    claude_transcript(ppath, 210000)
    out, code = run_hook("stop.py", {"cwd": plain, "session_id": sid(),
                                     "stop_hook_active": False, "transcript_path": ppath})
    check("large: fires in a non-git repo with .handoff", "210k tokens" in (context_of(out) or ""))


INVENTORY = os.path.join(os.path.dirname(HOOKS), "scripts", "context_inventory.py")
SECRET = "sk-test-SECRET-value-123"


def jdump(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh)


def fake_plugin(root, name, skills=0, mcp=None, manifest_mcp=None):
    os.makedirs(os.path.join(root, ".claude-plugin"), exist_ok=True)
    manifest = {"name": name}
    if manifest_mcp is not None:
        manifest["mcpServers"] = manifest_mcp
    jdump(os.path.join(root, ".claude-plugin", "plugin.json"), manifest)
    for i in range(skills):
        d = os.path.join(root, "skills", "s{}".format(i))
        os.makedirs(d, exist_ok=True)
        write(d, "SKILL.md", "---\nname: s{}\ndescription: {}\n---\nbody\n".format(i, "word " * 80))
    if mcp:
        jdump(os.path.join(root, ".mcp.json"), {"mcpServers": mcp})


def run_inventory(project, home, *args):
    env = hook_env({"HOME": home})
    for key in ("CLAUDE_CONFIG_DIR", "CODEX_HOME"):
        env.pop(key, None)
    proc = subprocess.run([sys.executable, INVENTORY, project] + list(args),
                          capture_output=True, text=True, timeout=60, env=env)
    return proc.stdout, proc.returncode


def inventory_checks():
    home = tempfile.mkdtemp(prefix="home-", dir=TEST_ROOT.name)
    project = make_repo()
    other = make_repo()
    cdir = os.path.join(home, ".claude")
    cache = os.path.join(cdir, "plugins", "cache")
    fake_plugin(os.path.join(cache, "big"), "big", skills=3,
                mcp={"bigsrv": {"command": "npx", "env": {"API_KEY": SECRET}}})
    fake_plugin(os.path.join(cache, "quiet"), "quiet", skills=1)
    fake_plugin(os.path.join(cache, "inline"), "inline",
                manifest_mcp={"inl": {"url": "https://example.com/mcp?token=" + SECRET}})
    fake_plugin(os.path.join(cache, "elsewhere"), "elsewhere", skills=1)
    fake_plugin(os.path.join(cache, "off"), "off", skills=2)
    jdump(os.path.join(cdir, "plugins", "installed_plugins.json"), {"version": 2, "plugins": {
        "big@mk": [{"scope": "user", "installPath": os.path.join(cache, "big")}],
        "quiet@mk": [{"scope": "user", "installPath": os.path.join(cache, "quiet")}],
        "inline@mk": [{"scope": "user", "installPath": os.path.join(cache, "inline")}],
        "elsewhere@mk": [{"scope": "local", "projectPath": other,
                          "installPath": os.path.join(cache, "elsewhere")}],
        "off@mk": [{"scope": "user", "installPath": os.path.join(cache, "off")}],
    }})
    jdump(os.path.join(cdir, "settings.json"), {"enabledPlugins": {
        "big@mk": True, "quiet@mk": True, "inline@mk": True, "elsewhere@mk": True}})
    jdump(os.path.join(project, ".claude", "settings.local.json"),
          {"enabledPlugins": {"quiet@mk": False}})
    jdump(os.path.join(home, ".claude.json"), {
        "mcpServers": {"usersrv": {"command": "x", "env": {"TOKEN": SECRET}}},
        "projects": {project: {"mcpServers": {"localsrv": {"url": "https://a/" + SECRET}}}}})
    jdump(os.path.join(project, ".mcp.json"), {"mcpServers": {"projsrv": {"command": "y"}}})
    os.makedirs(os.path.join(cdir, "skills", "mine"))
    write(os.path.join(cdir, "skills", "mine"), "SKILL.md", "---\nname: mine\ndescription: personal skill\n---\n")
    os.makedirs(os.path.join(home, ".codex"))
    write(os.path.join(home, ".codex"), "config.toml",
          '[plugins."cx@mk"]\nenabled = true\n\n[plugins."cxoff@mk"]\nenabled = false\n\n'
          '[mcp_servers.cxsrv]\ncommand = "z"\n\n[mcp_servers.cxsrv.env]\nKEY = "' + SECRET + '"\n')

    def snapshot():
        out = []
        for base in (home, project):
            for dp, _, fs in os.walk(base):
                if "/.git" in dp:
                    continue
                for f in fs:
                    with open(os.path.join(dp, f), "rb") as fh:
                        out.append((os.path.join(dp, f), fh.read()))
        return sorted(out)

    before = snapshot()
    out, code = run_inventory(project, home)
    check("inventory: exits 0", code == 0)
    check("inventory: never prints secret values", SECRET not in out)
    check("inventory: lists enabled plugin with skills and MCP", "big@mk" in out and "bigsrv" in out)
    check("inventory: inline manifest MCP server listed", "inl" in out)
    data = json.loads(run_inventory(project, home, "--json")[0])
    plugins = {p["name"]: p for p in data["claude"]["plugins"]}
    check("inventory: json mode parses with secrets absent",
          SECRET not in json.dumps(data))
    check("inventory: project settings.local overrides user enable",
          plugins["quiet@mk"]["enabled"] is False and plugins["quiet@mk"]["decided_by"].endswith("settings.local.json"))
    check("inventory: plugin never enabled reads as disabled", plugins["off@mk"]["enabled"] is False)
    check("inventory: local install for another project is excluded", "elsewhere@mk" not in plugins)
    check("inventory: skill description cost estimated",
          plugins["big@mk"]["skills"] == 3 and plugins["big@mk"]["est_tokens"] > 150)
    check("inventory: MCP servers from every Claude scope",
          {s["name"] for s in data["claude"]["mcp_servers"]} >= {"usersrv", "localsrv", "projsrv"})
    check("inventory: user skills listed", any(s["name"] == "mine" for s in data["claude"]["user_skills"]))
    codex = {p["name"]: p["enabled"] for p in data["codex"]["plugins"]}
    check("inventory: Codex plugins and enabled flags", codex == {"cx@mk": True, "cxoff@mk": False})
    check("inventory: Codex MCP servers (not env subsections)",
          [s["name"] for s in data["codex"]["mcp_servers"]] == ["cxsrv"])
    check("inventory: read-only", snapshot() == before)

    empty_home = tempfile.mkdtemp(prefix="home-", dir=TEST_ROOT.name)
    out, code = run_inventory(make_repo(), empty_home)
    check("inventory: empty home exits 0", code == 0 and "No Claude Code plugins" in out)
    bad_home = tempfile.mkdtemp(prefix="home-", dir=TEST_ROOT.name)
    write(bad_home, ".claude.json", "{not json")
    os.makedirs(os.path.join(bad_home, ".claude", "plugins"))
    write(os.path.join(bad_home, ".claude", "plugins"), "installed_plugins.json", "[]")
    out, code = run_inventory(make_repo(), bad_home)
    check("inventory: malformed config files don't crash", code == 0)


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
    check("stop: updated but uncommitted state gets a commit reminder", code == 0
          and "commit completed, verified changes" in (context_of(out) or "")
          and "STATUS.md was not updated" not in (context_of(out) or ""))
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
    check("sessionstart: injects the risk-tier reminder", ctx is not None
          and "T1" in ctx and "T2" in ctx and "T3" in ctx
          and "workflow" in ctx)

    out, code = run_hook("sessionstart.py", {"cwd": bare, "session_id": sid()})
    check("sessionstart: exit 0 without .handoff/", code == 0)
    check("sessionstart: no tier reminder without .handoff/",
          "T3" not in (context_of(out) or ""))

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
    stop_message_checks()
    handoffs_checks()
    lint_checks()
    large_session_checks()
    inventory_checks()
    commit_reminder_checks()

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
