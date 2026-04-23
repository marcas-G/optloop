---
name: optloop-start-loop
description: Start the OptLoop background supervisor for the current repository. Use when the user asks to start OptLoop, launch the optimization loop, run the supervisor, or run the former /optloop:start-loop command.
---

# OptLoop Start Loop

## Action

Run exactly this shell block:

```bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop-launch" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop-launch"
elif command -v optloop-launch >/dev/null 2>&1; then
  bash "$(command -v optloop-launch)"
else
  echo "optloop error: cannot locate optloop-launch. Reinstall the optloop plugin." >&2
  exit 127
fi
```

## Rules

- Do not inspect repository files before launching.
- Do not diagnose benchmark readiness in the foreground session.
- Report only whether the launch succeeded.
