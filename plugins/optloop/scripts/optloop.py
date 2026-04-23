#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import filecmp
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from typing import Any, Dict, Optional

RUNTIME_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "runtime" / "claude-home"

DEFAULT_CONFIG: Dict[str, Any] = {
    "benchmarks": [
        {
            "name": "primary",
            "command": None,
            "direction": "lower",
            "sample_runs": 9,
            "warmup_runs": 1,
            "timeout_sec": 1800,
            "min_improvement_pct": 1.0,
            "noise_floor_pct": 0.35,
            "bootstrap_resamples": 1200,
            "weight": 1.0,
            "min_runtime_sec": 0.15,
            "max_cv_pct": 10.0,
        }
    ],
    "acceptance": {
        "require_primary_acceptance": True,
        "secondary_max_regression_pct": 0.35,
    },
    "validation": {
        "commands": [],
        "equivalence_commands": [],
        "require_clean_git": True,
        "forbid_paths": [".git/**", ".optloop/**"],
        "allow_generated_benchmark_under": ".optloop/benchmarks",
        "compare_stdout_exact": True,
        "compare_stderr_exact": True,
    },
    "loop": {
        "parallel_candidates": 2,
        "max_candidate_turns": 20,
        "max_bootstrap_turns": 20,
        "claude_model": "sonnet",
        "claude_effort": "medium",
        "sleep_between_iterations_sec": 5,
        "keep_rejected_worktrees": False,
        "use_bare_mode": False,
        "candidate_timeout_sec": 1800,
    },
    "runtime": {
        "enabled": True,
        "container_home": "/opt/optloop-home",
        "sync_template": True,
        "copy_user_settings": True,
        "overwrite_user_settings": True,
    },
    "execution": {
        "mode": "docker",
        "runtime": "docker",
        "image": "optloop-worker:latest",
        "network_mode": "bridge",
        "container_workspace": "/workspace",
        "container_home": "/tmp/optloop-home",
        "cpus": "2",
        "memory": "4g",
        "pids_limit": 512,
        "user": "",
        "mount_host_claude_dir": False,
        "settings_host_path": "",
        "settings_container_path": "/opt/optloop-home/.claude/settings.json",
        "passthrough_env": ["ANTHROPIC_API_KEY"],
        "extra_run_args": [],
    },
    "scaffold": {
        "benchmark_owner": ".optloop/benchmarks",
        "notes_file": ".optloop/README.md",
    },
    "workspace": {
        "auto_initial_commit": True,
        "auto_initial_commit_message": "[optloop] baseline snapshot",
        "allow_untracked_only_autocommit": True,
        "refuse_tracked_dirty_repo": True,
    },
}


class OptLoopError(RuntimeError):
    pass


def state_paths(repo: Path) -> Dict[str, Path]:
    base = repo / ".optloop"
    runtime_root = base / "runtime"
    runtime_home = runtime_root / "home"
    runtime_claude_dir = runtime_home / ".claude"
    return {
        "base": base,
        "config": base / "config.json",
        "status": base / "status.json",
        "live": base / "live.ndjson",
        "history": base / "history",
        "worktrees": base / "worktrees",
        "benchmarks": base / "benchmarks",
        "logs": base / "logs",
        "notes": base / "README.md",
        "runner_pid": base / "runner.pid",
        "stop": base / "STOP",
        "runtime_root": runtime_root,
        "runtime_home": runtime_home,
        "runtime_claude_dir": runtime_claude_dir,
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: Optional[Any] = None) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return copy.deepcopy(default)


