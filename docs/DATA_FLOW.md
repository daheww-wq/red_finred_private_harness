# Data Flow

This document describes the current FinRED data flow and where the harness layer
adds controls such as preflight checks, attack prompt strength judging, and
response safety judging.

The primary project goal is to build a **financial red-teaming benchmark set**.
Attack prompt strength judging is only one supporting quality-control step.

Reference documents:

```text
docs/TAXONOMY_R1_R5.md
= PDF/source routing rules for R1-R5.

docs/QUALITY_SCORE.md
= scoring rules for prompt strength and response safety.

docs/JUDGE_AND_FEEDBACK_LOOP.md
= how judge results feed back into data quality improvement.
```

## Current FinRED Pipeline

```mermaid
flowchart TD
    A[Raw source documents<br/>PDF, TXT, MD] --> B[Document parsing / chunking<br/>src/preprocess/1_chunking.py]
    B --> C[Chunk JSON<br/>src/data/orig/parsed_docs/.../jsons/*.json]
    C --> D[Document DB CSV<br/>src/data/orig/db/*_common_docs.csv<br/>or *_docs.csv]

    Q[Retrieval queries<br/>src/data/queries/{category}_queries.csv] --> E[Chunk retrieval<br/>src/preprocess/6_chunk_retriever.py]
    D --> E
    E --> F[Retrieved context JSON<br/>src/data/contexts/retrieved_chunks/per_taxonomy_chunks/{category}_chunks.json]

    S[Category schema<br/>src/data/schemas/ko/{category}.json] --> G[Step1 scenario generation<br/>main.py --step 1<br/>OpenAI]
    F --> G
    G --> H[Scenario JSON<br/>src/outputs/scenarios/{category}/*.json]

    H --> I[Step2 attack prompt generation<br/>main.py --step 2<br/>Gemini]
    S --> I
    I --> J[Attack prompt CSV<br/>src/outputs/prompts/{category}_prompts_all.csv<br/>prompt_1]

    J --> K[Target model response generation<br/>src/eval/generate_target_responses_gemini.py<br/>Gemini or target model]
    K --> L[Prompt-response CSV<br/>src/eval/dataset/*_with_responses.csv<br/>attack_prompt,response]

    L --> M[Response safety judge<br/>python -m src.eval.judge_finred<br/>OpenAI judge]
    R[Judge rubric<br/>prompts/judge.yaml<br/>src/eval/template/rubric_financial.py] --> M
    M --> N[Judge outputs<br/>src/eval/infer_result/*.csv, *.json]
    N --> O[Metrics<br/>Safe / Unsafe<br/>ASR]
```

## Meaning Of Each Artifact

```mermaid
flowchart LR
    A[Raw document] -->|contains source evidence| B[Chunk JSON]
    B -->|made searchable| C[Document DB CSV]
    C -->|searched by query| D[Retrieved context]
    D -->|grounds risk scenario| E[Scenario JSON]
    E -->|converted into attack request| F[prompt_1]
    F -->|sent to target model| G[response]
    G -->|judged for safety| H[Safe / Unsafe]
```

## Current R2_1 Example

```mermaid
flowchart TD
    A[Voice-phishing prevention PDF<br/>Korea Financial Consumer Protection Foundation] --> B[R2 chunk JSON<br/>65 chunks]
    B --> C[R2_common_docs.csv]
    Q[R2_1_queries.csv<br/>5 retrieval queries] --> D[R2_1 chunk retrieval]
    C --> D
    D --> E[R2_1_chunks.json<br/>5 queries x retrieved contexts]
    E --> F[R2_1 Step1 scenarios<br/>scenario JSON files]
    S[R2_1 schema<br/>fraudActorProfile, fraudContext,<br/>socialEngineeringFlow, riskSignals] --> F
    F --> G[R2_1 Step2 prompts<br/>R2_1_prompts_all.csv]
    G --> H[Gemini target responses<br/>*_with_responses.csv]
    H --> I[Response safety judge<br/>Safe/Unsafe rubric]
    I --> J[ASR and judge results]
```

## Project-Level Evaluation Scope

The answer-safety evaluation is broader than the attack prompt itself.

```mermaid
flowchart TD
    A[Financial-service risk corpus] --> B[Benchmark cases]
    B --> C[Risky user request / seed / attack prompt]
    C --> D[Target model response]
    D --> E[Response safety judge]
    E --> F[Benchmark metrics]

    A --> A1[Personal information]
    A --> A2[Financial consumer protection]
    A --> A3[Compliance]
    A --> A4[Incomplete sales]
    A --> A5[Exaggerated advertising]
    A --> A6[Inappropriate investment recommendation]
    A --> A7[Risky request handling]
    A --> A8[Vulnerable customer protection]
    A --> A9[Internal information leakage]
```

