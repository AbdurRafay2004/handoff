#!/usr/bin/env python3
"""Context inventory: what loads into an agent session for this project.

Usage: python3 context_inventory.py [project-path] [--json]

Lists, for Claude Code and Codex, the plugins (with their effective enabled
state for THIS project), MCP servers, and personal skills, plus a rough
per-session token estimate of the skill/agent/command descriptions each plugin
adds. The context-audit skill uses this to propose per-project disables.

Read-only. Prints names, scopes, transports, counts and sizes only — never
config values (env, headers, args, URLs), because those often hold secrets.
Every file read is best-effort: missing or malformed files are skipped.
Stdlib only; Python 3.8+.
"""
import json
import os
import re
import subprocess
import sys

CHARS_PER_TOKEN = 4
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---", re.S)
FIELD = re.compile(r"^(name|description):[ \t]*(.*?)(?=^[\w-]+:|\Z)", re.S | re.M)
TOML_SECTION = re.compile(r"^\s*\[([^\[\]]+)\]\s*$")
TOML_ENABLED = re.compile(r"^\s*enabled\s*=\s*(true|false)\s*$", re.I)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def norm(path):
    try:
        return os.path.realpath(path)
    except Exception:
        return path


def project_root(start):
    try:
        out = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return os.path.abspath(start)


def describe_tokens(path):
    """Rough tokens a skill/agent/command file adds via its name + description."""
    m = FRONTMATTER.search(read_text(path))
    if not m:
        return 0
    chars = sum(len(v.strip()) for _, v in FIELD.findall(m.group(1)))
    return (chars + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def md_files(folder, pattern_skill=False):
    if not os.path.isdir(folder):
        return []
    found = []
    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if pattern_skill:
            skill = os.path.join(full, "SKILL.md")
            if os.path.isfile(skill):
                found.append(skill)
        elif name.endswith(".md") and os.path.isfile(full):
            found.append(full)
    return found


def server_entries(mapping, scope):
    """[{name, scope, transport}] from an mcpServers mapping; values never kept."""
    out = []
    if not isinstance(mapping, dict):
        return out
    if isinstance(mapping.get("mcpServers"), dict):
        mapping = mapping["mcpServers"]
    for name, cfg in sorted(mapping.items()):
        cfg = cfg if isinstance(cfg, dict) else {}
        transport = cfg.get("type") or ("http" if cfg.get("url") else
                                        "stdio" if cfg.get("command") else "unknown")
        out.append({"name": str(name), "scope": scope, "transport": str(transport)})
    return out


def plugin_mcp(install):
    servers = server_entries(load_json(os.path.join(install, ".mcp.json")), "plugin")
    manifest = load_json(os.path.join(install, ".claude-plugin", "plugin.json"))
    ref = manifest.get("mcpServers")
    if isinstance(ref, dict):
        servers += server_entries(ref, "plugin")
    elif isinstance(ref, str) and os.path.normpath(ref) != ".mcp.json":
        servers += server_entries(load_json(os.path.join(install, ref)), "plugin")
    seen, unique = set(), []
    for s in servers:
        if s["name"] not in seen:
            seen.add(s["name"])
            unique.append(s)
    return unique


def claude_inventory(root, home):
    cdir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home, ".claude")
    layers = [
        (os.path.join(cdir, "settings.json"), "user settings"),
        (os.path.join(root, ".claude", "settings.json"), ".claude/settings.json"),
        (os.path.join(root, ".claude", "settings.local.json"), ".claude/settings.local.json"),
    ]
    enabled, decided = {}, {}
    for path, label in layers:
        ep = load_json(path).get("enabledPlugins")
        if isinstance(ep, dict):
            for key, val in ep.items():
                enabled[key] = bool(val)
                decided[key] = label

    installed = load_json(os.path.join(cdir, "plugins", "installed_plugins.json")).get("plugins")
    plugins = []
    root_n = norm(root)
    for key, records in sorted((installed if isinstance(installed, dict) else {}).items()):
        records = records if isinstance(records, list) else [records]
        install = None
        for rec in records:
            if not isinstance(rec, dict):
                continue
            scope = rec.get("scope", "user")
            if scope in ("local", "project") and norm(rec.get("projectPath") or "") != root_n:
                continue
            install = rec.get("installPath")
            break
        if not install:
            continue
        skills = md_files(os.path.join(install, "skills"), pattern_skill=True)
        agents = md_files(os.path.join(install, "agents"))
        commands = md_files(os.path.join(install, "commands"))
        plugins.append({
            "name": key,
            "enabled": enabled.get(key, False),
            "decided_by": decided.get(key, "not set (off)"),
            "skills": len(skills),
            "agents": len(agents),
            "commands": len(commands),
            "hooks": os.path.isfile(os.path.join(install, "hooks", "hooks.json")),
            "mcp_servers": plugin_mcp(install),
            "est_tokens": sum(describe_tokens(p) for p in skills + agents + commands),
        })

    # ~/.claude.json sits beside ~/.claude/, or inside CLAUDE_CONFIG_DIR when set.
    cfg_dir = cdir if os.environ.get("CLAUDE_CONFIG_DIR") else home
    cfg = load_json(os.path.join(cfg_dir, ".claude.json"))
    servers = server_entries(cfg.get("mcpServers"), "user")
    projects = cfg.get("projects") if isinstance(cfg.get("projects"), dict) else {}
    for path, entry in projects.items():
        if norm(path) == root_n and isinstance(entry, dict):
            servers += server_entries(entry.get("mcpServers"), "local")
    servers += server_entries(load_json(os.path.join(root, ".mcp.json")), "project (.mcp.json)")

    user_skills = [{"name": os.path.basename(os.path.dirname(p)), "est_tokens": describe_tokens(p)}
                   for p in md_files(os.path.join(cdir, "skills"), pattern_skill=True)]
    project_skills = [{"name": os.path.basename(os.path.dirname(p)), "est_tokens": describe_tokens(p)}
                      for p in md_files(os.path.join(root, ".claude", "skills"), pattern_skill=True)]
    return {"plugins": plugins, "mcp_servers": servers,
            "user_skills": user_skills, "project_skills": project_skills}