def append_live(repo: Path, payload: Dict[str, Any]) -> None:
    paths = state_paths(repo)
    paths["live"].parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **payload}
    with paths["live"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_config(repo: Path) -> Dict[str, Any]:
    cfg = read_json(state_paths(repo)["config"], {})
    return deep_merge(DEFAULT_CONFIG, cfg)


def save_config(repo: Path, cfg: Dict[str, Any]) -> None:
    write_json(state_paths(repo)["config"], cfg)


def sync_tree_overlay(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            sync_tree_overlay(item, target)
        else:
            if not target.exists() or not filecmp.cmp(item, target, shallow=False):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)


def copy_user_settings_into_runtime(repo: Path, overwrite: bool = False) -> None:
    paths = state_paths(repo)

    user_settings = Path.home() / ".claude" / "settings.json"
    runtime_settings = paths["runtime_claude_dir"] / "settings.json"

    if not user_settings.exists():
        return

    runtime_settings.parent.mkdir(parents=True, exist_ok=True)

    if runtime_settings.exists() and not overwrite:
        return

    shutil.copy2(user_settings, runtime_settings)


def ensure_runtime_pack(repo: Path, cfg: Optional[Dict[str, Any]] = None) -> None:
    paths = state_paths(repo)
    paths["runtime_root"].mkdir(parents=True, exist_ok=True)
    paths["runtime_home"].mkdir(parents=True, exist_ok=True)
    paths["runtime_claude_dir"].mkdir(parents=True, exist_ok=True)

    sync_tree_overlay(RUNTIME_TEMPLATE_DIR, paths["runtime_claude_dir"])

    if cfg is None:
        cfg = load_config(repo)

    runtime_cfg = cfg.get("runtime", {})
    if runtime_cfg.get("copy_user_settings", True):
        copy_user_settings_into_runtime(
            repo,
            overwrite=runtime_cfg.get("overwrite_user_settings", True),
        )


def init_repo(repo: Path) -> None:
    paths = state_paths(repo)
    paths["base"].mkdir(parents=True, exist_ok=True)
    paths["history"].mkdir(parents=True, exist_ok=True)
    paths["worktrees"].mkdir(parents=True, exist_ok=True)
    paths["benchmarks"].mkdir(parents=True, exist_ok=True)
    paths["logs"].mkdir(parents=True, exist_ok=True)

    cfg = load_config(repo)
    execution_cfg = cfg.setdefault("execution", {})
    if execution_cfg.get("image") in {None, "", "optloop-worker:latest"}:
        execution_cfg["image"] = default_project_image(repo)
    ensure_runtime_pack(repo, cfg)
    save_config(repo, cfg)

    if not paths["status"].exists():
        write_json(paths["status"], {
            "phase": "idle",
            "iteration": 0,
            "accepted_total": 0,
            "rejected_total": 0,
            "active_candidates": {},
            "execution_mode": cfg["execution"]["mode"],
        })

    if not paths["live"].exists():
        paths["live"].write_text("", encoding="utf-8")

    if not paths["notes"].exists():
        paths["notes"].write_text(
            "# optloop working state\n\nThis directory is managed by the optloop plugin.\n",
            encoding="utf-8",
        )

    info_exclude = repo / ".git" / "info" / "exclude"
    if info_exclude.exists():
        current = info_exclude.read_text(encoding="utf-8")
        if ".optloop/" not in current:
            suffix = "" if current.endswith("\n") or current == "" else "\n"
            info_exclude.write_text(current + suffix + ".optloop/\n", encoding="utf-8")

    print(f"initialized {paths['base']}")


def set_status(repo: Path, **updates: Any) -> Dict[str, Any]:
    paths = state_paths(repo)
    status = read_json(paths["status"], {
        "phase": "idle",
        "iteration": 0,
        "accepted_total": 0,
        "rejected_total": 0,
        "active_candidates": {},
        "execution_mode": load_config(repo)["execution"]["mode"],
    })
    status.update(updates)
    status["updated_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_json(paths["status"], status)
    return status


def repo_key(repo: Path) -> str:
    return hashlib.sha1(str(repo.resolve()).encode("utf-8")).hexdigest()[:12]


def sanitize_name(raw: str) -> str:
    cleaned = []
    last_dash = False
    for ch in raw.lower():
        if ch.isalnum() or ch in {"_", ".", "-"}:
            cleaned.append(ch)
            last_dash = False
        elif not last_dash:
            cleaned.append("-")
            last_dash = True
    value = "".join(cleaned).strip("-")
    return value or "optloop"


def default_project_image(repo: Path) -> str:
    return f"optloop-{sanitize_name(repo.name)}:local"


def runtime_container_name(repo: Path) -> str:
    return f"optloop-{sanitize_name(repo.name)}"


def run(cmd: list[str], cwd: Optional[Path] = None, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
    )
    if check and proc.returncode != 0:
        raise OptLoopError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def docker_available() -> bool:
    try:
        proc = run(["docker", "info"], check=False)
        return proc.returncode == 0
    except Exception:
        return False


def docker_image_exists(image: str) -> bool:
    proc = run(["docker", "image", "inspect", image], check=False)
    return proc.returncode == 0


def docker_container_state(name: str) -> str:
    proc = run(["docker", "inspect", "-f", "{{.State.Status}}", name], check=False)
    if proc.returncode != 0:
        return "missing"
    return (proc.stdout or "").strip() or "unknown"


def ensure_runtime_container(repo: Path, cfg: Dict[str, Any]) -> str:
    if cfg["execution"].get("mode") != "docker":
        return "local"
    if not docker_available():
        raise OptLoopError("Docker is not available")

    image = str(cfg["execution"].get("image", "optloop-worker:latest"))
    if not docker_image_exists(image):
        raise OptLoopError(f"Docker image not found: {image}")

    ensure_runtime_pack(repo, cfg)
    paths = state_paths(repo)
    name = runtime_container_name(repo)
    state = docker_container_state(name)

    runtime_cfg = cfg.get("runtime", {})
    runtime_container_home = str(
        runtime_cfg.get("container_home", "/opt/optloop-home")
    ).strip()
    runtime_home_host = paths["runtime_home"]

    workspace = str(
        cfg["execution"].get("container_workspace", "/workspace")
    ).strip()

    settings_host = str(
        cfg["execution"].get("settings_host_path", "")
    ).strip()

    settings_container = str(
        cfg["execution"].get(
            "settings_container_path",
            f"{runtime_container_home}/.claude/settings.json",
        )
    ).strip()

    if state == "running":
        return name
    if state in {"created", "exited", "paused", "restarting"}:
        run(["docker", "start", name], check=True)
        return name

    cmd = [
        "docker", "run", "-d",
        "--name", name,
        "-w", workspace,
        "-e", f"HOME={runtime_container_home}",
        "-e", f"PYTHONPATH={workspace}:{workspace}/src",
        "-v", f"{repo}:{workspace}",
        "-v", f"{runtime_home_host}:{runtime_container_home}",
    ]

    network_mode = str(cfg["execution"].get("network_mode", "bridge")).strip()
    if network_mode:
        cmd += ["--network", network_mode]

    cpus = str(cfg["execution"].get("cpus", "")).strip()
    if cpus:
        cmd += ["--cpus", cpus]

    memory = str(cfg["execution"].get("memory", "")).strip()
    if memory:
        cmd += ["--memory", memory]

    pids_limit = str(cfg["execution"].get("pids_limit", "")).strip()
    if pids_limit:
        cmd += ["--pids-limit", pids_limit]

    user_value = str(cfg["execution"].get("user", "")).strip()
    if user_value:
        cmd += ["--user", user_value]

    for key in cfg["execution"].get("passthrough_env", []):
        val = os.environ.get(key)
        if val:
            cmd += ["-e", f"{key}={val}"]

    if settings_host:
        shp = Path(settings_host).expanduser()
        if shp.exists():
            cmd += ["-v", f"{shp}:{settings_container}:ro"]

    extra_run_args = cfg["execution"].get("extra_run_args", [])
    if isinstance(extra_run_args, list):
        cmd += [str(x) for x in extra_run_args]

    cmd += [image, "bash", "-lc", "sleep infinity"]
    run(cmd, check=True)
    return name


def stop_runtime_container(repo: Path) -> None:
    name = runtime_container_name(repo)
    state = docker_container_state(name)
    if state != "missing":
        run(["docker", "rm", "-f", name], check=False)


def read_pidfile(path: Path) -> Optional[int]:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError:
        return None
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def acquire_lock(repo: Path) -> None:
    pid_path = state_paths(repo)["runner_pid"]
    current = os.getpid()
    existing = read_pidfile(pid_path)
    if existing is not None:
        if existing == current:
            pid_path.write_text(str(current), encoding="utf-8")
            return
        if pid_is_alive(existing):
            raise OptLoopError(f"optloop is already running with pid {existing}. Use status/stop first.")
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(current), encoding="utf-8")


def release_lock(repo: Path) -> None:
    pid_path = state_paths(repo)["runner_pid"]
    existing = read_pidfile(pid_path)
    current = os.getpid()
    if existing is None or existing == current or not pid_is_alive(existing):
        try:
            pid_path.unlink()
        except FileNotFoundError:
            pass


def handle_signal_factory(repo: Path):
    def _handler(signum: int, frame: Any) -> None:
        stop_path = state_paths(repo)["stop"]
        stop_path.parent.mkdir(parents=True, exist_ok=True)
        stop_path.touch()
    return _handler


def loop(repo: Path) -> None:
    cfg = load_config(repo)
    init_repo(repo)
    acquire_lock(repo)
    signal.signal(signal.SIGTERM, handle_signal_factory(repo))
    signal.signal(signal.SIGINT, handle_signal_factory(repo))
    set_status(repo, phase="starting", execution_mode=cfg["execution"]["mode"])
    append_live(repo, {"event": "runner_started", "pid": os.getpid(), "execution_mode": cfg["execution"]["mode"]})
    stop_file = state_paths(repo)["stop"]
    try:
        while not stop_file.exists():
            container_name = ensure_runtime_container(repo, cfg)
            set_status(
                repo,
                phase="runtime_active",
                execution_mode=cfg["execution"]["mode"],
                runtime_container=container_name,
                last_reason="runtime container healthy",
            )
            append_live(repo, {"event": "runtime_heartbeat", "container": container_name})
            time.sleep(int(cfg["loop"].get("sleep_between_iterations_sec", 5)))
    finally:
        stop_runtime_container(repo)
        if stop_file.exists():
            try:
                stop_file.unlink()
            except OSError:
                pass
        set_status(repo, phase="stopped", last_reason="supervisor stopped")
        append_live(repo, {"event": "runner_stopped"})
        release_lock(repo)


def cmd_init(repo: Path) -> None:
    init_repo(repo)


def cmd_start(repo: Path) -> None:
    loop(repo)


def cmd_stop(repo: Path) -> None:
    paths = state_paths(repo)
    paths["base"].mkdir(parents=True, exist_ok=True)

    pid = read_pidfile(paths["runner_pid"])
    paths["stop"].touch()

    if pid and pid_is_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        deadline = time.time() + 10
        while time.time() < deadline and pid_is_alive(pid):
            time.sleep(0.2)
        if pid_is_alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    stop_runtime_container(repo)
    release_lock(repo)
    set_status(repo, phase="stopped", last_reason="stop requested")
    print("stopped")


def cmd_status(repo: Path) -> None:
    init_repo(repo)
    status = read_json(state_paths(repo)["status"], {})
    print(json.dumps(status, indent=2, ensure_ascii=False))


def cmd_doctor(repo: Path) -> None:
    init_repo(repo)
    cfg = load_config(repo)
    paths = state_paths(repo)
    runtime_name = runtime_container_name(repo)
    info = {
        "repo": str(repo),
        "git_clean": True,
        "execution_mode": cfg["execution"].get("mode"),
        "docker_visible": docker_available(),
        "runtime_pack_present": paths["runtime_claude_dir"].exists(),
        "runtime_home_host": str(paths["runtime_home"]),
        "runtime_claude_dir": str(paths["runtime_claude_dir"]),
        "use_bare_mode": cfg["loop"].get("use_bare_mode"),
        "settings_container_path": cfg["execution"].get("settings_container_path"),
        "runtime_container_name": runtime_name,
        "runtime_container_state": docker_container_state(runtime_name),
        "worker_image": cfg["execution"].get("image"),
        "worker_image_present": docker_image_exists(str(cfg["execution"].get("image"))),
        "benchmarks": cfg.get("benchmarks", []),
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))


