# optloop-marketplace

Current plugin version: `0.1.35`

OptLoop is an outer supervisor plugin. It runs in the host repository, manages a Docker container pool, and keeps in-container Claude workers running in iterative optimization cycles.

## What It Does

- Starts a detached background supervisor (`optloop start` or `/optloop:start-loop`).
- Keeps container count aligned with `loop.parallel_candidates`.
- Optionally auto-starts one worker loop per container (`execution.auto_start_claude=true` by default).
- Tracks runtime state, worker health, logs, and container process visibility.
- Persists per-iteration history under `.optloop/history/<iteration>/`.

## Runtime Flow

1. `optloop-launch` runs `optloop-init`, then starts `optloop start` in the background.
2. Every loop iteration:
   - increments `iteration`,
   - reconciles runtime containers,
   - probes/starts container workers,
   - writes status + live events,
   - captures iteration history artifacts.
3. If workers are not healthy, phase is `runtime_degraded`.

Container naming:

- Primary: `optloop-<repo-name>`
- Additional: `optloop-<repo-name>-2`, `optloop-<repo-name>-3`, ...

## Requirements

Host:

- `bash`
- `python3` or `python`
- Docker daemon accessible by the current user

Worker image:

- `claude` CLI available in container
- runtime dependencies installed
- reference image: `plugins/optloop/docker/Dockerfile.example`

## Authentication and Settings

Primary auth path is `ANTHROPIC_AUTH_TOKEN`.

Credential sources used by workers:

1. Host env vars from `execution.passthrough_env`
2. `env` entries read from host settings file and passed through
3. Runtime home auth files (`auth.json`, `credentials.json`, etc.)

Settings discovery order:

1. `CLAUDE_SETTINGS_PATH`
2. `~/.claude/settings.json`
3. `~/.claude/setting.json`

Detected settings path is written to `execution.settings_host_path` and mounted read-only to `execution.settings_container_path` (default `/opt/optloop-home/.claude/settings.json`).

## Commands

Plugin commands:

- `/optloop:start-loop`
- `/optloop:stop-loop`
- `/optloop:status`
- `/optloop:doctor`
- `/optloop:logs`
- `/optloop:reset-workspace`

CLI commands:

```bash
optloop init
optloop start
optloop stop
optloop status
optloop status --json
optloop doctor
optloop logs latest
optloop logs tail
optloop reset
```

## Files Written Under Target Repo

State:

- `.optloop/config.json`
- `.optloop/status.json`
- `.optloop/live.ndjson`
- `.optloop/runner.pid`
- `.optloop/STOP`

Logs:

- `.optloop/logs/controller.out`
- `.optloop/logs/claude-worker-<container>.log`

Per-iteration archive:

- `.optloop/history/<iteration>/summary.json`
- `.optloop/history/<iteration>/status.snapshot.json`
- `.optloop/history/<iteration>/git.status.txt`
- `.optloop/history/<iteration>/git.diff.patch`
- `.optloop/history/<iteration>/git.diff.staged.patch`
- `.optloop/history/<iteration>/controller.tail.log` (if available)
- `.optloop/history/<iteration>/worker-<container>.tail.log` (if available)

Runtime pack:

- `.optloop/runtime/home/.claude`
- `.optloop/runtime/workers/*.pid`
- `.optloop/runtime/claude_prompt.txt`

## Important Config

Example `.optloop/config.json` fields:

```json
{
  "loop": {
    "parallel_candidates": 2,
    "sleep_between_iterations_sec": 5
  },
  "execution": {
    "mode": "docker",
    "image": "optloop-<repo>:local",
    "auto_start_claude": true,
    "claude_command": "claude",
    "claude_skip_permissions": true,
    "auth_precheck_mode": "warn",
    "claude_restart_delay_sec": 15,
    "settings_host_path": "",
    "settings_container_path": "/opt/optloop-home/.claude/settings.json",
    "passthrough_env": [
      "ANTHROPIC_AUTH_TOKEN",
      "ANTHROPIC_BASE_URL",
      "ANTHROPIC_DEFAULT_SONNET_MODEL"
    ]
  }
}
```

## Observability

- `optloop status`: summary, containers, workers, and detected Claude processes
- `accepted_total` / `rejected_total` are sourced from `.optloop-runtime/state.json` (`accepted_count` / `rejected_count`) with fallback to counting JSON files under `.optloop-runtime/accepted` and `.optloop-runtime/rejected`.
- `active_candidates` is sourced from `.optloop-runtime/state.json.current_attempt`.
- `optloop logs latest`: controller log + live events + worker log tails
- `optloop doctor`: resolved settings/auth signals and runtime diagnostics

Typical phases:

- `runtime_active`
- `runtime_degraded`
- `stopped`

## Quick Start

1. Install or update plugin in Claude Code.
2. In target repo, run `/optloop:start-loop`.
3. Check `/optloop:status` and `/optloop:logs`.
4. If `auth_missing` appears, provide `ANTHROPIC_AUTH_TOKEN` (and base URL/model env when needed), then restart the loop.
