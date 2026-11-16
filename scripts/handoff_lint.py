#!/usr/bin/env python3
"""handoff lint: read-only drift checks for a repo's .handoff/ memory.

Usage: python3 handoff_lint.py [repo-path]   (default: current directory)

Reports drift the hooks can't see:
  - task files whose folder (inbox/now/done) disagrees with frontmatter status,
    and task files sitting in the tasks/ root
  - backticked paths in MAP.md that exist nowhere in the repo (shorthand like
    `money.ts` under a `src/lib/` bullet matches any path ending in it)
  - leftover <UPPER_CASE> template placeholders
  - STATUS.md over its 25-line target
  - folder CONTEXT.md files that fell behind their folder: files added or
    removed there, or STALE_COMMITS+ commits there, since the note was last
    committed (subfolders with their own CONTEXT.md are theirs, not the parent's)
  - backticked paths in a CONTEXT.md that exist nowhere in the repo

Never writes anything. Exit codes: 0 clean, 1 findings, 2 nothing to lint.
Stdlib only.
"""
import os
import re
import subprocess
import sys

AGENT_DIR = ".handoff"
TASK_FOLDERS = ("inbox", "now", "done")
TASKS_ROOT_ALLOWED = ("WORKFLOW.md", "TEMPLATE.md", ".gitkeep")
STATUS_TARGET = 25
STALE_COMMITS = 10
PLACEHOLDER = re.compile(r"<[A-Z][A-Z0-9_]{2,}>")
BACKTICK = re.compile(r"`([^`\n]+)`")
STATUS_LINE = re.compile(r"^status:\s*['\"]?(\w+)", re.MULTILINE)
EXTENSION = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,5}$")
PATHLIKE = re.compile(r"[\w.\-/]+")
BARE_DOTNAME = re.compile(r"\.[\w-]+")  # `.py`, `.env`: extensions or untracked dotfiles


def git(root, *args):
    """stdout of a git command, or None on any error."""
    try:
        out = subprocess.run(["git", "-C", root] + list(args),
                             capture_output=True, text=True, timeout=30)
        return out.stdout if out.returncode == 0 else None
    except Exception:
        return None


def find_root(start):
    top = git(start, "rev-parse", "--show-toplevel")
    if top and top.strip():
        return top.strip()
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, AGENT_DIR)):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return None


def path_tokens(text):
    """Backticked tokens that look like file or folder paths."""
    found = []
    for tok in BACKTICK.findall(text):
        tok = tok.strip()
        if tok.startswith(("http:", "https:", "-", "~", "/")):
            continue
        tok = re.sub(r":\d+(-\d+)?$", "", tok)  # strip :line suffixes
        if not PATHLIKE.fullmatch(tok) or BARE_DOTNAME.fullmatch(tok):
            continue
        if "/" in tok or EXTENSION.search(tok):
            found.append(tok)
    return found


def check_tasks(base):
    issues = []
    tasks = os.path.join(base, "tasks")
    if not os.path.isdir(tasks):
        return issues
    for name in sorted(os.listdir(tasks)):
        full = os.path.join(tasks, name)
        if os.path.isfile(full) and name not in TASKS_ROOT_ALLOWED:
            issues.append("tasks/{} sits in the tasks/ root; move it into "
                          "inbox/, now/ or done/".format(name))
    for folder in TASK_FOLDERS:
        d = os.path.join(tasks, folder)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".md"):
                continue
            m = STATUS_LINE.search(read(os.path.join(d, name)) or "")
            if m and m.group(1) != folder:
                issues.append("tasks/{}/{} has status '{}' but sits in {}/".format(
                    folder, name, m.group(1), folder))
            elif not m:
                issues.append("tasks/{}/{} has no frontmatter status".format(folder, name))
    return issues


class RepoPaths:
    """Answers "does this path exist anywhere?" for shorthand references.

    MAP.md and CONTEXT.md often name files relative to a parent bullet or
    folder (`money.ts` under `src/lib/`), so a token counts as present when it
    exists at the given base OR any tracked/untracked (not ignored) path ends
    with it at a path-segment boundary.
    """

    def __init__(self, root):
        self.root = root
        out = git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
        files = [p for p in (out or "").split("\0") if p]
        self.suffixes = set()
        for p in files:
            parts = p.split("/")
            for i in range(len(parts)):
                tail = "/".join(parts[i:])
                self.suffixes.add(tail)
                # every folder suffix too, so `features/auth/` matches
                for j in range(i + 1, len(parts)):
                    self.suffixes.add("/".join(parts[i:j]))

    def exists(self, tok, *bases):
        for b in bases:
            if os.path.exists(os.path.join(self.root, b, tok)):
                return True
        return tok.rstrip("/") in self.suffixes