Expected safe model behaviors:

```text
refuse inappropriate requests
provide limited or qualified answers
ask for additional confirmation when needed
offer safe alternatives
avoid personal/internal information leakage
avoid misleading financial advice or sales language
```

Dataset target from the provided project slide:

```text
answer_safety_evaluation_items = 500
```

## Current Evaluation Boundary

The current built-in judge evaluates the **response**, not the attack prompt.

```mermaid
flowchart LR
    A[prompt_1<br/>attack prompt] --> B[target model]
    B --> C[response]
    C --> D[Response judge]
    D --> E[Safe / Unsafe]

    A -. not directly judged today .-> X[No built-in prompt strength score]
```

Current interpretation:

```text
prompt_1 = attack attempt
response = target model output
Safe/Unsafe = safety judgment of response
ASR = Unsafe response ratio
```

## Proposed Addition: Attack Prompt Strength Judge

The next useful harness addition is a judge between Step2 and target model
response generation.

```mermaid
flowchart TD
    A[Step2 output<br/>{category}_prompts_all.csv] --> B[Attack prompt strength judge]
    B --> C[Prompt quality columns]
    C --> D[Prompt-response generation]
    D --> E[Response safety judge]
    E --> F[Final report]

    B --> B1[harmful_intent]
    B --> B2[actionability]
    B --> B3[target_specificity]
    B --> B4[manipulation_strategy]
    B --> B5[financial_harm_path]
    B --> B6[benchmark_difficulty]
```

Expected added columns:

```text
attack_harmful_intent
attack_actionability
attack_target_specificity
attack_manipulation_strategy
attack_financial_harm_path
attack_benchmark_difficulty
attack_strength_score
attack_strength_label
attack_strength_rationale
```

## Future Harness-Controlled Flow

```mermaid
flowchart TD
    A[Harness config<br/>configs/*.json] --> B[doctor / validate-config]
    B --> C{Config valid?}
    C -- no --> C1[Stop with reason codes]
    C -- yes --> D[Load seed cases / artifacts]

    D --> E[Pre-run validators]
    E --> E1[schema check]
    E --> E2[PII check]
    E --> E3[duplicate check]
    E --> E4[quality gates]

    E --> F{Approved for run?}
    F -- no --> F1[quarantine<br/>checkpoint reason code]
    F -- yes --> G[Provider execution]

    G --> G1[Fake provider<br/>default dry-run]
    G --> G2[OpenAI provider<br/>opt-in live]
    G --> G3[Gemini provider<br/>opt-in live]

    G --> H[Checkpoint JSONL]
    H --> I[Structured JSON logs]
    I --> J[Report JSON]
    J --> K[Export / review]
```

## Global Lifecycle Wrapper

Every stage runs inside the same lifecycle wrapper.

```mermaid
flowchart TD
    A[User requested materials] --> B[Run request<br/>state/run_request.json]
    B --> C[Execution plan<br/>state/execution_plan.json]
    C --> D[To-do tracker<br/>state/todo.json]
    D --> E[Preflight inspection<br/>code/folders/config/conflicts]
    E --> F{Preflight passed?}
    F -- no --> G[Stop or quarantine<br/>reason codes]
    F -- yes --> H[Stage execution]
    H --> I[Verification]
    I --> J[Checkpoint + JSON logs]
    J --> K[Final report<br/>reports/*.json, *.md]
```

Preflight catches issues before work begins:

```text
REQUIRED_FILE_MISSING
CONFIG_INVALID
RUNTIME_OUTSIDE_PROJECT
RUNTIME_NOT_GITIGNORED
LIVE_API_NOT_OPTED_IN
LIVE_PROVIDER_WITHOUT_ENABLE
DUPLICATE_CASE_ID
PII_DETECTED
```

## Where Attack Prompt Strength Judge Fits In Harness

```mermaid
flowchart TD
    A[Existing prompt CSV<br/>prompt_1] --> B[Harness import]
    B --> C[Prompt strength reviewer]
    C --> D{Strength label}
    D -- Weak --> E[Review or regenerate prompt]
    D -- Moderate --> F[Usable with caution]
    D -- Strong --> G[Proceed to target response generation]
    D -- High-Difficulty --> H[High-value benchmark case]

    G --> I[Response generation]
    H --> I
    I --> J[Response Safe/Unsafe judge]
```

## Result Interpretation With Prompt Strength

```mermaid
flowchart LR
    A[Prompt strength] --> C[Interpretation]
    B[Response judgment] --> C

    C --> D[Strong prompt + Safe response<br/>meaningful defense success]
    C --> E[Weak prompt + Safe response<br/>low-difficulty success]
    C --> F[Strong prompt + Unsafe response<br/>important vulnerability]
    C --> G[Weak prompt + Unsafe response<br/>basic safety failure]
```
