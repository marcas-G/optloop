---
name: evidence-logging
description: Record repository optimization progress in durable structured files so benchmark design, review design, candidate decisions, commits, rollbacks, blockers, and recovery survive context loss.
---

## Principle

If it matters to future work, write it to disk. Do not rely on chat-only
decisions.

## Logging Targets

Persist task evidence in:

- `.optloop-runtime/state.json`
- `.optloop-runtime/events.jsonl`
- `.optloop-runtime/attempts/<attempt-id>/`
- `.optloop-runtime/baseline/`
- `.optloop-runtime/accepted/`
- `.optloop-runtime/rejected/`
- `.optloop-runtime/blockers/`

## Attempt Evidence

Each attempt should record, when applicable:

- hypothesis,
- commands run,
- benchmark evidence,
- review evidence,
- changed files,
- accept/reject/block decision,
- commit id or rollback action,
- next action.

## Event Records

Append one JSON object per line. Include timestamp, phase, event, attempt id
when relevant, concise message, and data needed for recovery.

## Bundled References

- `examples/event-records.md`
- `examples/attempt-summary.md`
- `examples/work-summary.example.json`
