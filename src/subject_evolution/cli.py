from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from .config import load_config
from .simulation import Simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the nested-subject evolution MVP")
    parser.add_argument("--config", required=True, help="Path to a JSON configuration file")
    parser.add_argument("--output", required=True, help="Output directory")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config_path = Path(args.config)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, output / "config.json")
    cfg = load_config(config_path)
    simulation = Simulation(cfg, output)
    simulation.run()


if __name__ == "__main__":
    main()
