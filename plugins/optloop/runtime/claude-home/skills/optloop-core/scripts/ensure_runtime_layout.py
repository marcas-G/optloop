#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

REQUIRED_DIRS = ["attempts", "accepted", "baseline", "locks", "worktrees", "benchmarks"]


def detect_repo_root() -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd().resolve()


def default_state(root: Path) -> dict:
    template = root / ".claude" / "skills" / "optloop-core" / "templates" / "default_state.json"
    return json.loads(template.read_text(encoding="utf-8"))


def ensure_layout(root: Path, create: bool = True) -> Path:
    runtime = root / ".optloop-runtime"
    if not runtime.exists() and not create:
        return runtime

    if create:
        runtime.mkdir(parents=True, exist_ok=True)
        for rel in REQUIRED_DIRS:
            (runtime / rel).mkdir(parents=True, exist_ok=True)

        state_path = runtime / "state.json"
        if not state_path.exists():
            state_path.write_text(json.dumps(default_state(root), indent=2) + "\n", encoding="utf-8")

        events_path = runtime / "events.jsonl"
        if not events_path.exists():
            events_path.write_text("", encoding="utf-8")

    return runtime


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure .optloop-runtime exists and has required files.")
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument("--no-create", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve() if args.root else detect_repo_root()
    ensure_layout(root, create=not args.no_create)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
