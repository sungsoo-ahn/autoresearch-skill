#!/usr/bin/env bash
# Campaign startup for a task pack: validate the task, build a campaign-local
# base venv, prepare task data, detect compute resources, and freeze campaign.json.
# Usage: bootstrap.sh task=<slug> run_tag=<tag> [task_path=<path>] [device=auto|gpu|cpu] [gpus=all] [n_slots=<cpu slots>] [max_minutes=<task default>] [smoke_seconds=<task default>] [noise_sigma=<task default>]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
PYTHON_SPEC="3.13"

task=""; task_path=""; run_tag=""; device="auto"; gpus="all"; n_slots_arg=""; max_minutes=""; smoke_seconds=""; noise_sigma=""
for kv in "$@"; do
  case "$kv" in
    task=*)          task="${kv#*=}" ;;
    task_path=*)     task_path="${kv#*=}" ;;
    run_tag=*)       run_tag="${kv#*=}" ;;
    device=*)        device="${kv#*=}" ;;
    gpus=*)          gpus="${kv#*=}" ;;
    n_slots=*)       n_slots_arg="${kv#*=}" ;;
    max_minutes=*)   max_minutes="${kv#*=}" ;;
    smoke_seconds=*) smoke_seconds="${kv#*=}" ;;
    noise_sigma=*)   noise_sigma="${kv#*=}" ;;
    *) echo "bootstrap: unknown arg '$kv'" >&2; exit 2 ;;
  esac
done
[ -n "$task" ] || { echo "bootstrap: task=<slug> is required" >&2; exit 2; }
[ -n "$run_tag" ] || { echo "bootstrap: run_tag=<tag> is required" >&2; exit 2; }

case "$task" in
  *[!a-zA-Z0-9_-]*|"") echo "bootstrap: task must match [A-Za-z0-9_-]+" >&2; exit 2 ;;
esac
case "$run_tag" in
  *[!a-zA-Z0-9_-]*|"") echo "bootstrap: run_tag must match [A-Za-z0-9_-]+" >&2; exit 2 ;;
esac
case "$device" in
  auto|gpu|cpu) ;;
  *) echo "bootstrap: device must be auto, gpu, or cpu" >&2; exit 2 ;;
esac

if [ -z "$task_path" ]; then
  if [ -d "tasks/${task}" ]; then
    task_path="tasks/${task}"
  elif [ -d "examples/${task}" ]; then
    task_path="examples/${task}"
  else
    echo "bootstrap: no task pack at tasks/${task} or examples/${task}" >&2
    exit 1
  fi
