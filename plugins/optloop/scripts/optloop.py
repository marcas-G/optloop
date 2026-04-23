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
        "copy_user_auth": True,
        "overwrite_user_auth": False,
    },
    "execution": {
        "mode": "docker",
        "runtime": "docker",
        "image": "optloop-worker:latest",
        "auto_start_claude": True,
        "claude_command": "claude",
        "claude_skip_permissions": True,
        "auth_precheck_mode": "warn",
        "claude_restart_delay_sec": 15,
        "claude_prompt": "",
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
        "passthrough_env": [
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_API_KEY",
            "API_TIMEOUT_MS",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "OPENAI_API_KEY",
            "OPENROUTER_API_KEY",
            "AZURE_OPENAI_API_KEY",
        ],
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


DEFAULT_CLAUDE_AUTORUN_PROMPT = (
    "Run one autonomous repository optimization work session in /workspace.\n"
    "Use durable state under .optloop-runtime as the source of truth.\n"
    "Follow the instructions in $HOME/.claude/CLAUDE.md.\n"
    "Do not ask for human input.\n"
    "Complete one coherent step, persist evidence and state, then exit."
)


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


def worker_runtime_dir(repo: Path) -> Path:
    return state_paths(repo)["runtime_root"] / "workers"


def worker_pid_host_path(repo: Path, container_name: str) -> Path:
    return worker_runtime_dir(repo) / f"{container_name}.pid"


def worker_prompt_host_path(repo: Path) -> Path:
    return state_paths(repo)["runtime_root"] / "claude_prompt.txt"


def worker_log_host_path(repo: Path, container_name: str) -> Path:
    return state_paths(repo)["logs"] / f"claude-worker-{container_name}.log"


def worker_pid_container_path(container_name: str) -> str:
    return f"/workspace/.optloop/runtime/workers/{container_name}.pid"


def worker_prompt_container_path() -> str:
    return "/workspace/.optloop/runtime/claude_prompt.txt"


def worker_log_container_path(container_name: str) -> str:
    return f"/workspace/.optloop/logs/claude-worker-{container_name}.log"


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


def copy_user_settings_into_runtime(repo: Path, cfg: Optional[Dict[str, Any]] = None, overwrite: bool = False) -> None:
    paths = state_paths(repo)

    user_settings = resolve_settings_host_path(cfg)
    if user_settings is None:
        return
    runtime_settings = paths["runtime_claude_dir"] / "settings.json"

    runtime_settings.parent.mkdir(parents=True, exist_ok=True)

    if runtime_settings.exists() and not overwrite:
        return

    shutil.copy2(user_settings, runtime_settings)


def detect_host_claude_settings_path() -> Optional[Path]:
    env_path = os.environ.get("CLAUDE_SETTINGS_PATH", "").strip()
    if env_path:
        candidate = Path(env_path).expanduser()
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()

    homes: list[Path] = [Path.home()]
    env_home = os.environ.get("HOME", "").strip()
    if env_home:
        candidate_home = Path(env_home).expanduser()
        if candidate_home not in homes:
            homes.append(candidate_home)

    for home in homes:
        candidates = [
            home / ".claude" / "settings.json",
            home / ".claude" / "setting.json",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
    return None


def configured_settings_path_candidates(raw_path: str) -> list[Path]:
    raw = str(raw_path).strip()
    if not raw:
        return []

    variants: list[str] = [raw]
    slash_fixed = raw.replace("\\", "/")
    if slash_fixed not in variants:
        variants.append(slash_fixed)

    if slash_fixed.startswith("home/"):
        prefixed = f"/{slash_fixed}"
        if prefixed not in variants:
            variants.append(prefixed)

    candidates: list[Path] = []
    seen: set[str] = set()
    for item in variants:
        try:
            p = Path(item).expanduser()
        except Exception:
            continue
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(p)
    return candidates


def resolve_settings_host_path(cfg: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    if cfg is not None:
        execution = cfg.get("execution", {})
        configured = str(execution.get("settings_host_path", "")).strip()
        if configured:
            for candidate in configured_settings_path_candidates(configured):
                if candidate.exists() and candidate.is_file():
                    return candidate.resolve()
    return detect_host_claude_settings_path()


def resolve_host_claude_dir(cfg: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    candidates: list[Path] = []
    settings = resolve_settings_host_path(cfg)
    if settings is not None:
        candidates.append(settings.parent)

    homes: list[Path] = [Path.home()]
    env_home = os.environ.get("HOME", "").strip()
    if env_home:
        env_home_path = Path(env_home).expanduser()
        if env_home_path not in homes:
            homes.append(env_home_path)
    for home in homes:
        candidates.append(home / ".claude")

    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if resolved.exists() and resolved.is_dir():
            return resolved
    return None


def load_settings_json(settings_path: Optional[Path]) -> Any:
    if settings_path is None:
        return None
    try:
        return json.loads(settings_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def extract_settings_env_values(settings_path: Optional[Path]) -> Dict[str, str]:
    data = load_settings_json(settings_path)
    if not isinstance(data, dict):
        return {}
    env_block = data.get("env")
    if not isinstance(env_block, dict):
        return {}

    values: Dict[str, str] = {}
    for k, v in env_block.items():
        name = str(k).strip()
        if not name:
            continue
        if isinstance(v, str):
            value = v.strip()
        elif isinstance(v, (int, float, bool)):
            value = str(v).strip()
        else:
            continue
        if not value:
            continue
        values[name] = value
    return values


def _extract_setting_value_by_keys(
    data: Any,
    env_keys: list[str],
    normalized_keys: set[str],
    exact_upper_keys: set[str],
) -> Optional[str]:
    if isinstance(data, dict):
        env_block = data.get("env")
        if isinstance(env_block, dict):
            for env_key in env_keys:
                value = env_block.get(env_key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, (int, float, bool)):
                    text = str(value).strip()
                    if text:
                        return text
        for k, v in data.items():
            key_text = str(k).strip()
            key_norm = key_text.replace("-", "_").lower()
            if key_norm in normalized_keys or key_text.upper() in exact_upper_keys:
                if isinstance(v, str) and v.strip():
                    return v.strip()
                if isinstance(v, (int, float, bool)):
                    text = str(v).strip()
                    if text:
                        return text
            found = _extract_setting_value_by_keys(v, env_keys, normalized_keys, exact_upper_keys)
            if found:
                return found
        return None
    if isinstance(data, list):
        for item in data:
            found = _extract_setting_value_by_keys(item, env_keys, normalized_keys, exact_upper_keys)
            if found:
                return found
    return None


def extract_anthropic_api_key_from_settings(settings_path: Optional[Path]) -> Optional[str]:
    data = load_settings_json(settings_path)
    return _extract_setting_value_by_keys(
        data,
        env_keys=["ANTHROPIC_API_KEY", "anthropic_api_key"],
        normalized_keys={"anthropic_api_key", "anthropicapikey", "api_key", "apikey"},
        exact_upper_keys={"ANTHROPIC_API_KEY"},
    )


def extract_anthropic_auth_token_from_settings(settings_path: Optional[Path]) -> Optional[str]:
    data = load_settings_json(settings_path)
    return _extract_setting_value_by_keys(
        data,
        env_keys=["ANTHROPIC_AUTH_TOKEN", "anthropic_auth_token"],
        normalized_keys={"anthropic_auth_token", "anthropicauthtoken", "auth_token", "token"},
        exact_upper_keys={"ANTHROPIC_AUTH_TOKEN"},
    )


def detect_host_auth_artifacts() -> list[Path]:
    home = Path.home()
    explicit = [
        home / ".claude" / ".credentials.json",
        home / ".claude" / "credentials.json",
        home / ".claude" / "auth.json",
        home / ".config" / "claude" / "auth.json",
        home / ".config" / "claude" / "credentials.json",
        home / ".config" / "claude-code" / "auth.json",
        home / ".config" / "claude-code" / "credentials.json",
        home / ".config" / "@anthropic-ai" / "claude-code" / "auth.json",
        home / ".config" / "@anthropic-ai" / "claude-code" / "credentials.json",
    ]

    candidate_dirs = [
        home / ".claude",
        home / ".config" / "claude",
        home / ".config" / "claude-code",
        home / ".config" / "@anthropic-ai" / "claude-code",
    ]
    patterns = ["*auth*.json", "*credential*.json", "*token*.json"]

    seen: set[str] = set()
    found: list[Path] = []

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except Exception:
            return
        key = str(resolved)
        if key in seen:
            return
        if not resolved.exists() or not resolved.is_file():
            return
        seen.add(key)
        found.append(resolved)

    for path in explicit:
        add(path)

    for base in candidate_dirs:
        if not base.exists() or not base.is_dir():
            continue
        for pattern in patterns:
            for path in sorted(base.rglob(pattern)):
                add(path)

    return sorted(found, key=lambda p: str(p))


def detect_host_claude_auth_files() -> Dict[str, Path]:
    home = Path.home()
    files: Dict[str, Path] = {}
    for path in detect_host_auth_artifacts():
        key = path.name
        try:
            rel = path.relative_to(home)
            key = str(rel)
        except Exception:
            key = path.name
        files[key] = path
    return files


def copy_user_auth_into_runtime(repo: Path, overwrite: bool = False) -> None:
    paths = state_paths(repo)
    auth_files = detect_host_auth_artifacts()
    if not auth_files:
        return

    host_home = Path.home().resolve()
    runtime_home = paths["runtime_home"]
    runtime_claude_dir = paths["runtime_claude_dir"]
    runtime_claude_dir.mkdir(parents=True, exist_ok=True)
    runtime_home.mkdir(parents=True, exist_ok=True)

    for source in auth_files:
        copied = False
        try:
            rel = source.relative_to(host_home)
            target = runtime_home / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if overwrite or not target.exists():
                shutil.copy2(source, target)
            copied = True
        except Exception:
            copied = False

        # Compatibility fallback: keep common auth filenames in $HOME/.claude/.
        basename = source.name
        if basename in {".credentials.json", "credentials.json", "auth.json"}:
            fallback = runtime_claude_dir / basename
            if overwrite or not fallback.exists():
                shutil.copy2(source, fallback)
            copied = True

        if not copied:
            fallback_generic = runtime_claude_dir / basename
            if overwrite or not fallback_generic.exists():
                shutil.copy2(source, fallback_generic)


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
            cfg=cfg,
            overwrite=runtime_cfg.get("overwrite_user_settings", True),
        )
    if runtime_cfg.get("copy_user_auth", True):
        copy_user_auth_into_runtime(
            repo,
            overwrite=runtime_cfg.get("overwrite_user_auth", False),
        )


def init_repo(repo: Path) -> None:
    paths = state_paths(repo)
    paths["base"].mkdir(parents=True, exist_ok=True)
    paths["history"].mkdir(parents=True, exist_ok=True)
    paths["worktrees"].mkdir(parents=True, exist_ok=True)
    paths["benchmarks"].mkdir(parents=True, exist_ok=True)
    paths["logs"].mkdir(parents=True, exist_ok=True)
    worker_runtime_dir(repo).mkdir(parents=True, exist_ok=True)

    cfg = load_config(repo)
    execution_cfg = cfg.setdefault("execution", {})
    if execution_cfg.get("image") in {None, "", "optloop-worker:latest"}:
        execution_cfg["image"] = default_project_image(repo)
    host_settings = resolve_settings_host_path(cfg)
    if host_settings is not None:
        execution_cfg["settings_host_path"] = str(host_settings)
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
            "target_parallel_containers": target_parallel_containers(cfg),
            "runtime_containers": [],
            "runtime_container_count": 0,
            "container_workers": {},
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
        "target_parallel_containers": 1,
        "runtime_containers": [],
        "runtime_container_count": 0,
        "container_workers": {},
    })
    status.update(updates)
    status["updated_at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    write_json(paths["status"], status)
    return status


def parse_non_negative_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        return default
    if parsed < 0:
        return default
    return parsed


def runtime_log(event: str, **fields: Any) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tail = " ".join(f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in fields.items())
    if tail:
        print(f"[optloop] {ts} {event} {tail}", flush=True)
    else:
        print(f"[optloop] {ts} {event}", flush=True)


def console_safe_text(text: str) -> str:
    enc = sys.stdout.encoding or "utf-8"
    try:
        text.encode(enc)
        return text
    except Exception:
        return text.encode(enc, errors="replace").decode(enc, errors="replace")


def redact_env_assignment(value: str) -> str:
    if "=" not in value:
        return value
    key, _ = value.split("=", 1)
    return f"{key}=***"


def format_command_for_log(cmd: list[str]) -> str:
    rendered: list[str] = []
    idx = 0
    while idx < len(cmd):
        part = str(cmd[idx])
        if part in {"-e", "--env"}:
            rendered.append(part)
            idx += 1
            if idx < len(cmd):
                rendered.append(redact_env_assignment(str(cmd[idx])))
            idx += 1
            continue
        if part.startswith("--env="):
            _, rhs = part.split("--env=", 1)
            rendered.append(f"--env={redact_env_assignment(rhs)}")
            idx += 1
            continue
        rendered.append(part)
        idx += 1
    return " ".join(rendered)


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


def positive_int(value: Any, default: int, minimum: int = 1, maximum: int = 64) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    if parsed < minimum:
        parsed = minimum
    if parsed > maximum:
        parsed = maximum
    return parsed


def target_parallel_containers(cfg: Dict[str, Any]) -> int:
    loop_cfg = cfg.get("loop", {})
    return positive_int(loop_cfg.get("parallel_candidates", 1), default=1, minimum=1, maximum=64)


def auto_start_claude(cfg: Dict[str, Any]) -> bool:
    execution = cfg.get("execution", {})
    return bool(execution.get("auto_start_claude", True))


def claude_command(cfg: Dict[str, Any]) -> str:
    execution = cfg.get("execution", {})
    value = str(execution.get("claude_command", "claude")).strip()
    return value or "claude"


def claude_skip_permissions(cfg: Dict[str, Any]) -> bool:
    execution = cfg.get("execution", {})
    return bool(execution.get("claude_skip_permissions", True))


def claude_restart_delay_sec(cfg: Dict[str, Any]) -> int:
    execution = cfg.get("execution", {})
    return positive_int(execution.get("claude_restart_delay_sec", 15), default=15, minimum=1, maximum=3600)


def auth_precheck_mode(cfg: Dict[str, Any]) -> str:
    execution = cfg.get("execution", {})
    mode = str(execution.get("auth_precheck_mode", "warn")).strip().lower()
    if mode not in {"strict", "warn", "off"}:
        return "warn"
    return mode


def claude_prompt_text(cfg: Dict[str, Any]) -> str:
    execution = cfg.get("execution", {})
    override = str(execution.get("claude_prompt", "")).strip()
    if override:
        return override
    return DEFAULT_CLAUDE_AUTORUN_PROMPT


def runtime_container_names(repo: Path, cfg: Dict[str, Any]) -> list[str]:
    base = runtime_container_name(repo)
    total = target_parallel_containers(cfg)
    names = [base]
    for idx in range(2, total + 1):
        names.append(f"{base}-{idx}")
    return names


def passthrough_env_values(cfg: Dict[str, Any]) -> Dict[str, str]:
    settings_path = resolve_settings_host_path(cfg)
    settings_api_key = extract_anthropic_api_key_from_settings(settings_path)
    settings_auth_token = extract_anthropic_auth_token_from_settings(settings_path)
    settings_env_values = extract_settings_env_values(settings_path)
    values: Dict[str, str] = {}
    for key in cfg.get("execution", {}).get("passthrough_env", []):
        name = str(key).strip()
        if not name:
            continue
        value = os.environ.get(name)
        if value:
            values[name] = value
            continue
        if name in settings_env_values and settings_env_values[name]:
            values[name] = settings_env_values[name]
            continue
        if name == "ANTHROPIC_API_KEY" and settings_api_key:
            values[name] = settings_api_key
            continue
        if name == "ANTHROPIC_AUTH_TOKEN" and settings_auth_token:
            values[name] = settings_auth_token
    return values


def passthrough_env_presence(cfg: Dict[str, Any]) -> Dict[str, bool]:
    presence: Dict[str, bool] = {}
    values = passthrough_env_values(cfg)
    for key in cfg.get("execution", {}).get("passthrough_env", []):
        name = str(key).strip()
        if not name:
            continue
        presence[name] = name in values and bool(values[name])
    return presence


def passthrough_env_sources(cfg: Dict[str, Any]) -> Dict[str, str]:
    settings_path = resolve_settings_host_path(cfg)
    settings_api_key = extract_anthropic_api_key_from_settings(settings_path)
    settings_auth_token = extract_anthropic_auth_token_from_settings(settings_path)
    settings_env_values = extract_settings_env_values(settings_path)
    sources: Dict[str, str] = {}
    for key in cfg.get("execution", {}).get("passthrough_env", []):
        name = str(key).strip()
        if not name:
            continue
        if os.environ.get(name):
            sources[name] = "environment"
            continue
        if name in settings_env_values and settings_env_values[name]:
            sources[name] = "settings_env"
            continue
        if name == "ANTHROPIC_API_KEY" and settings_api_key:
            sources[name] = "settings_file"
            continue
        if name == "ANTHROPIC_AUTH_TOKEN" and settings_auth_token:
            sources[name] = "settings_file"
            continue
        sources[name] = "missing"
    return sources


def run(
    cmd: list[str],
    cwd: Optional[Path] = None,
    check: bool = True,
    capture: bool = True,
    timeout_sec: Optional[int] = 120,
) -> subprocess.CompletedProcess[str]:
    command_for_log = format_command_for_log(cmd)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=capture,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise OptLoopError(f"Command timed out after {timeout_sec}s: {command_for_log}") from exc
    if check and proc.returncode != 0:
        raise OptLoopError(
            f"Command failed ({proc.returncode}): {command_for_log}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc


def docker_available() -> bool:
    try:
        proc = run(["docker", "info"], check=False)
        return proc.returncode == 0
    except Exception:
        return False


def docker_image_exists(image: str) -> bool:
    try:
        proc = run(["docker", "image", "inspect", image], check=False)
    except Exception:
        return False
    return proc.returncode == 0


def docker_container_state(name: str) -> str:
    try:
        proc = run(["docker", "inspect", "-f", "{{.State.Status}}", name], check=False)
    except Exception:
        return "docker-unavailable"
    if proc.returncode != 0:
        return "missing"
    return (proc.stdout or "").strip() or "unknown"


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    normalized: list[list[str]] = []
    for row in rows:
        cells = [str(cell) for cell in row]
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        normalized.append(cells[: len(headers)])

    widths = [len(h) for h in headers]
    for row in normalized:
        for idx, cell in enumerate(row):
            if len(cell) > widths[idx]:
                widths[idx] = len(cell)

    def border(fill: str = "-") -> str:
        return "+" + "+".join(fill * (w + 2) for w in widths) + "+"

    lines = [
        border("-"),
        "| " + " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))) + " |",
        border("="),
    ]
    for row in normalized:
        lines.append("| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    lines.append(border("-"))
    return "\n".join(lines)


def trim_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def collect_claude_processes(container_name: str) -> list[Dict[str, str]]:
    if not container_name:
        return []
    if not docker_available():
        return []
    if docker_container_state(container_name) != "running":
        return []

    proc = run(
        [
            "docker",
            "exec",
            container_name,
            "sh",
            "-lc",
            "ps -eo pid,ppid,etime,args --no-headers",
        ],
        check=False,
    )
    if proc.returncode != 0:
        return []

    rows: list[Dict[str, str]] = []
    for raw in (proc.stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        pid, ppid, etime, args = parts
        lower_args = args.lower()
        if "claude" not in lower_args and "anthropic" not in lower_args:
            continue
        rows.append({
            "container": container_name,
            "pid": pid,
            "ppid": ppid,
            "etime": etime,
            "command": args,
        })

    rows.sort(key=lambda row: int(row["pid"]) if row["pid"].isdigit() else 0)
    return rows


def collect_claude_processes_for_containers(container_names: list[str]) -> list[Dict[str, str]]:
    all_rows: list[Dict[str, str]] = []
    for name in container_names:
        all_rows.extend(collect_claude_processes(name))
    all_rows.sort(key=lambda row: (row.get("container", ""), int(row["pid"]) if row["pid"].isdigit() else 0))
    return all_rows


def list_runtime_containers(repo: Path) -> list[str]:
    if not docker_available():
        return []
    base = runtime_container_name(repo)
    proc = run(["docker", "ps", "-a", "--format", "{{.Names}}"], check=False)
    if proc.returncode != 0:
        return []

    names: list[str] = []
    for raw in (proc.stdout or "").splitlines():
        name = raw.strip()
        if not name:
            continue
        if name == base or name.startswith(base + "-"):
            names.append(name)
    names.sort()
    return names


def ensure_worker_prompt_file(repo: Path, cfg: Dict[str, Any]) -> Path:
    prompt_path = worker_prompt_host_path(repo)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_text = claude_prompt_text(cfg).strip() + "\n"
    current = ""
    if prompt_path.exists():
        current = prompt_path.read_text(encoding="utf-8", errors="replace")
    if current != prompt_text:
        prompt_path.write_text(prompt_text, encoding="utf-8")
    return prompt_path


def probe_claude_worker(repo: Path, container_name: str) -> Dict[str, Any]:
    pid_path = worker_pid_container_path(container_name)
    check_script = (
        "set -eu\n"
        "PIDFILE=\"$OPTLOOP_WORKER_PIDFILE\"\n"
        "if [ -s \"$PIDFILE\" ]; then\n"
        "  PID=\"$(cat \"$PIDFILE\" 2>/dev/null || true)\"\n"
        "  if [ -n \"$PID\" ] && kill -0 \"$PID\" 2>/dev/null; then\n"
        "    echo \"alive:$PID\"\n"
        "    exit 0\n"
        "  fi\n"
        "  if [ -n \"$PID\" ]; then\n"
        "    echo \"stale:$PID\"\n"
        "    exit 0\n"
        "  fi\n"
        "fi\n"
        "echo \"missing\"\n"
    )
    proc = run(
        [
            "docker",
            "exec",
            "-e",
            f"OPTLOOP_WORKER_PIDFILE={pid_path}",
            container_name,
            "sh",
            "-lc",
            check_script,
        ],
        check=False,
    )
    line = (proc.stdout or "").strip()
    state = "missing"
    pid = ""
    if line.startswith("alive:"):
        state = "alive"
        pid = line.split(":", 1)[1].strip()
    elif line.startswith("stale:"):
        state = "stale"
        pid = line.split(":", 1)[1].strip()
    elif line:
        state = line

    last_line = ""
    recent_lines: list[str] = []
    log_host = worker_log_host_path(repo, container_name)
    if log_host.exists():
        lines = log_host.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            last_line = trim_text(lines[-1], 140)
            recent_lines = lines[-80:]

    auth_markers = ("auth_missing", "auth_required", "not logged in", "please run /login")
    if any(any(marker in line.lower() for marker in auth_markers) for line in recent_lines):
        state = "auth_missing"

    return {
        "container": container_name,
        "supervisor_state": state,
        "supervisor_pid": pid,
        "log_file": str(log_host),
        "last_log": last_line,
    }


def ensure_claude_worker(repo: Path, cfg: Dict[str, Any], container_name: str) -> Dict[str, Any]:
    ensure_worker_prompt_file(repo, cfg)
    command = claude_command(cfg)
    restart_delay = claude_restart_delay_sec(cfg)
    skip_permissions = "1" if claude_skip_permissions(cfg) else "0"
    precheck_mode = auth_precheck_mode(cfg)

    pid_host = worker_pid_host_path(repo, container_name)
    pid_host.parent.mkdir(parents=True, exist_ok=True)
    log_host = worker_log_host_path(repo, container_name)
    log_host.parent.mkdir(parents=True, exist_ok=True)

    start_script = (
        "set -eu\n"
        "mkdir -p \"$(dirname \"$OPTLOOP_WORKER_PIDFILE\")\" \"$(dirname \"$OPTLOOP_WORKER_LOGFILE\")\"\n"
        "if [ -s \"$OPTLOOP_WORKER_PIDFILE\" ]; then\n"
        "  OLD_PID=\"$(cat \"$OPTLOOP_WORKER_PIDFILE\" 2>/dev/null || true)\"\n"
        "  if [ -n \"$OLD_PID\" ] && kill -0 \"$OLD_PID\" 2>/dev/null; then\n"
        "    echo \"already:$OLD_PID\"\n"
        "    exit 0\n"
        "  fi\n"
        "fi\n"
        "(\n"
        "  set +e\n"
        "  export CLAUDE_PROJECT_DIR=/workspace\n"
        "  HAS_PROMPT=0\n"
        "  HAS_SKIP=0\n"
        "  if command -v \"$OPTLOOP_CLAUDE_COMMAND\" >/dev/null 2>&1; then\n"
        "    if \"$OPTLOOP_CLAUDE_COMMAND\" --help 2>/dev/null | grep -q -- ' -p'; then HAS_PROMPT=1; fi\n"
        "    if \"$OPTLOOP_CLAUDE_COMMAND\" --help 2>/dev/null | grep -q -- '--dangerously-skip-permissions'; then HAS_SKIP=1; fi\n"
        "  fi\n"
        "  while true; do\n"
        "    TS=\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"\n"
        "    if [ -d \"$HOME/.claude-host\" ]; then\n"
        "      mkdir -p \"$HOME/.claude\"\n"
        "      for SRC in \"$HOME/.claude-host/.credentials.json\" \"$HOME/.claude-host/credentials.json\" \"$HOME/.claude-host/auth.json\" \"$HOME/.claude-host/settings.json\"; do\n"
        "        if [ -f \"$SRC\" ]; then cp -f \"$SRC\" \"$HOME/.claude/$(basename \"$SRC\")\" 2>/dev/null || true; fi\n"
        "      done\n"
        "    fi\n"
        "    AUTH_READY=0\n"
        "    if [ -n \"${ANTHROPIC_API_KEY:-}\" ]; then AUTH_READY=1; fi\n"
        "    if [ \"$AUTH_READY\" -ne 1 ] && [ -n \"${ANTHROPIC_AUTH_TOKEN:-}\" ]; then AUTH_READY=1; fi\n"
        "    if [ \"$AUTH_READY\" -ne 1 ] && [ -f \"$HOME/.claude/settings.json\" ] && grep -qiE 'anthropic[_-]*(api[_-]*key|auth[_-]*token)' \"$HOME/.claude/settings.json\" 2>/dev/null; then AUTH_READY=1; fi\n"
        "    if [ \"$AUTH_READY\" -ne 1 ]; then\n"
        "      for AUTH_DIR in \"$HOME/.claude\" \"$HOME/.config/claude\" \"$HOME/.config/claude-code\" \"$HOME/.config/@anthropic-ai/claude-code\"; do\n"
        "        if [ -d \"$AUTH_DIR\" ] && find \"$AUTH_DIR\" -maxdepth 4 -type f \\( -name '*auth*.json' -o -name '*credential*.json' -o -name '*token*.json' \\) | grep -q .; then\n"
        "          AUTH_READY=1\n"
        "          break\n"
        "        fi\n"
        "      done\n"
        "    fi\n"
        "    if [ \"$AUTH_READY\" -ne 1 ]; then\n"
        "      if [ \"$OPTLOOP_AUTH_PRECHECK_MODE\" = \"strict\" ]; then\n"
        "        echo \"[$TS] auth_missing container=$OPTLOOP_WORKER_CONTAINER hint='credentials unavailable; strict precheck blocks execution'\" >>\"$OPTLOOP_WORKER_LOGFILE\"\n"
        "        sleep 60\n"
        "        continue\n"
        "      fi\n"
        "      if [ \"$OPTLOOP_AUTH_PRECHECK_MODE\" = \"warn\" ]; then\n"
        "        echo \"[$TS] auth_precheck_unmet container=$OPTLOOP_WORKER_CONTAINER hint='proceeding without hard auth precheck'\" >>\"$OPTLOOP_WORKER_LOGFILE\"\n"
        "      fi\n"
        "    fi\n"
        "    if ! command -v \"$OPTLOOP_CLAUDE_COMMAND\" >/dev/null 2>&1; then\n"
        "      echo \"[$TS] missing_claude_command container=$OPTLOOP_WORKER_CONTAINER cmd=$OPTLOOP_CLAUDE_COMMAND\" >>\"$OPTLOOP_WORKER_LOGFILE\"\n"
        "      sleep 30\n"
        "      continue\n"
        "    fi\n"
        "    if [ \"$HAS_PROMPT\" -ne 1 ]; then\n"
        "      echo \"[$TS] claude_prompt_mode_unsupported container=$OPTLOOP_WORKER_CONTAINER\" >>\"$OPTLOOP_WORKER_LOGFILE\"\n"
        "      sleep 30\n"
        "      continue\n"
        "    fi\n"
        "    PROMPT_TEXT=\"$(cat \"$OPTLOOP_PROMPT_FILE\" 2>/dev/null || true)\"\n"
        "    if [ -z \"$PROMPT_TEXT\" ]; then PROMPT_TEXT='Continue repository optimization in /workspace using durable state under .optloop-runtime.'; fi\n"
        "    echo \"[$TS] cycle_start container=$OPTLOOP_WORKER_CONTAINER\" >>\"$OPTLOOP_WORKER_LOGFILE\"\n"
        "    if [ \"$OPTLOOP_CLAUDE_SKIP_PERMISSIONS\" = \"1\" ] && [ \"$HAS_SKIP\" -eq 1 ]; then\n"
        "      \"$OPTLOOP_CLAUDE_COMMAND\" --dangerously-skip-permissions -p \"$PROMPT_TEXT\" >>\"$OPTLOOP_WORKER_LOGFILE\" 2>&1\n"
        "      RC=\"$?\"\n"
        "    else\n"
        "      \"$OPTLOOP_CLAUDE_COMMAND\" -p \"$PROMPT_TEXT\" >>\"$OPTLOOP_WORKER_LOGFILE\" 2>&1\n"
        "      RC=\"$?\"\n"
        "    fi\n"
        "    TS_END=\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"\n"
        "    echo \"[$TS_END] cycle_end container=$OPTLOOP_WORKER_CONTAINER exit_code=$RC\" >>\"$OPTLOOP_WORKER_LOGFILE\"\n"
        "    if [ \"$RC\" -ne 0 ] && tail -n 80 \"$OPTLOOP_WORKER_LOGFILE\" | grep -qi 'not logged in'; then\n"
        "      echo \"[$TS_END] auth_required container=$OPTLOOP_WORKER_CONTAINER hint='provide credentials required by current model provider or run /login'\" >>\"$OPTLOOP_WORKER_LOGFILE\"\n"
        "      sleep 60\n"
        "      continue\n"
        "    fi\n"
        "    sleep \"$OPTLOOP_CLAUDE_RESTART_DELAY_SEC\"\n"
        "  done\n"
        ") >/dev/null 2>&1 &\n"
        "NEW_PID=\"$!\"\n"
        "echo \"$NEW_PID\" > \"$OPTLOOP_WORKER_PIDFILE\"\n"
        "echo \"started:$NEW_PID\"\n"
    )

    exec_cmd = [
        "docker",
        "exec",
        "-w",
        "/workspace",
        "-e",
        f"OPTLOOP_WORKER_CONTAINER={container_name}",
        "-e",
        f"OPTLOOP_WORKER_PIDFILE={worker_pid_container_path(container_name)}",
        "-e",
        f"OPTLOOP_WORKER_LOGFILE={worker_log_container_path(container_name)}",
        "-e",
        f"OPTLOOP_PROMPT_FILE={worker_prompt_container_path()}",
        "-e",
        f"OPTLOOP_CLAUDE_COMMAND={command}",
        "-e",
        f"OPTLOOP_CLAUDE_RESTART_DELAY_SEC={restart_delay}",
        "-e",
        f"OPTLOOP_CLAUDE_SKIP_PERMISSIONS={skip_permissions}",
        "-e",
        f"OPTLOOP_AUTH_PRECHECK_MODE={precheck_mode}",
        "-e",
        "CLAUDE_PROJECT_DIR=/workspace",
    ]
    for key, val in passthrough_env_values(cfg).items():
        exec_cmd += ["-e", f"{key}={val}"]
    exec_cmd += [container_name, "sh", "-lc", start_script]

    run(exec_cmd, check=False)
    return probe_claude_worker(repo, container_name)


def ensure_claude_workers(repo: Path, cfg: Dict[str, Any], container_names: list[str]) -> Dict[str, Dict[str, Any]]:
    if not auto_start_claude(cfg):
        return {}
    workers: Dict[str, Dict[str, Any]] = {}
    for name in container_names:
        workers[name] = ensure_claude_worker(repo, cfg, name)
    return workers

def ensure_runtime_container(repo: Path, cfg: Dict[str, Any], name: str) -> str:
    if cfg["execution"].get("mode") != "docker":
        return "local"
    if not docker_available():
        raise OptLoopError("Docker is not available")

    image = str(cfg["execution"].get("image", "optloop-worker:latest"))
    if not docker_image_exists(image):
        raise OptLoopError(f"Docker image not found: {image}")

    ensure_runtime_pack(repo, cfg)
    paths = state_paths(repo)
    state = docker_container_state(name)

    runtime_cfg = cfg.get("runtime", {})
    runtime_container_home = str(
        runtime_cfg.get("container_home", "/opt/optloop-home")
    ).strip()
    runtime_home_host = paths["runtime_home"]

    workspace = str(
        cfg["execution"].get("container_workspace", "/workspace")
    ).strip()

    settings_host = resolve_settings_host_path(cfg)

    settings_container = str(
        cfg["execution"].get(
            "settings_container_path",
            f"{runtime_container_home}/.claude/settings.json",
        )
    ).strip()
    host_claude_dir = resolve_host_claude_dir(cfg)
    host_claude_mount = f"{runtime_container_home}/.claude-host"

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

    for key, val in passthrough_env_values(cfg).items():
        cmd += ["-e", f"{key}={val}"]

    if settings_host is not None:
        cmd += ["-v", f"{settings_host}:{settings_container}:ro"]
    if host_claude_dir is not None:
        cmd += ["-v", f"{host_claude_dir}:{host_claude_mount}:ro"]

    extra_run_args = cfg["execution"].get("extra_run_args", [])
    if isinstance(extra_run_args, list):
        cmd += [str(x) for x in extra_run_args]

    cmd += [image, "bash", "-lc", "sleep infinity"]
    run(cmd, check=True)
    return name


def ensure_runtime_containers(repo: Path, cfg: Dict[str, Any]) -> list[str]:
    if cfg["execution"].get("mode") != "docker":
        return ["local"]

    desired = runtime_container_names(repo, cfg)
    for name in desired:
        ensure_runtime_container(repo, cfg, name)

    existing = list_runtime_containers(repo)
    extras = [name for name in existing if name not in desired]
    for name in extras:
        run(["docker", "rm", "-f", name], check=False)
        try:
            worker_pid_host_path(repo, name).unlink()
        except FileNotFoundError:
            pass

    return desired


def stop_runtime_containers(repo: Path) -> None:
    if not docker_available():
        return
    names = list_runtime_containers(repo)
    for name in names:
        run(["docker", "rm", "-f", name], check=False)
        try:
            worker_pid_host_path(repo, name).unlink()
        except FileNotFoundError:
            pass


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
    init_repo(repo)
    cfg = load_config(repo)
    target_parallel = target_parallel_containers(cfg)
    sleep_sec = positive_int(cfg["loop"].get("sleep_between_iterations_sec", 5), default=5, minimum=1, maximum=3600)
    acquire_lock(repo)
    signal.signal(signal.SIGTERM, handle_signal_factory(repo))
    signal.signal(signal.SIGINT, handle_signal_factory(repo))
    previous_status = read_json(state_paths(repo)["status"], {})
    iteration = parse_non_negative_int(previous_status.get("iteration"), default=0)
    set_status(
        repo,
        phase="starting",
        execution_mode=cfg["execution"]["mode"],
        iteration=iteration,
        target_parallel_containers=target_parallel,
    )
    runtime_log(
        "runner_started",
        pid=os.getpid(),
        execution_mode=cfg["execution"]["mode"],
        target_parallel_containers=target_parallel,
        sleep_between_iterations_sec=sleep_sec,
    )
    append_live(
        repo,
        {
            "event": "runner_started",
            "pid": os.getpid(),
            "execution_mode": cfg["execution"]["mode"],
            "target_parallel_containers": target_parallel,
        },
    )
    stop_file = state_paths(repo)["stop"]
    try:
        while not stop_file.exists():
            iteration += 1
            try:
                container_names = ensure_runtime_containers(repo, cfg)
                states = {name: docker_container_state(name) for name in container_names}
                worker_statuses = ensure_claude_workers(repo, cfg, container_names)
                worker_state_map = {name: worker_statuses.get(name, {}).get("supervisor_state", "unknown") for name in container_names}
                workers_healthy = (not auto_start_claude(cfg)) or all(state == "alive" for state in worker_state_map.values())
                phase = "runtime_active" if workers_healthy else "runtime_degraded"
                reason = "runtime container healthy" if workers_healthy else "claude worker not alive"
                set_status(
                    repo,
                    phase=phase,
                    iteration=iteration,
                    execution_mode=cfg["execution"]["mode"],
                    runtime_container=container_names[0] if container_names else "",
                    runtime_containers=container_names,
                    runtime_states=states,
                    runtime_container_count=len(container_names),
                    target_parallel_containers=target_parallel,
                    container_workers=worker_statuses,
                    last_reason=reason,
                )
                runtime_log(
                    "runtime_heartbeat",
                    iteration=iteration,
                    container_count=len(container_names),
                    containers=container_names,
                    states=states,
                    worker_states=worker_state_map,
                    phase=phase,
                )
                append_live(
                    repo,
                    {
                        "event": "runtime_heartbeat",
                        "iteration": iteration,
                        "containers": container_names,
                        "states": states,
                        "worker_states": worker_state_map,
                        "phase": phase,
                        "container_count": len(container_names),
                    },
                )
            except Exception as exc:
                err = str(exc).strip() or exc.__class__.__name__
                set_status(
                    repo,
                    phase="runtime_degraded",
                    iteration=iteration,
                    execution_mode=cfg["execution"]["mode"],
                    target_parallel_containers=target_parallel,
                    last_reason=err,
                )
                runtime_log("runtime_error", iteration=iteration, error=err)
                append_live(repo, {"event": "runtime_error", "iteration": iteration, "error": err})
            time.sleep(sleep_sec)
    finally:
        stop_runtime_containers(repo)
        if stop_file.exists():
            try:
                stop_file.unlink()
            except OSError:
                pass
        set_status(
            repo,
            phase="stopped",
            iteration=iteration,
            last_reason="supervisor stopped",
            runtime_containers=[],
            runtime_container_count=0,
            container_workers={},
        )
        runtime_log("runner_stopped", iteration=iteration)
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

    stop_runtime_containers(repo)
    release_lock(repo)
    set_status(
        repo,
        phase="stopped",
        last_reason="stop requested",
        runtime_containers=[],
        runtime_container_count=0,
        container_workers={},
    )
    print("stopped")


def cmd_status(repo: Path, as_json: bool = False) -> None:
    paths = state_paths(repo)
    if not paths["status"].exists():
        init_repo(repo)
        paths = state_paths(repo)
    status = read_json(paths["status"], {})
    cfg = load_config(repo)

    execution_mode = str(status.get("execution_mode") or "docker")
    configured_containers = runtime_container_names(repo, cfg)
    status_containers = status.get("runtime_containers")
    has_runtime_container_list = isinstance(status_containers, list)
    runtime_containers: list[str] = []
    if has_runtime_container_list:
        runtime_containers = [str(name).strip() for name in status_containers if str(name).strip()]
    if not has_runtime_container_list and not runtime_containers:
        runtime_containers = [str(status.get("runtime_container") or configured_containers[0])]

    runtime_states: Dict[str, str] = {}
    claude_processes: list[Dict[str, str]] = []
    worker_statuses: Dict[str, Dict[str, Any]] = {}
    stored_workers = status.get("container_workers", {})
    if execution_mode == "docker":
        if docker_available():
            for name in runtime_containers:
                runtime_states[name] = docker_container_state(name)
                worker_statuses[name] = probe_claude_worker(repo, name)
            claude_processes = collect_claude_processes_for_containers(runtime_containers)
        else:
            for name in runtime_containers:
                runtime_states[name] = "docker-unavailable"
                if isinstance(stored_workers, dict):
                    existing = stored_workers.get(name, {})
                    if isinstance(existing, dict) and existing.get("supervisor_state"):
                        worker_statuses[name] = existing
                if name not in worker_statuses:
                    worker_statuses[name] = {
                        "container": name,
                        "supervisor_state": "docker-unavailable",
                        "supervisor_pid": "",
                        "log_file": str(worker_log_host_path(repo, name)),
                        "last_log": "",
                    }
    else:
        for name in runtime_containers:
            runtime_states[name] = "n/a"
            worker_statuses[name] = {
                "container": name,
                "supervisor_state": "n/a",
                "supervisor_pid": "",
                "log_file": str(worker_log_host_path(repo, name)),
                "last_log": "",
            }

    runner_pid = read_pidfile(paths["runner_pid"])
    runner_alive = bool(runner_pid and pid_is_alive(runner_pid))

    target_parallel = positive_int(
        status.get("target_parallel_containers"),
        default=target_parallel_containers(cfg),
        minimum=1,
        maximum=64,
    )

    payload = {
        "phase": status.get("phase", "unknown"),
        "iteration": status.get("iteration", 0),
        "accepted_total": status.get("accepted_total", 0),
        "rejected_total": status.get("rejected_total", 0),
        "active_candidates": status.get("active_candidates", {}),
        "execution_mode": execution_mode,
        "last_reason": status.get("last_reason", ""),
        "updated_at": status.get("updated_at", ""),
        "runtime_container": runtime_containers[0] if runtime_containers else "",
        "runtime_containers": runtime_containers,
        "runtime_states": runtime_states,
        "runtime_container_count": len(runtime_containers),
        "target_parallel_containers": target_parallel,
        "auto_start_claude": auto_start_claude(cfg),
        "container_workers": worker_statuses,
        "runner_pid": runner_pid,
        "runner_alive": runner_alive,
        "claude_processes": claude_processes,
    }

    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    active_candidates = payload["active_candidates"]
    if isinstance(active_candidates, dict):
        active_count = str(len(active_candidates))
    elif isinstance(active_candidates, list):
        active_count = str(len(active_candidates))
    else:
        active_count = str(active_candidates)

    summary_rows = [
        ["phase", str(payload["phase"])],
        ["iteration", str(payload["iteration"])],
        ["accepted_total", str(payload["accepted_total"])],
        ["rejected_total", str(payload["rejected_total"])],
        ["active_candidates", active_count],
        ["target_parallel_containers", str(payload["target_parallel_containers"])],
        ["runtime_container_count", str(payload["runtime_container_count"])],
        ["auto_start_claude", "true" if payload["auto_start_claude"] else "false"],
        ["execution_mode", str(payload["execution_mode"])],
        ["runner_pid", str(payload["runner_pid"] or "-")],
        ["runner_alive", "true" if payload["runner_alive"] else "false"],
        ["last_reason", str(payload["last_reason"] or "-")],
        ["updated_at", str(payload["updated_at"] or "-")],
    ]
    print(format_table(["field", "value"], summary_rows))

    print("")
    container_rows = [
        [name, runtime_states.get(name, "unknown")]
        for name in runtime_containers
    ]
    if not container_rows:
        container_rows = [["-", "no runtime container"]]
    print(format_table(["container", "state"], container_rows))

    print("")
    worker_rows = []
    for name in runtime_containers:
        worker = worker_statuses.get(name, {})
        worker_rows.append(
            [
                name,
                str(worker.get("supervisor_state", "unknown")),
                str(worker.get("supervisor_pid", "") or "-"),
                trim_text(str(worker.get("last_log", "") or "-"), 100),
            ]
        )
    if not worker_rows:
        worker_rows = [["-", "-", "-", "no worker supervisor"]]
    print(format_table(["container", "worker_state", "worker_pid", "last_log"], worker_rows))

    print("")
    if claude_processes:
        process_rows = [
            [
                row.get("container", "-"),
                row["pid"],
                row["ppid"],
                row["etime"],
                trim_text(row["command"], 96),
            ]
            for row in claude_processes
        ]
        print(format_table(["container", "claude_pid", "ppid", "elapsed", "command"], process_rows))
    else:
        print(
            format_table(
                ["container", "claude_pid", "ppid", "elapsed", "command"],
                [["-", "-", "-", "-", "no active claude process"]],
            )
        )


def cmd_doctor(repo: Path) -> None:
    init_repo(repo)
    cfg = load_config(repo)
    paths = state_paths(repo)
    runtime_names = runtime_container_names(repo, cfg)
    docker_visible = docker_available()
    runtime_states = {name: docker_container_state(name) for name in runtime_names}
    env_presence = passthrough_env_presence(cfg)
    env_sources = passthrough_env_sources(cfg)
    effective_settings = resolve_settings_host_path(cfg)
    effective_host_claude_dir = resolve_host_claude_dir(cfg)
    settings_key_present = bool(extract_anthropic_api_key_from_settings(effective_settings))
    settings_auth_token_present = bool(extract_anthropic_auth_token_from_settings(effective_settings))
    settings_env_keys = sorted(extract_settings_env_values(effective_settings).keys())
    host_auth_files = sorted(detect_host_claude_auth_files().keys())
    runtime_auth_files = sorted([str(p.relative_to(paths["runtime_home"])) for p in paths["runtime_home"].rglob("*auth*.json")] +
                                [str(p.relative_to(paths["runtime_home"])) for p in paths["runtime_home"].rglob("*credential*.json")])
    runtime_auth_files = sorted(set(runtime_auth_files))
    if docker_visible:
        worker_states = {name: probe_claude_worker(repo, name) for name in runtime_names}
    else:
        worker_states = {
            name: {
                "container": name,
                "supervisor_state": "docker-unavailable",
                "supervisor_pid": "",
                "log_file": str(worker_log_host_path(repo, name)),
                "last_log": "",
            }
            for name in runtime_names
        }
    info = {
        "repo": str(repo),
        "git_clean": True,
        "execution_mode": cfg["execution"].get("mode"),
        "docker_visible": docker_visible,
        "runtime_pack_present": paths["runtime_claude_dir"].exists(),
        "runtime_home_host": str(paths["runtime_home"]),
        "runtime_claude_dir": str(paths["runtime_claude_dir"]),
        "use_bare_mode": cfg["loop"].get("use_bare_mode"),
        "target_parallel_containers": target_parallel_containers(cfg),
        "settings_container_path": cfg["execution"].get("settings_container_path"),
        "runtime_container_name": runtime_names[0] if runtime_names else "",
        "runtime_container_names": runtime_names,
        "runtime_container_states": runtime_states,
        "auto_start_claude": auto_start_claude(cfg),
        "claude_command": claude_command(cfg),
        "claude_skip_permissions": claude_skip_permissions(cfg),
        "auth_precheck_mode": auth_precheck_mode(cfg),
        "claude_restart_delay_sec": claude_restart_delay_sec(cfg),
        "passthrough_env_present": env_presence,
        "passthrough_env_sources": env_sources,
        "settings_host_path_effective": str(effective_settings) if effective_settings else "",
        "host_claude_dir_effective": str(effective_host_claude_dir) if effective_host_claude_dir else "",
        "settings_contains_anthropic_key": settings_key_present,
        "settings_contains_anthropic_auth_token": settings_auth_token_present,
        "settings_env_keys": settings_env_keys,
        "host_auth_files_detected": host_auth_files,
        "runtime_auth_files_detected": runtime_auth_files,
        "container_workers": worker_states,
        "worker_image": cfg["execution"].get("image"),
        "worker_image_present": docker_image_exists(str(cfg["execution"].get("image"))),
        "benchmarks": cfg.get("benchmarks", []),
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))


def cmd_logs(repo: Path, mode: str) -> None:
    paths = state_paths(repo)
    log_path = paths["logs"] / "controller.out"
    live_path = paths["live"]
    worker_logs = sorted(paths["logs"].glob("claude-worker-*.log"))
    if mode == "latest":
        has_controller = log_path.exists()
        has_live = live_path.exists()
        if not has_controller and not has_live and not worker_logs:
            print("No log file found")
            return
        if has_controller:
            print("== controller.out ==")
            controller_text = log_path.read_text(encoding="utf-8", errors="replace")[-20000:]
            print(console_safe_text(controller_text))
        else:
            print("== controller.out ==\nNo log file found")

        print("")
        if has_live:
            print("== live.ndjson (last 60 events) ==")
            lines = live_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines[-60:]:
                print(console_safe_text(line))
        else:
            print("== live.ndjson ==\nNo live event file found")

        print("")
        if worker_logs:
            for worker_log in worker_logs:
                print(f"== {worker_log.name} (last 40 lines) ==")
                lines = worker_log.read_text(encoding="utf-8", errors="replace").splitlines()
                for line in lines[-40:]:
                    print(console_safe_text(line))
                print("")
        else:
            print("== claude worker logs ==\nNo claude worker log found")
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
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true", help="print status as json")
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
            cmd_status(repo, as_json=bool(getattr(args, "json", False)))
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
    except Exception as exc:
        print(f"optloop fatal: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
