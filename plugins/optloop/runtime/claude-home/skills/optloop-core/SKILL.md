---
name: optloop-core
description: Operating model for an autonomous optimization runtime that repeatedly generates candidates, benchmarks them, accepts only statistically supported improvements, and keeps trying after rejected attempts.
user-invocable: false
---

## Objective

Run a persistent performance-optimization loop that is conservative about acceptance and aggressive about cleanup and retry.

The system is successful when it does the following reliably:
- produces valid benchmark evidence,
- rejects noisy or behavior-changing candidates,
- keeps searching after failures,
- persists durable state outside the chat transcript.

## Required bundled tools

Use these support files from this skill directory:
- `scripts/ensure_runtime_layout.py` — create `.optloop-runtime/` when missing
- `scripts/render_runtime_status.py` — summarize the current runtime state
- `scripts/session_start.py` — continuity summary for hooks
- `scripts/session_stop.py` — durable stop marker for hooks
- `templates/default_state.json` — canonical initial state structure
- `examples/state-transitions.md` — phase usage reference

## State machine

Use these phases in `.optloop-runtime/state.json`:
- `uninitialized`
- `discovering`
- `repairing-environment`
- `building-benchmark`
- `baselining`
- `selecting-candidate`
- `implementing-candidate`
- `running-correctness`
- `running-benchmark`
- `judging`
- `accepting`
- `rejecting`
- `recovering`
- `paused`

A phase change should be accompanied by an event entry in `events.jsonl`.

## Loop invariants

1. Acceptance requires evidence.
2. Behavior beats performance.
3. Rollback is mandatory on rejection.
4. The loop does not self-terminate.
5. State belongs on disk.
