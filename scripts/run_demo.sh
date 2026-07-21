#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python -m subject_evolution.cli --config configs/mvp_small.json --output runs/demo
