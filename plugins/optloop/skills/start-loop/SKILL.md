---
name: start-loop
description: Start the optloop supervisor in the background.
disable-model-invocation: true
---

Run exactly:

```bash
optloop-launch
```

Rules:
1. Do not inspect the repository.
2. Do not attempt benchmark repair in the foreground session.
3. Do not read project files or logs automatically after launch.
4. Only report whether launch succeeded.
5. Tell the user to use `/optloop:status` or `/optloop:logs`.
