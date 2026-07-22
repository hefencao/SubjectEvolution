from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from .config import load_config
from .counterfactual import run_paired
from .simulation import Simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the nested-subject evolution MVP")
    parser.add_argument("--config", required=True, help="Path to a JSON configuration file")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument(
        "--backend",
        choices=("cpu", "gpu", "auto"),
        default="cpu",
        help="Execution backend. GPU accelerates fields, observations and policy batches; default: cpu.",
    )
    parser.add_argument(
        "--counterfactual",
        help=(
            "Run a paired branch from the same snapshot. Choices: "
            "disable-social-control, cut-social-connections, shuffle-memory, "
            "freeze-genotype, reverse-environment."
        ),
    )
    parser.add_argument(
        "--intervention-tick",
        type=int,
        help=(
            "Absolute tick at which a paired intervention is applied after a shared "
            "prehistory. Defaults to 0."
        ),
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.intervention_tick is not None and not args.counterfactual:
        parser.error("--intervention-tick requires --counterfactual")
    config_path = Path(args.config)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_path, output / "config.json")
    cfg = load_config(config_path)
    if args.counterfactual:
        simulation = Simulation(cfg, output / "baseline", backend=args.backend)
        run_paired(
            simulation,
            args.counterfactual,
            output,
            intervention_tick=args.intervention_tick,
        )
    else:
        simulation = Simulation(cfg, output, backend=args.backend)
        simulation.run()


if __name__ == "__main__":
    main()
