# FinRED: Financial Red-teaming Evaluation Dataset

금융 도메인 특화 AI 안전성 평가를 위한 레드팀 벤치마크 생성 파이프라인입니다.

---

### 1. 레포지토리 설명

연관 프로젝트: RED (Red-teaming Evaluation Dataset)  
담당자: 정민재, 임용택
작성일: 2026-02-23  

금융 도메인에 특화된 레드팀 시드 프롬프트를 자동으로 생성하고, 생성된 프롬프트에 대한 LLM 응답을 평가하는 파이프라인입니다.  
금융 보안 위협(R1), 사기 및 불법 행위(R2), 불완전판매(R3), 시장 조작(R4), 규제 위반(R5) 등 5개 카테고리 / 26개 서브카테고리로 구성된 위험 시나리오를 기반으로, OpenAI GPT-4로 시나리오를 생성하고 Gemini로 시드 프롬프트를 생성합니다. 이후 생성된 프롬프트에 대한 모델 응답을 LLM Judge 기반으로 평가합니다.

---

### 2. 데이터셋

준비 데이터 : https://drive.google.com/drive/u/0/folders/1cfBf419OUDrQQMRKMPLLJqRX97WMxExC

설명:
- **원본 출처**: 금융감독원 공시 자료, R3 금융상품 설명서 등 내부 금융 도메인 문서를 PDF 파싱 후 청크화하여 구성
- **제작 방법**: `src/preprocess/`의 전처리 파이프라인(청킹 → CSV 변환 → 상품 요약 → 청크 검색)을 통해 컨텍스트 데이터를 구성하고, Step1(시나리오 생성) → Step2(시드 프롬프트 생성) 파이프라인으로 데이터셋 생성
- **스키마**:
  - 시나리오 JSON (Step 1 출력): `scenario_id`, `context`, `risk_description`, `attack_vector`
  - 프롬프트 JSON (Step 2 출력): `prompt_1`, `prompt_1_optionalelements`, `prompt_2`, `prompt_2_optionalelements`, ...
  - 평가 결과: 입력 CSV + 모델 응답 컬럼 + judge 점수 컬럼
- **외부 사용 가능 여부**: 비공개 (내부 사용 전용)

---

### 3. 구체적인 설명

**방법 1. Step1 - 시나리오 생성 (`src/Step1_build.py`)**
- 컨텍스트(`src/data/contexts/`), 스키마(`src/schemas/`), 쿼리(`src/data/queries/`)를 조합하여 금융 도메인 레드팀 시나리오를 생성
- 모델: OpenAI GPT-4
- 출력: `src/outputs/scenarios/{category}/` 에 시나리오 JSON 파일

**방법 2. Step2 - 시드 프롬프트 생성 (`src/Step2_build.py`)**
- Step 1에서 생성된 시나리오 JSON을 입력으로 받아 레드팀 시드 프롬프트를 생성
- 모델: Google Gemini 2.5 Pro
- 출력: `src/outputs/prompts/{category}/` 에 프롬프트 JSON + 통합 CSV

**방법 3. Evaluation - 모델 응답 평가 (`src/eval/judge_finred.py`)**
- 생성된 시드 프롬프트에 대한 대상 LLM의 응답을 LLM Judge 방식으로 평가
- 루브릭 기반 채점 (`src/eval/template/rubric_financial.py`)으로 금융 위험도 점수 산출
- 출력: `infer_result/` (평가 결과 CSV/JSON), `judge_errors/` (에러 로그)

**카테고리 구성**

| 카테고리 | 서브카테고리 | 설명 |
|----------|--------------|------|
| R1 | R1_1 ~ R1_6 | 금융 보안 위협 |
| R2 | R2_1 ~ R2_5 | 사기 및 불법 행위 |
| R3 | R3_1 ~ R3_3 | 불완전판매 |
| R4 | R4_1 ~ R4_5 | 시장 조작 |
| R5 | R5_1 ~ R5_7 | 규제 위반 |

