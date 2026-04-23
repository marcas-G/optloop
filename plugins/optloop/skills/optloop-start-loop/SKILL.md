---
name: optloop-start-loop
description: Start OptLoop for the current repository by opening Claude Code in the runtime container as a foreground interactive process. Use when the user asks to start OptLoop, launch the optimization work, open the runtime window, or run the former /optloop:start-loop command.
---

# OptLoop Start

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
- Do not diagnose benchmark readiness before launching.
- Keep the launched container session in the foreground.
