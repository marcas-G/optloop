# optloop-marketplace (clean outer-layer rebuild)

This is a lean rebuild of `optloop-marketplace` focused on the **outer supervisor** only.

## What this rebuild includes

- Detached/background supervisor launcher
- Isolated non-bare Docker Claude runtime home mounted into the container
- Command-surface style slash skills (`start-loop`, `stop-loop`, `status`, `doctor`, `logs`, `reset-workspace`)
- Runtime template sync into `.optloop/runtime/home/.claude`
- PID / STOP / status / live event handling
- Docker runtime container lifecycle (start/stop/health)
- Minimal logging and doctor output

## What this rebuild intentionally does NOT include yet

- Inner autonomous benchmark repair workflow
- Inner autonomous optimization loop
- Runtime-local agents / skills / MCP logic beyond placeholders
- Benchmark semantics in the outer layer

## Typical flow

1. Build the Docker image:
   ```bash
   docker build --no-cache -t optloop-worker:latest -f plugins/optloop/docker/Dockerfile.example .
   ```
2. Install/update the plugin in Claude Code.
3. In a target repo, run:
   ```bash
   optloop init
   optloop start
   optloop status
   ```

The supervisor will create `.optloop/` in the target repository, sync the runtime template into `.optloop/runtime/home/.claude`, and keep a Docker runtime container alive.
