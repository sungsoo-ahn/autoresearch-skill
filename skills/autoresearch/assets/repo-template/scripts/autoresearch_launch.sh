#!/usr/bin/env bash
# Create a persistent orchestration prompt and optionally re-run an agent command.
# Usage:
#   scripts/autoresearch_launch.sh task=<slug> run_tag=<tag>
#   scripts/autoresearch_launch.sh task=<slug> run_tag=<tag> [max_turns=0] [sleep_seconds=15] [max_failures=3] -- <agent command...>
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

task=""; run_tag=""; max_turns="0"; sleep_seconds="15"; max_failures="3"; reconcile="1"
agent_cmd=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --)
      shift
      agent_cmd=("$@")
      break
      ;;
    task=*)          task="${1#*=}" ;;
    run_tag=*)       run_tag="${1#*=}" ;;
    max_turns=*)     max_turns="${1#*=}" ;;
    sleep_seconds=*) sleep_seconds="${1#*=}" ;;
    max_failures=*)  max_failures="${1#*=}" ;;
    reconcile=*)     reconcile="${1#*=}" ;;
    *) echo "autoresearch_launch: unknown arg '$1'" >&2; exit 2 ;;
  esac
  shift
done

[ -n "$task" ] || { echo "autoresearch_launch: task=<slug> is required" >&2; exit 2; }
[ -n "$run_tag" ] || { echo "autoresearch_launch: run_tag=<tag> is required" >&2; exit 2; }
case "$max_turns" in *[!0-9]*|"") echo "autoresearch_launch: max_turns must be a non-negative integer" >&2; exit 2 ;; esac
case "$sleep_seconds" in *[!0-9]*|"") echo "autoresearch_launch: sleep_seconds must be a non-negative integer" >&2; exit 2 ;; esac
case "$max_failures" in *[!0-9]*|"") echo "autoresearch_launch: max_failures must be a non-negative integer" >&2; exit 2 ;; esac
case "$reconcile" in 0|1) ;; *) echo "autoresearch_launch: reconcile must be 0 or 1" >&2; exit 2 ;; esac

campaign="runs/${task}/${run_tag}/campaign.json"
[ -f "$campaign" ] || { echo "autoresearch_launch: campaign not found: $campaign" >&2; exit 1; }

read_campaign() {
  python3 - "$campaign" "$1" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
print(data.get(sys.argv[2], ""))
PY
}

task_path="$(read_campaign task_path)"
n_slots="$(read_campaign n_slots)"
device_mode="$(read_campaign device_mode)"
devices="$(read_campaign devices)"
metric_name="$(read_campaign metric_name)"
metric_direction="$(read_campaign metric_direction)"
max_minutes="$(read_campaign max_minutes)"
smoke_seconds="$(read_campaign smoke_seconds)"
noise_sigma="$(read_campaign noise_sigma)"

mkdir -p .slots
prompt_file=".slots/autoresearch-${task}-${run_tag}.prompt.md"
cat > "$prompt_file" <<EOF
# Persistent Autoresearch Orchestrator

You are the persistent orchestrator for this autoresearch campaign.

Campaign:
- task: ${task}
- run_tag: ${run_tag}
- task_path: ${task_path}
- device_mode: ${device_mode}
- devices: ${devices}
- n_slots: ${n_slots}
- metric: ${metric_name} (${metric_direction})
- max_minutes: ${max_minutes}
- smoke_seconds: ${smoke_seconds}
- noise_sigma: ${noise_sigma}

Continuation contract:
- Continue the campaign until the human explicitly stops you, changes the task
  contract, or an external blocker prevents useful progress after recovery.
- Do not stop after one candidate, one slot cycle, one summary, or one good
  result. Treat every idle slot as work to refill.
- If you reach a model/tool/context limit and must yield, write a concise
  resume note and tell the human to rerun:
  \`scripts/autoresearch_launch.sh task=${task} run_tag=${run_tag}\`
- Never restart the campaign from scratch. Resume from git branches,
  campaign.json, .slots/, .worktrees/, and runs/.

Start or resume sequence:
1. Read \`program.md\`, root \`contract.md\`, and \`${campaign}\`.
2. Run \`scripts/slot_reconcile.sh ${task} ${run_tag} ${n_slots}\`.
3. Inspect the current search graph:
   \`git log --branches='agent/${task}/${run_tag}/*' --format='%h %s%n%b'\`
4. For every idle slot, choose the next valid role from \`program.md\`, set up
   the slot, register the hypothesis, run smoke, run the candidate, parse,
   analyze, finalize, and immediately continue.
5. Ask the human only for decisions that change the task contract, require
   unavailable credentials/data/compute, or would materially change evaluation
   policy.

Operate now. Keep the loop moving.
EOF

echo "autoresearch_launch: prompt written to ${prompt_file}"

if [ "${#agent_cmd[@]}" -eq 0 ]; then
  echo
  echo "No agent command supplied. Paste the prompt below into your agent UI,"
  echo "or rerun with: scripts/autoresearch_launch.sh task=${task} run_tag=${run_tag} -- <agent command...>"
  echo
  cat "$prompt_file"
  exit 0
fi

turn=0
failures=0
while true; do
  if [ "$max_turns" -ne 0 ] && [ "$turn" -ge "$max_turns" ]; then
    echo "autoresearch_launch: reached max_turns=${max_turns}"
    exit 0
  fi

  turn=$((turn + 1))
  echo "autoresearch_launch: starting turn ${turn} with command: ${agent_cmd[*]}"
  set +e
  "${agent_cmd[@]}" < "$prompt_file"
  rc="$?"
  set -e

  if [ "$reconcile" = "1" ]; then
    scripts/slot_reconcile.sh "$task" "$run_tag" "$n_slots" || true
  fi

  if [ "$rc" -ne 0 ]; then
    failures=$((failures + 1))
    echo "autoresearch_launch: agent command exited ${rc} (failure ${failures}/${max_failures})" >&2
    if [ "$max_failures" -ne 0 ] && [ "$failures" -ge "$max_failures" ]; then
      echo "autoresearch_launch: stopping after repeated agent command failures" >&2
      exit "$rc"
    fi
  else
    failures=0
  fi

  sleep "$sleep_seconds"
done
