---
name: statistical-acceptance
description: Decide whether repeated benchmark samples justify keeping an optimization candidate, using a minimum meaningful improvement threshold and uncertainty-aware acceptance.
user-invocable: false
---

## Required bundled tool

Use:
- `scripts/metric_gate.py`

This script accepts JSON files containing either a bare list of samples or an object with a `samples` list.

## Default policy

Unless the benchmark manifest says otherwise, use:
- confidence: `0.95`
- minimum relative improvement: `0.03`
- decision set: `ACCEPT`, `REJECT`, `RERUN`

## Fixtures

Use the JSON fixtures in `fixtures/` to sanity-check the script or to understand accepted and rejected sample patterns.
