#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def detect_repo_root() -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd().resolve()


def main() -> int:
    root = detect_repo_root()
    runtime = root / ".optloop-runtime"
    state_path = runtime / "state.json"
    if not state_path.exists():
        return 0

    stop_record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "state_path": str(state_path.relative_to(root))
    }
    (runtime / "last-work-stop.json").write_text(json.dumps(stop_record, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
