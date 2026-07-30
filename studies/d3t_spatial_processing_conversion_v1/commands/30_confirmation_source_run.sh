#!/usr/bin/env bash
set -euo pipefail
se-multi \
  --config studies/d3t_spatial_processing_conversion_v1/protocol/source_confirmation.json \
  --seeds 71301,71302,71303,71304,71305,71306,71307,71308 \
  --output runs/base/d3t_spatial_processing_conversion_v1/confirmation \
  --backend auto \
  --until-tick 480 \
  --exploration-plan runs/base/d3t_spatial_processing_conversion_v1/confirmation/exploration_plan.json
