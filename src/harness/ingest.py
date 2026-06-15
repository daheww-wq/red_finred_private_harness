from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


PDF_INTAKE_ROOT = Path("src/data/orig/incoming_pdfs")
ROUTING_ROOT = Path("src/data/orig/routing")


@dataclass(frozen=True)
class RoutingRecord:
    source_file: str
    document_summary: str
    main_context: str
    primary_category: str
    secondary_categories: List[str]
    routing_rationale: str
    candidate_queries: List[str]
    quality_flags: List[str] = field(default_factory=list)
    routed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, object]:
        return {
            "source_file": self.source_file,
            "document_summary": self.document_summary,
            "main_context": self.main_context,
            "primary_category": self.primary_category,
            "secondary_categories": list(self.secondary_categories),
            "routing_rationale": self.routing_rationale,
            "candidate_queries": list(self.candidate_queries),
            "quality_flags": list(self.quality_flags),
            "routed_at": self.routed_at,
        }


KEYWORD_RULES = {
    "R1": [
        "security",
        "cyber",
        "malware",
        "ransomware",
        "ddos",
        "authentication",
        "credential",
        "breach",
        "incident",
        "\ubcf4\uc548",
        "\uc0ac\uc774\ubc84",
        "\uc545\uc131\ucf54\ub4dc",
        "\ub79c\uc12c\uc6e8\uc5b4",
        "\uc778\uc99d",
        "\uce68\ud574",
        "\uc720\ucd9c\uc0ac\uace0",
    ],
    "R2": [
        "voice phishing",
        "phishing",
        "fraud",
        "scam",
        "impersonation",
        "safe account",
        "loan fraud",
        "mule",
        "\ubcf4\uc774\uc2a4\ud53c\uc2f1",
        "\ud53c\uc2f1",
        "\uc0ac\uae30",
        "\uc0ac\uce6d",
        "\uc548\uc804\uacc4\uc88c",
        "\ub300\ud3ec\ud1b5\uc7a5",
        "\ubd88\ubc95\ub300\ucd9c",
    ],
    "R3": [
        "product",
        "terms",
        "suitability",
        "disclosure",
        "principal loss",
        "fund",
        "insurance",
        "derivative",
        "\uc0c1\ud488",
        "\uc57d\uad00",
        "\uc124\uba85\uc11c",
        "\uc801\ud569\uc131",
        "\uc704\ud5d8\ub4f1\uae09",
        "\uc6d0\uae08\uc190\uc2e4",
        "\ubd88\uc644\uc804\ud310\ub9e4",
    ],
    "R4": [
        "advertising",
        "exaggerated",
        "consumer rights",
        "consumer protection",
        "financial consumer",
        "cooling off",
        "withdrawal",
        "vulnerable",
        "complaint",
        "market manipulation",
        "\uad11\uace0",
        "\uacfc\uc7a5\uad11\uace0",
        "\uae08\uc18c\ubc95",
        "\uae08\uc735\uc18c\ube44\uc790",
        "\uae08\uc735\uc18c\ube44\uc790\ubcf4\ud638",
        "\uc18c\ube44\uc790\ubcf4\ud638",
        "\uc18c\ube44\uc790 \uad8c\ub9ac",
        "\uccad\uc57d\ucca0\ud68c",
        "\ucde8\uc57d\uacc4\uce35",
        "\ubbfc\uc6d0",
        "\uc2dc\uc7a5\uc870\uc791",
        "\ubd88\uacf5\uc815",
    ],
    "R5": [
        "compliance",
        "audit",
        "supervision",
        "internal control",
        "risk management",
        "incident reporting",
        "outsourcing",
        "cloud",
        "disaster recovery",
        "\ucef4\ud50c\ub77c\uc774\uc5b8\uc2a4",
        "\uac10\uc0ac",
        "\uac10\ub3c5",
        "\ub0b4\ubd80\ud1b5\uc81c",
        "\uc704\ud5d8\uad00\ub9ac",
        "\uc0ac\uace0\ubcf4\uace0",
        "\uc678\uc8fc",
        "\ud074\ub77c\uc6b0\ub4dc",
        "\uc7ac\ud574\ubcf5\uad6c",
        "\uaddc\uc81c",
    ],
}


