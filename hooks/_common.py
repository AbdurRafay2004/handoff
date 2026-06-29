"""Shared helpers for agent-orch hooks.

Every hook is fail-safe: on any error it prints nothing and exits 0, so a bug
here can never break the user's session.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

AGENT_DIR = ".agent-orch"


def read_stdin_json():
    """Parse the hook payload from stdin; return {} on any problem."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def project_root(payload):
    """Resolve the user's project root: CLAUDE_PROJECT_DIR, then stdin cwd, then getcwd."""
    return (
        os.environ.get("CLAUDE_PROJECT_DIR")
        or payload.get("cwd")
        or os.getcwd()
    )


def agent_base(root):
    return os.path.join(root, AGENT_DIR)


def has_agent_orch(root):
    return os.path.isdir(agent_base(root))


def read_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except Exception:
        return None


def data_dir():
    """A writable, persistent-ish directory for markers."""
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
        os.path.expanduser("~"), ".cache", "agent-orch"
    )
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except Exception:
        return tempfile.gettempdir()


def session_marker_dir(session_id):
    """Per-session scratch dir for de-duping injections within one session."""
    sid = session_id or "nosession"
    d = os.path.join(tempfile.gettempdir(), "agent-orch-session-" + _short(sid))
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _short(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def marker_seen(path):
    return os.path.exists(path)


def marker_set(path):
    try:
        open(path, "w").close()
        return True
    except Exception:
        return False


def git_status_paths(root):
    """Repo-relative, normalized paths of all changed/untracked files; None on error.

    -uall lists untracked files individually so new directories aren't collapsed
    to one entry (which would hide nested CONTEXT.md folders and new files).
    """
    try:
        out = subprocess.run(
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
        paths.append(os.path.normpath(entry.strip().strip('"')))
    return paths


def _session_file(session_id, name):
    return os.path.join(session_marker_dir(session_id), name)


def load_baseline(session_id):
    """Set of dirty paths captured at session start, or None if not captured yet."""
    try:
        with open(_session_file(session_id, "git-baseline"), encoding="utf-8") as fh:
            return set(l.strip() for l in fh if l.strip())
    except Exception:
        return None


def save_baseline(session_id, paths):
    try:
        with open(_session_file(session_id, "git-baseline"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(sorted(paths)))
        return True
    except Exception:
        return False


def last_nudge_signature(session_id):
    try:
        with open(_session_file(session_id, "nudge-sig"), encoding="utf-8") as fh:
            return fh.read().strip()
    except Exception:
        return None


def set_nudge_signature(session_id, sig):
    try:
        with open(_session_file(session_id, "nudge-sig"), "w", encoding="utf-8") as fh:
            fh.write(sig)
        return True
    except Exception:
        return False


def signature(*parts):
    return _short("||".join(parts))


def emit(hook_event_name, additional_context):
    """Print the standard non-blocking context-injection payload and exit 0."""
    if additional_context:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": hook_event_name,
                "additionalContext": additional_context,
            }
        }))
    sys.exit(0)
