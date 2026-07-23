"""Example launcher for an importable single-file subject_evolution module."""

from __future__ import annotations

import argparse
from pathlib import Path

import subject_evolution as evolution

from .eco_shm_bridge import (
    SharedFramePublisher,
    attach_realtime_publisher,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--backend",
        choices=("cpu", "gpu", "auto"),
        default="cpu",
    )
    parser.add_argument(
        "--stream",
        default=str(
            Path(__file__).with_name("eco_live.bin")
        ),
    )
    parser.add_argument(
        "--publish-every",
        type=int,
        default=2,
    )
    args = parser.parse_args()

    cfg = evolution.load_config(args.config)
    simulation = evolution.Simulation(
        cfg,
        args.output,
        backend=args.backend,
    )

    publisher = SharedFramePublisher.from_simulation(
        simulation,
        path=args.stream,
        every_ticks=args.publish_every,
    )
    detach = attach_realtime_publisher(
        simulation,
        publisher,
    )

    try:
        simulation.run()
    finally:
        detach()
        publisher.close()


if __name__ == "__main__":
    main()
