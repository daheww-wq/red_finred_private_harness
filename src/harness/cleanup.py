from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict


def cleanup_check(project_root: Path, runtime_root: Path = Path(".runtime")) -> Dict[str, Any]:
    runtime = project_root / runtime_root
    reports = sorted(runtime.rglob("reports/*.json")) if runtime.exists() else []
    logs = sorted(runtime.rglob("logs/*.jsonl")) if runtime.exists() else []
    growth = sorted((runtime / "growth").glob("*")) if (runtime / "growth").exists() else []
    status = _git_status(project_root)
    result = {
        "project_root": str(project_root),
        "git_status": status,
        "runtime_exists": runtime.exists(),
        "runtime_root": str(runtime),
        "report_count": len(reports),
        "log_count": len(logs),
        "growth_run_count": len(growth),
        "latest_reports": [str(path.relative_to(project_root)) for path in reports[-5:]],
        "latest_logs": [str(path.relative_to(project_root)) for path in logs[-5:]],
    }
    return result


def write_cleanup_report(report: Dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _git_status(project_root: Path) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(project_root),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=10,
        )
        return {
            "returncode": proc.returncode,
            "lines": proc.stdout.strip().splitlines(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {"returncode": 1, "lines": [], "stderr": str(exc)}
