"""Run one simulation and expose its latest state to the native GUI."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from ..config import load_config
from ..simulation import Simulation
from .eco_shm_bridge import SharedFramePublisher, attach_realtime_publisher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a Subject Evolution simulation for the native GUI."
    )
    parser.add_argument("--config", required=True, help="Path to a JSON configuration file")
    parser.add_argument("--output", required=True, help="Directory for simulation results")
    parser.add_argument(
        "--backend",
        choices=("cpu", "gpu", "auto"),
        default="cpu",
        help="Simulation backend",
    )
    parser.add_argument(
        "--stream",
        required=True,
        help="Shared-memory frame file consumed by the native GUI",
    )
    parser.add_argument(
        "--publish-every",
        type=int,
        default=2,
        help="Publish one frame every N simulation ticks",
    )
    return parser


def run(
    config_path: str | Path,
    output: str | Path,
    stream: str | Path,
    *,
    backend: str = "cpu",
    publish_every: int = 2,
) -> None:
    """Run a configured simulation while publishing post-step snapshots."""
    config_path = Path(config_path)
    output = Path(output)
    stream = Path(stream)
    output.mkdir(parents=True, exist_ok=True)

    cfg = load_config(config_path)
    (output / "config.json").write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    simulation = Simulation(cfg, output, backend=backend)
    publisher = SharedFramePublisher.from_simulation(
        simulation,
        path=stream,
        every_ticks=publish_every,
    )
    detach = attach_realtime_publisher(simulation, publisher, publish_initial=True)
    try:
        simulation.run()
    finally:
        detach()
        publisher.close()


def main() -> None:
    args = build_parser().parse_args()
    run(
        args.config,
        args.output,
        args.stream,
        backend=args.backend,
        publish_every=args.publish_every,
    )


if __name__ == "__main__":
    main()
