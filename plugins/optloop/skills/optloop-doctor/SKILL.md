---
name: optloop-doctor
description: Run deterministic OptLoop diagnostics for the current repository. Use when the user asks to diagnose OptLoop, check Docker/runtime readiness, verify the worker image/container, or run the former /optloop:doctor command.
---

# OptLoop Doctor

## Action

Run one Bash command using the installed plugin root absolute path:

```text
bash <installed-plugin-root>/bin/optloop doctor
```

Before calling Bash, replace `<installed-plugin-root>` with the absolute path
of this installed plugin directory. The final Bash command must not contain
shell expansion, command substitution, fallback probing, globs, or environment
variable references.

## Rules

- Do not repair anything automatically.
- Return the diagnostics output only.
