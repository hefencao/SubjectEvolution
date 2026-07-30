#!/usr/bin/env bash
set -euo pipefail
se-study-layout-migrate \
  --study studies/d3t_spatial_processing_conversion_v1/study.json \
  --stage replication \
  --legacy-source-root analyses/d3n_replication \
  --legacy-paired-root analyses/d3t_spatial_processing_conversion_paired_replication \
  --materialize auto
