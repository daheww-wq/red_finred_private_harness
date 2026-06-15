from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal


TodoStatus = Literal[
    "pending",
    "in_progress",
    "completed",
    "failed",
    "skipped",
    "quarantined",
    "needs_review",
]


@dataclass(frozen=True)
class RequestedMaterials:
    config_path: str
    source_documents: List[str] = field(default_factory=list)
    retrieval_queries: List[str] = field(default_factory=list)
    retrieved_contexts: List[str] = field(default_factory=list)
    scenarios: List[str] = field(default_factory=list)
    attack_prompts: List[str] = field(default_factory=list)
    target_responses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_path": self.config_path,
            "source_documents": list(self.source_documents),
            "retrieval_queries": list(self.retrieval_queries),
            "retrieved_contexts": list(self.retrieved_contexts),
            "scenarios": list(self.scenarios),
            "attack_prompts": list(self.attack_prompts),
            "target_responses": list(self.target_responses),
        }


@dataclass
class TodoItem:
    step_id: str
    title: str
    status: TodoStatus = "pending"
    reason_codes: List[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: _now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class ExecutionPlan:
    run_name: str
    objective: str
    stages: List[str]
    requested_materials: RequestedMaterials
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_name": self.run_name,
            "objective": self.objective,
            "stages": list(self.stages),
            "requested_materials": self.requested_materials.to_dict(),
            "assumptions": list(self.assumptions),
            "risks": list(self.risks),
        }


def default_todo() -> List[TodoItem]:
    return [
        TodoItem("request_materials", "Record requested materials", "pending"),
        TodoItem("plan", "Write execution plan", "pending"),
        TodoItem("preflight", "Inspect code, folders, and configuration", "pending"),
        TodoItem("validate_inputs", "Validate cases and inputs", "pending"),
        TodoItem("execute", "Run configured stages", "pending"),
        TodoItem("verify_outputs", "Verify outputs and artifacts", "pending"),
        TodoItem("checkpoint", "Write checkpoint and logs", "pending"),
        TodoItem("report", "Write final report", "pending"),
    ]


def write_lifecycle_state(
    state_dir: Path,
    materials: RequestedMaterials,
    plan: ExecutionPlan,
    todo: Iterable[TodoItem],
) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    _write_json(state_dir / "run_request.json", materials.to_dict())
    _write_json(state_dir / "execution_plan.json", plan.to_dict())
    _write_json(state_dir / "todo.json", [item.to_dict() for item in todo])


def update_todo(state_dir: Path, step_id: str, status: TodoStatus, reason_codes: List[str] | None = None) -> None:
    todo_path = state_dir / "todo.json"
    todo = json.loads(todo_path.read_text(encoding="utf-8")) if todo_path.exists() else []
    found = False
    for item in todo:
        if item.get("step_id") == step_id:
            item["status"] = status
            item["reason_codes"] = list(reason_codes or [])
            item["updated_at"] = _now()
            found = True
            break
    if not found:
        todo.append(
            {
                "step_id": step_id,
                "title": step_id.replace("_", " ").title(),
                "status": status,
                "reason_codes": list(reason_codes or []),
                "updated_at": _now(),
            }
        )
    _write_json(todo_path, todo)


def load_status(state_dir: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for name in ("run_request", "execution_plan", "todo", "preflight"):
        path = state_dir / f"{name}.json"
        if path.exists():
            result[name] = json.loads(path.read_text(encoding="utf-8"))
    return result


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
