"""Offline continuation and paired counterfactual replay from full checkpoints."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from se.experiments.counterfactual import run_paired
from se.experiments.interventions import ExperimentMode, intervention_names
from ..runtime.sim import Simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resume or branch from a trusted SubjectEvolution .sechk checkpoint"
    )
    parser.add_argument("--checkpoint", required=True, help="Trusted .sechk checkpoint")
    parser.add_argument("--output", required=True, help="Replay output directory")
    parser.add_argument("--until-tick", type=int, required=True, help="Absolute final tick")
    parser.add_argument(
        "--backend", choices=("cpu", "gpu", "auto"), default="auto"
    )
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    parser.add_argument(
        "--intervention",
        help=(
            "Create a paired baseline/intervention replay. Scientific choices: "
            + ", ".join(intervention_names(mode=ExperimentMode.SCIENTIFIC))
        ),
    )
    parser.add_argument(
        "--intervention-tick",
        type=int,
        help="Absolute branch tick; defaults to the checkpoint tick.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    simulation_output = root / "baseline" if args.intervention else root
    simulation = Simulation.from_checkpoint(
        args.checkpoint,
        simulation_output,
        backend=args.backend,
        until_tick=args.until_tick,
        gpu_semantics_mode=args.gpu_semantics_mode,
    )
    resolved = json.dumps(asdict(simulation.cfg), ensure_ascii=False, indent=2)
    (root / "resolved_config.json").write_text(resolved, encoding="utf-8")
    if args.intervention:
        run_paired(
            simulation,
            args.intervention,
            root,
            intervention_tick=args.intervention_tick,
        )
    else:
        simulation.run(until_tick=args.until_tick)


if __name__ == "__main__":
    main()
