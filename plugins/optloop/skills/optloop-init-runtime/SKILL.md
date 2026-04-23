---
name: optloop-init-runtime
description: Initialize the OptLoop plugin runtime for a repository. Use when the user asks to prepare OptLoop, initialize runtime, build or start the OptLoop Docker container, repair plugin bin permissions, or run the former /optloop:init-runtime command.
---

# OptLoop Init Runtime

## Action

Run exactly this shell block:

```bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop-init" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop-init"
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop" init
elif command -v optloop-init >/dev/null 2>&1; then
  bash "$(command -v optloop-init)"
elif command -v optloop >/dev/null 2>&1; then
  bash "$(command -v optloop)" init
else
  echo "optloop error: cannot locate optloop-init or optloop. Reinstall the optloop plugin." >&2
  exit 127
fi
```

## Rules

- Do not inspect repository files before running the block.
- Do not run benchmark logic or enter the optimization loop.
- Return the initializer output only.
