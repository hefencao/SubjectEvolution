#!/usr/bin/env bash
set -euo pipefail
output=${1:-d1d_inherited_resource_sensing_v1_results.zip}
extra=()
if [[ ${INCLUDE_CHECKPOINTS:-0} == 1 ]]; then
  extra+=(--include-checkpoints)
fi
python scripts/package_required_results.py \
  --study-root studies/d1d_inherited_resource_sensing_v1 \
  --analysis-root analyses/d1d_inherited_resource_sensing_v1 \
  --runtime-root runs/base/d1d_inherited_resource_sensing_v1 \
  --runtime-root runs/interventions/d1d_inherited_resource_sensing_v1 \
  --output "$output" \
  "${extra[@]}"
