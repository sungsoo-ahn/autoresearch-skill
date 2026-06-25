# Autoresearch Skill

This repository packages a reusable `autoresearch` skill. Install or register
the skill, then use it to scaffold a fresh task-focused autoresearch repository.
The scaffolded repository includes the experiment harness, task-pack templates,
optional adapters, optional CSP example, and git setup.

The repository root is only the skill distribution source. The generated
autoresearch repository template lives inside:

```
skills/autoresearch/assets/repo-template/
```

There is intentionally no sync workflow. Edit the skill and its bundled template
directly so the installed skill is the single source of truth.

## Layout

```
.
+-- skills/autoresearch/SKILL.md
+-- skills/autoresearch/agents/openai.yaml
+-- skills/autoresearch/references/
+-- skills/autoresearch/scripts/
+-- skills/autoresearch/assets/repo-template/
+-- README.md
+-- LICENSE
```

## Install Locally

For development, symlink the skill into your Codex skills directory:

```
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s "$(pwd)/skills/autoresearch" "${CODEX_HOME:-$HOME/.codex}/skills/autoresearch"
```

For a copied install instead:

```
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R skills/autoresearch "${CODEX_HOME:-$HOME/.codex}/skills/autoresearch"
```

After registration, invoke the skill in Codex with `$autoresearch` or by asking
to initialize/scaffold an autoresearch repository.

## Scaffold A Repo

The skill bundles a direct scaffold helper:

```
python skills/autoresearch/scripts/scaffold_repo.py \
  --target /path/to/new-repo \
  --name "Project Name" \
  --adapter claude \
  --include-csp-example
```

By default the scaffold helper initializes git in the target repo on
`agent/root` and creates an initial commit. That matches the campaign bootstrap
precondition in the generated repository.

Omit `--adapter claude` for an agent-agnostic repo. Omit
`--include-csp-example` for a blank starter repo. Use `--no-git` only if
another system will initialize the repository.

If the target already contains only `.omx/` or `.DS_Store`, the scaffolder
preserves those entries and proceeds. Other non-empty targets still require
`--force`.

## Generated Repo Flow

Inside the generated repository:

```
scripts/validate_task.sh examples/csp
scripts/bootstrap.sh task=csp task_path=examples/csp run_tag=<run_tag>
scripts/autoresearch_launch.sh task=csp run_tag=<run_tag>
```

The generated repo is compute-neutral by default. Use `device=cpu n_slots=1`
for CPU-only campaigns, or `device=gpu gpus=0,1` when a task requires specific
GPUs. Task-specific CPU/GPU packages belong in the task pack's
`requirements.txt`.

For a new task, ask `$autoresearch` to interview you and create
`tasks/<slug>/`, then commit that task pack before bootstrap.
Task initialization should include `scripts/validate_task.sh`, the task
preparation path, and at least one measured baseline scored by the fixed
evaluator. Record the measured baseline in the task pack before bootstrap.

The launcher runs local `codex exec` by default, so one command starts or
resumes the persistent Bash round loop:

```
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag>
```

Each round writes a fresh campaign prompt, exports `AUTORESEARCH_ROUND`, runs
one agent process, reconciles slots, sleeps, and repeats until stopped. Use
`max_rounds=1` for one bounded agent round:

```
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag> max_rounds=1
```

`max_turns=1` remains accepted as a compatibility alias.

Set `AUTORESEARCH_AGENT_CMD`, or pass an explicit agent CLI after `--`, to use a
different command that accepts prompts on standard input:

```
scripts/autoresearch_launch.sh task=<slug> run_tag=<run_tag> -- <agent command...>
```

Use `agent=prompt` to print the persistent orchestration prompt without running
an agent.

## Validation

Useful checks while developing this skill:

```
python3 -B -c 'import pathlib; [compile(pathlib.Path(p).read_text(), p, "exec") for p in ["skills/autoresearch/scripts/scaffold_repo.py", "skills/autoresearch/assets/repo-template/prepare.py", "skills/autoresearch/assets/repo-template/evaluate.py"]]'
bash -n skills/autoresearch/assets/repo-template/scripts/*.sh
tmp="$(mktemp -d)" && mkdir "$tmp/repo" "$tmp/repo/.omx" && python skills/autoresearch/scripts/scaffold_repo.py --target "$tmp/repo" --name Smoke --no-git
```

## License

MIT. The bundled CSP example retains attribution for code derived from OMatG in
its task-specific files.
