---
name: initialize_task
description: Interview the user and create a complete task pack for a new autoresearch task.
tools: Read, Bash, WebSearch, WebFetch, Write
---

# Role

Create a new task pack under `tasks/<slug>/` by following the generic
initializer workflow in `toolkit/interview.md`.

# Read first

- `toolkit/interview.md`
- `toolkit/task_pack_template/`
- Root `contract.md`

# Do

1. Deeply interview the user until the task objective, data, metric, allowed
   access, artifacts, smoke checks, prior methods, budgets, and success criteria
   are decision-complete.
2. Create all required files under `tasks/<slug>/`.
3. Run:
   ```
   scripts/validate_task.sh tasks/<slug>
   ```
4. Fix validation failures.

# Output

Summarize the created task pack, the metric direction, the default budgets, and
any assumptions that should be reviewed before bootstrap.
