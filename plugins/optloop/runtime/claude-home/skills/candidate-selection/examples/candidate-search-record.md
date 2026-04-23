# Candidate search record example

Use this pattern when a work session searches for an optimization candidate.

```json
{
  "attempt_id": "attempt-0018",
  "phase": "selecting-candidate",
  "searched_at": "2026-04-23T10:00:00Z",
  "signals_checked": [
    "benchmark output",
    "hot loops in measured path",
    "repeated parsing and conversion",
    "avoidable allocations"
  ],
  "selected_hypothesis": "Avoid rebuilding the same lookup table for every row.",
  "why_this_candidate": "The lookup table is derived from immutable configuration and appears on the measured path.",
  "fallback_if_rejected": "Inspect serialization overhead in the same benchmark scenario."
}
```

If no useful hypothesis is found, record that as progress:

```json
{
  "attempt_id": "attempt-0019",
  "phase": "selecting-candidate",
  "searched_at": "2026-04-23T10:12:00Z",
  "selected_hypothesis": null,
  "result": "no-promising-candidate",
  "next_action": "collect a more informative profile for the benchmark scenario"
}
```
