---
name: evidence-logging
description: Record loop progress in structured runtime files so the optimization system can survive compaction, restart, and long unattended operation.
user-invocable: false
---

## Logging targets

Persist operational evidence in:
- `.optloop-runtime/state.json`
- `.optloop-runtime/events.jsonl`
- `.optloop-runtime/attempts/<attempt-id>/`
- `.optloop-runtime/baseline/`
- `.optloop-runtime/accepted/`

## Bundled references

- `examples/event-records.md`
- `examples/attempt-summary.md`
