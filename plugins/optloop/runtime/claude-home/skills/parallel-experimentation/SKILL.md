---
name: parallel-experimentation
description: Run several independent optimization candidates in isolated git worktrees while keeping acceptance serialized and state updates durable.
user-invocable: false
---

## Purpose

Increase throughput without corrupting the accepted code state.

## Rules

- The accepted code path is the only place where accepted changes may land.
- Each candidate should run in its own git worktree when the repo structure allows it.
- Acceptance is serialized through `.optloop-runtime/locks/accept.lock`.
- Search and implementation can be parallel; merging cannot.

## Bundled reference

- `examples/worktree-layout.md`