---

### 4. 파이프라인 설명 및 실행

**1. 파이프라인 설명**

```
[컨텍스트 + 스키마 + 쿼리]
         │
         ▼
   ┌─────────────┐
   │ Step1_build │  시나리오 생성 (OpenAI GPT-4)
   └─────────────┘
         │ src/outputs/scenarios/{category}/*.json
         ▼
   ┌─────────────┐
   │ Step2_build │  시드 프롬프트 생성 (Google Gemini)
   └─────────────┘
         │ src/outputs/prompts/{category}/*.json + all.csv
         ▼
   ┌─────────────┐
   │ Evaluation  │  LLM Judge 기반 모델 응답 평가
   └─────────────┘
        │ src/eval/infer_result/*.csv, *.json
         ▼
   [ASR (Attack Success Rate) 산출]
```

**2. 파이프라인 실행**

**데이터 생성 파이프라인 (Step1 + Step2)**

```bash
# run/run_data_generate.sh 참고
python main.py \
    --step <1|2|all> \
    --category <카테고리> \
    --openai_api_key $OPENAI_API_KEY \
    --gemini_api_key $GEMINI_API_KEY
```

주요 변경 인자:

| 파라미터 | 필수 | 설명 |
|----------|------|------|
| `--step` | ✅ | 실행 단계: `1` (시나리오), `2` (프롬프트), `all` (전체) |
| `--category` | ✅ | 카테고리: `R1`, `R2`, `R3`, `R4`, `R5` 또는 `R1_1` 등 서브카테고리 지정 가능 |
| `--openai_api_key` | Step 1 필수 | OpenAI API 키 |
| `--gemini_api_key` | Step 2 필수 | Gemini API 키 |
| `--lang` | ❌ | 프롬프트 언어: `ko` (기본값), `en` |
| `--num_prompts` | ❌ | 생성할 프롬프트 수 (기본값: 3) |

```bash
# 전체 파이프라인 실행 예시 (R1 카테고리)
python main.py \
    --step all \
    --category R1 \
    --openai_api_key "sk-proj-..." \
    --gemini_api_key "AIza..."

# Step 1만 실행 (시나리오 생성)
python main.py \
    --step 1 \
    --category R2 \
    --openai_api_key "sk-proj-..."

# Step 2만 실행 (영어, 5개 프롬프트)
python main.py \
    --step 2 \
    --category R5 \
    --lang en \
    --num_prompts 5 \
    --gemini_api_key "AIza..."
```

**평가 파이프라인**

```bash
# run/run_judge.sh 참고
# 사전에 대상 LLM의 응답이 포함된 CSV 파일 준비 필요
python src/eval/judge_finred.py \
    -i <입력 CSV 경로> \
    -o <출력 파일명(확장자 제외)> \
    -d <결과 저장 디렉토리>
```

주요 변경 인자:

| 파라미터 | 설명 |
|----------|------|
| `-i` | 입력 CSV 경로 (프롬프트 + 모델 응답 컬럼 포함) |
| `-o` | 출력 파일명 (확장자 제외, 예: `qwen2.5_7b_responses`) |
| `-d` | 결과 저장 디렉토리 (예: `./infer_result/`) |

```bash
# 평가 실행 예시
python src/eval/judge_finred.py \
    -i ./src/eval/dataset/qwen_2.5_7b_all_with_responses.csv \
    -o qwen2.5_7b_responses \
    -d ./src/eval/infer_result/
```

---

### 5. 이슈

- **관련 데이터 별도 다운로드 필요**: `src/data/` 하위 데이터는 Google Drive를 통해 별도로 다운로드해야 함  
  - 구글 드라이브: https://drive.google.com/drive/u/0/folders/1cfBf419OUDrQQMRKMPLLJqRX97WMxExC  
  - 노션 상세 가이드: https://www.notion.so/7-5-fine-grained-225f7db4228280aa8965c636f2ba4a91
