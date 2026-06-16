# Harness Folder Structure

This document describes the current FinRED harness repository layout after the
cleanup of generated test artifacts and the addition of the growth loop.

## Top Level

```text
RED.FinRED-private-main-harness/
├─ AGENTS.md
├─ ARCHITECTURE.md
├─ Readme.md
├─ main.py
├─ requirements.txt
├─ .env.example
├─ configs/
├─ docs/
├─ prompts/
├─ run/
├─ src/
├─ tests/
└─ .runtime/                  # generated, ignored by Git
```

## Harness Layer

```text
src/harness/
├─ __init__.py
├─ checkpoint.py
├─ cli.py
├─ comparison.py
├─ config.py
├─ improvement.py
├─ improvement_validators.py
├─ ingest.py
├─ lifecycle.py
├─ local_retrieve.py
├─ models.py
├─ pdf_chunk.py
├─ pipeline.py
├─ preflight.py
├─ providers.py
├─ result_schema.py
├─ run_analyzer.py
├─ runtime.py
└─ validators.py
```

Purpose:

```text
Controlled harness execution, configuration validation, preflight checks,
provider abstraction, checkpointing, runtime isolation, failure analysis,
improvement candidate generation, review queueing, and run comparison.
```

Common commands:

```powershell
python -m src.harness.cli doctor
python -m src.harness.cli validate-config -c configs\harness.sample.json
python -m src.harness.cli preflight -c configs\harness.sample.json
python -m src.harness.cli run -c configs\harness.sample.json
python -m src.harness.cli analyze --result-dir src\eval\infer_result --output-dir .runtime\growth\analysis-r4
python -m src.harness.cli improve --analysis-dir .runtime\growth\analysis-r4 --output-dir .runtime\growth\analysis-r4\improvements
python -m src.harness.cli compare --baseline .runtime\growth\baseline --candidate .runtime\growth\candidate
```

## Runtime Outputs

Runtime outputs are generated under `.runtime/` and are ignored by Git.

```text
.runtime/<worktree_id>/
├─ artifacts/
├─ cache/
├─ checkpoints/
├─ logs/
├─ reports/
├─ state/
│  ├─ execution_plan.json
│  ├─ preflight.json
│  ├─ run_request.json
│  └─ todo.json
└─ tmp/

.runtime/growth/<analysis-run>/
├─ summary.json
├─ cases.jsonl
├─ failure_cases.jsonl
└─ improvements/
   ├─ improvement_candidates.jsonl
   └─ improvement_summary.json

.runtime/review_queue/
└─ improvement_queue.jsonl

.runtime/comparisons/<comparison-run>/
├─ comparison.json
└─ comparison.md
```

## Original FinRED Pipeline

```text
main.py
src/Step1_build.py
src/Step2_build.py
prompts/
├─ step1.yaml
├─ step2.yaml
├─ step2_eng.yaml
└─ judge.yaml
```

Purpose:

```text
Original Step1 scenario generation and Step2 attack prompt generation remain
available. API/model-specific scripts are intentionally kept separate because
their setup and default model choices are documented in the README and run
guides.
```

## Data And Generated Dataset Artifacts

```text
src/data/
├─ orig/
├─ contexts/
├─ queries/
└─ schemas/

src/outputs/
├─ scenarios/
└─ prompts/

src/eval/
├─ dataset/
├─ infer_result/
├─ template/
├─ generate_target_responses.py
├─ generate_target_responses_gemini.py
├─ judge_finred.py
└─ judge_finred_gemini.py
```

Canonical evaluation outputs:

```text
Prompt-response CSV files       -> src/eval/dataset/
Judge CSV/JSON and ASR outputs  -> src/eval/infer_result/
Judge error logs                -> judge_errors/ or src/eval/judge_errors/
```

`src/eval/infer_result/*.csv` is treated as the canonical tabular result for
analysis. Matching `.json` files are audit artifacts. The analyzer avoids
double-counting CSV/JSON pairs.

## Tests

```text
tests/
├─ test_harness.py
├─ judge.ipynb
├─ preprocess.ipynb
├─ step_1_tutorial.ipynb
└─ step_2_tutorial.ipynb
```

Generated test artifacts are intentionally ignored:

```text
tests/infer_result/
tests/outputs/
```

The unit tests create temporary fixtures at runtime, so committed generated
test outputs are not required.

## Git Ignore Policy

These paths should not be committed:

```text
.env
.runtime/
__pycache__/
*.pyc
*.pdf
judge_errors/
tests/infer_result/
tests/outputs/
```

Small source-derived CSV/JSON files needed for reproducibility may be committed
when they are intentionally curated. Raw documents and runtime outputs should
remain outside Git.
