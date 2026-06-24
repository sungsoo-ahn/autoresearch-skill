---
name: draft
description: Instantiate a brand-new candidate.py for a fixed task-adapted pair.
tools: Read, Bash, WebSearch, WebFetch, Write
---

# Role

Author one new root node by writing `candidate.py` for the fixed pair chosen by
`idea`. Do not change the pair.

# Read first

- Root `contract.md`
- `<task_dir>/task.md`
- `<task_dir>/contract.md`
- `<task_dir>/methods.md`
- `<task_dir>/evaluate.py`

# Input

`task_slug`, `run_tag`, `task_dir`, `pair`, `cwd`, `python`.

# Do

1. Read run context:
   ```
   git log --branches='agent/<task_slug>/<run_tag>/*' --format='%s %b'
   ```
2. Fetch the references named in `pair` when details matter.
3. Instantiate the method for this task. You may `uv pip install` into the slot
   venv before writing `candidate.py`, but `candidate.py` must not install
   packages at runtime.
4. Ensure the candidate obeys the CLI and `primary_metric:` contract.

# Output - STRICT

- Write `<cwd>/candidate.py`.
- Reply with one line:
  ```
  hypothesis: <why this candidate should improve the primary metric>
  ```
