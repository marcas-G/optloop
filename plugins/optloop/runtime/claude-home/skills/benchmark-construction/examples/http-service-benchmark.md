# Example: HTTP service benchmark

When a repository exposes a service endpoint, a credible benchmark often looks like this:

- correctness command:
  - `pytest tests/test_api_contract.py`
- benchmark command:
  - start the service in an isolated process
  - issue repeated representative requests against a local port
  - write per-run latency samples to `.optloop-runtime/results/http_samples.json`

Do not replace end-to-end request handling with a direct function call unless the repository already treats that function as the canonical performance target.
