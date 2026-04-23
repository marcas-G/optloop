# OptLoop Inner Runtime

This repository hosts the inner Claude runtime for continuous optimization.

Execution rules:
- Work only through the runtime state machine persisted under `.optloop-runtime/`.
- Never treat the current chat history as authoritative state. Read persisted state before acting.
- Never accept a candidate based on a single noisy benchmark run.
- Never keep a change that alters observable behavior without explicit matching evidence and guard approval.
- Never mutate the accepted code path directly for speculative experiments. Use isolated worktrees.
- Never stop after repeated failed attempts. Continue the controlled search-fail-reset cycle until an explicit stop signal is present.
- Prefer small, reversible changes over wide refactors.
- When benchmark assets are missing, derive them from the repository's actual execution paths and keep generated measurement assets under `.optloop-runtime/benchmarks/` unless the repository already has a clear benchmark location.

Startup discipline:
1. Run `python3 .claude/skills/optloop-core/scripts/ensure_runtime_layout.py` before reading or writing loop state.
2. Reconstruct the current phase from `.optloop-runtime/state.json` and `.optloop-runtime/events.jsonl`.
3. Use the subagents and skills in this repository; do not invent a parallel control system.
