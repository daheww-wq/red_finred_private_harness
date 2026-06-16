from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, List, Set

from .models import RedTeamCase


PII_PATTERNS = [
    re.compile(r"\b\d{6}-\d{7}\b"),
    re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
]

COMMAND_LIKE_PATTERNS = [
    re.compile(r"\b(?:bash|sh|cmd|powershell|pwsh)\s+(?:-c|/c)\b", re.IGNORECASE),
    re.compile(r"\bpython\s+-c\b", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\b(?:curl|wget)\b.+\|", re.IGNORECASE),
    re.compile(r"\bStart-Process\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class ValidationResult:
    schema_valid: bool
    pii_detected: bool
    duplicate: bool
    reason_codes: List[str]

    @property
    def passed(self) -> bool:
        return self.schema_valid and not self.pii_detected and not self.duplicate and not self.reason_codes


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def normalized_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def contains_pii(*texts: str) -> bool:
    combined = "\n".join(texts)
    return any(pattern.search(combined) for pattern in PII_PATTERNS)


def contains_command_like_payload(*texts: str) -> bool:
    combined = "\n".join(texts)
    return any(pattern.search(combined) for pattern in COMMAND_LIKE_PATTERNS)


def exact_duplicate(case: RedTeamCase, seen_hashes: Set[str]) -> bool:
    digest = normalized_hash(f"{case.category}\n{case.query}\n{case.context}")
    if digest in seen_hashes:
        return True
    seen_hashes.add(digest)
    return False


def validate_case(case: RedTeamCase, seen_hashes: Set[str]) -> ValidationResult:
    reason_codes: List[str] = []
    schema_errors = case.validate()
    duplicate = exact_duplicate(case, seen_hashes)
    pii = contains_pii(case.query, case.context, case.expected_behavior)

    if schema_errors:
        reason_codes.append("SCHEMA_INVALID")
    if duplicate:
        reason_codes.append("EXACT_DUPLICATE")
    if pii:
        reason_codes.append("PII_DETECTED")
    if contains_command_like_payload(case.query, case.context, case.expected_behavior):
        reason_codes.append("COMMAND_LIKE_TEXT")
    if not case.context or len(case.context) < 20:
        reason_codes.append("INSUFFICIENT_EVIDENCE")

    return ValidationResult(
        schema_valid=not schema_errors,
        pii_detected=pii,
        duplicate=duplicate,
        reason_codes=reason_codes,
    )


def validate_batch(cases: Iterable[RedTeamCase]) -> List[ValidationResult]:
    seen: Set[str] = set()
    return [validate_case(case, seen) for case in cases]
