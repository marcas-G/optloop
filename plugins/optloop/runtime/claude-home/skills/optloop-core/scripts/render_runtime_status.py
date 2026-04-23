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


def newest_json(path: Path):
    if not path.exists():
        return None, None
    for candidate in sorted(path.rglob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            return candidate, json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None, None


def tail_lines(path: Path, n: int = 5):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-n:]


def main() -> int:
    root = detect_repo_root()
    runtime = root / ".optloop-runtime"
    state_path = runtime / "state.json"
    if not state_path.exists():
        print("OptLoop runtime is not initialized in this repository.")
        return 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    latest_accept_path, latest_accept = newest_json(runtime / "accepted")
    latest_attempt_path, latest_attempt = newest_json(runtime / "attempts")
    event_tail = tail_lines(runtime / "events.jsonl", 5)

    print("## OptLoop Runtime Status")
    print(f"- repo: {root}")
    print(f"- phase: {state.get('phase')}")
    print(f"- status: {state.get('status')}")
    print(f"- current_attempt: {state.get('current_attempt')}")
    print(f"- accepted_count: {state.get('accepted_count')}")
    print(f"- rejected_count: {state.get('rejected_count')}")
    print(f"- aborted_count: {state.get('aborted_count')}")
    print(f"- stop_requested: {state.get('stop_requested')}")
    print(f"- primary_metric: {state.get('primary_metric')}")
    print(f"- metric_direction: {state.get('metric_direction')}")
    print(f"- benchmark_manifest: {state.get('benchmark_manifest')}")

    if latest_accept_path and latest_accept:
        print("\n## Latest accepted attempt")
        print(f"- file: {latest_accept_path.relative_to(root)}")
        print(f"- attempt_id: {latest_accept.get('attempt_id')}")
        print(f"- hypothesis: {latest_accept.get('hypothesis')}")
        print(f"- metric_summary: {latest_accept.get('metric_summary')}")

    if latest_attempt_path and latest_attempt:
        print("\n## Latest attempt record")
        print(f"- file: {latest_attempt_path.relative_to(root)}")
        print(f"- attempt_id: {latest_attempt.get('attempt_id')}")
        print(f"- result: {latest_attempt.get('result')}")
        print(f"- rejection_reason: {latest_attempt.get('rejection_reason')}")

    if event_tail:
        print("\n## Event tail")
        for line in event_tail:
            print(f"- {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
