---
name: optloop-init-runtime
description: Initialize the OptLoop plugin runtime for a repository. Use when the user asks to prepare OptLoop, initialize runtime, build or start the OptLoop Docker container, repair plugin bin permissions, or run the former /optloop:init-runtime command.
---

# OptLoop Init Runtime

## Action

Run one Bash command using the installed plugin root absolute path:

```text
bash <installed-plugin-root>/bin/optloop-init
```

Before calling Bash, replace `<installed-plugin-root>` with the absolute path
of this installed plugin directory. The final Bash command must not contain
shell expansion, command substitution, fallback probing, globs, or environment
variable references.

## Rules

- Do not inspect repository files before running the command.
- Do not run benchmark logic or enter the optimization loop.
- Return the initializer output only.
