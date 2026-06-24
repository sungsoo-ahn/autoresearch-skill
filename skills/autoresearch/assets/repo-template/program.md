# Autoresearch toolkit orchestrator loop

The git commit DAG under `agent/<task_slug>/<run_tag>/*` is the search graph
and the memory. `git log` plus per-node artifacts under
`runs/<task_slug>/<run_tag>/<sha>/` are the only state stores. The orchestrator
decides operator, parent, and slot assignment; execution happens only through
`scripts/*.sh` and the role agents below. Optional adapters may provide concrete
prompt files for these roles.

## Startup

`runs/<task_slug>/<run_tag>/campaign.json` is the durable source of truth. It
contains `task_slug`, `task_path`, `run_tag`, `device_mode`, `devices`,
`n_slots`, `vram_total_mb`, `max_minutes`, `smoke_seconds`, `noise_sigma`,
metric metadata, and `candidate_entry`. Read it at launch, before every
dispatch, and during recovery. Do not reconstruct campaign config from the
prompt.

## Hard rules

- Dispatch only these roles: `idea`, `draft`, `improve`, `debug`, `smoke`,
  `analyze`.
- Continue until the human explicitly stops the campaign, changes the task
  contract, or an external blocker prevents useful progress after recovery. Do
  not stop after one candidate, one slot cycle, one summary, or one good result.
- Run candidates only via `scripts/slot_run.sh`; `smoke` may run probes inside
  its own subagent.
- Generated implementation file is always `candidate.py`.
- The task pack is read-only during a campaign. Candidate authors edit only
  `candidate.py` in their slot worktree and may extend the slot venv before the
  run.
- No same-cycle retry after a smoke fail, crash, timeout, or `nan`: finalize the
  node as `[BUGGY]`; any repair is a later `debug` cycle.
- `debug` and `improve` keep the target/parent's pair. Only `draft`, preceded by
  `idea`, establishes a new pair.
- Decisions use only this task/run branch set and artifacts. Never inspect other
  tasks' branches for strategy or code.

## Reading the tree

```
git log --branches='agent/<task_slug>/<run_tag>/*' --format='%h %s%n%b'
```

Subject tag is status: `[primary_metric=X]` scored, `[BUGGY]` invalid, or
`[RUNNING]` in progress. Body carries `pair:`, optional `parent:`,
`hypothesis:`, and `finding:`.

Selection policy:
- no useful scored node yet, or exploration is needed -> `idea` then `draft`
- build on a scored node -> `improve`
- fix a promising buggy leaf -> `debug`
- keep draft count at least one third of improve count; while violated, idle
  slots go to `idea` + `draft`

## Notation

- `$N` slot index `0..n_slots-1`
- `$WT=.worktrees/slot-$N`
- `$DEVICE=devices[$N]` (`cpu<i>` for CPU slots, GPU id for GPU slots)
- `$PY=$WT/runs/staging/.venv/bin/python`
- `$BRANCH=agent/<task_slug>/<run_tag>/n<i>-<op>`
- `parent_ref=<parent_sha>` for improve/debug, `agent/root` for draft

## Per-slot pipeline

1. Decide operator and parent/target. For `draft`, dispatch `idea` first and use
   its returned pair.
2. Setup:
   ```
   mkdir -p .slots
   printf '%s' "<pair>" > .slots/slot-$N.pair
   scripts/slot_setup.sh $N <parent_ref> $BRANCH <task_slug> <run_tag> <op> .slots/slot-$N.pair [<parent_sha>]
   ```
3. Dispatch the operator subagent with `task_slug`, `run_tag`, `task_dir`,
   `cwd`, and `python` as appropriate.
4. Verify `[ -s $WT/candidate.py ]`. Write the returned hypothesis to
   `.slots/slot-$N.hypothesis`, then register it:
   ```
   scripts/slot_register.sh $N
   ```
5. Dispatch `smoke` with `task_dir`, `device_mode`, `device`,
   `vram_total_mb`, `smoke_seconds`, `python`, and `cwd`.
   - `pass` -> remove `$WT/runs/staging-smoke` and continue
   - `fail` -> `scripts/slot_parse.sh $N <task_slug> <run_tag> --smoke`, then analyze/finalize
6. Run:
   ```
   scripts/slot_run.sh $N $DEVICE $PY <task_slug> <run_tag> <max_minutes>
   ```
7. On `.slots/events.log` line `slot=$N exit=<code>`, parse:
   ```
   scripts/slot_parse.sh $N <task_slug> <run_tag> <code>
   ```
8. Dispatch `analyze` with `task_dir`, `cwd`, `status`, `primary_metric`,
   `metric_direction`, and `noise_sigma`; write its `finding:` to
   `.slots/slot-$N.finding`.
9. Finalize:
   ```
   scripts/slot_finalize.sh $N <task_slug> <run_tag> <op> [<parent_sha>]
   ```
10. Slot is idle; re-read `program.md` and campaign config, then dispatch the
    next candidate.

## Recovery

Preferred user entrypoint:

```
scripts/autoresearch_launch.sh task=<task_slug> run_tag=<run_tag>
```

Read `runs/<task_slug>/<run_tag>/campaign.json`, then:

```
scripts/slot_reconcile.sh <task_slug> <run_tag> <n_slots>
```

Running slots keep their live event; stale worktrees are cleaned and treated as
idle.
