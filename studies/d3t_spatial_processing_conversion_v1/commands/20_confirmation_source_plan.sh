#!/usr/bin/env bash
set -euo pipefail
se-exploration-plan \
  --stage confirmation \
  --study-id d3t-spatial-processing-conversion-v1 \
  --candidate spatial-processing-conversion-acute-effect-v1 \
  --config studies/d3t_spatial_processing_conversion_v1/protocol/source_confirmation.json \
  --seeds 71301,71302,71303,71304,71305,71306,71307,71308 \
  --run-root runs/base/d3t_spatial_processing_conversion_v1/confirmation \
  --backend auto \
  --until-tick 480 \
  --prior-plan studies/d3t_spatial_processing_conversion_v1/frozen/replication/source_plan.json \
  --authorize-confirmation