def codex_sections(path):
    """[(section_name, enabled_or_None)] from a TOML file, headers and flags only."""
    sections, current = [], None
    for line in read_text(path).splitlines():
        m = TOML_SECTION.match(line)
        if m:
            current = [m.group(1).strip(), None]
            sections.append(current)
            continue
        e = TOML_ENABLED.match(line)
        if e and current is not None:
            current[1] = e.group(1).lower() == "true"
    return sections


def split_dotted(name):
    parts, buf, quoted = [], "", False
    for ch in name:
        if ch == '"':
            quoted = not quoted
        elif ch == "." and not quoted:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    parts.append(buf.strip())
    return parts


def codex_inventory(root, home):
    chome = os.environ.get("CODEX_HOME") or os.path.join(home, ".codex")
    plugins, servers = {}, {}
    for path, scope in ((os.path.join(chome, "config.toml"), "user"),
                        (os.path.join(root, ".codex", "config.toml"), "project")):
        for name, flag in codex_sections(path):
            parts = split_dotted(name)
            if len(parts) == 2 and parts[0] == "plugins":
                plugins[parts[1]] = {"name": parts[1], "enabled": flag is not False, "scope": scope}
            elif len(parts) == 2 and parts[0] == "mcp_servers":
                servers[parts[1]] = {"name": parts[1], "enabled": flag is not False, "scope": scope}
    return {"plugins": [plugins[k] for k in sorted(plugins)],
            "mcp_servers": [servers[k] for k in sorted(servers)]}


def render(root, inv):
    c, x = inv["claude"], inv["codex"]
    lines = ["Context inventory for {}".format(root), ""]
    if c["plugins"]:
        lines.append("Claude Code plugins (est. tokens = skill/agent/command descriptions per session):")
        for p in sorted(c["plugins"], key=lambda p: (not p["enabled"], -p["est_tokens"])):
            mcp = ", ".join(s["name"] for s in p["mcp_servers"]) or "-"
            lines.append("  [{}] {}  ~{} tokens  skills={} agents={} commands={} hooks={}  "
                         "mcp: {}  (set by {})".format(
                             "on " if p["enabled"] else "off", p["name"], p["est_tokens"],
                             p["skills"], p["agents"], p["commands"],
                             "yes" if p["hooks"] else "no", mcp, p["decided_by"]))
        on = [p for p in c["plugins"] if p["enabled"]]
        lines.append("  enabled here: {} plugins, ~{} tokens of descriptions, {} plugin MCP "
                     "servers".format(len(on), sum(p["est_tokens"] for p in on),
                                      sum(len(p["mcp_servers"]) for p in on)))
    else:
        lines.append("No Claude Code plugins installed for this project.")
    if c["mcp_servers"]:
        lines.append("")
        lines.append("Claude Code MCP servers outside plugins:")
        for s in c["mcp_servers"]:
            lines.append("  {}  ({}, {})".format(s["name"], s["scope"], s["transport"]))
    for label, items in (("Personal skills (~/.claude/skills)", c["user_skills"]),
                         ("Project skills (.claude/skills)", c["project_skills"])):
        if items:
            lines.append("")
            lines.append("{}: {} skills, ~{} tokens".format(
                label, len(items), sum(i["est_tokens"] for i in items)))
            lines.append("  " + ", ".join(i["name"] for i in items))
    if x["plugins"] or x["mcp_servers"]:
        lines.append("")
        lines.append("Codex (config.toml; report only):")
        for p in x["plugins"]:
            lines.append("  plugin [{}] {}  ({})".format("on " if p["enabled"] else "off",
                                                       p["name"], p["scope"]))
        for s in x["mcp_servers"]:
            lines.append("  mcp    [{}] {}  ({})".format("on " if s["enabled"] else "off",
                                                       s["name"], s["scope"]))
    lines.append("")
    lines.append("Not visible here: claude.ai connectors and MCP tool definitions "
                 "(check the session's own tool list or /context).")
    return "\n".join(lines)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    root = project_root(args[0] if args else os.getcwd())
    home = os.path.expanduser("~")
    inv = {"project": root, "claude": claude_inventory(root, home),
           "codex": codex_inventory(root, home)}
    if "--json" in argv:
        print(json.dumps(inv, indent=2))
    else:
        print(render(root, inv))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:  # never a traceback full of local paths
        print("context inventory failed: {}".format(type(exc).__name__))
        sys.exit(1)
