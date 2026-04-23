---
name: benchmark-construction
description: Design, repair, and document repository-specific benchmarks, metrics, workloads, correctness checks, and review policy as project decisions made from repository evidence.
---

## Principle

The benchmark is a project design decision made from repository evidence.
Choose the scenario, metric, workload, correctness checks, and review policy
from the repository itself.

## Durable Outputs

Write or update:

- `.optloop-runtime/benchmark-manifest.json`
- `.optloop-runtime/review-policy.json`
- benchmark support files when needed
- event records explaining what changed and why

Useful bundled examples:

- `templates/benchmark-manifest.template.json`
- `examples/review-policy.example.json`
- `examples/python-backtest-manifest.example.json`

## Benchmark Selection

Prefer, in order:

1. Existing project benchmark targets.
2. Existing performance tests or CI performance jobs.
3. Repository-native benchmark tools.
4. A light custom harness that exercises a realistic user path.
5. A provisional benchmark when no better option is visible.

If the benchmark is provisional, say so in the manifest and keep improving it
across future work sessions.

## Manifest Guidance

The manifest should capture your reasoning:

- measured user scenario,
- primary metric and direction,
- why that metric matters,
- commands to run,
- sample strategy,
- correctness or equivalence checks,
- artifact paths,
- known weaknesses or next improvements.

The schema is intentionally permissive. Prefer useful durable memory over
fitting a rigid shape.

## Import Path Discipline

Generated Python benchmark scripts must be runnable from the repository root
without requiring package installation. Add a small path bootstrap near the top
before project imports:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "src"):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)
```

Use the equivalent local bootstrap for other ecosystems when needed.