- **전처리 환경 별도 설치**: PDF 청킹 등 전처리가 필요한 경우, `unstructured` 및 시스템 의존성 별도 설치 필요 (상세 내용: `src/preprocess/preprocess_README.md` 참고)
- **API 키 환경변수 설정**: `OPENAI_API_KEY`, `GEMINI_API_KEY`를 환경변수 또는 인자로 전달해야 함

---

### 6. Requirements

```
accelerate>=1.4.0
bitsandbytes>=0.45.5
peft>=0.15.2
sentence-transformers>=3.4.1
sentencepiece>=0.2.0
openai>=1.57.1
anthropic>=0.42.0
google-genai>=1.15.0
instructor>=1.0.0
chromadb>=0.4.0
pandas>=2.2.3
numpy>=1.26.0
openpyxl>=3.1.5
scikit-learn>=1.6.0
nltk>=3.9.1
matplotlib>=3.9.3
seaborn>=0.13.2
streamlit>=1.43.2
streamlit-autorefresh>=1.0.1
python-dotenv>=1.0.1
fire>=0.7.0
tqdm>=4.66.0
pydantic>=2.0.0
wandb>=0.19.8
vllm>=0.9.2
autoawq>=0.2.9
flashinfer-python==0.2.2
google-generativeai
```

---

## Harness Layer

This copied project includes an isolated harness layer for repeatable financial
red-team dataset engineering. The original FinRED scripts remain available; the
harness adds provider abstraction, fake-provider dry-runs, checkpointing,
structured logs, and runtime isolation.

Default harness runs do not call live APIs.

```powershell
python -m src.harness.cli doctor
python -m src.harness.cli validate-config -c configs\harness.sample.json
python -m src.harness.cli preflight -c configs\harness.sample.json
python -m src.harness.cli preflight -c configs\harness.sample.json --require-plan
python -m src.harness.cli run -c configs\harness.sample.json
python -m src.harness.cli status -c configs\harness.sample.json
python -m src.harness.cli cleanup-check -c configs\harness.sample.json
python -m unittest tests.test_harness
```

Sync markdown exec-plans into runtime lifecycle state:

```powershell
python -m src.harness.cli plan-sync --plan docs\exec-plans\tech-debt-tracker.md -c configs\harness.sample.json
```

Harness growth loop commands:

```powershell
python -m src.harness.cli analyze --result-dir src\eval\infer_result --output-dir .runtime\growth\analysis-r4
python -m src.harness.cli improve --analysis-dir .runtime\growth\analysis-r4 --output-dir .runtime\growth\analysis-r4\improvements
python -m src.harness.cli compare --baseline .runtime\growth\baseline --candidate .runtime\growth\candidate
```

Copy reviewed final artifacts out of temporary runtime state:

```powershell
python -m src.harness.cli export-accepted src\eval\infer_result\shinhan_r4_1_gemini_judge.csv
```

Overwrite protection:

```text
main.py refuses to write over existing Step1/Step2 outputs unless --overwrite is passed.
```

Runtime artifacts are written under:

```text
.runtime/<worktree_id>/
```

Generated smoke/test outputs are intentionally ignored by Git:

```text
tests/infer_result/
tests/outputs/
judge_errors/
```

Each run writes lifecycle state:

```text
state/run_request.json
state/execution_plan.json
state/todo.json
state/preflight.json
```

Harness reference documents:

```text
docs/TAXONOMY_R1_R5.md
docs/FOLDER_STRUCTURE_HARNESS.md
docs/QUALITY_SCORE.md
docs/JUDGE_AND_FEEDBACK_LOOP.md
docs/DATA_FLOW.md
docs/GLOBAL_RUN_LIFECYCLE.md
```

Live provider smoke tests require explicit opt-in:

```powershell
$env:RUN_LIVE_LLM_TESTS="true"
```

Live provider runs also require a prior successful fake dry-run marker:

