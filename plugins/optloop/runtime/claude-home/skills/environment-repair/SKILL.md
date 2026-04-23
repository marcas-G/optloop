---
name: environment-repair
description: Repair command execution problems that block repository optimization work from continuing benchmark design, review, candidate evaluation, commit, rollback, or recovery.
---

## Goal

Make a future work session able to continue. Repair the smallest credible
blocker without hiding real project failures.

## Repair Order

1. Read the failing command and full stderr.
2. Determine whether the failure is caused by:
   - missing dependency installation,
   - wrong interpreter,
   - PATH resolution,
   - missing environment variable,
   - wrong working directory,
   - broken relative imports,
   - stale generated artifacts,
   - repository script drift,
   - git/worktree state.
3. Choose a local repair, record it, and verify it when practical.
4. If no safe repair is possible, write a blocker and set the next action.

## Bundled Examples

- `examples/python-import-failure.md`
- `examples/path-resolution-failure.md`
