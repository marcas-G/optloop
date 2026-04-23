---
name: invariant-guarding
description: Design and run project-specific behavior review checks that protect correctness, supported input coverage, API behavior, and benchmark integrity while optimizing.
---

## Principle

Review policy is project-specific. Use this skill as prompts for risk
discovery, not as a complete fixed checklist.

## Common Failure Modes

Look for candidates that gain speed by:

- skipping validation or error handling,
- reducing supported input shapes or sizes,
- changing output meaning or ordering semantics,
- changing numerical precision or rounding policy,
- caching stale or invalid results,
- moving work out of the measured path without preserving end-to-end semantics,
- hard-coding assumptions that only fit benchmark input,
- weakening tests or benchmark difficulty.

## Durable Policy

When useful, write `.optloop-runtime/review-policy.json` with repository-specific
risks, equivalence checks, and review commands. Update it as the project is
understood better.

## Bundled Checklist

Use `examples/review-checklist.md` when it helps, but adapt it to the project.

Useful examples:

- `examples/review-checklist.md`
- `examples/review-evidence.example.json`