```text
.runtime/<worktree_id>/state/fake_run_passed.json
```

Do not commit or store real API keys. Use `.env.example` only as a variable
name reference.

설치 방법:
```bash
# 가상환경 생성 (Python 3.10 권장)
conda create -n finred python=3.10 -y
conda activate finred

# 패키지 설치
pip install -r requirements.txt

# 전처리 필요 시 (선택사항)
pip install "unstructured[all-docs]"
sudo apt-get install -y libmagic-dev poppler-utils tesseract-ocr tesseract-ocr-kor libreoffice pandoc
```

---

### 7. 폴더 구조

```
FinRED/
├── main.py                          # 메인 실행 스크립트 (Step1/Step2 통합 실행)
├── requirements.txt                 # 패키지 의존성
├── Readme.md
│
├── run/                             # 실행 쉘 스크립트
│   ├── run_data_generate.sh         # 데이터 생성 파이프라인 실행
│   └── run_judge.sh                 # 평가 파이프라인 실행
│
├── prompts/                         # LLM 프롬프트 템플릿 (YAML)
│   ├── step1.yaml                   # Step1 시나리오 생성 프롬프트
│   ├── step2.yaml                   # Step2 시드 프롬프트 생성 (한국어)
│   ├── step2_eng.yaml               # Step2 시드 프롬프트 생성 (영어)
│   └── judge.yaml                   # 평가 프롬프트
│
├── src/
│   ├── Step1_build.py               # 시나리오 생성 모듈
│   ├── Step2_build.py               # 시드 프롬프트 생성 모듈
│   ├── __init__.py
│   │
│   ├── data/                        # ⚠️ 별도 다운로드 필요
│   │   ├── contexts/                # 컨텍스트 데이터
│   │   │   ├── R3_products/         # R3 금융상품 요약
│   │   │   └── retrieved_chunks/    # 유사도 검색 결과
│   │   ├── orig/                    # 원본 데이터
│   │   │   ├── db/                  # 청크 CSV DB
│   │   │   ├── parsed_docs/         # PDF + 청크 JSON
│   │   │   └── investinfo/          # R3 상품 텍스트
│   │   └── queries/                 # 쿼리 CSV
│   │
│   ├── schemas/                     # 출력 스키마 정의
│   │   ├── ko/                      # 한국어 스키마
│   │   └── en/                      # 영어 스키마
│   │
│   ├── outputs/                     # 생성 결과물
│   │   ├── scenarios/               # Step1 출력 (시나리오 JSON)
│   │   └── prompts/                 # Step2 출력 (프롬프트 JSON + CSV)
│   │
│   ├── preprocess/                  # 전처리 파이프라인
│   │   ├── preprocess_README.md     # 전처리 상세 가이드
│   │   ├── 1_chunking.py            # PDF 청킹
│   │   ├── 2_parsed_to_csv.py       # 파싱 결과 → CSV
│   │   ├── 3_common_to_csv.py       # 공통 데이터 → CSV
│   │   ├── 4_product_summarizer.py  # 금융상품 요약
│   │   ├── 5_summary_extractor.py   # 요약 추출
│   │   └── 6_chunk_retriever.py     # 청크 검색
│   │
│   └── eval/                        # 평가 모듈
│       ├── judge_finred.py          # LLM Judge 평가 스크립트
│       ├── dataset/                 # 평가용 입력 데이터 (모델 응답 CSV)
│       └── template/
│           └── rubric_financial.py  # 금융 루브릭 채점 템플릿
│
└── tests/                           # 테스트 코드 및 튜토리얼
    ├── judge.ipynb                  # 평가 실험 노트북
    ├── preprocess.ipynb             # 전처리 튜토리얼
    ├── step_1_tutorial.ipynb        # Step1 튜토리얼
    ├── step_2_tutorial.ipynb        # Step2 튜토리얼
    └── test_harness.py              # 하네스 단위 테스트
```
