---
id: 07dcb802-ce2a-437b-b34f-68c883701b31
title: Untitled
created: '2026-06-17T13:42:00.892Z'
updated: '2026-06-18T15:00:24.079Z'
tags: []
---
# Harness Architecture

## Purpose

The harness layer provides a reproducible environment for generating and\
 reviewing financial red-team benchmark data with OpenAI, Gemini, or deterministic\
 fake providers.

It is intentionally separate from the existing `Step1_build.py`,\
 `Step2_build.py`, and `src/eval/judge_finred.py` scripts. The harness can wrap\
 those flows later, but its first responsibility is operational safety:

* provider abstraction
* deterministic dry-runs
* schema validation
* duplicate checks
* PII checks
* secret pattern scanning
* command-like dataset payload detection
* checkpoint/resume
* structured logging
* runtime isolation
* accepted export separation

## Main Components

```text
src/harness/
  cli.py              command entry point
  config.py           config loader and validation
  models.py           typed case and result objects
  providers.py        fake/openai/gemini provider contract
  validators.py       schema, PII, duplicate, quality gates
  secret_scan.py      repository secret-pattern scanning
  cleanup.py          runtime/workspace cleanup summary
  exports.py          accepted artifact export helper
  overwrite_guard.py  output overwrite guard
  plan_sync.py        markdown exec-plan to runtime lifecycle sync
  checkpoint.py       JSONL checkpoint store
  runtime.py          worktree_id, run_id, paths, JSON logs
  pipeline.py         minimal generator/reviewer orchestration
```

## Runtime Layout

All transient execution state is stored below:

```text
.runtime/<worktree_id>/
  artifacts/
  checkpoints/
  logs/
  reports/
  tmp/
  cache/
  state/
```

Each run records lifecycle state:

```text
state/run_request.json
state/execution_plan.json
state/todo.json
state/preflight.json
state/fake_run_passed.json
```

The first executable gate is always preflight. It inspects code, folders,\
 configuration, runtime isolation, seed case conflicts, PII, secret patterns,\
 optional active exec-plan presence, fake dry-run state, and live API opt-in\
 before execution continues.

## Provider Contract

Each provider exposes:

```text
complete(request) -> ProviderResponse
```

The pipeline distinguishes provider roles:

* `generator`
* `reviewer`

The same provider may be used for both roles only when explicitly configured.

## Default Safety Posture

* Default provider: `fake`
* Default live API execution: disabled
* Default live API gate: a successful fake dry-run marker is required before

live OpenAI/Gemini provider execution.

* Default prompt/response logging: summaries only
* Default output state: generated, reviewed, approved, rejected, or quarantined
* Default run lifecycle: request materials, plan, preflight, execute, verify,

checkpoint, report

* Accepted exports are copied under `exports/accepted/`; temporary run state

remains under `.runtime/`.

## Existing FinRED Relationship

The original FinRED pipeline remains available:

```text
PDF -> chunks -> retrieved contexts -> Step1 scenarios -> Step2 prompts
    -> target responses -> judge
```

The harness adds operational controls around future generation and evaluation\
 runs. It does not replace the existing scripts in this first phase.
