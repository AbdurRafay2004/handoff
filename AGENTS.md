# Repository instructions

Keep responses simple, clear, concise, and easy to follow. Break complex
information into small steps and avoid unnecessary details.

Read `CLAUDE.md` for the plugin architecture, hook invariants, and contribution
rules; they apply to Codex too. See `docs/CODEX.md` for host differences.

Run `python3 tests/test_hooks.py` before claiming a hook change works. Keep
hooks standard-library-only and fail-safe, preserve all Stop loop-breakers,
and never grant edit permissions from a context hook. Keep the Claude plugin,
Codex plugin, and marketplace versions in sync.
