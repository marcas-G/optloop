---
name: optloop-logs
description: Show recent OptLoop supervisor logs for the current repository. Use when the user asks for OptLoop logs, recent controller output, debugging output, or the former /optloop:logs command.
---

# OptLoop Logs

## Action

Run exactly this shell block:

```bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop" logs latest
elif command -v optloop >/dev/null 2>&1; then
  bash "$(command -v optloop)" logs latest
else
  echo "optloop error: cannot locate optloop. Reinstall the optloop plugin." >&2
  exit 127
fi
```

## Rules

- Do not tail indefinitely unless the user explicitly asks for live logs.
- Return the command output only.