fi
[ -d "$task_path" ] || { echo "bootstrap: task_path not found: $task_path" >&2; exit 1; }
case "$task_path" in
  /*) echo "bootstrap: task_path must be relative to the repo root" >&2; exit 2 ;;
esac
case "$task_path" in
  *[!a-zA-Z0-9_./-]*|"") echo "bootstrap: task_path contains unsupported characters" >&2; exit 2 ;;
esac
scripts/validate_task.sh "$task_path"

read_manifest() {
  python3 - "$task_path/task.json" "$1" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
cur = data
for part in sys.argv[2].split("."):
    cur = cur[part]
print(cur)
PY
}

manifest_slug="$(read_manifest slug)"
[ "$manifest_slug" = "$task" ] || {
  echo "bootstrap: task=${task} does not match manifest slug=${manifest_slug}" >&2
  exit 1
}
metric_name="$(read_manifest metric.name)"
metric_direction="$(read_manifest metric.direction)"
[ -n "$max_minutes" ] || max_minutes="$(read_manifest defaults.max_minutes)"
[ -n "$smoke_seconds" ] || smoke_seconds="$(read_manifest defaults.smoke_seconds)"
[ -n "$noise_sigma" ] || noise_sigma="$(read_manifest defaults.noise_sigma)"

# --- preconditions ---
[ "$(git rev-parse --abbrev-ref HEAD)" = "agent/root" ] \
  || { echo "bootstrap: must be on agent/root" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] \
  || { echo "bootstrap: working tree not clean" >&2; exit 1; }
if git for-each-ref --format='%(refname)' "refs/heads/agent/${task}/${run_tag}/" | grep -q .; then
  echo "bootstrap: agent/${task}/${run_tag}/* branches already exist" >&2; exit 1
fi
[ ! -e "runs/${task}/${run_tag}" ] || { echo "bootstrap: runs/${task}/${run_tag} already exists" >&2; exit 1; }

run_root="runs/${task}/${run_tag}"
base_venv="${run_root}/base-venv"
data_dir="data/${task}"
mkdir -p "$run_root" "$data_dir"

# --- campaign-local base venv ---
"$UV" venv --python "$PYTHON_SPEC" "$base_venv"
VIRTUAL_ENV="$base_venv" "$UV" pip install --quiet -r requirements.txt
VIRTUAL_ENV="$base_venv" "$UV" pip install --quiet -r "$task_path/requirements.txt"
VIRTUAL_ENV="$base_venv" "$UV" pip freeze > "${run_root}/base.lock"

# --- task data setup ---
"$base_venv/bin/python" prepare.py --task_dir "$task_path" --out_dir "$data_dir"

# --- compute resource detection ---
device_mode="$device"
if [ "$device_mode" = "auto" ]; then
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    device_mode="gpu"
  else
    device_mode="cpu"
  fi
fi

if [ "$device_mode" = "gpu" ]; then
  command -v nvidia-smi >/dev/null 2>&1 \
    || { echo "bootstrap: device=gpu requires nvidia-smi" >&2; exit 1; }
  if [ "$gpus" = "all" ]; then
    mapfile -t device_ids < <(nvidia-smi --query-gpu=index --format=csv,noheader)
  else
    IFS=',' read -r -a device_ids <<< "$gpus"
  fi
  n_slots="${#device_ids[@]}"
  [ "$n_slots" -ge 1 ] || { echo "bootstrap: no GPUs detected" >&2; exit 1; }
  devices="$(IFS=,; echo "${device_ids[*]}")"
  vram_total_mb="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | sort -n | head -1)"
else
  if [ -z "$n_slots_arg" ]; then
    n_slots_arg="1"
  fi
  case "$n_slots_arg" in
    *[!0-9]*|"") echo "bootstrap: n_slots must be a positive integer for device=cpu" >&2; exit 2 ;;
  esac
  [ "$n_slots_arg" -ge 1 ] || { echo "bootstrap: n_slots must be >= 1" >&2; exit 2; }
  n_slots="$n_slots_arg"
  device_ids=()
  for ((i=0; i<n_slots; i++)); do
    device_ids+=("cpu${i}")
  done
  devices="$(IFS=,; echo "${device_ids[*]}")"
  vram_total_mb=0
fi

# --- persist campaign.json ---
"$base_venv/bin/python" - "$run_root/campaign.json" <<PY
import json
config = {
    "task_slug": "${task}",
    "task_path": "${task_path}",
    "run_tag": "${run_tag}",
    "device_mode": "${device_mode}",
    "devices": "${devices}",
    "n_slots": ${n_slots},
    "vram_total_mb": ${vram_total_mb},
    "max_minutes": float("${max_minutes}"),
    "smoke_seconds": float("${smoke_seconds}"),
    "noise_sigma": float("${noise_sigma}"),
    "metric_name": "${metric_name}",
    "metric_direction": "${metric_direction}",
    "candidate_entry": "candidate.py",
    "data_dir": "${data_dir}",
}
with open("${run_root}/campaign.json", "w", encoding="utf-8") as fh:
    json.dump(config, fh, indent=2)
    fh.write("\\n")
PY

python3 scripts/campaign_log.py log \
  --task "$task" \
  --run-tag "$run_tag" \
  --event campaign_bootstrap \
  --status ok \
  --message "bootstrap complete; report initialized" || true

echo "bootstrap ok: task=${task} run_tag=${run_tag} device=${device_mode} devices=${devices} n_slots=${n_slots} vram_total_mb=${vram_total_mb} max_minutes=${max_minutes} smoke_seconds=${smoke_seconds} noise_sigma=${noise_sigma}"
echo "next: start the persistent Bash round loop:"
echo "  scripts/autoresearch_launch.sh task=${task} run_tag=${run_tag}"
echo "report: runs/${task}/${run_tag}/report.html"
