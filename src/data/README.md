# FinRED Data Folder Guide

이 폴더는 FinRED 파이프라인이 사용하는 입력 데이터와 전처리 산출물을 보관합니다.

## 사람이 직접 넣는 파일

주로 아래 세 위치에 파일을 넣습니다.

- `orig/parsed_docs/`: PDF 원본 문서
- `queries/`: 카테고리별 검색 쿼리 CSV
- `schemas/`: Step1/Step2 출력 구조를 설명하는 JSON 스키마

## 전처리로 생성되는 파일

아래 위치는 스크립트 실행 후 자동 생성되는 산출물입니다.

- `orig/parsed_docs/**/jsons/`: `1_chunking.py`가 만드는 청크 JSON
- `orig/db/`: `2_parsed_to_csv.py`, `3_common_to_csv.py`가 만드는 검색용 CSV
- `contexts/retrieved_chunks/`: `6_chunk_retriever.py`가 만드는 Step1 입력 컨텍스트
- `contexts/R3_products/`: R3 상품 요약 결과

## 권장 실행 순서

```powershell
python src\preprocess\1_chunking.py --project_root . --category R1
python src\preprocess\2_parsed_to_csv.py --project_root . --parsed_data_path src\data\orig\parsed_docs\R1 --category R1
python src\preprocess\3_common_to_csv.py --project_root . --common_path src\data\orig\parsed_docs\Common --category R1
python src\preprocess\6_chunk_retriever.py --project_root . --category R1 --api_key $env:OPENAI_API_KEY --top_k 12
```

주의: `src/preprocess/6_chunk_retriever.py`의 DB 경로가 `src/data/org/db`로 되어 있으면 `src/data/orig/db`로 수정해야 합니다.
