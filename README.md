# optloop-marketplace

Current plugin version: `0.1.28`

This repository contains the OptLoop marketplace plugin. The current implementation is an outer supervisor that runs in the host project and orchestrates Docker runtime containers plus in-container Claude workers.

## What It Does Now

- Starts a detached background supervisor (`optloop start` / `/optloop:start-loop`).
- Ensures a Docker container pool for the current repository.
- Uses `loop.parallel_candidates` as target container count.
- Optionally auto-starts one Claude worker loop per container (`execution.auto_start_claude=true` by default).
- Collects supervisor state, container state, worker state, and process view.
- Exposes status/doctor/logs/reset commands through both CLI and plugin skills.

## Runtime Model

1. `optloop-launch` runs `optloop-init` and starts `optloop start` in the background.
2. The runner loop:
   - increments `iteration`,
   - reconciles container count to `loop.parallel_candidates`,
   - probes/starts Claude worker supervisors in each container,
   - writes heartbeat and status.
3. If worker supervisors are not healthy, phase is set to `runtime_degraded`.

Container naming:

- Primary: `optloop-<repo-name>`
- Additional: `optloop-<repo-name>-2`, `-3`, ...

## Requirements

- Host:
  - `bash`
  - `python3` or `python`
  - Docker daemon reachable by current user
- Worker image:
  - Must contain Claude CLI (`claude`) and runtime deps.
  - `plugins/optloop/docker/Dockerfile.example` installs `@anthropic-ai/claude-code`.

## Authentication And Settings

Worker auth sources:

1. `ANTHROPIC_API_KEY` from host env (via `execution.passthrough_env`).
2. `ANTHROPIC_API_KEY` found in host settings file (if present) and injected as passthrough env.
3. Claude login credentials inside container runtime home.

If missing, worker state becomes `auth_missing` and retries slowly instead of tight failing loops.

By default, runtime sync also copies host auth files when found (`copy_user_auth=true`):

- `.credentials.json`
- `credentials.json`
- `auth.json`

Settings file behavior:

- OptLoop auto-detects host settings file in this order:
  1. `CLAUDE_SETTINGS_PATH` (if set)
  2. `~/.claude/settings.json`
  3. `~/.claude/setting.json`
- Detected path is written to `execution.settings_host_path` (if not already set) and mounted read-only into container at `execution.settings_container_path` (default `/opt/optloop-home/.claude/settings.json`).

## Commands

### Plugin skill surface

- `/optloop:start-loop`
- `/optloop:stop-loop`
- `/optloop:status`
- `/optloop:doctor`
- `/optloop:logs`
- `/optloop:reset-workspace`

### CLI surface

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

## Key Files In Target Repository

- `.optloop/config.json`
- `.optloop/status.json`
- `.optloop/live.ndjson`
- `.optloop/runner.pid`
- `.optloop/STOP`
- `.optloop/logs/controller.out`
- `.optloop/logs/claude-worker-<container>.log`
- `.optloop/runtime/home/.claude` (synced runtime template)
- `.optloop/runtime/workers/*.pid`
- `.optloop/runtime/claude_prompt.txt`

## Important Config Knobs

`.optloop/config.json`:

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
    "claude_restart_delay_sec": 15,
    "claude_prompt": "",
    "settings_host_path": "",
    "settings_container_path": "/opt/optloop-home/.claude/settings.json",
    "passthrough_env": ["ANTHROPIC_API_KEY"]
  }
}
```

## Observability

- `optloop status` shows:
  - supervisor summary table
  - container table
  - worker supervisor table
  - detected Claude process table
- `optloop logs latest` shows:
  - `controller.out`
  - tail of `live.ndjson`
  - tail of each `claude-worker-*.log`
- `optloop doctor` emits JSON diagnostics, including worker status and auth-related runtime signals.

## Current Scope And Boundaries

- Outer layer behavior is deterministic supervision and runtime orchestration.
- Repository-specific optimization decisions are executed by in-container Claude sessions and runtime instructions under `.optloop-runtime/`.
- This plugin does not expose a separate hard-coded benchmark acceptance engine in outer Python code.

## Quick Start

1. Install/update this plugin in Claude Code.
2. In your target repository, run `/optloop:start-loop`.
3. Check `/optloop:status` and `/optloop:logs`.
4. If worker state is `auth_missing`, provide `ANTHROPIC_API_KEY` or login in runtime context, then restart loop.
