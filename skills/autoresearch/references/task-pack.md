# Task Pack Reference

A task pack is the task-specific contract for a generated autoresearch repo.
It must be precise enough that future agents can run without inventing domain
policy.

## Required Files

- `task.json`: machine-readable manifest for scripts.
- `task.md`: objective, data, metric, artifacts, success criteria, assumptions.
- `contract.md`: hard rules for data access, outputs, evaluation, resources.
- `methods.md`: prior methods, baselines, and novelty boundary.
- `prepare.py`: idempotent setup into `data/<slug>/`.
- `evaluate.py`: fixed evaluator for candidate artifacts.
- `requirements.txt`: task-specific dependencies, including CPU/GPU ML stack
  choices when needed.
- `smoke.md`: cheap pre-run checks.

## Manifest Shape

```json
{
  "slug": "task_slug",
  "name": "Task name",
  "candidate_entry": "candidate.py",
  "metric": {
    "name": "Primary metric",
    "direction": "maximize"
  },
  "defaults": {
    "max_minutes": 120,
    "smoke_seconds": 120,
    "noise_sigma": 0.0
  },
  "artifacts": {
    "data_dir": "data/<slug>",
    "run_subdir": "runs/<run_name>"
  }
}
```

`metric.direction` is `maximize` or `minimize`. `candidate_entry` is always
`candidate.py`.

## Candidate Contract

Every generated candidate must accept:

```bash
python candidate.py \
  --run_name <name> \
  --max_minutes <float> \
  --task_dir <path> \
  --data_dir <path>
```

It must write artifacts only under `runs/<run_name>/` and print:

```text
primary_metric: <float>
```

Use `primary_metric: nan` for invalid or timed-out evaluations when the
candidate can exit cleanly.

## Baseline Evidence

Before a task pack is considered ready for bootstrap, prepare the data and score
at least one cheap valid baseline through the fixed evaluator. Prefer measuring:

- a trivial baseline such as mean, constant, majority-class, or random policy;
- one simple domain baseline if it is cheap and dependency-light;
- the expected invalid-output behavior when practical.

Record the command and measured primary metric in `task.md` or `methods.md`.
If a baseline is impossible to run during initialization, state the concrete
reason and the conservative assumption that replaces it.

## Validation Rules

Run the generated repo validator:

```bash
scripts/validate_task.sh tasks/<slug>
```

Reject task packs with placeholders, missing files, invalid JSON, no metric
direction, or a candidate entry other than `candidate.py`.
