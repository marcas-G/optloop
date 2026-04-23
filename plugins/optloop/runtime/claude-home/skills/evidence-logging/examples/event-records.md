# Event record examples

Useful event names:

- `work_started`
- `work_finished`
- `benchmark_strategy_updated`
- `review_policy_updated`
- `baseline_refreshed`
- `candidate_selected`
- `candidate_rejected`
- `candidate_accepted`
- `candidate_committed`
- `rollback_completed`
- `blocker_recorded`
- `recovery_completed`

Each event should include:

- UTC timestamp,
- phase,
- event name,
- attempt id if relevant,
- concise message,
- key payload fields needed for recovery.
