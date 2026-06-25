#!/usr/bin/env bash
# Run a persistent bash round loop that invokes an agent command.
# Usage:
#   scripts/autoresearch_launch.sh task=<slug> [run_tag=<tag>] [agent=auto|prompt]
#   scripts/autoresearch_launch.sh task=<slug> [run_tag=<tag>] [max_rounds=0] [sleep_seconds=15] [max_failures=3] -- <agent command...>
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

task=""; run_tag=""; max_rounds="0"; sleep_seconds="15"; max_failures="3"; reconcile="1"; agent="auto"
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
    max_rounds=*)    max_rounds="${1#*=}" ;;
    max_turns=*)     max_rounds="${1#*=}" ;;
    sleep_seconds=*) sleep_seconds="${1#*=}" ;;
    max_failures=*)  max_failures="${1#*=}" ;;
    reconcile=*)     reconcile="${1#*=}" ;;
    agent=*)         agent="${1#*=}" ;;
    *) echo "autoresearch_launch: unknown arg '$1'" >&2; exit 2 ;;
  esac
  shift
done

[ -n "$task" ] || { echo "autoresearch_launch: task=<slug> is required" >&2; exit 2; }
if [ -z "$run_tag" ]; then
  candidates=()
  if [ -d "runs/${task}" ]; then
    while IFS= read -r campaign_path; do
      rel="${campaign_path#runs/${task}/}"
      candidates+=("${rel%/campaign.json}")
    done < <(find "runs/${task}" -mindepth 2 -maxdepth 2 -type f -name campaign.json | sort)
  fi

  if [ "${#candidates[@]}" -eq 1 ]; then
    run_tag="${candidates[0]}"
    echo "autoresearch_launch: inferred run_tag=${run_tag}"
  elif [ "${#candidates[@]}" -eq 0 ]; then
    echo "autoresearch_launch: run_tag=<tag> is required; no bootstrapped campaigns found for task=${task}" >&2
    echo "autoresearch_launch: bootstrap first, for example: scripts/bootstrap.sh task=${task} run_tag=<tag> device=cpu n_slots=1" >&2
    exit 2
  else
    echo "autoresearch_launch: run_tag=<tag> is required; available run tags: ${candidates[*]}" >&2
    exit 2
  fi
fi
case "$max_rounds" in *[!0-9]*|"") echo "autoresearch_launch: max_rounds/max_turns must be a non-negative integer" >&2; exit 2 ;; esac
case "$sleep_seconds" in *[!0-9]*|"") echo "autoresearch_launch: sleep_seconds must be a non-negative integer" >&2; exit 2 ;; esac
case "$max_failures" in *[!0-9]*|"") echo "autoresearch_launch: max_failures must be a non-negative integer" >&2; exit 2 ;; esac
case "$reconcile" in 0|1) ;; *) echo "autoresearch_launch: reconcile must be 0 or 1" >&2; exit 2 ;; esac
case "$agent" in auto|prompt) ;; *) echo "autoresearch_launch: agent must be auto or prompt" >&2; exit 2 ;; esac

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

write_prompt() {
  local round="$1"
  cat > "$prompt_file" <<EOF
# Persistent Autoresearch Orchestrator

You are the persistent orchestrator for this autoresearch campaign.

Campaign:
- task: ${task}
- run_tag: ${run_tag}
- launch_round: ${round}
- task_path: ${task_path}
- device_mode: ${device_mode}
- devices: ${devices}
- n_slots: ${n_slots}
- metric: ${metric_name} (${metric_direction})
- max_minutes: ${max_minutes}
- smoke_seconds: ${smoke_seconds}
- noise_sigma: ${noise_sigma}

Round contract:
- The launcher is a persistent bash loop. It invokes one agent process per
  round with this prompt on standard input and exports
  AUTORESEARCH_ROUND=${round}, AUTORESEARCH_TASK=${task}, and
  AUTORESEARCH_RUN_TAG=${run_tag}.
- Treat each round as stateless except for durable repository artifacts. Persist
  all decisions, evidence, and recovery state through git branches,
  campaign.json, .slots/, .worktrees/, and runs/.
- At the end of a round, leave enough evidence for the next round to resume
  without relying on hidden chat context.

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
}

if [ "${#agent_cmd[@]}" -eq 0 ]; then
  if [ "$agent" = "prompt" ]; then
    write_prompt 0
    echo
    echo "agent=prompt selected. Paste the prompt below into your agent UI,"
    echo "or rerun with: scripts/autoresearch_launch.sh task=${task} run_tag=${run_tag} -- <agent command...>"
    echo
    cat "$prompt_file"
    exit 0
  fi

  if [ -n "${AUTORESEARCH_AGENT_CMD:-}" ]; then
    agent_cmd=(bash -lc "$AUTORESEARCH_AGENT_CMD")
    echo "autoresearch_launch: using AUTORESEARCH_AGENT_CMD"
  elif command -v codex >/dev/null 2>&1; then
    agent_cmd=(
      codex exec
      --dangerously-bypass-approvals-and-sandbox
      --dangerously-bypass-hook-trust
      --skip-git-repo-check
      -C "$PWD"
      -
    )
    echo "autoresearch_launch: using default agent command: ${agent_cmd[*]}"
  else
    echo "autoresearch_launch: no agent command supplied and codex was not found on PATH" >&2
    echo "autoresearch_launch: install Codex, set AUTORESEARCH_AGENT_CMD, pass -- <agent command...>, or use agent=prompt" >&2
    exit 1
  fi
fi

round=0
failures=0
while true; do
  if [ "$max_rounds" -ne 0 ] && [ "$round" -ge "$max_rounds" ]; then
    echo "autoresearch_launch: reached max_rounds=${max_rounds}"
    exit 0
  fi

  round=$((round + 1))
  write_prompt "$round"
  echo "autoresearch_launch: starting round ${round} with command: ${agent_cmd[*]}"
  set +e
  AUTORESEARCH_TASK="$task" \
    AUTORESEARCH_RUN_TAG="$run_tag" \
    AUTORESEARCH_ROUND="$round" \
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
