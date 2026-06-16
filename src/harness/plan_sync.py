from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .lifecycle import ExecutionPlan, RequestedMaterials, TodoItem, write_lifecycle_state
from .runtime import ensure_runtime


TASK_RE = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX~-])\]\s+(?P<title>.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(?P<title>.+?)\s*$")


@dataclass(frozen=True)
class ParsedExecPlan:
    title: str
    objective: str
    stages: List[str]
    todo: List[TodoItem]
    assumptions: List[str]
    risks: List[str]


def sync_exec_plan(plan_path: Path, runtime_root: Path, worktree_id: str) -> Dict[str, Any]:
    parsed = parse_exec_plan(plan_path)
    paths = ensure_runtime(runtime_root, worktree_id)
    materials = RequestedMaterials(config_path=str(plan_path))
    plan = ExecutionPlan(
        run_name=parsed.title,
        objective=parsed.objective,
        stages=parsed.stages,
        requested_materials=materials,
        assumptions=parsed.assumptions,
        risks=parsed.risks,
    )
    write_lifecycle_state(paths.state, materials, plan, parsed.todo)
    manifest = {
        "plan_path": str(plan_path),
        "runtime_state": str(paths.state),
        "execution_plan": str(paths.state / "execution_plan.json"),
        "todo": str(paths.state / "todo.json"),
        "todo_count": len(parsed.todo),
    }
    (paths.state / "plan_sync.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def parse_exec_plan(plan_path: Path) -> ParsedExecPlan:
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = _first_heading(lines) or plan_path.stem.replace("-", " ").title()
    sections = _sections(lines)
    scope = sections.get("scope", [])
    verification = sections.get("verification", [])
    open_items = sections.get("open items", [])
    risks = _bullets(sections.get("risks", [])) or _bullets(sections.get("out of scope for phase 1", []))
    assumptions = _bullets(sections.get("assumptions", [])) or _bullets(sections.get("decision log", []))

    todo = _tasks(lines)
    if not todo:
        source_lines = open_items or scope or verification
        todo = [
            TodoItem(step_id=_slug(item), title=item, status="pending")
            for item in _bullets(source_lines)
        ]
    if not todo:
        todo = [TodoItem(step_id="review_plan", title=f"Review {title}", status="pending")]

    stages = [item.step_id for item in todo]
    objective = _objective(sections, title)
    return ParsedExecPlan(
        title=title,
        objective=objective,
        stages=stages,
        todo=todo,
        assumptions=assumptions,
        risks=risks,
    )


def _first_heading(lines: List[str]) -> str:
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _sections(lines: List[str]) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    current = ""
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
            continue
        if current:
            sections[current].append(line)
    return sections


def _tasks(lines: List[str]) -> List[TodoItem]:
    tasks: List[TodoItem] = []
    for line in lines:
        match = TASK_RE.match(line)
        if not match:
            continue
        title = match.group("title").strip()
        status = _status_from_mark(match.group("mark"))
        tasks.append(TodoItem(step_id=_slug(title), title=title, status=status))
    return tasks


def _status_from_mark(mark: str) -> str:
    if mark.lower() == "x":
        return "completed"
    if mark == "~":
        return "in_progress"
    if mark == "-":
        return "skipped"
    return "pending"


def _bullets(lines: List[str]) -> List[str]:
    items: List[str] = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        match = BULLET_RE.match(line)
        if match and "[" not in line[: line.find(match.group("title"))]:
            items.append(match.group("title").strip())
            continue
        if items and line.startswith("  ") and line.strip():
            items[-1] = f"{items[-1]} {line.strip()}"
    return items


def _objective(sections: Dict[str, List[str]], title: str) -> str:
    for key in ("objective", "scope", "summary"):
        lines = [line.strip() for line in sections.get(key, []) if line.strip() and not line.strip().startswith("-")]
        if lines:
            return " ".join(lines)
    return f"Execute and track {title}."


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9가-힣]+", "_", text.lower()).strip("_")
    return slug[:80] or "task"
