# Smoke checklist

Define cheap probes that catch broken candidates before a full run.

Recommended checks:

1. Import `candidate.py`.
2. Load a tiny amount of training data.
3. Run one minimal training/update step.
4. Produce one small artifact under `runs/staging-smoke/`.
5. Run the task evaluator or a lightweight parser on that artifact.
6. Check memory use against `vram_total_mb` for GPU runs or available system
   memory for CPU runs.

The `smoke` subagent must write diagnostics to:

```
runs/staging-smoke/smoke.log
```
