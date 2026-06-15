# Global Run Lifecycle

Every harness operation follows the same lifecycle, regardless of whether the
stage is chunking, retrieval, scenario generation, prompt generation, prompt
strength judging, target response generation, or response judging.

## Lifecycle

```text
1. Request materials
2. Execution plan
3. To-do tracking
4. Preflight inspection
5. Stage execution
6. Stage verification
7. Checkpoint and logs
8. Final report
9. Limitations and next steps
```

## Required State Files

Each run writes state under:

```text
.runtime/<worktree_id>/state/
  run_request.json
  execution_plan.json
  todo.json
  preflight.json
```

## Preflight Gate

The first executable stage is always preflight. It checks the current code and
folder state before any generation or evaluation work begins.

Minimum checks:

- required files exist
- config is valid
- runtime path is isolated
- `.runtime/` is ignored
- live API provider is not enabled without explicit opt-in
- seed case IDs are unique
- seed case schemas are valid
- seed text does not contain obvious PII
- no unsupported provider type is configured
- repository/worktree metadata is recorded when present

Preflight findings use machine-readable reason codes.

## To-do Status Values

```text
pending
in_progress
completed
failed
skipped
quarantined
needs_review
```

## Standard Stages

```text
request_materials
plan
preflight
validate_inputs
execute
verify_outputs
checkpoint
report
```

Feature-specific stages can extend this list, for example:

```text
attack_prompt_strength_judge
combined_interpretation
safe_response_quality_judge
```

## User-Facing Rhythm

The user should be able to see:

```text
what materials were requested
what the harness plans to do
which tasks are pending/in progress/completed
what failed and why
what final outputs mean
what remains unresolved
```

