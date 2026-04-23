---
name: optloop-core
description: Operating model for one bounded repository optimization work session where Claude reconstructs context from `.optloop-runtime/`, makes one coherent optimization step, and persists a handoff for future work.
---

## Objective

Complete one useful work session for unattended repository optimization. Do not
assume hidden memory or outside coordination. Use `.optloop-runtime/` as the
handoff medium.

The session is successful when it:

- reconstructs state from disk,
- decides the next useful action,
- performs one coherent unit of work,
- persists evidence and state,
- records a clear `next_action`.

## Required Bundled Tools

Use these support files from this skill directory:

- `scripts/ensure_runtime_layout.py` to create `.optloop-runtime/` when missing.
- `scripts/render_runtime_status.py` to summarize durable state.
- `scripts/session_start.py` for continuity context.
- `scripts/session_stop.py` for session stop records.
- `templates/default_state.json` as canonical initial state.
- `examples/state-transitions.md` as phase guidance.
- `references/work-session-handoff.md` when deciding how much work this session should do.

## State Machine

Use these phases in `.optloop-runtime/state.json`:

- `uninitialized`
- `discovering`
- `designing-benchmark`
- `repairing-environment`
- `baselining`
- `selecting-candidate`
- `implementing-candidate`
- `reviewing-candidate`
- `running-benchmark`
- `judging`
- `accepting`
- `committing`
- `rejecting`
- `rolling-back`
- `recovering`
- `blocked`

Do not create a terminal `done` phase. A phase change should append an event to
`.optloop-runtime/events.jsonl`.

## Work Session Rules

1. Read durable state before acting.
2. Do not ask for human input.
3. Do not defer benchmark, review, accept, reject, commit, or rollback judgment.
4. Decide benchmark, review, accept, reject, commit, and rollback in this task context.
5. Persist `next_action` before exiting.
6. If blocked, record the blocker and the recovery direction.
7. If no improvement is found, record the failed attempt and set `next_action`
   to continued exploration instead of declaring completion.

## Decision Scope

Benchmark design, code review design, metric choice, candidate implementation,
commit strategy, and rollback strategy are decisions to make from repository
evidence. Use scripts when they help; do not treat bundled scripts as the only
valid method.
