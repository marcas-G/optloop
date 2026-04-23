---
name: optloop-status
description: Show the current OptLoop supervisor status for a repository. Use when the user asks for OptLoop status, loop phase, runtime state, active container, or the former /optloop:status command.
---

# OptLoop Status

## Action

Run exactly this shell block:

```bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop" status
elif command -v optloop >/dev/null 2>&1; then
  bash "$(command -v optloop)" status
else
  echo "optloop error: cannot locate optloop. Reinstall the optloop plugin." >&2
  exit 127
fi
```

## Rules

- Do not infer status from chat history.
- Return the command output only.
