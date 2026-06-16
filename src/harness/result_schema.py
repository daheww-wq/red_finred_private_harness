from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class AnalyzedCase:
    case_id: str
    taxonomy: str
    prompt: str
    response: str
    final_judgment: str
    rubric_results: Dict[str, str]
    failure_type: str
    source_file: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        return self.failure_type != "PASS"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "taxonomy": self.taxonomy,
            "prompt": self.prompt,
            "response": self.response,
            "final_judgment": self.final_judgment,
            "rubric_results": dict(self.rubric_results),
            "failure_type": self.failure_type,
            "source_file": self.source_file,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ImprovementCandidate:
    candidate_id: str
    source_case_id: str
    taxonomy: str
    failure_type: str
    proposed_action: str
    candidate_prompt: str
    expected_behavior: str
    status: str = "proposed"
    validation_codes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_case_id": self.source_case_id,
            "taxonomy": self.taxonomy,
            "failure_type": self.failure_type,
            "proposed_action": self.proposed_action,
            "candidate_prompt": self.candidate_prompt,
            "expected_behavior": self.expected_behavior,
            "status": self.status,
            "validation_codes": list(self.validation_codes),
            "metadata": dict(self.metadata),
        }
