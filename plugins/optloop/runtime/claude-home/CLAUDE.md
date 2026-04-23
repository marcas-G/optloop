This is the isolated Claude runtime home for optloop's inner Docker Claude.

Rules:
- This runtime is independent from the host user's ~/.claude.
- Project/problem solving happens inside the container.
- Outer optloop only provides lifecycle, execution, snapshots, logs, and monitoring.
- Future runtime-local agents, skills, MCP config, and plugins should be placed under this .claude directory.
