#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
python -m subject_evolution.parity \
  --config "${1:-configs/mvp_short_k1_compat.json}" \
  --output "${2:-runs/cpu_gpu_parity}" \
  --ticks "${3:-5}" \
  --entities "${4:-64}" \
  --device-backend auto
