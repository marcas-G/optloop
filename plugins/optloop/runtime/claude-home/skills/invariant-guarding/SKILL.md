---
name: invariant-guarding
description: Protect correctness, supported input coverage, API behavior, and safety while optimizing. Use to detect or prevent benchmark gaming and behavior-changing edits.
user-invocable: false
---

## Forbidden acceptance patterns

Reject a candidate if it achieves speed by any of the following:
- skipping validation or error handling,
- reducing supported input shapes or sizes,
- changing output meaning or ordering semantics unless explicitly allowed,
- changing numerical precision or rounding policy without approval,
- caching stale or invalid results,
- moving work out of the benchmark without preserving end-to-end semantics,
- hard-coding assumptions that only fit the benchmark input.

## Bundled checklist

Use `examples/review-checklist.md` on every candidate.
