#!/usr/bin/env bash
set -euo pipefail
output=${1:?usage: 80_export_result_bundle.sh <output.zip>}
se-study-result-export \
  --study studies/d3t_spatial_processing_conversion_v1/study.json \
  --output "$output"
