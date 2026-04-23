---
name: optloop-logs
description: Show recent OptLoop supervisor logs for the current repository. Use when the user asks for OptLoop logs, recent controller output, debugging output, or the former /optloop:logs command.
---

# OptLoop Logs

## Action

Run one Bash command using the installed plugin root absolute path:

```text
bash <installed-plugin-root>/bin/optloop logs latest
```

Before calling Bash, replace `<installed-plugin-root>` with the absolute path
of this installed plugin directory. The final Bash command must not contain
shell expansion, command substitution, fallback probing, globs, or environment
variable references.

## Rules

- Do not tail indefinitely unless the user explicitly asks for live logs.
- Return the command output only.
