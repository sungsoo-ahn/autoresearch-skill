# <Task name> contract

## Data rules

- Define exactly which files candidates may read during training.
- Define exactly which validation/test fields candidates may read, and when.
- State any forbidden leakage or external data rules.

## Candidate output

Candidates must write artifacts only under:

```
runs/<run_name>/
```

Candidates must print:

```
primary_metric: <float>
```

## Evaluation

Define the fixed evaluator command and invalid-output behavior.

## Constraints

- Resource limits.
- Runtime package policy.
- Checkpoint/output policy.
- Any domain-specific validity rules.
