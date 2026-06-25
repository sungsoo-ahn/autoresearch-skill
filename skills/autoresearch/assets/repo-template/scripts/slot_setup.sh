#!/usr/bin/env bash
# Create a slot worktree, reconstruct its venv, and write the [RUNNING]
# placeholder commit.
# Usage: slot_setup.sh <N> <parent_ref> <branch> <task_slug> <run_tag> <op> <pair_file> [parent_sha]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
PYTHON_SPEC="3.13"
EXTRA_INDEX="https://download.pytorch.org/whl/cu121"

N="$1"; parent_ref="$2"; branch="$3"; task_slug="$4"; run_tag="$5"; op="$6"
pair_file="$7"; parent_sha="${8:-}"
WT=".worktrees/slot-${N}"
run_root="runs/${task_slug}/${run_tag}"
campaign="${run_root}/campaign.json"

[ -f "$campaign" ] || { echo "slot_setup: campaign not found: $campaign" >&2; exit 1; }
task_path="$(python3 - "$campaign" <<'PY'
import json, sys
print(json.load(open(sys.argv[1]))["task_path"])
PY
)"

git worktree add -b "$branch" "$WT" "$parent_ref"
ln -s "../../data/${task_slug}" "$WT/data"
chmod 444 "$WT/evaluate.py" "$WT/prepare.py" "$WT/requirements.txt" \
          "$WT/program.md" "$WT/contract.md"
if [ -d "$WT/$task_path" ]; then
  find "$WT/$task_path" -type f -exec chmod 444 {} +
fi
mkdir -p "$WT/runs/staging"

"$UV" venv --python "$PYTHON_SPEC" "$WT/runs/staging/.venv"
if [ -n "$parent_sha" ] && [ -f "${run_root}/${parent_sha}/requirements.lock" ]; then
  lock="${run_root}/${parent_sha}/requirements.lock"; venv_src="parent"
else
  lock="${run_root}/base.lock"; venv_src="base"
fi
VIRTUAL_ENV="$WT/runs/staging/.venv" "$UV" pip install --quiet \
  --extra-index-url "$EXTRA_INDEX" --index-strategy unsafe-best-match -r "$lock"

pair="$(cat "$pair_file")"
msg_args=(-m "${op}: [RUNNING]" -m "pair: ${pair}")
[ -n "$parent_sha" ] && msg_args+=(-m "parent: ${parent_sha}")
git -C "$WT" commit --allow-empty "${msg_args[@]}"

python3 scripts/campaign_log.py log \
  --task "$task_slug" \
  --run-tag "$run_tag" \
  --event slot_setup \
  --slot "$N" \
  --op "$op" \
  --parent "$parent_sha" \
  --branch "$branch" \
  --pair-file "$pair_file" \
  --message "slot setup from ${venv_src} environment" || true

echo "slot_setup ok: slot=${N} branch=${branch} task=${task_slug} venv=${venv_src}"
