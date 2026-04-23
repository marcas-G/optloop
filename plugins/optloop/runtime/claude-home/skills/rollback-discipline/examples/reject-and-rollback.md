# Reject and rollback example

Use this pattern when a candidate does not have enough evidence to keep.

1. Preserve attempt files under `.optloop-runtime/attempts/<attempt-id>/`.
2. Write `decision.json` with `decision: "reject"`.
3. Save a diff or changed-file list if useful for future learning.
4. Undo candidate edits using the method that fits the repository:
   - remove the attempt worktree,
   - reset the attempt branch,
   - reverse the patch,
   - or commit a recorded revert when that is the safest local option.
5. Append an event such as `candidate_rejected` or `rollback_completed`.
6. Update `state.json`:
   - `phase`: `selecting-candidate` or `recovering`
   - `last_rejected_attempt`: current attempt id
   - `rejected_count`: incremented when practical
   - `current_attempt`: `null`
   - `next_action`: the next exploration or repair step

If rollback itself fails, write a blocker under `.optloop-runtime/blockers/` and
set `phase` to `blocked` or `recovering`.
