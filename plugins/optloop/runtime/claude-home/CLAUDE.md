# Repository Optimization Workspace

This Claude home contains instructions for unattended repository optimization.
Treat the current Claude Code session as an independent work session. Do not
infer how or why the session was started.

Use files under `.optloop-runtime/` as the only handoff channel. Previous work,
unfinished decisions, blockers, benchmark choices, review choices, commits, and
rollbacks must be reconstructed from those files and the repository itself.

## Session Discipline

- Read durable state before acting.
- Complete one coherent unit of work.
- Persist state, evidence, and logs before exiting.
- If blocked, write the blocker to durable state and exit.
- Never ask for human input.
- Do not wait idly for future work.

## Durable State

Use `.optloop-runtime/` as the source of truth. Never treat current chat history
as authoritative.

Before acting:

1. Run `python3 .claude/skills/optloop-core/scripts/ensure_runtime_layout.py`.
2. Read `.optloop-runtime/state.json`.
3. Read the tail of `.optloop-runtime/events.jsonl`.
4. Inspect `git status`.
5. Decide the next useful action from persisted state.

## Responsibility

Within the current session, make the best progress you can on the optimization
task:

- design or repair benchmarks,
- choose metrics and workloads,
- design code review checks,
- repair environment failures,
- create and evaluate candidates,
- run benchmark and review procedures,
- accept and commit improvements when your evidence supports it,
- reject and roll back failures,
- update durable state,
- record a handoff for future work.

Use the bundled agents and skills as helpers. Do not rely on hidden channels or
assumptions outside `.optloop-runtime/`.

## Persistence Rule

Do not write a terminal `done` state merely because optimization is difficult,
because no obvious candidate exists, or because recent attempts failed. Record
the failed attempt or blocker, set a useful `next_action`, and exit cleanly.
