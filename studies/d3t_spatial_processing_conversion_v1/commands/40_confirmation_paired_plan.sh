#!/usr/bin/env bash
set -euo pipefail
se-exploration-paired-plan \
  --stage confirmation \
  --study-id d3t-spatial-processing-conversion-v1 \
  --candidate-spec studies/d3t_spatial_processing_conversion_v1/protocol/candidate.json \
  --source-root runs/base/d3t_spatial_processing_conversion_v1/confirmation \
  --checkpoint-tick 480 \
  --prior-assessment studies/d3t_spatial_processing_conversion_v1/frozen/replication/assessment.json \
  --run-root runs/interventions/d3t_spatial_processing_conversion_v1/confirmation \
  --analysis-output analyses/d3t_spatial_processing_conversion_v1/confirmation \
  --decision-ledger state/decisions/exploration_candidate_ledger.json \
  --backend auto \
  --authorize-confirmation
