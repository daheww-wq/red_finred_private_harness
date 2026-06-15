# FinRED Preprocessing Pipeline
FinRED 벤치마크 생성을 위한 전처리 파이프라인

---

## 환경 설정

### 1. 가상환경 생성 (Python 3.10)

```bash
# Conda 사용
conda create -n finred python=3.10 -y
conda activate finred

# 또는 venv 사용
python3.10 -m venv finred_env
source finred_env/bin/activate  # Linux/Mac
# finred_env\Scripts\activate   # Windows
```

### 2. 기본 패키지 설치

```bash
cd /path/to/FinRED
pip install -r requirements.txt
```

### 3. Unstructured 설치 (PDF 청킹용)

```bash
# Python 패키지
pip install "unstructured[all-docs]"

# 시스템 의존성 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-kor \
    libreoffice \
    pandoc
```

> **참고**: `tesseract-ocr-kor`는 한국어 OCR 지원을 위해 필요함
---

## 디렉토리 구조

```
src/
├── data/
│   ├── contexts/
│   │   ├── R3_products/              # R3 금융상품 요약 (Step 5 결과)
│   │   └── retrieved_chunks/         # 유사도 검색 결과 (Step 6 결과)
│   │       ├── per_taxonomy_chunks/  # R1, R2, R4, R5용
│   │       └── common_R3/            # R3 공통 컨텍스트
│   ├── orig/
│   │   ├── db/                       # 청크 CSV 데이터베이스 (Step 2, 3 결과)
│   │   ├── investinfo/               # R3 원본 추출 텍스트
│   │   ├── investinfo_sum/           # R3 요약 결과 (Step 4 결과)
│   │   └── parsed_docs/              # PDF 원본 + 청크 JSON (Step 1 결과)
│   │       ├── Common/
│   │       │   ├── R1/
│   │       │   │   ├── jsons/        # 청크 JSON
│   │       │   │   └── *.pdf         # 원본 PDF
│   │       │   ├── R2/
│   │       │   └── R5/
│   │       ├── R1/
│   │       │   ├── R1_1/
│   │       │   │   ├── jsons/
│   │       │   │   └── *.pdf
│   │       │   ├── R1_2/
│   │       │   └── ...
│   │       └── ...
│   └── queries/                      # 쿼리 CSV 파일
│       ├── R1_1_queries.csv
│       ├── R1_2_queries.csv
│       └── ...
├── preprocess/
│   ├── __init__.py
│   ├── 1_chunking.py                 # PDF → 청크 JSON
│   ├── 2_parsed_to_csv.py            # 청크 JSON → DB CSV
│   ├── 3_common_to_csv.py            # Common 청크 → DB CSV
│   ├── 4_product_summarizer.py       # R3 상품 PDF 요약 (vLLM)
│   ├── 5_summary_extractor.py        # 요약 후처리
│   └── 6_chunk_retriever.py          # 유사도 검색
└── ...
```

---

## 파이프라인 실행

### 전체 흐름도

```
[PDF 원본]
    │
    ▼ (Step 1)
[청크 JSON] ─────────────────────────────┐
    │                                    │
    ▼ (Step 2, 3)                        │
[DB CSV] ──────────────────┐             │
    │                      │             │
    │    [쿼리 CSV] ───────┤             │
    │         │            │             │
    ▼         ▼            ▼             │
    └────► (Step 6) ◄──────┘             │
              │                          │
              ▼                          │
    [retrieved_chunks JSON] ─────────────┤
                                         │
                                         ▼
                              [Step1_build.py]
                                         │
                                         ▼
                              [시나리오 JSON]
                                         │
                                         ▼
                              [Step2_build.py]
                                         │
                                         ▼
                              [시드 프롬프트]
```

### Step 1: PDF → 청크 JSON

PDF 문서를 의미론적 청크로 분할합니다.

```bash
cd /path/to/FinRED

# 단일 카테고리
python src/preprocess/1_chunking.py --category R1

# 전체 카테고리
python src/preprocess/1_chunking.py --category all
```

**입력**: `src/data/orig/parsed_docs/{category}/{subcategory}/*.pdf`  
**출력**: `src/data/orig/parsed_docs/{category}/{subcategory}/jsons/*.json`

---

### Step 2: 청크 JSON → DB CSV

Parse된 청크들을 검색용 CSV 데이터베이스로 변환합니다.

```bash
python src/preprocess/2_parsed_to_csv.py \
    --parsed_data_path src/data/orig/parsed_docs/R1 \
    --category R1
```

