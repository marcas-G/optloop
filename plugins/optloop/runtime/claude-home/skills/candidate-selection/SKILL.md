---
name: candidate-selection
description: Select and scope one optimization hypothesis at a time, preferring reversible changes tied to measured or obvious cost centers.
user-invocable: false
---

## Candidate sources

Use these sources, in order of confidence:
1. profile or benchmark output identifying a hot path,
2. repeated allocations or serialization overhead,
3. redundant work in loops,
4. unnecessary copying or conversions,
5. avoidable blocking I/O on the measured path,
6. obvious algorithmic waste,
7. configuration-level runtime improvements.

## One-hypothesis rule

Each attempt should have one primary hypothesis. If a candidate idea unfolds into multiple changes, split them into separate attempts whenever possible.
