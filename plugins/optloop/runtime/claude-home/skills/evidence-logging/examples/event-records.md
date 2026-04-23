# Event record examples

Good event names:
- `baseline_refreshed`
- `candidate_selected`
- `candidate_rejected:no-meaningful-improvement`
- `candidate_accepted`
- `recovery_completed`

Each event should include:
- UTC timestamp
- phase
- attempt id if relevant
- concise message
- key payload fields needed for recovery
