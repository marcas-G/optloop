---
name: optloop-start-loop
description: Start OptLoop for the current repository by opening Claude Code in the runtime container as a foreground interactive process. Use when the user asks to start OptLoop, launch the optimization work, open the runtime window, or run the former /optloop:start-loop command.
---

# OptLoop Start

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
- Keep the launched container session in the foreground.
