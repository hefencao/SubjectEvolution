#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m subject_evolution.cli --config configs/mvp_100k.json --output runs/mvp_100k_gpu --backend gpu
