# Harness Folder Structure

This document describes the recommended folder structure for the harness version
of the FinRED project.

The original project files remain in their existing locations. The harness adds
an operating layer for controlled runs, lifecycle state, validation, judging, and
feedback-driven dataset improvement.

## Top-Level Structure

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
└─ .runtime/
```

## Harness-Specific Folders

```text
configs/
└─ harness.sample.json
```

Purpose:

```text
Harness run configuration.
Controls run name, worktree/runtime identity, providers, max cases, and seed cases.
```

```text
src/harness/
├─ __init__.py
├─ checkpoint.py
├─ cli.py
├─ config.py
├─ lifecycle.py
├─ models.py
├─ pipeline.py
├─ preflight.py
├─ providers.py
├─ runtime.py
└─ validators.py
```

Purpose:

```text
Harness execution layer.
Adds config validation, preflight checks, lifecycle tracking, fake/live provider
abstraction, checkpoints, runtime logs, reports, and validation gates.
```

```text
docs/
├─ DATA_FLOW.md
├─ FOLDER_STRUCTURE_HARNESS.md
├─ GLOBAL_RUN_LIFECYCLE.md
├─ JUDGE_AND_FEEDBACK_LOOP.md
├─ QUALITY_SCORE.md
├─ TAXONOMY_R1_R5.md
├─ exec-plans/
│  ├─ completed/
│  │  └─ financial-redteam-harness.md
│  └─ tech-debt-tracker.md
└─ ...
```

Purpose:

```text
Operating rules and documentation for the harness version.
This is where routing, judge criteria, lifecycle, data flow, and execution plans live.
```

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
```

Purpose:

```text
Generated runtime state.
This folder should stay ignored by Git and should not be treated as source data.
```

## Original FinRED Pipeline Folders

These folders keep their original pipeline responsibilities.

```text
prompts/
├─ step1.yaml
├─ step2.yaml
├─ step2_eng.yaml
└─ judge.yaml
```

Purpose:

```text
LLM prompt templates for scenario generation, attack prompt generation, and judging.
```

```text
src/preprocess/
├─ 1_chunking.py
├─ 2_parsed_to_csv.py
├─ 3_common_to_csv.py
├─ 4_product_summarizer.py
├─ 5_summary_extractor.py
├─ 6_chunk_retriever.py
└─ preprocess_README.md
```

Purpose:

```text
Document parsing, chunking, CSV conversion, product summary extraction, and
retrieval-context construction.
```

```text
src/data/
├─ orig/
│  ├─ parsed_docs/
│  ├─ db/
│  └─ investinfo/
├─ contexts/
│  ├─ R3_products/
│  └─ retrieved_chunks/
├─ queries/
└─ schemas/
   ├─ ko/
   └─ en/
```

Purpose:

```text
Input data, parsed/chunked source documents, document DB CSVs, retrieval queries,
retrieved contexts, and category schemas.
```

```text
src/outputs/
├─ scenarios/
└─ prompts/
```

Purpose:

```text
Generated Step1 scenario JSON files and Step2 attack prompt JSON/CSV files.
```

```text
src/eval/
├─ dataset/
├─ infer_result/
├─ judge_errors/
├─ template/
│  └─ rubric_financial.py
├─ generate_target_responses_gemini.py
└─ judge_finred.py
```

Purpose:

```text
Target model response generation, response safety judging, judge outputs, errors,
and evaluation datasets.
```

```text
tests/
├─ test_harness.py
├─ outputs/
└─ infer_result/
```

Purpose:

```text
Harness tests and existing test/evaluation artifacts.
```

## Recommended PDF Intake Structure

For new PDF work, use this structure under `src/data/orig/` so raw sources,
parsed artifacts, and routing decisions do not get mixed.

```text
src/data/orig/
├─ incoming_pdfs/
│  ├─ unclassified/
│  ├─ R1/
│  ├─ R2/
│  ├─ R3/
│  ├─ R4/
│  └─ R5/
├─ routing/
│  ├─ pdf_routing_records.jsonl
│  └─ review_queue.jsonl
├─ parsed_docs/
│  └─ <source_or_category>/
│     └─ jsons/
└─ db/
   └─ *_common_docs.csv
```

Folder rules:

```text
incoming_pdfs/unclassified/
= New PDFs before classification.

incoming_pdfs/R1-R5/
= Raw PDFs after routing review. Keep the original files unchanged.

routing/pdf_routing_records.jsonl
= One JSON record per PDF using docs/TAXONOMY_R1_R5.md.

routing/review_queue.jsonl
= Ambiguous or low-quality routing decisions requiring review.

parsed_docs/
= Parser/chunker output. Do not manually edit unless repairing extraction issues.

db/
= Searchable document DB CSVs produced from parsed/chunked data.
```

## Recommended Benchmark Artifact Flow

```text
1. Put raw PDF in:
   src/data/orig/incoming_pdfs/unclassified/

2. Classify it with:
   docs/TAXONOMY_R1_R5.md

3. Move or copy the raw PDF to:
   src/data/orig/incoming_pdfs/R1/
   src/data/orig/incoming_pdfs/R2/
   src/data/orig/incoming_pdfs/R3/
   src/data/orig/incoming_pdfs/R4/
   src/data/orig/incoming_pdfs/R5/

4. Record routing decision in:
   src/data/orig/routing/pdf_routing_records.jsonl

5. Parse/chunk into:
   src/data/orig/parsed_docs/

6. Convert to searchable CSV:
   src/data/orig/db/

7. Create or update retrieval queries:
   src/data/queries/

8. Retrieve contexts into:
   src/data/contexts/retrieved_chunks/per_taxonomy_chunks/

9. Generate Step1 scenarios into:
   src/outputs/scenarios/<category>/

10. Generate Step2 attack prompts into:
    src/outputs/prompts/

11. Generate target model responses into:
    src/eval/dataset/

12. Run response judge into:
    src/eval/infer_result/

13. Run harness lifecycle/checks into:
    .runtime/<worktree_id>/
```

## What Belongs Where

```text
Raw PDFs
= src/data/orig/incoming_pdfs/

Routing decisions
= src/data/orig/routing/

Parsed/chunk JSON
= src/data/orig/parsed_docs/

Searchable document CSV
= src/data/orig/db/

Retrieval query CSV
= src/data/queries/

Retrieved chunk context JSON
= src/data/contexts/retrieved_chunks/

Step1 scenario JSON
= src/outputs/scenarios/

Step2 attack prompt JSON/CSV
= src/outputs/prompts/

Prompt-response CSV
= src/eval/dataset/

Judge result CSV/JSON
= src/eval/infer_result/

Judge errors
= src/eval/judge_errors/

Harness logs/checkpoints/reports/state
= .runtime/<worktree_id>/
```

## Do Not Mix

```text
Do not put raw PDFs directly in src/outputs/.
Do not put generated prompts in src/data/orig/.
Do not put API keys in configs/, docs/, or runtime reports.
Do not treat .runtime/ as source-of-truth data.
Do not overwrite original FinRED files when adding harness-specific behavior.
```

