#!/usr/bin/env bash
set -euo pipefail
se-multi \
  --config studies/d1e_persistent_multiscale_resources_v1/protocol/source_pilot.json \
  --seeds 84001,84002,84003 \
  --output runs/base/d1e_persistent_multiscale_resources_v1/pilot \
  --backend auto \
  --until-tick 480 \
  --checkpoint-ticks 480 \
  --skip-post-run-audits
