from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shlex
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class RuntimePaths:
    root: Path
    artifacts: Path
    checkpoints: Path
    logs: Path
    reports: Path
    tmp: Path
    cache: Path
    state: Path


def make_worktree_id(repo_name: str, branch_name: str = "no-git", head: str = "nohead") -> str:
    seed = f"{repo_name}:{branch_name}:{head}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", f"{repo_name}-{branch_name}-{digest}").strip("-").lower()
    return slug[:64]


def create_run_id() -> str:
    return f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"


def ensure_runtime(root: Path, worktree_id: str) -> RuntimePaths:
    base = root / worktree_id
    paths = RuntimePaths(
        root=base,
        artifacts=base / "artifacts",
        checkpoints=base / "checkpoints",
        logs=base / "logs",
        reports=base / "reports",
        tmp=base / "tmp",
        cache=base / "cache",
        state=base / "state",
    )
    for path in paths.__dict__.values():
        Path(path).mkdir(parents=True, exist_ok=True)
    return paths


def write_json_log(log_path: Path, event: Dict[str, Any]) -> None:
    event = dict(event)
    event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def parse_harness_env_file(project_root: Path | None = None, env_file: str = ".env") -> Dict[str, str]:
    root = project_root or Path.cwd()
    path = root / env_file
    if not path.exists():
        return {}

    parsed: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not match:
            match = re.match(r"^\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not match:
            continue

        key, raw_value = match.groups()
        try:
            value = shlex.split(raw_value, posix=False)[0]
        except (IndexError, ValueError):
            value = raw_value
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        parsed[key] = value

    return parsed


def load_harness_env(project_root: Path | None = None, env_file: str = ".env") -> Dict[str, str]:
    loaded: Dict[str, str] = {}
    for key, value in parse_harness_env_file(project_root, env_file).items():
        if key in os.environ:
            continue
        os.environ[key] = value
        loaded[key] = value

    return loaded


def doctor_summary() -> Dict[str, Any]:
    loaded = load_harness_env()
    env_path = Path.cwd() / ".env"
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "env_file": str(env_path),
        "env_file_exists": env_path.exists(),
        "env_file_keys": sorted(parse_harness_env_file().keys()),
        "env_file_loaded_keys": sorted(loaded.keys()),
        "live_tests": os.environ.get("RUN_LIVE_LLM_TESTS", "false").lower() == "true",
        "openai_key_set": bool(os.environ.get("OPENAI_API_KEY")),
        "gemini_key_set": bool(os.environ.get("GEMINI_API_KEY")),
    }


class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        self.elapsed_ms = 0
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed_ms = int((time.perf_counter() - self.start) * 1000)
