#!/usr/bin/env bash
set -euo pipefail
se-multi \
  --config studies/d1d_inherited_resource_sensing_v1/protocol/source_pilot.json \
  --seeds 83001,83002,83003 \
  --output runs/base/d1d_inherited_resource_sensing_v1/pilot \
  --backend auto \
  --until-tick 480 \
  --checkpoint-ticks 480 \
  --skip-post-run-audits
