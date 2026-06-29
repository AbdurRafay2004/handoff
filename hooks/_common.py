"""Shared helpers for agent-orch hooks.

Every hook is fail-safe: on any error it prints nothing and exits 0, so a bug
here can never break the user's session.
"""
import hashlib
import json
import os
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
