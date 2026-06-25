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
The scaffolder treats an existing target containing only runtime metadata
(`.omx/` or `.DS_Store`) as safe and preserves those entries. Any other
pre-existing entry still blocks scaffolding unless `--force` is used.

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

Then run the task-specific setup and evaluator smoke path. At minimum:

```bash
python prepare.py --task_dir tasks/<slug> --out_dir data/<slug>
python tasks/<slug>/evaluate.py --run_dir runs/<baseline> --data_dir data/<slug>
```

The baseline artifact may be mean, constant, random, or another cheap
task-appropriate predictor. Record measured baseline scores in `task.md` or
`methods.md`; do not leave guessed ranges as the only evidence.

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

After bootstrap, tell the user to launch or resume the campaign with the
generated persistent Bash round loop:

```bash
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag>
```

Initialization must specify that this command owns autonomous execution. The
launcher writes a fresh prompt for each round, exports `AUTORESEARCH_ROUND`,
`AUTORESEARCH_TASK`, and `AUTORESEARCH_RUN_TAG`, runs one agent process with the
prompt on stdin, reconciles slots, sleeps, and repeats until the user stops it,
`max_rounds` is reached, or repeated command failures hit `max_failures`.
`max_turns` is still accepted as a compatibility alias. Use `max_rounds=1` for
one bounded agent round:

```bash
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag> max_rounds=1
```

It can also repeatedly invoke an explicit agent CLI:

```bash
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag> -- <agent command...>
```

Use `agent=prompt` to print the persistent orchestration prompt without running
an agent.

## Logging And Report

Tell the user that campaign scripts automatically append structured events to:

```bash
runs/<slug>/<run_tag>/campaign_events.jsonl
```

They also refresh this self-contained HTML report:

```bash
runs/<slug>/<run_tag>/report.html
```

The report shows clickable idea nodes, green rings for nodes that raise the
campaign-best metric, green parent-inspiration curves, and the campaign-best
metric curve over wall-clock time. Rebuild it manually with:

```bash
python3 scripts/campaign_log.py render --task <slug> --run-tag <run_tag>
```

Add a manual note event when useful:

```bash
python3 scripts/campaign_log.py log --task <slug> --run-tag <run_tag> \
  --event note --message "<human-readable note>"
```
