---
name: runtime-state-contract
description: Durable file contract for repository optimization work, including work-session state, benchmark and review manifests, attempts, evidence, commits, rollbacks, blockers, and event logs under `.optloop-runtime/`.
---

## State Directory Contract

The task source of truth lives under `.optloop-runtime/`. Do not rely on
chat-only state for optimization quality, benchmark choices, review decisions,
commits, or rollbacks.

Required directories:

- `attempts/`
- `accepted/`
- `rejected/`
- `baseline/`
- `locks/`
- `worktrees/`
- `benchmarks/`
- `results/`
- `blockers/`

Required files:

- `state.json`
- `events.jsonl`

Repository-specific design files:

- `benchmark-manifest.json`
- `review-policy.json`

Attempt directories should contain durable evidence such as:

- `summary.json`
- `decision.json`
- `commands.txt`
- `review-evidence.*`
- `benchmark-evidence.*`
- `diff.patch`
- command logs or artifact pointers

## Event Records

Append newline-delimited JSON to `events.jsonl`. Include at least timestamp,
phase, event name, attempt id when relevant, and a concise message.

## Schemas And Examples

- `schemas/runtime-state.schema.json`
- `schemas/benchmark-manifest.schema.json`
- `examples/state.example.json`
- `examples/attempt.example.json`
- `examples/decision.accept.example.json`
- `examples/decision.reject.example.json`
- `examples/blocker.example.json`
