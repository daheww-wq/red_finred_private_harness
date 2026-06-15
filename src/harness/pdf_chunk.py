from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from pypdf import PdfReader


DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP = 150
DEFAULT_MIN_CHARS = 40


def chunk_common_category(
    project_root: Path,
    category: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
    min_chars: int = DEFAULT_MIN_CHARS,
    overwrite: bool = False,
) -> Dict[str, object]:
    target_dir = project_root / "src" / "data" / "orig" / "parsed_docs" / "Common" / category
    jsons_dir = target_dir / "jsons"
    jsons_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(path for path in target_dir.glob("*.pdf") if path.is_file())
    outputs = []
    errors = []
    for pdf in pdfs:
        output_path = jsons_dir / f"{pdf.stem}.json"
        if output_path.exists() and not overwrite:
            outputs.append(str(output_path.relative_to(project_root)))
            continue
        try:
            chunks = pdf_to_chunks(pdf, max_chars=max_chars, overlap=overlap, min_chars=min_chars)
            output_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
            outputs.append(str(output_path.relative_to(project_root)))
        except Exception as exc:
            errors.append({"pdf": str(pdf.relative_to(project_root)), "error": str(exc)})

    return {
        "category": category,
        "input_dir": str(target_dir.relative_to(project_root)),
        "pdf_count": len(pdfs),
        "outputs": outputs,
        "errors": errors,
    }


def pdf_to_chunks(
    pdf_path: Path,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> List[dict]:
    reader = PdfReader(str(pdf_path))
    page_texts = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        if len(text) >= min_chars:
            page_texts.append((page_number, text))

    chunks = []
    chunk_idx = 0
    for page_number, text in page_texts:
        for part in split_text(text, max_chars=max_chars, overlap=overlap):
            chunks.append(
                {
                    "chunk_idx": chunk_idx,
                    "text": part,
                    "metadata": {
                        "filename": pdf_path.name,
                        "element_type": "PyPDFText",
                        "page_number": page_number,
                        "parser": "pypdf",
                    },
                }
            )
            chunk_idx += 1
    return chunks


def split_text(text: str, max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP) -> List[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap < 0:
        raise ValueError("overlap must not be negative")
    if len(text) <= max_chars:
        return [text] if text else []

    parts = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end), text.rfind("다. ", start, end))
            if boundary > start + max_chars // 2:
                end = boundary + 1
        part = text[start:end].strip()
        if part:
            parts.append(part)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return parts


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
