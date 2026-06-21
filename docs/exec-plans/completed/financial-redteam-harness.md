---
id: 9960a9c4-1142-487a-95cd-b28e574ac7a4
title: 'Execution Plan: Financial Red-Team Harness'
created: '2026-06-21T02:19:28.902Z'
updated: '2026-06-21T02:19:30.930Z'
tags: []
---
# Execution Plan: Financial Red-Team Harness

## Repository State

* Working source: copied project folder `RED.FinRED-private-main-harness`.
* Original folder: `RED.FinRED-private-main`.
* Git repository: not detected in either the parent folder or project folder.
* Git branch: unavailable.
* Git worktree: unavailable because no `.git` metadata exists.

## Worktree Decision

The user requested original preservation and branch/worktree isolation when new\
 construction is required. Because this folder is not a Git repository, a branch\
 or Git worktree cannot be created. The conservative substitute is a separate\
 filesystem copy:

```text
RED.FinRED-private-main-harness
```

All harness changes are made only in that copied folder.

## Scope

Phase 1 implements a minimal, runnable harness:

* repository guide and architecture docs
* provider contract
* deterministic fake provider
* OpenAI/Gemini adapter shells with live opt-in
* config loader
* typed case schema
* generator/reviewer orchestration
* schema, duplicate, and PII checks
* JSONL checkpoint
* structured JSON logging
* runtime path isolation
* CLI commands
* fake provider dry-run tests

## Out Of Scope For Phase 1

* rewriting existing FinRED Step1/Step2 internals
* live API execution by default
* production data migration
* Docker/Compose isolation
* semantic duplicate detection
* full CI integration

## Verification

Run:

```powershell
python -m src.harness.cli doctor
python -m src.harness.cli validate-config -c configs/harness.sample.json
python -m src.harness.cli run -c configs/harness.sample.json
python -m unittest tests.test_harness
```

## Results

Implemented in the isolated filesystem copy:

```text
RED.FinRED-private-main-harness
```

Added:

* `AGENTS.md`
* `ARCHITECTURE.md`
* `docs/QUALITY_SCORE.md`
* `docs/exec-plans/tech-debt-tracker.md`
* `configs/harness.sample.json`
* `.env.example`
* `src/harness/*`
* `tests/test_harness.py`

Verified:

```powershell
python -m src.harness.cli doctor
python -m src.harness.cli validate-config -c configs\harness.sample.json
python -m src.harness.cli run -c configs\harness.sample.json
python -m unittest tests.test_harness
```

Observed dry-run:

```text
records: 2
statuses: approved, approved
provider: fake
live API calls: none
```

Runtime outputs were written under:

```text
.runtime/finred-harness-local/
```

`.runtime/` is ignored by `.gitignore`.

## Decision Log

* No Git worktree was created because this project copy has no `.git` metadata.
* Runtime state is isolated under `.runtime/<worktree_id>/`.
* Fake provider is the only default execution provider.
* Live provider smoke tests require `RUN_LIVE_LLM_TESTS=true`.
* Original folder `RED.FinRED-private-main` was not modified.
