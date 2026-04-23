---
name: optloop-doctor
description: Run deterministic OptLoop diagnostics for the current repository. Use when the user asks to diagnose OptLoop, check Docker/runtime readiness, verify the worker image/container, or run the former /optloop:doctor command.
---

# OptLoop Doctor

## Action

Run exactly this shell block:

```bash
set -euo pipefail
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "${CLAUDE_PLUGIN_ROOT}/bin/optloop" ]; then
  bash "${CLAUDE_PLUGIN_ROOT}/bin/optloop" doctor
elif command -v optloop >/dev/null 2>&1; then
  bash "$(command -v optloop)" doctor
else
  echo "optloop error: cannot locate optloop. Reinstall the optloop plugin." >&2
  exit 127
fi
```

## Rules

- Do not repair anything automatically.
- Return the diagnostics output only.
