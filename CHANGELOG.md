# Changelog

## 2.1.0 — 2026-10-08

- Add a Codex manifest alongside the Claude manifest, using the same skills,
  hooks, templates, and marketplace.
- Read all file headers in Codex `apply_patch` inputs, including moves, and
  inject each affected folder's notes once per session.
- Find the git root when the host starts in a subfolder; resolve patch paths
  against the actual working directory. Ignore paths that escape through symlinks.
- Emit the supported Stop continuation response for both hosts, preserving
  the active-hook guard, session baseline, and signature cooldown.
- Support Codex's `PLUGIN_DATA` directory, silent malformed-input handling,
  host-specific setup fallbacks, and portable workflow instructions.
- Expand subprocess regression coverage for both hook contracts.
