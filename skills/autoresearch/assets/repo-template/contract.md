# Generic autoresearch contract

This repository is an initialization toolkit for ML autoresearch campaigns. A
task pack supplies domain-specific data preparation, evaluation, constraints,
and smoke checks. The root harness supplies the repeatable search machinery:
git-DAG memory, per-slot worktrees, isolated virtual environments, background
runs, parsing, analysis, and finalization.

## Task packs

A task pack lives under `tasks/<slug>/` for a new active task, or
`examples/<slug>/` for a reusable example. It must contain:

| file | purpose |
|---|---|
| `task.json` | machine-readable manifest used by shell scripts |
| `task.md` | human-readable problem statement and success criteria |
| `contract.md` | task-specific data, artifact, budget, and safety rules |
| `methods.md` | prior methods and novelty boundary for `idea` |
| `prepare.py` | idempotent setup into `data/<slug>/` |
| `evaluate.py` | fixed scorer for task artifacts |
| `requirements.txt` | task-specific Python dependencies |
| `smoke.md` | task-specific smoke-test checklist |

The manifest must set `candidate_entry` to `candidate.py`, define a primary
metric name and direction, and provide default `max_minutes`, `smoke_seconds`,
and `noise_sigma`.

## Candidate contract

Every generated node implements one file at the worktree root:
`candidate.py`.

Required CLI:

```
python candidate.py \
  --run_name <str> \
  --max_minutes <float> \
  --task_dir <path> \
  --data_dir <path>
```

Required behavior:

- Train/search only within the task pack's allowed data and rules.
- Write artifacts only under `runs/<run_name>/` in the current worktree.
- Invoke the task pack's fixed evaluator, or compute the same fixed metric.
- Print this exact final line prefix once a score is known:
  ```
  primary_metric: <float>
  ```
- If evaluation times out or cannot produce a valid score, print
  `primary_metric: nan` and exit cleanly when possible.
- Do not install packages at runtime. `draft`, `improve`, and `debug` may extend
  the slot venv before writing `candidate.py`; that environment is frozen at
  finalize and inherited by children.
- Do not write checkpoints or auxiliary files outside `runs/<run_name>/`.

## Search protocol

- Editable by candidate-authoring agents: `candidate.py` only.
- Read-only during campaigns: root harness files, `scripts/`, `toolkit/`,
  adapter directories such as `.claude/` when present, task-pack copies inside
  `.worktrees/`, `examples/`, and `data/`. Root `tasks/` is writable only
  during task initialization.
- Operators do not run the full candidate directly. Full runs go through
  `scripts/slot_run.sh`; probes go through the `smoke` subagent.
- Each finalized node is a commit under `agent/<task_slug>/<run_tag>/*`.
- Commit subjects use `[primary_metric=X]` for valid scored nodes and `[BUGGY]`
  for smoke failures, crashes, timeouts, or invalid metrics.
- Commit bodies record `pair:`, optional `parent:`, `hypothesis:`, and
  `finding:`.

## Metrics

The harness parses only `primary_metric:` from candidate stdout. The task pack
defines what the metric means and whether it is maximized or minimized. Analysis
uses `noise_sigma` from the campaign config to classify small deltas as
inconclusive.