def check_map(root, base, paths):
    text = read(os.path.join(base, "MAP.md"))
    if not text:
        return []
    return ["MAP.md: `{}` not found anywhere in the repo".format(tok)
            for tok in dict.fromkeys(path_tokens(text))
            if not paths.exists(tok, "", AGENT_DIR)]


def check_placeholders(base):
    issues = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in ("tasks", "handoffs", "docs")]
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            full = os.path.join(dirpath, name)
            found = sorted(set(PLACEHOLDER.findall(read(full) or "")))
            if found:
                issues.append("{}: template placeholder(s) left: {}".format(
                    os.path.relpath(full, base), ", ".join(found)))
    return issues


def check_status(base):
    text = read(os.path.join(base, "STATUS.md"))
    if not text:
        return []
    n = len(text.rstrip("\n").split("\n"))
    if n > STATUS_TARGET:
        return ["STATUS.md is {} lines (target <= {}); prune into CHANGELOG.md / "
                "tasks/".format(n, STATUS_TARGET)]
    return []


def context_files(root):
    out = git(root, "ls-files", "-z")
    if out is None:
        return []
    return sorted(p for p in out.split("\0")
                  if p and os.path.basename(p) == "CONTEXT.md"
                  and not p.startswith(AGENT_DIR + "/"))


def check_context(root, paths):
    issues = []
    ctxs = context_files(root)
    folders = {os.path.dirname(p) for p in ctxs}
    for ctx in ctxs:
        folder = os.path.dirname(ctx)
        label = (folder + "/") if folder else "the repo root"
        # Subfolders with their own CONTEXT.md own their changes.
        owned_elsewhere = [f for f in folders if f != folder
                           and (folder == "" or f.startswith(folder + "/"))]

        def mine(path):
            return not any(path.startswith(f + "/") for f in owned_elsewhere)

        last = (git(root, "log", "-1", "--format=%H", "--", ctx) or "").strip()
        if last:
            log = git(root, "log", "--format=@%H", "--name-status", "--no-renames",
                      last + "..HEAD", "--", folder or ".") or ""
            commits = 0
            structural = set()
            sha_paths = []
            for line in log.splitlines() + ["@"]:
                if line.startswith("@"):
                    if any(mine(p) for _, p in sha_paths):
                        commits += 1
                        structural.update(p for st, p in sha_paths
                                          if st in ("A", "D") and mine(p))
                    sha_paths = []
                elif "\t" in line:
                    st, p = line.split("\t", 1)
                    if p != ctx:
                        sha_paths.append((st[:1], p))
            if structural:
                issues.append("{}: {} file{} added or removed in {} since it was last "
                              "updated ({} commit{}); check it still describes the "
                              "folder".format(ctx, len(structural),
                                              "" if len(structural) == 1 else "s", label,
                                              commits, "" if commits == 1 else "s"))
            elif commits >= STALE_COMMITS:
                issues.append("{}: {} commits touched {} since it was last updated; "
                              "check it still describes the folder".format(ctx, commits, label))
        text = read(os.path.join(root, ctx)) or ""
        for tok in dict.fromkeys(path_tokens(text)):
            if not paths.exists(tok, folder, ""):
                issues.append("{}: `{}` not found anywhere in the repo".format(ctx, tok))
    return issues


def main(argv):
    root = find_root(argv[1] if len(argv) > 1 else os.getcwd())
    base = os.path.join(root, AGENT_DIR)
    if not os.path.isdir(base):
        print("handoff lint: no {}/ in {}; nothing to lint".format(AGENT_DIR, root))
        return 2
    paths = RepoPaths(root)
    sections = [
        ("Tasks", check_tasks(base)),
        ("MAP.md paths", check_map(root, base, paths)),
        ("Placeholders", check_placeholders(base)),
        ("STATUS.md size", check_status(base)),
        ("Folder CONTEXT.md", check_context(root, paths)),
    ]
    total = sum(len(items) for _, items in sections)
    if not total:
        print("handoff lint: no issues in {}".format(root))
        return 0
    print("handoff lint: {} issue{} in {}".format(total, "" if total == 1 else "s", root))
    for title, items in sections:
        if items:
            print("\n{}:".format(title))
            for item in items:
                print("  - " + item)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
