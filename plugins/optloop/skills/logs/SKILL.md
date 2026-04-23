---
name: optloop-logs
description: Read recent OptLoop supervisor logs for the current repository without changing runtime state. Use when the user asks for OptLoop logs, recent controller output, or the former /optloop:logs command.
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

- This is a read-only terminal action.
- Do not tail indefinitely unless the user explicitly asks for live logs.
- Do not run any additional command after the logs command.
- Do not run init, doctor, start, stop, reset, repair, or cleanup commands in the same turn.
- Do not diagnose or fix errors shown in the logs unless the user separately asks for that.
- Return the log command output only, then stop.
