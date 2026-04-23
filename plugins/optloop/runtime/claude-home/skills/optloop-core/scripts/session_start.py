#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def detect_repo_root() -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd().resolve()


def ensure_layout(root: Path) -> None:
    from pathlib import Path as _Path
    script = root / ".claude" / "skills" / "optloop-core" / "scripts" / "ensure_runtime_layout.py"
    if script.exists():
        import subprocess, sys
        subprocess.run([sys.executable, str(script), "--root", str(root)], check=False)


def main() -> int:
    root = detect_repo_root()
    ensure_layout(root)
    state_path = root / ".optloop-runtime" / "state.json"
    if not state_path.exists():
        return 0
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return 0

    print("## Durable repository optimization context")
    print(f"- phase: {state.get('phase')}")
    print(f"- status: {state.get('status')}")
    print(f"- current_attempt: {state.get('current_attempt')}")
    print(f"- accepted_count: {state.get('accepted_count')}")
    print(f"- rejected_count: {state.get('rejected_count')}")
    print(f"- stop_requested: {state.get('stop_requested')}")
    print(f"- next_action: {state.get('next_action')}")
    if state.get("last_blocker"):
        print(f"- last_blocker: {state.get('last_blocker')}")
    if state.get("primary_metric"):
        print(f"- primary_metric: {state.get('primary_metric')} ({state.get('metric_direction')})")
    if state.get("baseline_summary"):
        print(f"- baseline_summary: {state.get('baseline_summary')}")
    print("- persist progress before stopping.")
    print("- durable state is stored under `.optloop-runtime/`; prefer those files over transcript memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
