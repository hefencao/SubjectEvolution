#!/usr/bin/env bash
set -euo pipefail
se-d1-resource-sensing \
  --plan analyses/d1d_inherited_resource_sensing_v1/pilot/paired_plan.json \
  --output analyses/d1d_inherited_resource_sensing_v1/pilot/paired_results.json \
  --backend auto
