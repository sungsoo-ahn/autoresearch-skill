# Initialize Repo Workflow

Use this when the user wants a new autoresearch repository or wants to convert
an existing repo into the generated autoresearch harness.

## Interview Checklist

Lock these before writing files:

- task slug and short name
- research objective and target audience
- data source, setup steps, split policy, licenses, and secrets policy
- primary metric, direction, expected range, noise estimate, and timeout
- fixed evaluator behavior and invalid-output policy
- candidate artifacts and allowed output paths
- compute assumptions: CPU/GPU, memory, wall-clock budget, package policy, and
  whether GPU is required or merely preferred
- what candidates may read during training, validation, and test
- off-limits files, public APIs, and compatibility constraints
- prior methods and novelty boundary
- smoke checks that catch broken candidates cheaply

If the user is unsure, choose conservative defaults and record assumptions in
the task pack. Do not leave `TODO` or `TBD`.

## Scaffold

Use the bundled template. By default it initializes git on `agent/root` and
creates an initial commit:

```bash
python skills/autoresearch/scripts/scaffold_repo.py \
  --target <target_dir> \
  --name "<project_name>" \
  [--adapter claude] \
  [--include-csp-example]
```

If the skill is installed outside this repo, replace `skills/autoresearch` with
the actual skill path.

Use `--adapter claude` only when the user wants Claude Code prompts/settings in
the generated repo. Omit it for an agent-agnostic repo. Use
`--include-csp-example` only when the user wants a runnable example task pack.

## Generate First Task Pack

Create `tasks/<slug>/` with:

- `task.json`
- `task.md`
- `contract.md`
- `methods.md`
- `prepare.py`
- `evaluate.py`
- `requirements.txt`
- `smoke.md`

Read `task-pack.md` before writing these files. After writing, run:

```bash
scripts/validate_task.sh tasks/<slug>
```

## Bootstrap Instructions To Return

If `scaffold_repo.py` handled git initialization, the target repo is already on
`agent/root`. Tell the user to commit the generated task pack before bootstrap,
then run:

```bash
scripts/bootstrap.sh task=<slug> run_tag=<run_tag>
```

For CPU-only campaigns:

```bash
scripts/bootstrap.sh task=<slug> run_tag=<run_tag> device=cpu n_slots=1
```

For GPU-required tasks:

```bash
scripts/bootstrap.sh task=<slug> run_tag=<run_tag> device=gpu gpus=0
```

For a bundled example:

```bash
scripts/bootstrap.sh task=csp task_path=examples/csp run_tag=<run_tag>
```

After bootstrap, tell the user to launch or resume the campaign with:

```bash
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag>
```

This prints a persistent orchestration prompt when no agent command is supplied.
It can also repeatedly invoke an agent CLI:

```bash
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag> -- <agent command...>
```
