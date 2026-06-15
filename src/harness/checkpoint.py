from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Set


class JsonlCheckpoint:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def records(self) -> Iterable[Dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"corrupt checkpoint at line {line_no}: {exc}") from exc
        return rows

    def completed_case_ids(self) -> Set[str]:
        ids: Set[str] = set()
        for row in self.records():
            case = row.get("case", {})
            case_id = case.get("case_id")
            if case_id:
                ids.add(str(case_id))
        return ids