**입력**: `src/data/orig/parsed_docs/R1/R1_*/jsons/*.json`  
**출력**: `src/data/orig/db/R1_1_docs.csv`, `R1_2_docs.csv`, ...

---

### Step 3: Common → DB CSV

공통 문서들을 별도 CSV로 변환합니다.

```bash
python src/preprocess/3_common_to_csv.py \
    --common_path src/data/orig/parsed_docs/Common \
    --category R1
```

**입력**: `src/data/orig/parsed_docs/Common/R1/jsons/*.json`  
**출력**: `src/data/orig/db/R1_common_docs.csv`

---

### Step 4: R3 상품 PDF 요약 (GPU 필요)

R3 금융상품 설명서를 vLLM으로 요약합니다.

```bash
export CUDA_VISIBLE_DEVICES=0
python src/preprocess/4_product_summarizer.py
```

**입력**: `src/data/orig/investinfo/*_extracted.json`  
**출력**: `src/data/orig/investinfo_sum/*_sum.json`

---

### Step 5: Summary 추출

요약 결과에서 summary만 추출하여 최종 위치로 이동합니다.

```bash
python src/preprocess/5_summary_extractor.py
```

**입력**: `src/data/orig/investinfo_sum/*_sum.json`  
**출력**: `src/data/contexts/R3_products/*_sum.json`

---

### Step 6: 유사도 검색

쿼리와 청크 DB를 활용해 관련 청크를 검색합니다.

```bash
python src/preprocess/6_chunk_retriever.py \
    --category R1 \
    --api_key "sk-your-openai-api-key" \
    --top_k 12
```

**입력**: 
- `src/data/orig/db/R1_*_docs.csv`
- `src/data/queries/R1_*_queries.csv`

**출력**: `src/data/contexts/retrieved_chunks/per_taxonomy_chunks/R1_*_chunks.json`

---

## 카테고리별 실행 예시

### R1 전체 파이프라인

```bash
# Step 1-3: 문서 처리
python src/preprocess/1_chunking.py --category R1
python src/preprocess/2_parsed_to_csv.py --parsed_data_path src/data/orig/parsed_docs/R1 --category R1
python src/preprocess/3_common_to_csv.py --common_path src/data/orig/parsed_docs/Common --category R1

# Step 6: 검색
python src/preprocess/6_chunk_retriever.py --category R1 --api_key "sk-..." --top_k 12
```

### R3 전체 파이프라인 (상품 요약 포함)

```bash
# Step 1-3: 문서 처리
python src/preprocess/1_chunking.py --category R3
python src/preprocess/2_parsed_to_csv.py --parsed_data_path src/data/orig/parsed_docs/R3 --category R3
python src/preprocess/3_common_to_csv.py --common_path src/data/orig/parsed_docs/Common --category R3

# Step 4-5: 상품 요약 (GPU 필요)
export CUDA_VISIBLE_DEVICES=0
python src/preprocess/4_product_summarizer.py
python src/preprocess/5_summary_extractor.py

# Step 6: 검색
python src/preprocess/6_chunk_retriever.py --category R3 --api_key "sk-..." --top_k 12
```

---

## 주요 설정값

| 파일 | 설정 | 기본값 | 설명 |
|------|------|--------|------|
| `1_chunking.py` | `MAX_CHUNK_LENGTH` | 1200 | 최종 청크 최대 글자 수 |
| `4_product_summarizer.py` | `MODEL_MAX_LENGTH` | 32768 | 모델 컨텍스트 길이 |
| `4_product_summarizer.py` | `MAX_NEW_TOKENS` | 8192 | 생성 최대 토큰 수 |
| `6_chunk_retriever.py` | `top_k` | 12 | 검색 결과 개수 |

---

## 파일 형식

### 청크 JSON (Step 1 출력)

```json
[
  {
    "chunk_idx": 0,
    "text": "청크 텍스트 내용...",
    "metadata": {
      "filename": "원본파일.pdf",
      "element_type": "NarrativeText"
    }
  }
]
```

### DB CSV (Step 2, 3 출력)

| chunk_idx | text | filename | is_rule | lv2_name | lv1_name |
|-----------|------|----------|---------|----------|----------|
| 0 | 청크 텍스트... | file.pdf | False | R1_1 | R1 |

### Retrieved Chunks JSON (Step 6 출력)

```json
[
  {
    "query_idx": 0,
    "korean_query": "한국어 쿼리",
    "english_query": "English query",
    "extracted_texts": ["관련 청크 1", "관련 청크 2", ...]
  }
]
```