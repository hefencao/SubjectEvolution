from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

from ..cfg import load_config
from se.experiments.counterfactual import run_paired
from se.experiments.interventions import ExperimentMode, intervention_names
from ..runtime.sim import Simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the nested-subject evolution MVP")
    parser.add_argument("--config", help="Path to a JSON configuration file")
    parser.add_argument(
        "--resume-checkpoint",
        help=(
            "Resume or branch from a trusted project-generated .sechk full-world "
            "checkpoint. Do not load untrusted checkpoint files."
        ),
    )
    parser.add_argument("--seed", type=int, help="Override run.seed for a config-based run.")
    parser.add_argument(
        "--checkpoint-ticks",
        help="Comma-separated exact ticks at which full .sechk checkpoints are written.",
    )
    parser.add_argument(
        "--until-tick",
        type=int,
        help="Absolute final tick for a normal or resumed run.",
    )
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument(
        "--backend",
        choices=("cpu", "gpu", "auto"),
        default="auto",
        help=(
            "Execution backend. auto (default) uses the hybrid GPU path when "
            "CuPy/CUDA is available and records a CPU fallback otherwise."
        ),
    )
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
        help=(
            "Override run.gpu_semantics_mode. hybrid-accelerated is the production "
            "default; strict-reference retains the historical CPU-authoritative "
            "diagnostic path."
        ),
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
    if bool(args.config) == bool(args.resume_checkpoint):
        parser.error("provide exactly one of --config or --resume-checkpoint")
    if args.resume_checkpoint and args.experiment_mode is not None:
        parser.error("--experiment-mode cannot change a restored world")
    if args.resume_checkpoint and args.seed is not None:
        parser.error("--seed cannot change a restored world")

    checkpoint_ticks: tuple[int, ...] | None = None
    if args.checkpoint_ticks:
        try:
            checkpoint_ticks = tuple(
                sorted(
                    set(
                        int(item.strip())
                        for item in args.checkpoint_ticks.split(",")
                        if item.strip()
                    )
                )
            )
        except ValueError as exc:
            parser.error(f"invalid --checkpoint-ticks: {exc}")
        if not checkpoint_ticks or checkpoint_ticks[0] < 0:
            parser.error("--checkpoint-ticks must contain non-negative integers")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    if args.resume_checkpoint:
        simulation_output = output / "baseline" if args.counterfactual else output
        simulation = Simulation.from_checkpoint(
            args.resume_checkpoint,
            simulation_output,
            backend=args.backend,
            until_tick=args.until_tick,
            gpu_semantics_mode=args.gpu_semantics_mode,
            checkpoint_ticks=checkpoint_ticks,
        )
        cfg = simulation.cfg
    else:
        config_path = Path(args.config)
        cfg = load_config(config_path)
        run_overrides = {}
        if args.seed is not None:
            run_overrides["seed"] = int(args.seed)
        if args.experiment_mode is not None:
            run_overrides["experiment_mode"] = args.experiment_mode
        if args.gpu_semantics_mode is not None:
            run_overrides["gpu_semantics_mode"] = args.gpu_semantics_mode
        if checkpoint_ticks is not None:
            run_overrides["checkpoint_ticks"] = checkpoint_ticks
            run_overrides["full_checkpoint_enabled"] = True
        if args.until_tick is not None:
            if args.until_tick < 0:
                parser.error("--until-tick must be non-negative")
            run_overrides["ticks"] = args.until_tick
        target_tick = int(run_overrides.get("ticks", cfg.run.ticks))
        if checkpoint_ticks and checkpoint_ticks[-1] > target_tick:
            parser.error(
                f"--checkpoint-ticks includes {checkpoint_ticks[-1]} beyond final tick {target_tick}"
            )
        if run_overrides:
            cfg = replace(cfg, run=replace(cfg.run, **run_overrides))
        simulation_output = output / "baseline" if args.counterfactual else output
        simulation = Simulation(cfg, simulation_output, backend=args.backend)

    resolved = json.dumps(asdict(cfg), ensure_ascii=False, indent=2)
    (output / "config.json").write_text(resolved, encoding="utf-8")
    (output / "resolved_config.json").write_text(resolved, encoding="utf-8")
    if args.counterfactual:
        run_paired(
            simulation,
            args.counterfactual,
            output,
            intervention_tick=args.intervention_tick,
            shared_intervention=args.shared_intervention,
            shared_intervention_tick=args.shared_intervention_tick,
        )
    else:
        simulation.run(until_tick=args.until_tick)


if __name__ == "__main__":
    main()
