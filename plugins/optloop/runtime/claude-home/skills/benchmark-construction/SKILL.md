---
name: benchmark-construction
description: Build or repair benchmark coverage that reflects real repository usage, produces repeated measurements, and includes a correctness gate for the same code path.
user-invocable: false
---

## Bundled support files

- `templates/benchmark-manifest.template.json` — starting structure for `.optloop-runtime/benchmark-manifest.json`
- `examples/python-cli-benchmark.md` — benchmark pattern for command-line Python repositories
- `examples/http-service-benchmark.md` — benchmark pattern for service-style repositories

## Benchmark selection order

Prefer in this order:
1. existing project benchmark targets,
2. existing performance tests in CI,
3. repository-native test or benchmark frameworks,
4. light custom harness under `.optloop-runtime/benchmarks/`.

A benchmark is acceptable only if:
- it exercises the code path that a user or upstream caller actually cares about,
- it can be run repeatedly,
- it produces a primary metric with a clear direction,
- it has a paired correctness gate,
- it is documented in `.optloop-runtime/benchmark-manifest.json`.

## Import path discipline

Generated Python benchmark scripts must be runnable from the repository root without requiring package installation. Add a small path bootstrap near the top before project imports:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "src"):
    value = str(candidate)
    if value not in sys.path:
        sys.path.insert(0, value)
```

Prefer this bootstrap for generated benchmark files under `benchmarks/` or `.optloop-runtime/benchmarks/` so `python benchmarks/name.py` works for both flat and `src/` Python layouts.
