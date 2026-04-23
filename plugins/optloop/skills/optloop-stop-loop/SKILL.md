---
name: optloop-stop-loop
description: Stop the OptLoop background supervisor for the current repository. Use when the user asks to stop OptLoop, halt the optimization loop, stop the supervisor, or run the former /optloop:stop-loop command.
---

# OptLoop Stop Loop

## Action

Run one Bash command using the installed plugin root absolute path:

```text
bash <installed-plugin-root>/bin/optloop stop
```

Before calling Bash, replace `<installed-plugin-root>` with the absolute path
of this installed plugin directory. The final Bash command must not contain
shell expansion, command substitution, fallback probing, globs, or environment
variable references.

## Rules

- Do not inspect repository files before stopping.
- Return the stop result only.