def ingest_unclassified_pdfs(
    project_root: Path,
    move_files: bool = False,
    force: bool = False,
    intake_root: Path = PDF_INTAKE_ROOT,
    routing_root: Path = ROUTING_ROOT,
) -> Dict[str, object]:
    intake_root = project_root / intake_root
    routing_root = project_root / routing_root
    unclassified = intake_root / "unclassified"
    routing_root.mkdir(parents=True, exist_ok=True)
    unclassified.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(path for path in unclassified.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    records = [_route_pdf(path) for path in pdfs]

    routing_path = routing_root / "pdf_routing_records.jsonl"
    review_path = routing_root / "review_queue.jsonl"

    if force:
        _remove_existing_sources(routing_path, [record.source_file for record in records])
        _remove_existing_sources(review_path, [record.source_file for record in records])
    else:
        existing = _existing_sources(routing_path)
        records = [record for record in records if record.source_file not in existing]

    _append_jsonl(routing_path, [record.to_dict() for record in records])

    review_records = [
        {
            "source_file": record.source_file,
            "primary_category": record.primary_category,
            "artifact_stage": "routing",
            "issue_code": flag,
            "severity": "medium" if flag == "NEEDS_HUMAN_REVIEW" else "low",
            "evidence": record.routing_rationale,
            "recommended_action": "Review PDF text extraction and confirm R1-R5 routing before generation.",
            "owner": "human",
            "status": "open",
        }
        for record in records
        for flag in record.quality_flags
    ]
    _append_jsonl(review_path, review_records)

    moved: List[str] = []
    if move_files:
        for pdf, record in zip(pdfs, records):
            target_dir = intake_root / record.primary_category
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = _unique_path(target_dir / pdf.name)
            pdf.replace(target_path)
            moved.append(str(target_path.relative_to(project_root)))

    return {
        "scanned_dir": str(unclassified.relative_to(project_root)),
        "pdf_count": len(pdfs),
        "records_written": len(records),
        "review_items_written": len(review_records),
        "moved_files": moved,
        "routing_records": str(routing_path.relative_to(project_root)),
        "review_queue": str(review_path.relative_to(project_root)),
        "records": [record.to_dict() for record in records],
    }


def _route_pdf(path: Path) -> RoutingRecord:
    text = _normalize(path.stem)
    scores = {
        category: sum(1 for keyword in keywords if _normalize(keyword) in text)
        for category, keywords in KEYWORD_RULES.items()
    }
    primary = max(scores, key=lambda item: scores[item])
    max_score = scores[primary]
    secondary = [category for category, score in scores.items() if category != primary and score > 0]
    flags: List[str] = []

    if max_score == 0:
        primary = "R4"
        flags.extend(["CATEGORY_AMBIGUOUS", "NEEDS_HUMAN_REVIEW"])
        rationale = "No strong filename keyword matched; defaulted to R4 for financial-consumer safety review."
    else:
        flags.append("NEEDS_HUMAN_REVIEW")
        rationale = f"Filename matched {max_score} keyword(s) for {primary}; confirm with PDF body text before generation."

    return RoutingRecord(
        source_file=path.name,
        document_summary=f"Initial routing draft for {path.name}. Body text has not been parsed by this ingest command.",
        main_context="Pending PDF parsing and chunk extraction.",
        primary_category=primary,
        secondary_categories=secondary,
        routing_rationale=rationale,
        candidate_queries=_candidate_queries(primary, path.stem),
        quality_flags=flags,
    )


def _candidate_queries(category: str, source_name: str) -> List[str]:
    topic = re.sub(r"[_\\-]+", " ", source_name).strip()
    defaults = {
        "R1": ["financial security threat controls", "financial IT incident response"],
        "R2": ["financial fraud impersonation prevention", "voice phishing fund transfer fraud"],
        "R3": ["financial product risk disclosure", "incomplete sales suitability explanation"],
        "R4": ["financial consumer rights unfair conduct", "vulnerable customer exaggerated advertising"],
        "R5": ["financial compliance internal control audit", "regulatory reporting risk management"],
    }
    return [topic, *defaults.get(category, [])]


def _append_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        path.touch(exist_ok=True)
        return
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _existing_sources(path: Path) -> set[str]:
    if not path.exists():
        return set()
    sources: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        source = raw.get("source_file")
        if isinstance(source, str):
            sources.add(source)
    return sources


def _remove_existing_sources(path: Path, sources: Iterable[str]) -> None:
    source_set = set(sources)
    if not path.exists() or not source_set:
        return
    kept = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if raw.get("source_file") not in source_set:
            kept.append(line)
    ending = "\n" if kept else ""
    path.write_text("\n".join(kept) + ending, encoding="utf-8")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find unique path for {path}")
