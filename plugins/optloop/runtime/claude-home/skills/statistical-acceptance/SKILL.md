---
name: statistical-acceptance
description: Provide optional statistical tools for repository optimization work when judging repeated benchmark samples; use when the project-specific evidence fits numeric repeated measurements, but do not treat this script as the only valid judgment method.
---

## Bundled Tool

Use when it fits the evidence:

- `scripts/metric_gate.py`

The script accepts JSON files containing either a bare list of samples or an
object with a `samples` list.

## Default Numeric Policy

When the benchmark manifest does not specify otherwise:

- confidence: `0.95`
- minimum relative improvement: `0.03`
- decision set: `ACCEPT`, `REJECT`, `RERUN`

## Freedom

If the project metric is not compatible with repeated numeric samples, use a
project-appropriate method and write the reasoning to attempt evidence. The
Make the final accept/reject/rerun/block judgment from all available evidence.

## Fixtures

Use the JSON fixtures in `fixtures/` to sanity-check the script or understand
accepted and rejected sample patterns.
