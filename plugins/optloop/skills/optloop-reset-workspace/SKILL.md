---
name: optloop-reset-workspace
description: Reset OptLoop working state for the current repository. Use when the user asks to reset OptLoop, clear OptLoop state, reset workspace state, recover from a bad OptLoop run, or run the former /optloop:reset-workspace command.
---

# OptLoop Reset Workspace

## Action

Run exactly this shell block:

```bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop" reset
elif command -v optloop >/dev/null 2>&1; then
  bash "$(command -v optloop)" reset
else
  echo "optloop error: cannot locate optloop. Reinstall the optloop plugin." >&2
  exit 127
fi
```

## Rules

- Do not inspect repository files before resetting.
- Do not manually delete project files.
- Return the reset result only.
