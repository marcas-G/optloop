---
name: optloop-stop-loop
description: Stop the OptLoop background supervisor for the current repository. Use when the user asks to stop OptLoop, halt the optimization loop, stop the supervisor, or run the former /optloop:stop-loop command.
---

# OptLoop Stop Loop

## Action

Run exactly this shell block:

```bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop" stop
elif command -v optloop >/dev/null 2>&1; then
  bash "$(command -v optloop)" stop
else
  echo "optloop error: cannot locate optloop. Reinstall the optloop plugin." >&2
  exit 127
fi
```

## Rules

- Do not inspect repository files before stopping.
- Return the stop result only.
