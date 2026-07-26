#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

for spec in \
  none:configs/mvp_small_k1_none.json \
  private:configs/mvp_small_k1_private.json \
  costly:configs/mvp_small_k1.json \
  zero_cost:configs/mvp_small_k1_zero_cost.json
do
  name="${spec%%:*}"
  cfg="${spec#*:}"
  PYTHONPATH=src python -m se \
    --config "$cfg" \
    --output "runs/mvp_small_k1_${name}" \
    --backend cpu
done
