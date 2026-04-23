---
name: rollback-discipline
description: Ensure rejected or interrupted optimization attempts are reverted cleanly, with durable evidence preserved and no patch leakage into the accepted code path.
user-invocable: false
---

## Principle

Rejection without cleanup is a bug in the runtime.

## Required actions on rejection

1. Preserve the evidence directory.
2. Record the rejection category and short reason.
3. Hard-reset the attempt worktree or branch to the parent accepted state.
4. Delete or quarantine the attempt worktree.
5. Release any attempt-local locks.
6. Update `.optloop-runtime/state.json` and append an event entry.
