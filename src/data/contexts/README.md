---
id: 7fd6b042-dc7d-4692-8fe5-6535cef6c8ad
title: Untitled
created: '2026-06-17T13:53:14.596Z'
updated: '2026-06-17T13:53:16.608Z'
tags: []
---
# Context Output Guide

이 폴더는 Step1이 읽는 최종 컨텍스트 산출물을 보관합니다.

## R1, R2, R4, R5

`6_chunk_retriever.py` 실행 결과가 아래에 저장됩니다.

```text
contexts/retrieved_chunks/per_taxonomy_chunks/{category}_chunks.json
```

예:

```text
contexts/retrieved_chunks/per_taxonomy_chunks/R1_1_chunks.json
```

`Step1_build.py`는 R1, R2, R4, R5에서 이 파일을 읽습니다.

## R3

R3는 상품 설명서 요약과 공통 컨텍스트를 함께 씁니다.

```text
contexts/R3_products/*_sum.json
contexts/retrieved_chunks/common_R3/R3_contents.json
```

R3 상품 요약은 `4_product_summarizer.py`와 `5_summary_extractor.py`를 통해 생성합니다.
