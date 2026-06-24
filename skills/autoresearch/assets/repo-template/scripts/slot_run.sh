#!/usr/bin/env bash
# Launch a slot's candidate.py in the background with GPU pinning, timeout, and
# an exit-marker writer.
# Usage: slot_run.sh <N> <gpu> <python> <task_slug> <run_tag> <max_minutes>
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

N="$1"; gpu="$2"; py="$3"; task_slug="$4"; run_tag="$5"; max_minutes="$6"
WT=".worktrees/slot-${N}"
repo="$PWD"
campaign="runs/${task_slug}/${run_tag}/campaign.json"

[ -s "$WT/candidate.py" ] || { echo "slot_run: $WT/candidate.py missing/empty" >&2; exit 1; }
[ -f "$campaign" ] || { echo "slot_run: campaign not found: $campaign" >&2; exit 1; }

task_path="$(python3 - "$campaign" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["task_path"])
PY
)"
os_timeout="$(python3 - "$max_minutes" <<'PY'
import math, sys
print(int(math.ceil((float(sys.argv[1]) + 90.0) * 60.0)))
PY
)"

mkdir -p "$repo/.slots"
setsid bash -c "CUDA_VISIBLE_DEVICES='${gpu}' timeout ${os_timeout} '${py}' '${WT}/candidate.py' --max_minutes ${max_minutes} --run_name staging --task_dir '${WT}/${task_path}' --data_dir '${WT}/data' > '${WT}/runs/staging/run.log' 2>&1; echo \"slot=${N} exit=\$?\" >> '${repo}/.slots/events.log'" >/dev/null 2>&1 &

echo "slot_run launched: slot=${N} task=${task_slug} gpu=${gpu} os_timeout=${os_timeout}s"
