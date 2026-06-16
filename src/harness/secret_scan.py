from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


SECRET_PATTERNS = [
    re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
]

DEFAULT_EXCLUDED_PARTS = {
    ".git",
    ".runtime",
    ".env",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    reason_code: str

    def to_message(self) -> str:
        return f"{self.reason_code}: {self.path}:{self.line}"


def scan_for_secrets(root: Path, extra_excluded_parts: Iterable[str] = ()) -> List[SecretFinding]:
    excluded = DEFAULT_EXCLUDED_PARTS | set(extra_excluded_parts)
    findings: List[SecretFinding] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in excluded for part in path.parts):
            continue
        if path.name == ".env":
            continue
        if path.suffix.lower() in {".pdf", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".pyc"}:
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines, start=1):
            if any(pattern.search(line) for pattern in SECRET_PATTERNS):
                findings.append(
                    SecretFinding(
                        path=str(path.relative_to(root)),
                        line=idx,
                        reason_code="SECRET_PATTERN_DETECTED",
                    )
                )
    return findings
