#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

for condition in k1_compat k2_private k2_exchange; do
  config="configs/mvp_short_${condition}.json"
  for repeat in a b; do
    output="runs/k2_short_validation/${condition}_${repeat}"
    rm -rf "$output"
    python -m se \
      --config "$config" \
      --output "$output" \
      --backend cpu
  done
done
