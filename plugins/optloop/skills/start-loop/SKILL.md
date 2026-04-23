---
name: optloop-start-loop
description: Start the OptLoop background runner for the current repository. Use when the user asks to start OptLoop, launch the optimization work, start the background runner, or run the former /optloop:start-loop command.
---

# OptLoop Start Loop

## Action

Run one Bash command using the installed plugin root absolute path:

```text
bash <installed-plugin-root>/bin/optloop-launch
```

Before calling Bash, replace `<installed-plugin-root>` with the absolute path
of this installed plugin directory. The final Bash command must not contain
shell expansion, command substitution, fallback probing, globs, or environment
variable references.

## Rules

- Do not inspect repository files before launching.
- Do not diagnose benchmark readiness before launching.
- Report only whether the background launch succeeded.
