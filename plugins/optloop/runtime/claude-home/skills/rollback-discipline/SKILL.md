---
name: rollback-discipline
description: Guide rejection, interruption, or rollback of repository optimization attempts, preserving evidence while preventing rejected changes from leaking into future work.
---

## Principle

Rollback is part of rejection. Rejection without cleanup and evidence is a task
failure.

## Required Actions On Rejection

1. Preserve the attempt evidence directory.
2. Record the decision and reason.
3. Undo candidate edits by the method appropriate for the repository: git
   worktree removal, reset, revert, patch reversal, or another recorded method.
4. Release attempt-local locks.
5. Update `.optloop-runtime/state.json`.
6. Append an event entry.
7. Set `next_action` so future work can continue.

## Interrupted Work

If cleanup cannot be completed in this session, record a blocker under
`.optloop-runtime/blockers/` and set the next action to recovery.

## Bundled Example

- `examples/reject-and-rollback.md`
