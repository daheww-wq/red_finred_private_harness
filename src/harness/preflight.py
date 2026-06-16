from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

from .config import HarnessConfig, validate_config
from .secret_scan import scan_for_secrets
from .validators import contains_pii


@dataclass(frozen=True)
class PreflightFinding:
    severity: str
    reason_code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "reason_code": self.reason_code,
            "message": self.message,
        }


@dataclass(frozen=True)
class PreflightReport:
    passed: bool
    findings: List[PreflightFinding] = field(default_factory=list)
    repository: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [finding.to_dict() for finding in self.findings],
            "repository": dict(self.repository),
        }


REQUIRED_FILES = [
    "Readme.md",
    "requirements.txt",
    "main.py",
    "prompts/step1.yaml",
    "prompts/step2.yaml",
    "prompts/judge.yaml",
]


def run_preflight(config: HarnessConfig, project_root: Path, require_plan: bool = False) -> PreflightReport:
    findings: List[PreflightFinding] = []
    project_root = project_root.resolve()

    for error in validate_config(config):
        findings.append(PreflightFinding("error", "CONFIG_INVALID", error))

    for rel_path in REQUIRED_FILES:
        if not (project_root / rel_path).exists():
            findings.append(PreflightFinding("error", "REQUIRED_FILE_MISSING", rel_path))

    if not _gitignore_contains(project_root, ".runtime/"):
        findings.append(PreflightFinding("warning", "RUNTIME_NOT_GITIGNORED", ".runtime/ is not ignored"))

    for secret in scan_for_secrets(project_root):
        findings.append(PreflightFinding("error", secret.reason_code, secret.to_message()))

    if require_plan and not _has_active_plan(project_root):
        findings.append(
            PreflightFinding(
                "error",
                "EXEC_PLAN_REQUIRED",
                "docs/exec-plans/active/ must contain at least one markdown plan",
            )
        )

    if not _is_subpath(config.runtime_root.resolve(), project_root):
        findings.append(
            PreflightFinding(
                "error",
                "RUNTIME_OUTSIDE_PROJECT",
                f"runtime_root is outside project: {config.runtime_root}",
            )
        )

    if config.live_api_enabled and os.environ.get("RUN_LIVE_LLM_TESTS", "false").lower() != "true":
        findings.append(
            PreflightFinding(
                "error",
                "LIVE_API_NOT_OPTED_IN",
                "live_api_enabled=true requires RUN_LIVE_LLM_TESTS=true",
            )
        )

    live_types = {config.generator.type, config.reviewer.type} & {"openai", "gemini"}
    if config.live_api_enabled and live_types and not _fake_run_passed(config):
        findings.append(
            PreflightFinding(
                "error",
                "FAKE_DRY_RUN_REQUIRED",
                "live execution requires a prior fake provider dry-run marker",
            )
        )

    if not config.live_api_enabled:
        if live_types:
            findings.append(
                PreflightFinding(
                    "error",
                    "LIVE_PROVIDER_WITHOUT_ENABLE",
                    f"live providers configured while disabled: {sorted(live_types)}",
                )
            )

    case_ids: Set[str] = set()
    for case in config.seed_cases:
        if case.case_id in case_ids:
            findings.append(PreflightFinding("error", "DUPLICATE_CASE_ID", case.case_id))
        case_ids.add(case.case_id)
        if contains_pii(case.query, case.context, case.expected_behavior):
            findings.append(PreflightFinding("error", "PII_DETECTED", case.case_id))

    repository = _repository_state(project_root)
    passed = not any(finding.severity == "error" for finding in findings)
    return PreflightReport(passed=passed, findings=findings, repository=repository)


def write_preflight_report(path: Path, report: PreflightReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _gitignore_contains(project_root: Path, entry: str) -> bool:
    gitignore = project_root / ".gitignore"
    if not gitignore.exists():
        return False
    lines = [line.strip() for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()]
    return entry in lines


def _has_active_plan(project_root: Path) -> bool:
    active = project_root / "docs" / "exec-plans" / "active"
    return active.exists() and any(path.suffix.lower() == ".md" and path.name.lower() != "readme.md" for path in active.iterdir())


def _fake_run_passed(config: HarnessConfig) -> bool:
    marker = config.runtime_root / config.worktree_id / "state" / "fake_run_passed.json"
    return marker.exists()


def _is_subpath(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _repository_state(project_root: Path) -> Dict[str, Any]:
    root = _git(["rev-parse", "--show-toplevel"], project_root)
    branch = _git(["branch", "--show-current"], project_root)
    status = _git(["status", "--short", "--branch"], project_root)
    return {
        "project_root": str(project_root),
        "git_detected": root["returncode"] == 0,
        "git_root": root["stdout"] if root["returncode"] == 0 else None,
        "branch": branch["stdout"] if branch["returncode"] == 0 else None,
        "status": status["stdout"].splitlines() if status["returncode"] == 0 else [],
        "git_error": root["stderr"] if root["returncode"] != 0 else None,
    }


def _git(args: List[str], cwd: Path) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=10,
        )
        return {
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    except Exception as exc:
        return {"returncode": 1, "stdout": "", "stderr": str(exc)}
