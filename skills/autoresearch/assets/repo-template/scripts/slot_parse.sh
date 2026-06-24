#!/usr/bin/env bash
# Parse a full run result, or consolidate smoke-fail artifacts.
# Writes runs/staging/parsed.env with status + primary_metric.
# Usage: slot_parse.sh <N> <task_slug> <run_tag> <exit_code>
#        slot_parse.sh <N> <task_slug> <run_tag> --smoke
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

N="$1"; task_slug="$2"; run_tag="$3"; mode="$4"
WT=".worktrees/slot-${N}"
staging="$WT/runs/staging"
primary_metric=""; status=""

if [ "$mode" = "--smoke" ]; then
  [ -f "$WT/runs/staging-smoke/smoke.log" ] && mv "$WT/runs/staging-smoke/smoke.log" "$staging/"
  [ -d "$WT/runs/staging-smoke/artifacts" ] && mv "$WT/runs/staging-smoke/artifacts" "$staging/smoke_artifacts"
  rmdir "$WT/runs/staging-smoke" 2>/dev/null || true
  status="crash"
else
  exit_code="$mode"
  primary_metric="$(grep '^primary_metric:' "$staging/run.log" 2>/dev/null | tail -1 | awk '{print $2}' || true)"
  if [ "$exit_code" = "0" ] && [ -n "$primary_metric" ] && [ "$primary_metric" != "nan" ]; then
    status="ok"
  else
    status="crash"
  fi
fi

cat > "$staging/parsed.env" <<ENV
status=${status}
primary_metric=${primary_metric}
ENV

echo "slot_parse ok: slot=${N} task=${task_slug} status=${status} primary_metric=${primary_metric:-}"
