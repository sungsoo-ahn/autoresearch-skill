# Autoresearch Repository

This repository is a task-neutral harness for autonomous ML research campaigns.
Task-specific behavior lives in task packs under `tasks/<slug>/` or reusable
examples under `examples/<slug>/`.

The harness provides:

- a git-DAG search memory under `agent/<task>/<run>/*`
- per-slot worktrees and isolated `uv` environments
- role prompts for `idea`, `draft`, `improve`, `debug`, `smoke`, and `analyze`
  when an adapter is included
- fixed task packs for data setup, scoring, contracts, novelty boundaries, and
  smoke checks
- campaign artifacts under `runs/<task>/<run>/<sha>/`

The original CSP/HACO material is preserved only as a runnable living example in
`examples/csp/` when included by the scaffolder.

## Repository layout

```
.
+-- contract.md                 generic harness and candidate contract
+-- program.md                  generic orchestrator loop
+-- prepare.py                  wrapper around a task pack's prepare.py
+-- evaluate.py                 wrapper around a task pack's evaluate.py
+-- requirements.txt            generic base dependencies
+-- scripts/                    bootstrap, launch, and slot lifecycle scripts
+-- toolkit/                    initializer interview and task templates
+-- examples/csp/               optional runnable CSP example task pack
+-- tasks/                      generated task packs for active campaigns
```

Runtime directories are ignored by git: `.omx/`, `data/`, `runs/`,
`.worktrees/`, `.slots/`, and virtual environments. Generated task packs under
`tasks/` should be reviewed and committed before bootstrap so campaign worktrees
can read them.

## Task packs

Each autoresearch task is represented by a task pack under `tasks/<slug>/` or
`examples/<slug>/`. A valid task pack contains:

- `task.json` - manifest for scripts
- `task.md` - problem statement and success criteria
- `contract.md` - task-specific rules for data, artifacts, and evaluation
- `methods.md` - prior methods and novelty boundary
- `prepare.py` - idempotent data/setup script
- `evaluate.py` - fixed evaluator
- `requirements.txt` - task dependencies
- `smoke.md` - task-specific smoke-test checklist

Use the initializer agent or the `$autoresearch` skill to interview you and
create a new pack under `tasks/<slug>/`.

## Optional adapters

The core repository is agent-agnostic. If scaffolded with
`--adapter claude`, the repo also includes `.claude/` prompts, settings, and
guard hooks for Claude Code.

## Candidate contract

Generated research nodes implement one root file in a slot worktree:
`candidate.py`.

Required CLI:

```
python candidate.py --run_name staging --max_minutes 120 --task_dir tasks/<slug> --data_dir data/<slug>
```

The candidate must write artifacts only under `runs/<run_name>/` and print:

```
primary_metric: <float>
```

The task manifest defines the metric display name and whether higher or lower is
better.

## Validate a task pack

```
scripts/validate_task.sh examples/csp
scripts/validate_task.sh tasks/<slug>
```

Before bootstrap, also run the task setup and score at least one cheap baseline
through the fixed evaluator. Record measured baseline scores in the task pack so
future `idea`, `draft`, `improve`, and `analyze` roles have a concrete starting
point.

## Launch a campaign

Scaffolded repositories are initialized on `agent/root`. Bootstrap requires a
clean working tree and `uv`. It auto-detects GPUs when available, but CPU-only
campaigns are supported.

```
scripts/bootstrap.sh task=<slug> run_tag=<run_tag>
```

Force CPU mode with one or more CPU slots:

```
scripts/bootstrap.sh task=<slug> run_tag=<run_tag> device=cpu n_slots=1
```

Force specific GPU ids when a task requires GPU execution:

```
scripts/bootstrap.sh task=<slug> run_tag=<run_tag> device=gpu gpus=0,1
```

The root template does not prescribe a specific ML stack. Put task-specific CPU
or GPU packages in the task pack's `requirements.txt`.

For an example task:

```
scripts/bootstrap.sh task=csp task_path=examples/csp run_tag=<run_tag>
```

Then start or resume the persistent Bash round loop:

```
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag>
```

By default the launcher uses local `codex exec`. Each round writes a fresh
campaign prompt, exports `AUTORESEARCH_ROUND`, runs one agent process, reconciles
slots, sleeps, and repeats until the user stops it or repeated command failures
hit `max_failures`. Use `max_rounds=1` for one bounded agent round:

```
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag> max_rounds=1
```

`max_turns=1` remains accepted as a compatibility alias.

Set `AUTORESEARCH_AGENT_CMD` or pass an explicit command after `--` to use a
different agent CLI that accepts prompts on standard input:

```
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag> -- <agent command...>
```

Use `agent=prompt` to print the persistent orchestration prompt without running
an agent.

## License

MIT. The CSP example retains attribution for code derived from OMatG in its
task-specific files.
