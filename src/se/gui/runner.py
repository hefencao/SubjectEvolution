"""Run an authoritative simulation while publishing frames to a native GUI."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path

from ..cfg import load_config
from ..runtime.sim import Simulation
from .attachment import realtime_publisher_session
from .publisher import SharedFramePublisher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Subject Evolution with a one-way native GUI frame stream."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", help="Path to a JSON configuration file")
    source.add_argument(
        "--resume-checkpoint",
        help="Trusted project-generated .sechk checkpoint to resume.",
    )
    parser.add_argument("--output", required=True, help="Simulation output directory")
    parser.add_argument("--stream", required=True, help="Shared frame mmap file")
    parser.add_argument(
        "--manifest",
        help="Protocol sidecar path; defaults to <stream>.json",
    )
    parser.add_argument(
        "--backend", choices=("cpu", "gpu", "auto"), default="cpu"
    )
    parser.add_argument(
        "--gpu-semantics-mode",
        choices=("strict-reference", "hybrid-accelerated"),
    )
    parser.add_argument("--until-tick", type=int, help="Absolute final tick")
    parser.add_argument(
        "--publish-every",
        type=int,
        default=2,
        help="Publish one latest-only frame every N simulation ticks",
    )
    parser.add_argument(
        "--no-publish-initial",
        action="store_true",
        help="Do not publish tick 0/current checkpoint state before stepping",
    )
    return parser


def _create_simulation(
    *,
    config_path: str | Path | None,
    resume_checkpoint: str | Path | None,
    output: Path,
    backend: str,
    until_tick: int | None,
    gpu_semantics_mode: str | None,
) -> Simulation:
    if until_tick is not None and until_tick < 0:
        raise ValueError("until_tick must be non-negative")
    if resume_checkpoint is not None:
        return Simulation.from_checkpoint(
            resume_checkpoint,
            output,
            backend=backend,
            until_tick=until_tick,
            gpu_semantics_mode=gpu_semantics_mode,
        )
    if config_path is None:
        raise ValueError("config_path is required when not resuming")
    cfg = load_config(config_path)
    overrides: dict[str, object] = {}
    if until_tick is not None:
        overrides["ticks"] = int(until_tick)
    if gpu_semantics_mode is not None:
        overrides["gpu_semantics_mode"] = gpu_semantics_mode
    if overrides:
        cfg = replace(cfg, run=replace(cfg.run, **overrides))
    return Simulation(cfg, output, backend=backend)


def run(
    *,
    output: str | Path,
    stream: str | Path,
    config_path: str | Path | None = None,
    resume_checkpoint: str | Path | None = None,
    manifest_path: str | Path | None = None,
    backend: str = "cpu",
    gpu_semantics_mode: str | None = None,
    until_tick: int | None = None,
    publish_every: int = 2,
    publish_initial: bool = True,
) -> dict[str, float | int]:
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    simulation = _create_simulation(
        config_path=config_path,
        resume_checkpoint=resume_checkpoint,
        output=output_path,
        backend=backend,
        until_tick=until_tick,
        gpu_semantics_mode=gpu_semantics_mode,
    )
    resolved = json.dumps(asdict(simulation.cfg), ensure_ascii=False, indent=2)
    (output_path / "config.json").write_text(resolved, encoding="utf-8")
    (output_path / "resolved_config.json").write_text(resolved, encoding="utf-8")

    publisher = SharedFramePublisher.from_simulation(
        simulation,
        path=stream,
        every_ticks=publish_every,
        manifest_path=manifest_path,
    )
    with realtime_publisher_session(
        simulation, publisher, publish_initial=publish_initial
    ):
        return simulation.run(until_tick=until_tick)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(
            output=args.output,
            stream=args.stream,
            config_path=args.config,
            resume_checkpoint=args.resume_checkpoint,
            manifest_path=args.manifest,
            backend=args.backend,
            gpu_semantics_mode=args.gpu_semantics_mode,
            until_tick=args.until_tick,
            publish_every=args.publish_every,
            publish_initial=not args.no_publish_initial,
        )
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()


__all__ = ["build_parser", "main", "run"]
