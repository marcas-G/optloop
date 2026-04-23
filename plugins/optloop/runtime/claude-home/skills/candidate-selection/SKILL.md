---
name: candidate-selection
description: Help choose and scope repository optimization attempts from project evidence, while keeping benchmark design, review method, and accept/reject decisions inside the current work.
---

## Candidate Sources

Use any project-specific evidence you judge relevant. Useful sources include:

1. Benchmark or profile output.
2. Real user path inspection.
3. Repeated allocations, parsing, serialization, or conversions.
4. Repeated work on measured hot paths.
5. Avoidable copying or data structure churn.
6. Avoidable blocking I/O.
7. Algorithmic waste.
8. Configuration or runtime setup that clearly affects the measured path.

## Attempt Scope

Prefer one primary hypothesis per attempt when practical. If a candidate becomes
several unrelated changes, split or reject it. If the project demands a broader
change, record why in attempt evidence.

## No Human Wait

When no strong candidate is obvious, record a failed search attempt or blocker
and choose the next exploration direction for the handoff.

## Bundled Example

- `examples/candidate-search-record.md`
