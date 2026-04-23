---
name: runtime-state-contract
description: File and schema contract for `.optloop-runtime/`, including state, attempts, baseline evidence, acceptance records, lockfiles, and event logs.
user-invocable: false
---

## Runtime directory contract

The durable state for the optimization loop lives under `.optloop-runtime/`.

Required directories:
- `attempts/`
- `accepted/`
- `baseline/`
- `locks/`
- `worktrees/`
- `benchmarks/`

Required files:
- `state.json`
- `events.jsonl`

Optional files:
- `benchmark-manifest.json`
- attempt-local evidence files

## Bundled schemas and examples

- `schemas/runtime-state.schema.json`
- `schemas/benchmark-manifest.schema.json`
- `examples/state.example.json`
- `examples/attempt.example.json`
