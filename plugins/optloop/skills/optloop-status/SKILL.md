---
name: optloop-status
description: Show the current OptLoop supervisor status for a repository. Use when the user asks for OptLoop status, loop phase, runtime state, active container, or the former /optloop:status command.
---

# OptLoop Status

## Action

Run one Bash command using the installed plugin root absolute path:

```text
bash <installed-plugin-root>/bin/optloop status
```

Before calling Bash, replace `<installed-plugin-root>` with the absolute path
of this installed plugin directory. The final Bash command must not contain
shell expansion, command substitution, fallback probing, globs, or environment
variable references.

## Rules

- Do not infer status from chat history.
- Return the command output only.
