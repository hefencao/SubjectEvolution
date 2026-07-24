from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

from .config import load_config
from .counterfactual import run_paired
from .interventions import ExperimentMode, intervention_names
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
            "Run a paired branch from the same snapshot. Scientific choices: "
            + ", ".join(intervention_names(mode=ExperimentMode.SCIENTIFIC))
            + ". independent-foraging-override is entertainment-only."
        ),
    )
    parser.add_argument(
        "--experiment-mode",
        choices=tuple(mode.value for mode in ExperimentMode),
        help=(
            "Override run.experiment_mode. Scientific mode rejects direct action "
            "replacement; entertainment mode permits it and labels the output."
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
    parser.add_argument(
        "--shared-intervention",
        help=(
            "Apply one intervention to the still-shared history before branching; "
            "for example cut-social-connections before an entertainment override."
        ),
    )
    parser.add_argument(
        "--shared-intervention-tick",
        type=int,
        help="Absolute tick for --shared-intervention. Defaults to the current tick.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.intervention_tick is not None and not args.counterfactual:
        parser.error("--intervention-tick requires --counterfactual")
    if args.shared_intervention is not None and not args.counterfactual:
        parser.error("--shared-intervention requires --counterfactual")
    if args.shared_intervention_tick is not None and args.shared_intervention is None:
        parser.error("--shared-intervention-tick requires --shared-intervention")
    config_path = Path(args.config)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    cfg = load_config(config_path)
    if args.experiment_mode is not None:
        cfg = replace(cfg, run=replace(cfg.run, experiment_mode=args.experiment_mode))
    resolved = json.dumps(asdict(cfg), ensure_ascii=False, indent=2)
    (output / "config.json").write_text(resolved, encoding="utf-8")
    (output / "resolved_config.json").write_text(resolved, encoding="utf-8")
    if args.counterfactual:
        simulation = Simulation(cfg, output / "baseline", backend=args.backend)
        run_paired(
            simulation,
            args.counterfactual,
            output,
            intervention_tick=args.intervention_tick,
            shared_intervention=args.shared_intervention,
            shared_intervention_tick=args.shared_intervention_tick,
        )
    else:
        simulation = Simulation(cfg, output, backend=args.backend)
        simulation.run()


if __name__ == "__main__":
    main()
