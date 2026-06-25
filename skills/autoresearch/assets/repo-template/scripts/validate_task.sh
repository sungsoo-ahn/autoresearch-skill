#!/usr/bin/env bash
# Validate a task pack before bootstrap or review.
# Usage: validate_task.sh <task_dir>
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

task_dir="${1:-}"
[ -n "$task_dir" ] || { echo "validate_task: task_dir is required" >&2; exit 2; }
[ -d "$task_dir" ] || { echo "validate_task: not a directory: $task_dir" >&2; exit 1; }

required=(
  task.json
  task.md
  contract.md
  methods.md
  prepare.py
  evaluate.py
  requirements.txt
  smoke.md
)
for f in "${required[@]}"; do
  [ -f "${task_dir}/${f}" ] || { echo "validate_task: missing ${task_dir}/${f}" >&2; exit 1; }
done

python3 - "$task_dir/task.json" <<'PY'
import json
import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)

def require(key):
    cur = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise SystemExit(f"validate_task: task.json missing {key}")
        cur = cur[part]
    return cur

slug = require("slug")
if not isinstance(slug, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
    raise SystemExit("validate_task: slug must match [A-Za-z0-9_-]+")

metric_name = require("metric.name")
if not isinstance(metric_name, str) or not metric_name:
    raise SystemExit("validate_task: metric.name must be a non-empty string")

direction = require("metric.direction")
if direction not in {"maximize", "minimize"}:
    raise SystemExit("validate_task: metric.direction must be maximize or minimize")

candidate_entry = require("candidate_entry")
if candidate_entry != "candidate.py":
    raise SystemExit("validate_task: candidate_entry must be candidate.py")

for key in ("defaults.max_minutes", "defaults.smoke_seconds", "defaults.noise_sigma"):
    value = require(key)
    if not isinstance(value, (int, float)) or value < 0:
        raise SystemExit(f"validate_task: {key} must be a non-negative number")
PY

python3 - "$task_dir/prepare.py" "$task_dir/evaluate.py" <<'PY'
import pathlib
import sys

for arg in sys.argv[1:]:
    path = pathlib.Path(arg)
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
PY

python3 - "$task_dir" "${required[@]}" <<'PY'
import pathlib
import sys

task_dir = pathlib.Path(sys.argv[1])
required = sys.argv[2:]
blocked = (
    "example_slug",
    "Human-readable task name",
    "<Task name>",
    "State the research objective",
    "Describe data sources",
    "Define the primary metric",
    "List required files or directories",
    "Define what would count as a useful campaign result",
    "Record conservative assumptions made during initialization",
    "List known methods, baselines, and approaches",
    "Define exactly which files candidates may read",
    "Task-specific setup script template",
    "Task-specific fixed evaluator template",
    "replace this template",
    "TBD",
    "TODO",
)

for name in required:
    path = task_dir / name
    text = path.read_text(encoding="utf-8")
    for marker in blocked:
        if marker in text:
            raise SystemExit(f"validate_task: placeholder marker {marker!r} remains in {path}")
PY
echo "validate_task ok: ${task_dir}"
