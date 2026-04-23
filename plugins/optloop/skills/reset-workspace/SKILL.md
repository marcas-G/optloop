---
name: optloop-reset-workspace
description: Reset OptLoop working state for the current repository. Use when the user asks to reset OptLoop, clear OptLoop state, reset workspace state, recover from a bad OptLoop run, or run the former /optloop:reset-workspace command.
---

# OptLoop Reset Workspace

## Action

Run one Bash command using the installed plugin root absolute path:

```text
bash <installed-plugin-root>/bin/optloop reset
```

Before calling Bash, replace `<installed-plugin-root>` with the absolute path
of this installed plugin directory. The final Bash command must not contain
shell expansion, command substitution, fallback probing, globs, or environment
variable references.

## Rules

- Do not inspect repository files before resetting.
- Do not manually delete project files.
- Return the reset result only.
