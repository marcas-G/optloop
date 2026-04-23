---
name: environment-repair
description: Repair command execution problems that block correctness or benchmark runs, with a bias toward minimal, local, reversible fixes.
user-invocable: false
---

## Goal

Make the required commands run without broadening scope or hiding breakage.

## Repair order

1. Read the failing command and full stderr.
2. Determine whether the failure is caused by:
   - missing dependency installation,
   - wrong interpreter,
   - PATH resolution,
   - missing environment variable,
   - wrong working directory,
   - broken relative imports,
   - stale generated artifacts,
   - repository script drift.
3. Prefer the smallest credible fix.

## Bundled examples

- `examples/python-import-failure.md`
- `examples/path-resolution-failure.md`
