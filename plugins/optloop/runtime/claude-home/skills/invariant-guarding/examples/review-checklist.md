# Review checklist

For each candidate, answer all of the following:
1. Does this diff alter public behavior?
2. Does it narrow valid inputs or edge-case handling?
3. Does it remove safety checks?
4. Does it change data freshness or consistency?
5. Does it introduce hidden global state?
6. Does it optimize a synthetic path but not the real workload?

If any answer is uncertain, reject and request more evidence.
