#!/usr/bin/env bash
# Reconcile each slot after restart. A worktree with a live candidate.py keeps
# running; a stale worktree is cleaned up.
# Usage: slot_reconcile.sh <task_slug> <run_tag> <n_slots>
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

task_slug="$1"; run_tag="$2"; n_slots="$3"

for ((N=0; N<n_slots; N++)); do
  WT=".worktrees/slot-${N}"
  if [ ! -d "$WT" ]; then
    echo "slot=${N} idle"
    continue
  fi
  if pgrep -f "${WT}.*candidate.py" >/dev/null 2>&1; then
    echo "slot=${N} running (live candidate.py) - leave it"
  else
    branch="$(git -C "$WT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    git worktree remove --force "$WT"
    if [ -n "$branch" ] && [ "$branch" != "HEAD" ]; then
      git branch -D "$branch" 2>/dev/null || true
    fi
    echo "slot=${N} stalled -> cleaned (task=${task_slug} run=${run_tag})"
  fi
done

python3 scripts/campaign_log.py log \
  --task "$task_slug" \
  --run-tag "$run_tag" \
  --event slot_reconcile \
  --message "reconciled ${n_slots} slots" \
  --no-render || true
