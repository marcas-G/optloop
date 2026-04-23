# Work Session Handoff

Use this reference when deciding how much work to do before writing a durable
handoff.

## Model

A Claude Code session should make progress, persist state, and stop after a
coherent unit of work. Do not rely on hidden memory or channels outside the
repository; only persistent files and repository contents are authoritative.

## Session Steps

1. Ensure `.optloop-runtime/` exists.
2. Read `state.json`, recent `events.jsonl`, and `git status`.
3. Choose the next action from durable state.
4. Do one coherent unit of work.
5. Write evidence and update state.
6. Append events.
7. Record `next_action`.

## Good Work Units

- Design or repair benchmark and review policy.
- Repair one blocking environment failure.
- Select one candidate hypothesis.
- Implement one candidate.
- Run review and benchmark for one candidate.
- Accept and commit one candidate.
- Reject and roll back one candidate.
- Recover from an interrupted state.

## Handoff Discipline

Before stopping, update:

- `phase`
- `status`
- `last_work_finished_at`
- `next_action`
- `last_blocker` when blocked

If the session runs out of time, record what was completed and what should
happen next. Partial durable progress is better than chat-only progress.
