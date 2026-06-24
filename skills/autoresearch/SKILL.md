---
name: autoresearch
description: Initialize and scaffold task-focused autonomous ML autoresearch repositories. Use when asked to create or initialize an autoresearch repo, interview for a new research task, define or validate a task pack, scaffold a task-pack-driven experiment harness, or include an optional Claude adapter or CSP example.
---

# Autoresearch

Use this skill to create a fresh autoresearch repository and its first task
pack. The generated repository owns campaign execution through its own
`program.md`, scripts, task packs, and optional agent adapters.

## Route By Intent

- **Create or scaffold a repo**: read `references/initialize-repo.md`.
- **Define, validate, or repair a task pack**: read `references/task-pack.md`.

## Core Model

The skill is the initializer. The generated repository is the runtime
authority. It owns task packs, campaign scripts, `candidate.py` contracts, logs,
git branches, validation, and run-loop instructions.

Default repository contract:

- generated implementation file: `candidate.py`
- primary result line: `primary_metric: <float>`
- task pack path: `tasks/<slug>/` or `examples/<slug>/`
- campaign branches: `agent/<task_slug>/<run_tag>/*`
- artifacts: `runs/<task_slug>/<run_tag>/<sha>/`
- launch/resume entrypoint: `scripts/autoresearch_launch.sh`

## Scaffolding Commands

Use `scripts/scaffold_repo.py` to create a clean repo from the bundled template.
By default it initializes git on `agent/root` and creates the initial commit so
the generated repo is ready for task-pack creation and bootstrap:

```bash
python skills/autoresearch/scripts/scaffold_repo.py \
  --target /path/to/new-repo \
  --name "Project Name" \
  --adapter claude \
  --include-csp-example
```

`--adapter claude` is optional. Omit it for an agent-agnostic repository.
`--include-csp-example` is optional. Omit it for a blank starter repository.

Validate generated task packs with the generated repo's
`scripts/validate_task.sh`.
After bootstrap, use the generated repo's `scripts/autoresearch_launch.sh` to
produce a persistent prompt or repeatedly invoke an agent command.

## Discipline

- Interview until objective, data, metric, artifacts, compute constraints, and
  task safety rules are explicit.
- Establish a baseline before autonomous improvement.
- Keep task-specific rules in task packs; keep reusable process in this skill.
- Leave run-loop execution and reporting to the generated repository unless the
  user explicitly asks to inspect or modify the template.
