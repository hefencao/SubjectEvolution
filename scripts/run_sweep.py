#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from subject_evolution.config import load_config  # noqa: E402
from subject_evolution.simulation import Simulation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small noise/temperature experiment sweep")
    parser.add_argument("--base", default=str(ROOT / "configs" / "mvp_small.json"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--ticks", type=int, default=200)
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()

    base_raw = json.loads(Path(args.base).read_text(encoding="utf-8"))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    conditions = [
        ("low_noise_low_temp", 0.05, 0.04, 0.5),
        ("base", 0.15, 0.10, 0.8),
        ("high_noise_high_temp", 0.35, 0.25, 1.3),
    ]
    rows: list[dict[str, object]] = []
    for condition, loss, noise, temperature in conditions:
        for seed_offset in range(args.seeds):
            raw = copy.deepcopy(base_raw)
            raw["run"]["seed"] = int(base_raw["run"]["seed"]) + seed_offset
            raw["run"]["ticks"] = args.ticks
            raw["run"]["metrics_period"] = max(1, args.ticks)
            raw["run"]["checkpoint_period"] = args.ticks + 1
            raw["information"]["channel_loss"] = loss
            raw["information"]["receiver_noise"] = noise
            raw["policy"]["temperature"] = temperature
            run_dir = output / condition / f"seed_{raw['run']['seed']}"
            run_dir.mkdir(parents=True, exist_ok=True)
            cfg_path = run_dir / "config.json"
            cfg_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            final = Simulation(load_config(cfg_path), run_dir).run()
            rows.append({"condition": condition, "seed": raw["run"]["seed"], **final})

    if rows:
        with (output / "sweep_summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
