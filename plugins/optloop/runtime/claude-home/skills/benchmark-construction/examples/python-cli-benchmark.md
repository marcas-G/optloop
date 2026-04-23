# Example: Python CLI benchmark

When a repository exposes a command-line entrypoint, a credible benchmark often looks like this:

- correctness command:
  - `python -m pytest tests/test_cli_output.py`
- benchmark command:
  - `python -m pytest tests/benchmarks/test_cli_benchmark.py --benchmark-json .optloop-runtime/results/cli.json`

Keep the benchmark focused on a real CLI invocation path. Avoid importing an internal helper directly unless the helper is already the repository's stable benchmark target.
