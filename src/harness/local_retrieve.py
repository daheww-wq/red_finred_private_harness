from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set

import pandas as pd


def retrieve_local(
    project_root: Path,
    category_prefix: str,
    top_k: int = 12,
) -> Dict[str, object]:
    r_num = category_prefix.split("_")[0]
    db_path = project_root / "src" / "data" / "orig" / "db"
    query_path = project_root / "src" / "data" / "queries" / f"{category_prefix}_queries.csv"
    output_path = (
        project_root
        / "src"
        / "data"
        / "contexts"
        / "retrieved_chunks"
        / "per_taxonomy_chunks"
        / f"{category_prefix}_chunks.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frames = []
    for candidate in (db_path / f"{category_prefix}_docs.csv", db_path / f"{r_num}_common_docs.csv"):
        if candidate.exists():
            frames.append(pd.read_csv(candidate))
    if not frames:
        raise FileNotFoundError(f"No document CSV found for {category_prefix}")
    if not query_path.exists():
        raise FileNotFoundError(f"Query CSV not found: {query_path}")

    corpus = pd.concat(frames, ignore_index=True).dropna(subset=["text"])
    queries = pd.read_csv(query_path)
    results = []
    for idx, row in queries.iterrows():
        ko_query = str(row.get("한국어 쿼리", "") or "")
        en_query = str(row.get("영어 쿼리", "") or "")
        query_terms = tokenize(f"{ko_query} {en_query}")
        ranked = []
        for _, doc in corpus.iterrows():
            text = str(doc["text"])
            score = score_text(query_terms, text)
            if score > 0:
                ranked.append((score, text))
        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked:
            ranked = [(0, str(text)) for text in corpus["text"].head(top_k)]

        results.append(
            {
                "query_idx": int(idx),
                "korean_query": ko_query,
                "english_query": en_query,
                "retrieval_method": "local_keyword_overlap",
                "extracted_texts": [text for _, text in ranked[:top_k]],
            }
        )

    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "category_prefix": category_prefix,
        "query_count": len(results),
        "output": str(output_path.relative_to(project_root)),
        "non_empty_results": sum(1 for item in results if item["extracted_texts"]),
    }


def tokenize(text: str) -> Set[str]:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", " ", text.casefold())
    terms = {token for token in normalized.split() if len(token) >= 2}
    extras = set()
    for token in terms:
        if len(token) >= 4 and re.search(r"[가-힣]", token):
            extras.update(token[i : i + 3] for i in range(0, max(len(token) - 2, 0)))
    return terms | extras


def score_text(query_terms: Set[str], text: str) -> int:
    if not query_terms:
        return 0
    text_terms = tokenize(text)
    overlap = query_terms & text_terms
    substring_hits = {term for term in query_terms if term in text.casefold()}
    return len(overlap) * 3 + len(substring_hits)
