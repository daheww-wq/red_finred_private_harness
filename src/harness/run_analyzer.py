from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .result_schema import AnalyzedCase


RUBRIC_PREFIX = "rubric_"


def analyze_results(result_dir: Path, output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = list(_load_cases(result_dir))
    failures = [case for case in cases if case.failed]
    summary = _summary(cases, failures, result_dir)

    _write_jsonl(output_dir / "cases.jsonl", [case.to_dict() for case in cases])
    _write_jsonl(output_dir / "failure_cases.jsonl", [case.to_dict() for case in failures])
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "summary": summary,
        "cases_path": str(output_dir / "cases.jsonl"),
        "failure_cases_path": str(output_dir / "failure_cases.jsonl"),
        "summary_path": str(output_dir / "summary.json"),
    }


def _load_cases(result_dir: Path) -> Iterable[AnalyzedCase]:
    csv_stems = {path.stem for path in result_dir.glob("*.csv")}
    for path in sorted(result_dir.glob("*")):
        if path.suffix.lower() == ".csv":
            yield from _load_csv(path)
        elif path.suffix.lower() == ".json":
            if path.stem in csv_stems or "_asr_" in path.stem:
                continue
            yield from _load_json(path)


def _load_csv(path: Path) -> Iterable[AnalyzedCase]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            yield _case_from_row(row, path, index)


def _load_json(path: Path) -> Iterable[AnalyzedCase]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    rows = raw if isinstance(raw, list) else raw.get("records", raw.get("results", [])) if isinstance(raw, dict) else []
    if isinstance(rows, dict):
        rows = list(rows.values())
    for index, item in enumerate(rows):
        if isinstance(item, dict):
            yield _case_from_row(item, path, index)


def _case_from_row(row: Dict[str, Any], path: Path, index: int) -> AnalyzedCase:
    taxonomy = str(row.get("category_prefix") or row.get("taxonomy") or _taxonomy_from_name(path.name)).strip()
    prompt = str(row.get("attack_prompt") or row.get("prompt") or row.get("query") or "").strip()
    response = str(row.get("response") or row.get("target_response") or row.get("generated_response") or "").strip()
    final_judgment = str(row.get("final_judgment") or row.get("judgment") or row.get("status") or "").strip()
    rubrics = {str(k): str(v).strip() for k, v in row.items() if str(k).startswith(RUBRIC_PREFIX)}
    case_id = str(row.get("case_id") or row.get("id") or f"{path.stem}-{index:04d}").strip()
    failure_type = classify_failure(path.name, final_judgment, rubrics, response)
    return AnalyzedCase(
        case_id=case_id,
        taxonomy=taxonomy,
        prompt=prompt,
        response=response,
        final_judgment=final_judgment,
        rubric_results=rubrics,
        failure_type=failure_type,
        source_file=str(path),
        metadata={"row_index": index},
    )


def classify_failure(source_name: str, final_judgment: str, rubrics: Dict[str, str], response: str) -> str:
    source_lower = source_name.lower()
    judgment = final_judgment.strip().lower()
    rubric_values = {value.strip().lower() for value in rubrics.values() if value.strip()}

    if "partial" in source_lower or "quota" in source_lower or "timeout" in source_lower:
        return "QUOTA_OR_TIMEOUT"
    if not response:
        return "MODEL_ERROR"
    if not judgment or judgment in {"error", "unknown", "none", "nan"}:
        return "JUDGE_UNCLEAR"
    if "unsafe" in judgment:
        return "UNSAFE_RESPONSE"
    if "unsafe" in rubric_values and "safe" in judgment:
        return "RUBRIC_MISMATCH"
    return "PASS"


def _summary(cases: List[AnalyzedCase], failures: List[AnalyzedCase], result_dir: Path) -> Dict[str, Any]:
    by_taxonomy = Counter(case.taxonomy or "<unknown>" for case in cases)
    by_failure = Counter(case.failure_type for case in failures)
    by_judgment = Counter(case.final_judgment or "<empty>" for case in cases)
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result_dir": str(result_dir),
        "total_cases": len(cases),
        "failure_cases": len(failures),
        "pass_cases": len(cases) - len(failures),
        "failure_rate": round(len(failures) / len(cases), 4) if cases else 0.0,
        "by_taxonomy": dict(sorted(by_taxonomy.items())),
        "by_failure_type": dict(sorted(by_failure.items())),
        "by_final_judgment": dict(sorted(by_judgment.items())),
    }


def _taxonomy_from_name(name: str) -> str:
    lowered = name.lower()
    for prefix in ("r1", "r2", "r3", "r4", "r5"):
        marker = f"_{prefix}_"
        if marker in lowered:
            tail = lowered.split(marker, 1)[1]
            parts = tail.split("_")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return f"{prefix.upper()}_{parts[1]}"
            if parts and parts[0].isdigit():
                return f"{prefix.upper()}_{parts[0]}"
    return ""


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
