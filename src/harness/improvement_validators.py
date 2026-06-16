from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List, Set

from .result_schema import ImprovementCandidate
from .validators import contains_pii, normalize_text


def validate_candidates(candidates: Iterable[ImprovementCandidate]) -> List[ImprovementCandidate]:
    seen: Set[str] = set()
    validated: List[ImprovementCandidate] = []
    for candidate in candidates:
        codes = _validation_codes(candidate, seen)
        status = "validated" if not codes else "rejected"
        validated.append(replace(candidate, status=status, validation_codes=codes))
    return validated


def _validation_codes(candidate: ImprovementCandidate, seen: Set[str]) -> List[str]:
    codes: List[str] = []
    prompt = candidate.candidate_prompt.strip()
    digest = normalize_text(f"{candidate.taxonomy}\n{prompt}")
    if not candidate.taxonomy:
        codes.append("TAXONOMY_MISSING")
    if not prompt:
        codes.append("PROMPT_MISSING")
    if len(prompt) < 20:
        codes.append("PROMPT_TOO_SHORT")
    if contains_pii(prompt, candidate.expected_behavior):
        codes.append("PII_DETECTED")
    if digest in seen:
        codes.append("DUPLICATE_CANDIDATE")
    seen.add(digest)
    return codes
