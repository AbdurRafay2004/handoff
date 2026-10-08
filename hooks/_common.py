"""Shared helpers for handoff hooks.

Every hook is fail-safe: on any error it prints nothing and exits 0, so a bug
here can never break the user's session.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

AGENT_DIR = ".handoff"


def read_stdin_json():
    """Parse the hook payload from stdin; return {} on any problem."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def project_root(payload):
    """Honor Claude's explicit root; otherwise find the repo from the hook cwd.

    Codex supplies cwd, which can be a subdirectory. Git is the boundary (also
    for worktrees/nested repos); without git, look for an ancestor .handoff/.
    """
    explicit = os.environ.get("CLAUDE_PROJECT_DIR")
    if explicit:
        return os.path.abspath(explicit)
    cwd = os.path.abspath(payload.get("cwd") or os.getcwd())
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    candidate = cwd
    while True:
        if has_handoff(candidate):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            return cwd
        candidate = parent


def agent_base(root):
    return os.path.join(root, AGENT_DIR)


def has_handoff(root):
    return os.path.isdir(agent_base(root))


def read_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().strip()
    except Exception:
        return None


def data_dir():
    """A writable, persistent-ish directory for markers."""
    base = (
        os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.path.join(os.path.expanduser("~"), ".cache", "handoff")
    )
    try:
        os.makedirs(base, exist_ok=True)
        return base
    except Exception:
        return tempfile.gettempdir()


def session_marker_dir(session_id):
    """Per-session scratch dir for de-duping injections within one session."""
    sid = session_id or "nosession"
    d = os.path.join(tempfile.gettempdir(), "handoff-session-" + _short(sid))
    try:
        os.makedirs(d, mode=0o700, exist_ok=True)
        os.chmod(d, 0o700)  # tighten even if the dir pre-existed
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


def git_status_codes(root):
    """Dict of repo-relative normalized path -> porcelain status code; None on error.

    Uses -z (NUL-separated) so quoted/unicode paths and filenames containing
    " -> " parse exactly. Renames record BOTH sides: the new path keeps its R/C
    code; the old path is recorded as "D " so departures stay visible to the
    stale-CONTEXT and structural checks. -uall lists untracked files
    individually so new directories aren't collapsed to one entry.
    """
    try:
        out = subprocess.run(
            ["git", "-C", root, "status", "--porcelain", "-z", "-uall"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
    except Exception:
        return None
    codes = {}
    toks = out.stdout.split("\0")
    i = 0
    while i < len(toks):
        t = toks[i]
        if len(t) < 4:
            i += 1
            continue
        code, path = t[:2], t[3:]
        codes[os.path.normpath(path)] = code
        # In -z format a rename/copy in EITHER column ('R ', ' R', 'C ', ' C')
        # is followed by an extra NUL token: the OLD path. Always consume it so
        # it can't be misparsed as a status entry. Renames record the old path
        # as a departure; a copy's source still exists unchanged, so for C the
        # token is consumed but not recorded.
        if ("R" in code or "C" in code) and i + 1 < len(toks) and toks[i + 1]:
            if "R" in code:
                codes[os.path.normpath(toks[i + 1])] = "D "
            i += 1
        i += 1
    return codes


def git_status_paths(root):
    """Repo-relative, normalized paths of all changed/untracked files; None on error."""
    codes = git_status_codes(root)
    return None if codes is None else list(codes)


def git_head(root):
    """Current HEAD sha, or None (no commits yet / not a repo / error)."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
        return out.stdout.strip() or None
    except Exception:
        return None


def git_local_commit_codes(root, base_sha, cap=50):
    """path -> one-letter status across commits made since base_sha that exist
    ONLY locally (not reachable from any remote-tracking ref); None on error.

    Filtering by --not --remotes keeps upstream commits brought in by
    pull/merge/rebase out of the "this session's work" set. Local commits that
    were already pushed are also excluded — a deliberate quieter-not-noisier
    trade-off for an advisory nudge.
    """
    if not base_sha:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", root, "rev-list", "--max-count", str(cap),
             base_sha + "..HEAD", "--not", "--remotes"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
        shas = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    except Exception:
        return None
    codes = {}
    for sha in shas:
        try:
            show = subprocess.run(
                ["git", "-C", root, "show", "--name-status", "--no-renames",
                 "-z", "--format=", sha],
                capture_output=True, text=True, timeout=10,
            )
            if show.returncode != 0:
                continue
        except Exception:
            continue
        toks = show.stdout.split("\0")
        i = 0
        while i + 1 < len(toks):
            st, path = toks[i], toks[i + 1]
            if st and path:
                codes[os.path.normpath(path)] = st[:1]
            i += 2
    return codes


def plugin_version():
    """The plugin's own manifest version, or None."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for directory in (".codex-plugin", ".claude-plugin"):
        try:
            with open(os.path.join(root, directory, "plugin.json"), encoding="utf-8") as fh:
                version = json.load(fh).get("version")
            if version:
                return version
        except Exception:
            pass
    return None


def _session_file(session_id, name):
    return os.path.join(session_marker_dir(session_id), name)


def _esc_path(p):
    """Escape a path for the newline-delimited baseline file."""
    return p.replace("\\", "\\\\").replace("\n", "\\n")


def _unesc_path(p):
    out = []
    i = 0
    while i < len(p):
        if p[i] == "\\" and i + 1 < len(p):
            nxt = p[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(p[i])
        i += 1
    return "".join(out)


def load_baseline(session_id):
    """(head_sha_or_None, {path: code}) captured at session start; None if absent.

    Backward compatible: pre-v1.4 baselines were bare path lists — those load
    as (None, {path: ""}); callers treat code "" as "present at baseline,
    code unknown" and must NOT count such paths as session-changed.
    """
    try:
        with open(_session_file(session_id, "git-baseline"), encoding="utf-8") as fh:
            lines = [l.rstrip("\n") for l in fh if l.strip()]
    except Exception:
        return None
    sha = None
    codes = {}
    for line in lines:
        if line.startswith("#sha "):
            val = line[5:].strip()
            sha = val if val and val != "-" else None
        elif "\t" in line:
            code, path = line.split("\t", 1)
            codes[_unesc_path(path)] = code
        else:  # legacy bare-path format
            codes[line] = ""
    return (sha, codes)


def save_baseline(session_id, sha, codes):
    try:
        with open(_session_file(session_id, "git-baseline"), "w", encoding="utf-8") as fh:
            fh.write("#sha {}\n".format(sha or "-"))
            for path in sorted(codes):
                fh.write("{}\t{}\n".format(codes[path], _esc_path(path)))
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
    """Emit context, or a bounded Stop continuation, using both hosts' schema.

    Stop does not accept hookSpecificOutput.additionalContext. Its documented
    decision=block means continue the turn with reason, not deny a tool.
    """
    if additional_context:
        if hook_event_name == "Stop":
            print(json.dumps({"decision": "block", "reason": additional_context}))
        else:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": hook_event_name,
                    "additionalContext": additional_context,
                }
            }))
    sys.exit(0)
