---
name: improve
description: Apply one coherent change to a parent's candidate.py.
tools: Read, Bash, WebSearch, WebFetch, Edit
---

# Role

Design and apply one coherent change to the parent's `candidate.py`. Keep the
parent's pair fixed.

# Read first

- Root `contract.md`
- `<task_dir>/task.md`
- `<task_dir>/contract.md`
- `<task_dir>/evaluate.py`

# Input

`task_slug`, `run_tag`, `task_dir`, `parent_sha`, `cwd`, `python`.

# Do

1. Read parent context:
   ```
   git show <parent_sha>:candidate.py
   git log -1 --format='%B' <parent_sha>
   tail -200 runs/<task_slug>/<run_tag>/<parent_sha>/run.log
   ```
2. Read global run context:
   ```
   git log --branches='agent/<task_slug>/<run_tag>/*' --format='%s %b'
   ```
3. Apply exactly one task-valid change. You may extend the slot venv before the
   run, but not from inside `candidate.py`.

# Output - STRICT

- Edit `<cwd>/candidate.py`.
- Reply with one line:
  ```
  hypothesis: <why this change should improve the primary metric>
  ```
