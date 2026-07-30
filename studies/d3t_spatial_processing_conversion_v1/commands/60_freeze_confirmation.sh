#!/usr/bin/env bash
set -euo pipefail
se-study-freeze \
  --study studies/d3t_spatial_processing_conversion_v1/study.json \
  --stage confirmation \
  --source-plan runs/base/d3t_spatial_processing_conversion_v1/confirmation/exploration_plan.json \
  --paired-plan runs/interventions/d3t_spatial_processing_conversion_v1/confirmation/paired_exploration_plan.json \
  --assessment analyses/d3t_spatial_processing_conversion_v1/confirmation/paired_exploration_assessment.json \
  --decision analyses/d3t_spatial_processing_conversion_v1/confirmation/candidate_decision.json \
  --results analyses/d3t_spatial_processing_conversion_v1/confirmation/paired_exploration_results.json
