#!/usr/bin/env bash
set -euo pipefail
se-d1-resource-sensing-plan \
  --source-root runs/base/d1d_inherited_resource_sensing_v1/pilot \
  --checkpoint-tick 480 \
  --horizon 120 \
  --runtime-root runs/interventions/d1d_inherited_resource_sensing_v1/pilot \
  --output analyses/d1d_inherited_resource_sensing_v1/pilot/paired_plan.json
