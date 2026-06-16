# Active Exec Plans

Put in-progress execution plans in this folder.

Sync a plan into runtime lifecycle state before or during substantial work:

```powershell
python -m src.harness.cli plan-sync --plan docs\exec-plans\active\<plan>.md -c configs\harness.sample.json
```

Completed plans can be moved to `docs/exec-plans/completed/`.
