#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m se --config configs/mvp_100k.json --output runs/mvp_100k_gpu --backend gpu
