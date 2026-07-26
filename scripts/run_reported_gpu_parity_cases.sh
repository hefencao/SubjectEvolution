#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"

python -m se.analysis.parity \
  --config configs/mvp_small_k2.json \
  --output runs/parity_reported_mvp_small_k2_tick100 \
  --ticks 100 \
  --preserve-config-world \
  --world-only \
  --device-backend gpu \
  --require-gpu

python -m se.analysis.parity \
  --config configs/mvp_short_k2_exchange.json \
  --output runs/parity_reported_short_exchange_tick160 \
  --ticks 160 \
  --preserve-config-world \
  --world-only \
  --device-backend gpu \
  --require-gpu
