---
name: parallel-experimentation
description: Run independent optimization attempts in isolated git worktrees or equivalent directories while keeping commits and rollback state durable.
---

## Purpose

Parallel work may improve throughput, but isolation and commit discipline must
be explicit. Do not defer candidate judgment or merge discipline.

## Rules

- Prefer one isolated worktree or equivalent workspace per attempt.
- Do not let two candidates edit the same accepted checkout at the same time.
- Serialize commits through `.optloop-runtime/locks/accept.lock` or an
  equivalent recorded lock.
- If parallel attempts are based on an old accepted revision, either revalidate
  them before commit or reject/requeue them.
- Record workspace paths in the attempt directory.

## Bundled Reference

- `examples/worktree-layout.md`
