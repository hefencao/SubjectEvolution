#!/usr/bin/env bash
set -euo pipefail
bundle=${1:?usage: 74_check_result_bundle.sh <result-bundle.zip-or-directory>}
se-study-result-import \
  --study studies/d3t_spatial_processing_conversion_v1/study.json \
  --bundle "$bundle" \
  --check-only
