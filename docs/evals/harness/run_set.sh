#!/usr/bin/env bash
# One pilot set: every task in <tasks_dir>, one epoch, one arm, concurrency 1, logs to <log_dir>.
# Usage: docs/evals/harness/run_set.sh <tasks_dir> <log_dir> [arm=plain] [epochs=1]
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
tasks_dir="$1"; log_dir="$2"; arm="${3:-plain}"; epochs="${4:-1}"
mkdir -p "$log_dir"
exec uv run --no-project --python 3.12 --with inspect-ai --with pytest \
  inspect eval "$here/inspect_task.py@stillwright_impossible" --model none \
  -T tasks_dir="$tasks_dir" -T arm="$arm" --epochs "$epochs" \
  --log-dir "$log_dir" --max-samples 1 --max-tasks 1 --display plain
