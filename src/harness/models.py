from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


CaseStatus = Literal["generated", "reviewed", "approved", "rejected", "quarantined", "failed"]


@dataclass(frozen=True)
class RedTeamCase:
    case_id: str
    category: str
    query: str
    context: str
    expected_behavior: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        errors: List[str] = []
        for field_name in ("case_id", "category", "query", "context", "expected_behavior"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{field_name} is required")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "query": self.query,
            "context": self.context,
            "expected_behavior": self.expected_behavior,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "RedTeamCase":
        return cls(
            case_id=str(raw.get("case_id", "")).strip(),
            category=str(raw.get("category", "")).strip(),
            query=str(raw.get("query", "")).strip(),
            context=str(raw.get("context", "")).strip(),
            expected_behavior=str(raw.get("expected_behavior", "")).strip(),
            metadata=dict(raw.get("metadata", {}) or {}),
        )


@dataclass(frozen=True)
class ProviderRequest:
    role: str
    case: RedTeamCase
    prompt: str
    run_id: str


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    model: str
    text: str
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewResult:
    status: CaseStatus
    reason_codes: List[str]
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PipelineRecord:
    case: RedTeamCase
    generated: ProviderResponse
    review: ReviewResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case": self.case.to_dict(),
            "generated": {
                "provider": self.generated.provider,
                "model": self.generated.model,
                "text": self.generated.text,
                "raw": dict(self.generated.raw),
            },
            "review": self.review.to_dict(),
        }
