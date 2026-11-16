#!/usr/bin/env python3
"""SessionStart hook.

If the project has .handoff/  -> inject STATUS (full) + RULES (full) + a
one-line pointer to the on-demand docs (BOOT/MAP/context/tasks), plus a
one-line list of open overflow handoffs in .handoff/handoffs/ when any exist.

If it does NOT -> inject a one-time, self-suppressing nudge to run setup, then
write a per-repo marker so it never nags that repo again. Silent thereafter.
"""
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402
    read_stdin_json, project_root, agent_base, has_handoff, read_file,
    data_dir, marker_seen, marker_set, emit, _short,
    git_status_codes, git_head, save_baseline, load_baseline, plugin_version,
)

POINTER = (
    "\n\n----- handoff pointer -----\n"
    "RULES + STATUS above are auto-loaded. Read on demand only when the task needs it:\n"
    "  .handoff/BOOT.md (session procedure + end-of-session updates),\n"
    "  .handoff/MAP.md, .handoff/context/PRODUCT.md, .handoff/context/TECH_STACK.md,\n"
    "  .handoff/tasks/ (durable backlog), .handoff/CHANGELOG.md, and any <dir>/CONTEXT.md.\n"
    "Update STATUS.md + CHANGELOG.md whenever code or configuration changes — "
    "BEFORE committing, so state rides in the same commit as the change.\n"
    "Before any development task, state its risk tier in one line: "
    "T1 trivial (small isolated edit: edit, check, done), "
    "T2 standard (typical feature or refactor), "
    "T3 risky (money, auth, user data, migrations, deletes, cross-cutting). "
    "For T2 and T3, load the `workflow` skill and follow its process."
)


HANDOFFS_SHOWN = 5        # cap the listing; the rest are summarised as "+N more"
HANDOFF_STALE_DAYS = 14   # older notes are flagged "verify before trusting"
DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def handoffs_line(base):
    """One line listing open overflow handoffs in .handoff/handoffs/, or "".

    Ages come from the file name's date prefix (mtimes reset on checkout).
    Fail-safe: any error -> "" so SessionStart still injects STATUS/RULES.
    """
    try:
        folder = os.path.join(base, "handoffs")
        if not os.path.isdir(folder):
            return ""
        names = sorted((n for n in os.listdir(folder)
                        if n.endswith(".md") and not n.startswith(".")
                        and os.path.isfile(os.path.join(folder, n))), reverse=True)
        if not names:
            return ""
        today = datetime.date.today()
        items = []
        for name in names[:HANDOFFS_SHOWN]:
            m = DATE_PREFIX.match(name)
            try:
                days = (today - datetime.date.fromisoformat(m.group(1))).days if m else None
            except ValueError:
                days = None
            if days is None:
                age = "undated"
            elif days <= 0:
                age = "today"
            else:
                age = "{} day{} old".format(days, "" if days == 1 else "s")
            if days is None or days > HANDOFF_STALE_DAYS:
                age += ", verify before trusting"
            items.append("{} ({})".format(name, age))
        if len(names) > HANDOFFS_SHOWN:
            items.append("+{} more".format(len(names) - HANDOFFS_SHOWN))
        return ("\nOpen session handoffs in .handoff/handoffs/ — read the one for the "
                "work you continue, then delete it once absorbed: " + "; ".join(items))
    except Exception:
        return ""


def main():
    payload = read_stdin_json()
    if not payload:
        return
    root = project_root(payload)

    if has_handoff(root):
        # Capture the git baseline (HEAD sha + dirty paths with codes) so the
        # Stop hook can nudge about ALL changes made during this session —
        # committed or not — while ignoring pre-existing uncommitted dirt.
        # A resume or compaction continues the same session, so an existing
        # baseline is kept — re-capturing it would hide earlier session work.
        session_id = payload.get("session_id")
        keep = (payload.get("source") in ("resume", "compact")
                and load_baseline(session_id) is not None)
        codes = None if keep else git_status_codes(root)
        if codes is not None:
            save_baseline(session_id, git_head(root), codes)

        base = agent_base(root)
        parts = []
        for name in ("STATUS.md", "RULES.md"):
            body = read_file(os.path.join(base, name))
            if body:
                parts.append("===== .handoff/{} =====\n{}".format(name, body))
        if not parts:
            sys.exit(0)

        # Template-drift check: compare the install's stamped VERSION to the
        # plugin's. Mismatch nags each session; a MISSING stamp nags once per
        # repo ever (older installs predate the stamp).
        drift = ""
        pv = plugin_version()
        if pv:
            installed = read_file(os.path.join(base, "VERSION"))
            if installed and installed.strip() != pv:
                drift = ("\n\nhandoff: this repo's .handoff tree is stamped v{} "
                         "but the plugin is v{} — templates/hook expectations may have "
                         "drifted; consider a refresh (setup skill) and update "
                         ".handoff/VERSION.".format(installed.strip(), pv))
            elif not installed:
                vmarker = os.path.join(data_dir(), "nover-" + _short(os.path.abspath(root)))
                if not marker_seen(vmarker):
                    marker_set(vmarker)
                    drift = ("\n\nhandoff: this repo's .handoff has no VERSION stamp "
                             "(predates v1.4). Write the plugin version to "
                             ".handoff/VERSION to enable template-drift detection. "
                             "This tip shows only once for this repo.")

        context = (
            "Project context auto-loaded from .handoff (read before acting):\n\n"
            + "\n\n".join(parts)
            + POINTER
            + handoffs_line(base)
            + drift
        )
        emit("SessionStart", context)
        return

    # No .handoff — nudge once per repo, then stay silent forever.
    marker = os.path.join(data_dir(), "seen-" + _short(os.path.abspath(root)))
    if marker_seen(marker):
        sys.exit(0)
    marker_set(marker)
    emit(
        "SessionStart",
        "This repo has no handoff project memory. To enable durable STATUS, "
        "RULES, MAP, a task backlog, and folder-level CONTEXT.md, run the "
        "handoff setup skill (say \"set up handoff\" or /handoff:setup). "
        "This tip shows only once for this repo.",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
