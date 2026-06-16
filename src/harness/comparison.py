from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def compare_analyses(baseline_dir: Path, candidate_dir: Path, output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline = _load_summary(baseline_dir)
    candidate = _load_summary(candidate_dir)
    comparison = {
        "baseline": str(baseline_dir),
        "candidate": str(candidate_dir),
        "baseline_total_cases": baseline.get("total_cases", 0),
        "candidate_total_cases": candidate.get("total_cases", 0),
        "baseline_failure_cases": baseline.get("failure_cases", 0),
        "candidate_failure_cases": candidate.get("failure_cases", 0),
        "failure_case_delta": candidate.get("failure_cases", 0) - baseline.get("failure_cases", 0),
        "baseline_failure_rate": baseline.get("failure_rate", 0.0),
        "candidate_failure_rate": candidate.get("failure_rate", 0.0),
        "failure_rate_delta": round(candidate.get("failure_rate", 0.0) - baseline.get("failure_rate", 0.0), 4),
        "baseline_by_failure_type": baseline.get("by_failure_type", {}),
        "candidate_by_failure_type": candidate.get("by_failure_type", {}),
    }
    (output_dir / "comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "comparison.md").write_text(_markdown(comparison), encoding="utf-8")
    return comparison


def _load_summary(path: Path) -> Dict[str, Any]:
    return json.loads((path / "summary.json").read_text(encoding="utf-8"))


def _markdown(comparison: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Harness Growth Comparison",
            "",
            f"- Baseline: `{comparison['baseline']}`",
            f"- Candidate: `{comparison['candidate']}`",
            f"- Failure cases delta: `{comparison['failure_case_delta']}`",
            f"- Failure rate delta: `{comparison['failure_rate_delta']}`",
            "",
            "## Failure Types",
            "",
            f"- Baseline: `{comparison['baseline_by_failure_type']}`",
            f"- Candidate: `{comparison['candidate_by_failure_type']}`",
            "",
        ]
    )
