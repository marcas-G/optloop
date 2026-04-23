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
