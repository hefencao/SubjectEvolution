#!/usr/bin/env bash
set -euo pipefail
se-study-layout-migrate \
  --study studies/d3t_spatial_processing_conversion_v1/study.json \
  --stage screen \
  --legacy-source-root analyses/d3n_screen \
  --legacy-paired-root analyses/d3t_spatial_processing_conversion_paired_screen \
  --materialize auto
