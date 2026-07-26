#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH="${PYTHONPATH:-src}" python -m se \
  --config configs/mvp_small_k2_retest350.json \
  --output runs/mvp_small_k2_gpu_v065_retest350 \
  --backend gpu \
  --gpu-semantics-mode hybrid-accelerated