def cmd_logs(repo: Path, mode: str) -> None:
    log_path = state_paths(repo)["logs"] / "controller.out"
    if mode == "latest":
        if not log_path.exists():
            print("No log file found")
            return
        print(log_path.read_text(encoding="utf-8")[-10000:])
        return
    if mode == "tail":
        if not log_path.exists():
            print("No log file found")
            return
        proc = subprocess.Popen(["tail", "-f", str(log_path)])
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
        return
    raise OptLoopError(f"Unknown logs mode: {mode}")


def cmd_reset(repo: Path) -> None:
    paths = state_paths(repo)
    cmd_stop(repo)
    for key in ["runner_pid", "stop", "status", "live"]:
        p = paths[key]
        if p.exists() and p.is_file():
            p.unlink()
    for key in ["history", "worktrees", "benchmarks", "logs", "runtime_root"]:
        p = paths[key]
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    init_repo(repo)
    set_status(repo, phase="idle", last_reason="workspace reset")
    print("reset complete")


def find_repo_root() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True)
    if proc.returncode == 0:
        return Path(proc.stdout.strip())
    return Path.cwd()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="optloop")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    sub.add_parser("doctor")
    logs = sub.add_parser("logs")
    logs.add_argument("mode", nargs="?", default="latest", choices=["latest", "tail"])
    sub.add_parser("reset")
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo = find_repo_root()
    try:
        if args.cmd == "init":
            cmd_init(repo)
        elif args.cmd == "start":
            cmd_start(repo)
        elif args.cmd == "stop":
            cmd_stop(repo)
        elif args.cmd == "status":
            cmd_status(repo)
        elif args.cmd == "doctor":
            cmd_doctor(repo)
        elif args.cmd == "logs":
            cmd_logs(repo, args.mode)
        elif args.cmd == "reset":
            cmd_reset(repo)
        else:
            parser.error(f"Unknown command: {args.cmd}")
        return 0
    except OptLoopError as exc:
        print(f"optloop error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
