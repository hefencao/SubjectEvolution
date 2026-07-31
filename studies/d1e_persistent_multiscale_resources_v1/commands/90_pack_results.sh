#!/usr/bin/env bash
set -euo pipefail
output=${1:-d1e_persistent_multiscale_resources_v1_results.zip}
extra=()
if [[ ${INCLUDE_CHECKPOINTS:-0} == 1 ]]; then
  extra+=(--include-checkpoints)
fi
python scripts/package_required_results.py \
  --study-root studies/d1e_persistent_multiscale_resources_v1 \
  --analysis-root analyses/d1e_persistent_multiscale_resources_v1 \
  --runtime-root runs/base/d1e_persistent_multiscale_resources_v1 \
  --runtime-root runs/interventions/d1e_persistent_multiscale_resources_v1 \
  --output "$output" \
  "${extra[@]}"
