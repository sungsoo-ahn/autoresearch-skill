#!/usr/bin/env bash
# Amend the [RUNNING] placeholder into the final node, move artifacts, and
# remove the worktree.
# Usage: slot_finalize.sh <N> <task_slug> <run_tag> <prefix> [parent_sha]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

UV="$(command -v uv || echo "$HOME/.local/bin/uv")"

N="$1"; task_slug="$2"; run_tag="$3"; prefix="$4"; parent_sha="${5:-}"
WT=".worktrees/slot-${N}"
repo="$PWD"
run_root="$repo/runs/${task_slug}/${run_tag}"
staging="$WT/runs/staging"

if [ ! -d "$WT" ]; then
  echo "slot_finalize: slot=${N} already finalized (no worktree)"; exit 0
fi

status=""; primary_metric=""
# shellcheck disable=SC1090,SC1091
[ -f "$staging/parsed.env" ] && . "$staging/parsed.env"

subject="$(git -C "$WT" log -1 --format='%s')"
tag="cleanup"
if [[ "$subject" == *"[RUNNING]"* ]]; then
  body="$(git -C "$WT" log -1 --format='%B')"
  pair="$(printf '%s\n' "$body" | sed -n 's/^pair: //p' | head -1)"
  hypothesis="$(printf '%s\n' "$body" | sed -n 's/^hypothesis: //p' | head -1)"
  finding="$(cat ".slots/slot-${N}.finding" 2>/dev/null || true)"
  if [ "$status" = "ok" ]; then
    tag="[primary_metric=${primary_metric}]"
  else
    tag="[BUGGY]"
  fi
  args=(-m "${prefix}: ${tag}" -m "pair: ${pair}")
  [ "$prefix" != "draft" ] && [ -n "$parent_sha" ] && args+=(-m "parent: ${parent_sha}")
  [ -n "$hypothesis" ] && args+=(-m "hypothesis: ${hypothesis}")
  [ -n "$finding" ]    && args+=(-m "finding: ${finding}")
  git -C "$WT" add candidate.py 2>/dev/null || true
  git -C "$WT" commit --amend --allow-empty "${args[@]}"
else
  echo "slot_finalize: slot=${N} already amended; completing cleanup only"
fi

sha="$(git -C "$WT" rev-parse --short HEAD)"
mkdir -p "$run_root"
if [ -d "$staging/.venv" ]; then
  VIRTUAL_ENV="$staging/.venv" "$UV" pip freeze > "$staging/requirements.lock"
fi
[ -d "$staging" ] && mv "$staging" "${run_root}/${sha}"
git worktree remove --force "$WT"

echo "slot_finalize ok: slot=${N} task=${task_slug} sha=${sha} tag=${tag}"
