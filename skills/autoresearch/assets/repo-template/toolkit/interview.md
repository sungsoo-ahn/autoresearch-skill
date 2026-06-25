# Task initialization interview

Use this workflow when creating a new task pack under `tasks/<slug>/`.

## Interview goals

Gather enough information that future `idea`, `draft`, `improve`, `debug`,
`smoke`, and `analyze` agents can run without making domain decisions.

You must lock:

- task slug, short name, and objective
- exact train/validation/test or benchmark split policy
- data source, download/setup steps, licenses, and secrets policy
- primary metric, metric direction, noise estimate, and tie handling
- fixed evaluator behavior and timeout expectations
- candidate artifacts and allowed output paths
- required candidate CLI behavior beyond the root contract, if any
- resource constraints: CPU/GPU assumptions, memory, wall-clock budget,
  package policy, and whether GPU is required or merely preferred
- what data candidates may read during training and evaluation
- prior methods, measured baselines, and novelty boundaries for `idea`
- smoke checks that cheaply catch broken candidates
- known failure modes and invalid-output handling

## Output

Create a complete task pack in `tasks/<slug>/` using the files in
`toolkit/task_pack_template/` as shape references. Then run:

```
scripts/validate_task.sh tasks/<slug>
```

Also run the task's preparation path and score at least one cheap baseline
through the fixed evaluator before calling the pack ready. Record the measured
primary metric and command in `task.md` or `methods.md`.

Do not leave placeholders like `TBD` or `TODO` in the generated task pack.
If a fact is genuinely unknown, record a concrete conservative assumption in
`task.md` and `contract.md`.
